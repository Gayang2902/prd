"""Tests for HuntingAgent and helper functions."""

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

from app.agents.hunting_agent import (
    PHASE_PROMPTS,
    SEVERITY_MAP,
    SKILL_BY_TYPE,
    HuntingAgent,
    _estimate_cost,
    _load_skill,
    _log,
    _parse_findings,
)

# ── _load_skill ──


def test_load_skill_exists(tmp_path):
    skill_dir = tmp_path / "opentarget"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill")

    with patch("app.agents.hunting_agent.SKILLS_DIR", tmp_path):
        assert _load_skill("opentarget") == "# Skill"


def test_load_skill_via_type_mapping(tmp_path):
    skill_dir = tmp_path / "opentarget"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# TD Skill")

    with patch("app.agents.hunting_agent.SKILLS_DIR", tmp_path):
        assert _load_skill("target_discovery") == "# TD Skill"


def test_load_skill_missing(tmp_path):
    with patch("app.agents.hunting_agent.SKILLS_DIR", tmp_path):
        assert _load_skill("nonexistent") == ""


# ── _estimate_cost ──


def test_estimate_cost():
    assert _estimate_cost(0) == 0.0
    assert _estimate_cost(100_000) == 1.5


# ── _log ──


def test_log_basic():
    event = _log("test message")
    assert event.message == "test message"
    assert event.progress is None
    assert event.tokens_used is None


def test_log_with_progress_and_tokens():
    event = _log("msg", progress=0.5, tokens=1000)
    assert event.progress == 0.5
    assert event.tokens_used == 1000


# ── _parse_findings ──


def test_parse_findings_valid_json():
    text = json.dumps(
        {
            "findings": [
                {
                    "title": "Buffer overflow",
                    "file_path": "src/parse.c",
                    "line_start": 10,
                    "line_end": 20,
                    "severity": "critical",
                    "category": "memory",
                    "description": "Stack buffer overflow in parse()",
                    "code_snippet": "char buf[8]; strcpy(buf, input);",
                }
            ]
        }
    )
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].title == "Buffer overflow"
    assert findings[0].file_path == "src/parse.c"


def test_parse_findings_with_results_key():
    text = json.dumps({"results": [{"title": "UAF", "file_path": "x.c", "severity": "high"}]})
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH


def test_parse_findings_embedded_json():
    text = (
        "Some preamble text\n"
        '{"findings": [{"title": "XSS", "file_path": "a.js", "severity": "medium"}]}'
        "\nMore text"
    )
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].title == "XSS"


def test_parse_findings_invalid_json():
    assert _parse_findings("this is not json at all") == []


def test_parse_findings_dedup():
    text = json.dumps(
        {
            "findings": [
                {"title": "Bug", "file_path": "a.c", "line_start": 1, "severity": "low"},
                {"title": "Bug", "file_path": "a.c", "line_start": 1, "severity": "low"},
            ]
        }
    )
    findings = _parse_findings(text)
    assert len(findings) == 1


def test_parse_findings_non_dict_items():
    text = json.dumps({"findings": ["not_a_dict", 42, None]})
    assert _parse_findings(text) == []


def test_parse_findings_unknown_severity():
    text = json.dumps(
        {"findings": [{"title": "edge", "file_path": "x.c", "severity": "unknown_sev"}]}
    )
    findings = _parse_findings(text)
    assert len(findings) == 1
    assert findings[0].severity == Severity.MEDIUM


def test_parse_findings_with_fingerprint():
    text = json.dumps(
        {
            "findings": [
                {"title": "A", "file_path": "a.c", "fingerprint": "fp1", "severity": "low"},
                {"title": "B", "file_path": "b.c", "fingerprint": "fp1", "severity": "high"},
            ]
        }
    )
    findings = _parse_findings(text)
    assert len(findings) == 1


def test_parse_findings_repo_fallback():
    text = json.dumps({"findings": [{"title": "T", "repo": "org/lib", "severity": "info"}]})
    findings = _parse_findings(text)
    assert findings[0].file_path == "org/lib"


def test_parse_findings_non_list_findings():
    text = json.dumps({"findings": "not a list"})
    assert _parse_findings(text) == []


# ── HuntingAgent.describe ──


def test_describe():
    meta = HuntingAgent.describe()
    assert meta.name == "hunting-agent"
    assert meta.version == "1.0.0"
    assert "c" in meta.supported_languages


# ── HuntingAgent.prepare ──


@pytest.mark.asyncio
async def test_prepare():
    agent = HuntingAgent()
    ctx = AnalysisContext(
        session_id=uuid.uuid4(),
        scope=CodeScope(repo_path="/tmp", commit_sha="abc"),
        preset=PresetConfig(
            id=uuid.uuid4(),
            version_sha="v1",
            prompt_template="hunting",
            ruleset={"skill": "openresearch"},
        ),
        limits=ResourceLimits(),
    )
    with patch("app.agents.hunting_agent.AsyncAnthropic") as mock_cls:
        mock_cls.return_value = AsyncMock()
        await agent.prepare(ctx)

    assert agent._client is not None
    assert agent._skill_name == "openresearch"


# ── HuntingAgent.terminate ──


@pytest.mark.asyncio
async def test_terminate():
    agent = HuntingAgent()
    agent._client = AsyncMock()
    await agent.terminate()
    assert agent._client is None


# ── HuntingAgent.analyze — success ──


@pytest.mark.asyncio
async def test_analyze_success():
    agent = HuntingAgent()
    mock_client = AsyncMock()
    agent._client = mock_client
    agent._skill_name = "opentarget"
    agent._skill_content = "# skill"

    mock_usage = MagicMock()
    mock_usage.input_tokens = 500
    mock_usage.output_tokens = 300
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {"findings": [{"title": "vuln", "file_path": "x.c", "severity": "high"}]}
            )
        )
    ]
    mock_response.usage = mock_usage
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    ctx = AnalysisContext(
        session_id=uuid.uuid4(),
        scope=CodeScope(repo_path="/tmp", commit_sha="abc"),
        preset=PresetConfig(
            id=uuid.uuid4(),
            version_sha="v1",
            prompt_template="hunting",
            ruleset={
                "skill": "opentarget",
                "session_type": "target_discovery",
                "phase": "gathering",
            },
        ),
        limits=ResourceLimits(),
    )

    events = []
    async for item in agent.analyze(ctx):
        events.append(item)

    log_events = [e for e in events if isinstance(e, LogEvent)]
    results = [e for e in events if isinstance(e, AnalysisResult)]
    assert len(results) == 1
    assert len(results[0].findings) == 1
    assert results[0].tokens_used == 800
    assert len(log_events) >= 3


# ── HuntingAgent.analyze — API error ──


@pytest.mark.asyncio
async def test_analyze_api_error():
    agent = HuntingAgent()
    mock_client = AsyncMock()
    agent._client = mock_client
    agent._skill_name = "opentarget"
    agent._skill_content = ""
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("timeout"))

    ctx = AnalysisContext(
        session_id=uuid.uuid4(),
        scope=CodeScope(repo_path="/tmp", commit_sha="abc"),
        preset=PresetConfig(
            id=uuid.uuid4(),
            version_sha="v1",
            prompt_template="hunting",
            ruleset={},
        ),
        limits=ResourceLimits(),
    )

    events = []
    async for item in agent.analyze(ctx):
        events.append(item)

    results = [e for e in events if isinstance(e, AnalysisResult)]
    assert len(results) == 1
    assert results[0].findings == []
    assert "timeout" in results[0].raw_output


# ── _build_user_prompt ──


def test_build_user_prompt_all_phases():
    agent = HuntingAgent()
    prompt = agent._build_user_prompt("target_discovery", "all", {"skill": "opentarget"})
    assert "전체 파이프라인" in prompt


def test_build_user_prompt_specific_phase():
    agent = HuntingAgent()
    prompt = agent._build_user_prompt("target_discovery", "gathering", {"skill": "opentarget"})
    assert "Phase 1" in prompt


def test_build_user_prompt_with_previous_results():
    agent = HuntingAgent()
    prompt = agent._build_user_prompt(
        "target_discovery",
        "filtering",
        {"previous_results": {"gathering": [{"name": "lib"}]}},
    )
    assert "previous_results" in prompt


def test_build_user_prompt_unknown_phase():
    agent = HuntingAgent()
    prompt = agent._build_user_prompt("target_discovery", "nonexistent", {})
    assert "nonexistent" in prompt


# ── constants ──


def test_severity_map_keys():
    assert set(SEVERITY_MAP.keys()) == {"critical", "high", "medium", "low", "info"}


def test_skill_by_type():
    assert SKILL_BY_TYPE["target_discovery"] == "opentarget"
    assert SKILL_BY_TYPE["zero_day_hunting"] == "openresearch"


def test_phase_prompts_all_types():
    for stype in ("target_discovery", "zero_day_hunting"):
        assert stype in PHASE_PROMPTS
        for _phase, prompt in PHASE_PROMPTS[stype].items():
            assert len(prompt) > 10
