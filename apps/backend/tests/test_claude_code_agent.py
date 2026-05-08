"""Tests for ClaudeCodeAgent and helper functions."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from securescope_schemas.agent_interface import (
    AnalysisContext,
    AnalysisResult,
    CodeScope,
    LogEvent,
    PresetConfig,
    ResourceLimits,
    Severity,
)

from app.agents.claude_code_agent import (
    ClaudeCodeAgent,
    _get_phase_instruction,
    _parse_findings,
    _safe_json,
)


# ── _get_phase_instruction ──


def test_phase_instruction_all():
    result = _get_phase_instruction("target_discovery", "all")
    assert "full analysis pipeline" in result


def test_phase_instruction_specific():
    result = _get_phase_instruction("target_discovery", "gathering")
    assert "Phase 1" in result


def test_phase_instruction_zero_day():
    result = _get_phase_instruction("zero_day_hunting", "fuzzing")
    assert "Fuzz" in result


def test_phase_instruction_unknown():
    result = _get_phase_instruction("target_discovery", "nonexistent")
    assert "nonexistent" in result


# ── _parse_findings ──


def test_parse_findings_json_block():
    text = '```json\n{"findings": [{"title": "XSS", "file_path": "a.js", "severity": "high"}]}\n```'
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH


def test_parse_findings_raw_json():
    text = json.dumps({"findings": [{"title": "SQLi", "file_path": "b.py", "severity": "critical"}]})
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL


def test_parse_findings_with_results_key():
    text = json.dumps({"results": [{"title": "Bug", "file_path": "c.c", "severity": "low"}]})
    findings = _parse_findings(text)
    assert len(findings) == 1


def test_parse_findings_embedded():
    text = 'Some text before\n{"findings": [{"title": "UAF", "file_path": "d.c", "severity": "medium"}]}\nafter'
    findings = _parse_findings(text)
    assert len(findings) == 1


def test_parse_findings_invalid():
    assert _parse_findings("not json at all") == []


def test_parse_findings_dedup():
    text = json.dumps({"findings": [
        {"title": "A", "file_path": "x.c", "line_start": 1, "severity": "low"},
        {"title": "A", "file_path": "x.c", "line_start": 1, "severity": "low"},
    ]})
    assert len(_parse_findings(text)) == 1


def test_parse_findings_non_dict_items():
    text = json.dumps({"findings": ["str", 42, None]})
    assert _parse_findings(text) == []


def test_parse_findings_non_list():
    text = json.dumps({"findings": "not a list"})
    assert _parse_findings(text) == []


def test_parse_findings_fingerprint_dedup():
    text = json.dumps({"findings": [
        {"title": "A", "file_path": "a.c", "fingerprint": "fp1", "severity": "low"},
        {"title": "B", "file_path": "b.c", "fingerprint": "fp1", "severity": "high"},
    ]})
    assert len(_parse_findings(text)) == 1


# ── _safe_json ──


def test_safe_json_valid():
    assert _safe_json('{"key": "val"}') == {"key": "val"}


def test_safe_json_invalid():
    assert _safe_json("not json") == {}


# ── ClaudeCodeAgent.describe ──


def test_describe():
    meta = ClaudeCodeAgent.describe()
    assert meta.name == "claude-code"
    assert meta.version == "1.0.0"
    assert "python" in meta.supported_languages


# ── ClaudeCodeAgent.prepare ──


@pytest.mark.asyncio
async def test_prepare():
    agent = ClaudeCodeAgent()
    ctx = AnalysisContext(
        session_id=uuid.uuid4(),
        scope=CodeScope(repo_path="/tmp/repo", commit_sha="abc123"),
        preset=PresetConfig(
            id=uuid.uuid4(), version_sha="v1",
            prompt_template="hunting", ruleset={},
        ),
        limits=ResourceLimits(),
    )
    await agent.prepare(ctx)
    assert agent._repo_path == "/tmp/repo"
    assert agent._commit_sha == "abc123"


# ── ClaudeCodeAgent.terminate ──


@pytest.mark.asyncio
async def test_terminate():
    agent = ClaudeCodeAgent()
    await agent.terminate()


# ── ClaudeCodeAgent.analyze — success ──


@pytest.mark.asyncio
async def test_analyze_success():
    agent = ClaudeCodeAgent()
    agent._repo_path = "/tmp"
    agent._commit_sha = "HEAD"

    output = json.dumps({
        "result": json.dumps({
            "findings": [{"title": "vuln", "file_path": "x.c", "severity": "high"}]
        }),
        "cost_usd": 0.5,
    })

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(output.encode(), b""))
    mock_proc.returncode = 0

    with patch("app.agents.claude_code_agent.asyncio.create_subprocess_exec", return_value=mock_proc):
        ctx = AnalysisContext(
            session_id=uuid.uuid4(),
            scope=CodeScope(repo_path="/tmp", commit_sha="HEAD"),
            preset=PresetConfig(
                id=uuid.uuid4(), version_sha="v1",
                prompt_template="hunting",
                ruleset={"skill": "opentarget", "session_type": "target_discovery", "phase": "gathering"},
            ),
            limits=ResourceLimits(),
        )
        events = []
        async for item in agent.analyze(ctx):
            events.append(item)

    results = [e for e in events if isinstance(e, AnalysisResult)]
    assert len(results) == 1
    assert len(results[0].findings) == 1
    assert results[0].cost_usd == 0.5


# ── ClaudeCodeAgent.analyze — process error ──


@pytest.mark.asyncio
async def test_analyze_process_error():
    agent = ClaudeCodeAgent()
    agent._repo_path = "/tmp"
    agent._commit_sha = "HEAD"

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Error occurred"))
    mock_proc.returncode = 1

    with patch("app.agents.claude_code_agent.asyncio.create_subprocess_exec", return_value=mock_proc):
        ctx = AnalysisContext(
            session_id=uuid.uuid4(),
            scope=CodeScope(repo_path="/tmp", commit_sha="HEAD"),
            preset=PresetConfig(
                id=uuid.uuid4(), version_sha="v1",
                prompt_template="hunting", ruleset={},
            ),
            limits=ResourceLimits(),
        )
        events = []
        async for item in agent.analyze(ctx):
            events.append(item)

    results = [e for e in events if isinstance(e, AnalysisResult)]
    assert len(results) == 1
    assert results[0].findings == []
    assert "Error occurred" in results[0].raw_output


# ── ClaudeCodeAgent.analyze — command not found ──


@pytest.mark.asyncio
async def test_analyze_command_not_found():
    agent = ClaudeCodeAgent()
    agent._repo_path = "/tmp"
    agent._commit_sha = "HEAD"

    with patch("app.agents.claude_code_agent.asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        ctx = AnalysisContext(
            session_id=uuid.uuid4(),
            scope=CodeScope(repo_path="/tmp", commit_sha="HEAD"),
            preset=PresetConfig(
                id=uuid.uuid4(), version_sha="v1",
                prompt_template="hunting", ruleset={},
            ),
            limits=ResourceLimits(),
        )
        events = []
        async for item in agent.analyze(ctx):
            events.append(item)

    results = [e for e in events if isinstance(e, AnalysisResult)]
    assert len(results) == 1
    assert results[0].findings == []
    assert "not found" in results[0].raw_output
