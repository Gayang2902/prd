"""Tests for hunting activity functions."""

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio import activity

from app.workflows.hunting_activities import (
    PHASE_PROMPTS,
    SKILL_BY_TYPE,
    _extract_tool_calls,
    _fingerprint,
    run_hunting_phase,
    save_hunting_findings,
)


@pytest.fixture(autouse=True)
def _mock_activity_ctx():
    """Provide a fake Temporal activity context so heartbeat/logger work."""
    with patch.object(activity, "heartbeat"), patch.object(activity, "logger", MagicMock()):
        yield


async def _async_lines(lines: list[bytes]) -> AsyncIterator[bytes]:
    for line in lines:
        yield line


def _mock_proc(
    stdout_lines: list[bytes],
    stderr: bytes = b"",
    returncode: int = 0,
) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.wait = AsyncMock()
    proc.stdout = _async_lines(stdout_lines)
    mock_stderr = MagicMock()
    mock_stderr.read = AsyncMock(return_value=stderr)
    proc.stderr = mock_stderr
    return proc


def _skill_dir_patch(exists: bool = False, content: str = "") -> MagicMock:
    mock_dir = MagicMock()
    mock_skill_path = MagicMock()
    mock_skill_path.exists.return_value = exists
    if exists:
        mock_skill_path.read_text.return_value = content
    mock_dir.__truediv__ = MagicMock(
        return_value=MagicMock(__truediv__=MagicMock(return_value=mock_skill_path))
    )
    return mock_dir


# ── run_hunting_phase (stream-json) ──


@pytest.mark.asyncio
async def test_run_hunting_phase_success():
    result_json = '{"phase": "gathering", "status": "done", "results": []}'
    assistant_msg = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "ok"}]},
    }
    result_msg = {
        "type": "result",
        "result": result_json,
        "cost_usd": 0.1,
        "duration_ms": 5000,
        "num_turns": 1,
    }
    lines = [
        json.dumps({"type": "system", "subtype": "init"}).encode() + b"\n",
        json.dumps(assistant_msg).encode() + b"\n",
        json.dumps(result_msg).encode() + b"\n",
    ]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ),
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch(True, "# Skill")),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {"keyword": "parser"}, "/tmp/work"
        )

    assert result["phase"] == "gathering"
    assert result["status"] == "done"
    assert "_trace" in result
    assert result["_trace"]["num_turns"] == 1
    assert result["_trace"]["cost_usd"] == 0.1


@pytest.mark.asyncio
async def test_run_hunting_phase_cli_not_found():
    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError,
        ),
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    assert result["status"] == "failed"
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_run_hunting_phase_nonzero_exit():
    proc = _mock_proc([], stderr=b"auth error", returncode=1)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ),
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    assert result["status"] == "failed"
    assert "auth error" in result["error"]


@pytest.mark.asyncio
async def test_run_hunting_phase_invalid_json():
    lines = [
        json.dumps({"type": "result", "result": "not json at all"}).encode() + b"\n",
    ]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ),
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    assert result["status"] == "done"
    assert "raw" in result


@pytest.mark.asyncio
async def test_run_hunting_phase_with_previous_results():
    result_json = '{"phase": "filtering", "status": "done", "results": []}'
    lines = [
        json.dumps({"type": "result", "result": result_json}).encode() + b"\n",
    ]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec,
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        result = await run_hunting_phase(
            uuid.uuid4(),
            "target_discovery",
            "filtering",
            {"previous_results": {"gathering": {"results": [{"name": "lib"}]}}},
            "/tmp/work",
        )

    assert result["phase"] == "filtering"
    prompt_arg = mock_exec.call_args[0][2]
    assert "이전 페이즈 결과" in prompt_arg


@pytest.mark.asyncio
async def test_run_hunting_phase_includes_skill():
    result_json = '{"phase": "gathering", "status": "done", "results": []}'
    lines = [
        json.dumps({"type": "result", "result": result_json}).encode() + b"\n",
    ]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec,
        patch(
            "app.workflows.hunting_activities.SKILLS_DIR",
            _skill_dir_patch(True, "# Target Discovery Skill"),
        ),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        await run_hunting_phase(uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work")

    prompt_arg = mock_exec.call_args[0][2]
    assert "<skill>" in prompt_arg
    assert "Target Discovery Skill" in prompt_arg


@pytest.mark.asyncio
async def test_run_hunting_phase_broadcasts_events():
    result_json = '{"phase": "gathering", "status": "done"}'
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Reading file"},
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "x.c"}},
                    ]
                },
            }
        ).encode()
        + b"\n",
        json.dumps(
            {
                "type": "result",
                "result": result_json,
                "cost_usd": 0.05,
                "num_turns": 1,
            }
        ).encode()
        + b"\n",
    ]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ),
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock) as mock_bcast,
    ):
        result = await run_hunting_phase(
            uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work"
        )

    events = [call.args[1] for call in mock_bcast.call_args_list]
    event_types = [e["event"] for e in events]
    assert "phase_start" in event_types
    assert "turn" in event_types
    assert "phase_done" in event_types

    turn_event = next(e for e in events if e["event"] == "turn")
    assert "Read" in turn_event["tool_calls"]

    assert result["_trace"]["tool_calls_count"] == 1


@pytest.mark.asyncio
async def test_run_hunting_phase_stream_json_format():
    """Verify --output-format stream-json is used."""
    result_json = '{"phase": "gathering", "status": "done"}'
    lines = [json.dumps({"type": "result", "result": result_json}).encode() + b"\n"]
    proc = _mock_proc(lines)

    with (
        patch(
            "app.workflows.hunting_activities.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec,
        patch("app.workflows.hunting_activities.SKILLS_DIR", _skill_dir_patch()),
        patch("app.workflows.hunting_activities._broadcast", new_callable=AsyncMock),
    ):
        await run_hunting_phase(uuid.uuid4(), "target_discovery", "gathering", {}, "/tmp/work")

    cmd_args = mock_exec.call_args[0]
    assert "--output-format" in cmd_args
    fmt_idx = list(cmd_args).index("--output-format")
    assert cmd_args[fmt_idx + 1] == "stream-json"
    assert "--verbose" in cmd_args
    assert "--append-system-prompt" in cmd_args


# ── _extract_tool_calls ──


def test_extract_tool_calls():
    msg = {
        "content": [
            {"type": "text", "text": "Let me read"},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "a.c"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
        ]
    }
    tools = _extract_tool_calls(msg)
    assert len(tools) == 2
    assert tools[0]["tool"] == "Read"
    assert tools[1]["tool"] == "Bash"


def test_extract_tool_calls_no_tools():
    msg = {"content": [{"type": "text", "text": "Just text"}]}
    assert _extract_tool_calls(msg) == []


def test_extract_tool_calls_empty():
    assert _extract_tool_calls({}) == []
    assert _extract_tool_calls({"content": "not a list"}) == []


# ── save_hunting_findings ──


@pytest.mark.asyncio
async def test_save_target_discovery_findings():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
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
    mock_session.add = MagicMock()
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
    mock_session.add = MagicMock()
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
    mock_session.add = MagicMock()
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
    mock_session.add = MagicMock()
    mock_analysis = MagicMock()
    mock_analysis.phase_data = {}
    mock_session.get = AsyncMock(return_value=mock_analysis)

    @asynccontextmanager
    async def mock_factory():
        yield mock_session

    phase_results = {"complete": {"results": ["not_a_dict", 42, None]}}

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
