"""Tests for hunting activity functions."""

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.hunting_activities import (
    CLAUDE_CODE_AGENT_ID,
    PHASE_PROMPTS,
    SKILL_BY_TYPE,
    _fingerprint,
    _run_via_claude_code,
    run_hunting_phase,
    save_hunting_findings,
)


# ── run_hunting_phase ──


@pytest.mark.asyncio
async def test_run_hunting_phase_success():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"phase": "gathering", "status": "done", "results": []}')]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.workflows.hunting_activities.AsyncAnthropic", return_value=mock_client), \
         patch("app.workflows.hunting_activities.SKILLS_DIR") as mock_dir:
        mock_skill_path = MagicMock()
        mock_skill_path.exists.return_value = True
        mock_skill_path.read_text.return_value = "# Skill content"
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path)))

        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {"keyword": "parser"}, "/tmp/work"
        )

    assert result["phase"] == "gathering"
    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_run_hunting_phase_api_error():
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("app.workflows.hunting_activities.AsyncAnthropic", return_value=mock_client), \
         patch("app.workflows.hunting_activities.SKILLS_DIR") as mock_dir:
        mock_skill_path = MagicMock()
        mock_skill_path.exists.return_value = False
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path)))

        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    assert result["status"] == "failed"
    assert "API down" in result["error"]


@pytest.mark.asyncio
async def test_run_hunting_phase_invalid_json():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is not valid JSON")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.workflows.hunting_activities.AsyncAnthropic", return_value=mock_client), \
         patch("app.workflows.hunting_activities.SKILLS_DIR") as mock_dir:
        mock_skill_path = MagicMock()
        mock_skill_path.exists.return_value = False
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path)))

        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    assert result["status"] == "done"
    assert "raw" in result


@pytest.mark.asyncio
async def test_run_hunting_phase_with_previous_results():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"phase": "filtering", "status": "done", "results": []}')]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.workflows.hunting_activities.AsyncAnthropic", return_value=mock_client), \
         patch("app.workflows.hunting_activities.SKILLS_DIR") as mock_dir:
        mock_skill_path = MagicMock()
        mock_skill_path.exists.return_value = False
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path)))

        result = await run_hunting_phase(
            uuid.uuid4(),
            "target_discovery",
            "filtering",
            {"previous_results": {"gathering": {"results": [{"name": "lib"}]}}},
            "/tmp/work",
        )

    assert result["phase"] == "filtering"
    call_args = mock_client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "previous_results" in user_msg


# ── save_hunting_findings ──


@pytest.mark.asyncio
async def test_save_target_discovery_findings():
    mock_session = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    phase_results = {
        "complete": {
            "results": [
                {"name": "vuln-lib", "repo": "vuln/lib", "crackability_score": 8.5},
                {"name": "safe-lib", "repo": "safe/lib", "crackability_score": 3.0},
            ]
        }
    }

    with patch("app.core.database.async_session_factory", mock_factory):
        count = await save_hunting_findings(uuid.uuid4(), "target_discovery", phase_results)

    assert count == 2
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_zero_day_findings():
    mock_session = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    phase_results = {
        "triage": {
            "results": [
                {"title": "buffer-overflow", "file_path": "src/parse.c", "severity": "critical"},
            ]
        },
        "code_reading": {
            "results": [
                {"title": "use-after-free", "file_path": "src/alloc.c", "severity": "high"},
            ]
        },
    }

    with patch("app.core.database.async_session_factory", mock_factory):
        count = await save_hunting_findings(uuid.uuid4(), "zero_day_hunting", phase_results)

    assert count == 2
    assert mock_session.add.call_count == 2


@pytest.mark.asyncio
async def test_save_findings_invalid_severity():
    mock_session = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    phase_results = {
        "triage": {
            "results": [
                {"title": "edge-case", "file_path": "x.c", "severity": "unknown_sev"},
            ]
        }
    }

    with patch("app.core.database.async_session_factory", mock_factory):
        count = await save_hunting_findings(uuid.uuid4(), "zero_day_hunting", phase_results)

    assert count == 1


@pytest.mark.asyncio
async def test_save_findings_empty_results():
    mock_session = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    with patch("app.core.database.async_session_factory", mock_factory):
        count = await save_hunting_findings(uuid.uuid4(), "target_discovery", {})

    assert count == 0


@pytest.mark.asyncio
async def test_save_findings_non_dict_items():
    mock_session = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    phase_results = {
        "complete": {"results": ["not_a_dict", 42, None]}
    }

    with patch("app.core.database.async_session_factory", mock_factory):
        count = await save_hunting_findings(uuid.uuid4(), "target_discovery", phase_results)

    assert count == 0


# ── helpers ──


def test_fingerprint_deterministic():
    assert _fingerprint("hello") == _fingerprint("hello")
    assert _fingerprint("a") != _fingerprint("b")
    assert len(_fingerprint("test")) == 64


def test_phase_prompts_coverage():
    for stype in ("target_discovery", "zero_day_hunting"):
        assert stype in PHASE_PROMPTS
        assert len(PHASE_PROMPTS[stype]) > 0


def test_skill_mapping():
    assert SKILL_BY_TYPE["target_discovery"] == "opentarget"
    assert SKILL_BY_TYPE["zero_day_hunting"] == "openresearch"


# ── agent routing ──


@pytest.mark.asyncio
async def test_run_hunting_phase_routes_to_api_by_default():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"phase": "gathering", "status": "done"}')]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.workflows.hunting_activities.AsyncAnthropic", return_value=mock_client), \
         patch("app.workflows.hunting_activities.SKILLS_DIR") as mock_dir:
        mock_skill_path = MagicMock()
        mock_skill_path.exists.return_value = False
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path)))

        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp", None
        )

    assert result["status"] == "done"
    mock_client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_hunting_phase_routes_to_claude_code():
    output = json.dumps({"result": '{"phase": "gathering", "status": "done", "results": []}'})
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(output.encode(), b""))
    mock_proc.returncode = 0

    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp", CLAUDE_CODE_AGENT_ID
        )

    assert result["status"] == "done"


# ── _run_via_claude_code ──


@pytest.mark.asyncio
async def test_claude_code_success():
    output = json.dumps({"result": '{"phase": "fuzzing", "status": "done", "results": [{"title": "crash"}]}'})
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(output.encode(), b""))
    mock_proc.returncode = 0

    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await _run_via_claude_code(
            uuid.uuid4(), "zero_day_hunting", "fuzzing", {}, "/tmp"
        )

    assert result["status"] == "done"
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_claude_code_not_found():
    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result = await _run_via_claude_code(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp"
        )

    assert result["status"] == "failed"
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_claude_code_nonzero_exit():
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"auth error"))
    mock_proc.returncode = 1

    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await _run_via_claude_code(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp"
        )

    assert result["status"] == "failed"
    assert "auth error" in result["error"]


@pytest.mark.asyncio
async def test_claude_code_invalid_json_output():
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"not json at all", b""))
    mock_proc.returncode = 0

    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await _run_via_claude_code(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp"
        )

    assert result["status"] == "done"
    assert "raw" in result


@pytest.mark.asyncio
async def test_claude_code_with_previous_results():
    output = json.dumps({"result": '{"phase": "filtering", "status": "done", "results": []}'})
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(output.encode(), b""))
    mock_proc.returncode = 0

    with patch("app.workflows.hunting_activities.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        result = await _run_via_claude_code(
            uuid.uuid4(), "target_discovery", "filtering",
            {"previous_results": {"gathering": {"results": []}}},
            "/tmp",
        )

    assert result["status"] == "done"
    prompt_arg = mock_exec.call_args[0][2]
    assert "이전 페이즈 결과" in prompt_arg
