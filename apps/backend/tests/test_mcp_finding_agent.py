"""Tests for McpFindingAgent (Claude Code CLI backend) and helper functions."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from securescope_schemas.agent_interface import (
    AnalysisResult,
    LogEvent,
    Severity,
)

from app.agents.mcp_finding_agent import (
    McpFindingAgent,
    _map_severity,
    _parse_findings_json,
    _raw_to_finding,
    _safe_json,
)

# ── Helper ─────────────────────────────────────────────────


def _make_context(repo_path: str = "/tmp/repo") -> Any:
    scope = SimpleNamespace(repo_path=repo_path)
    return SimpleNamespace(scope=scope, session_id=uuid4())


def _claude_json_output(result_text: str, cost: float = 0.01, returncode: int = 0) -> bytes:
    return json.dumps({"result": result_text, "cost_usd": cost}).encode()


SAMPLE_FINDINGS_BLOCK = """\
Here is my analysis:

```json
{"findings": [
  {
    "fingerprint": "taint:Vuln.java:10:sqli",
    "file_path": "Vuln.java",
    "line_start": 10,
    "line_end": 12,
    "severity": "high",
    "category": "taint/sqli",
    "title": "SQL injection via user input",
    "description": "User input flows directly to SQL query",
    "code_snippet": "db.query(req.getParameter('id'))",
    "confidence": 0.9
  },
  {
    "fingerprint": "auth:unprotected:GET:/admin",
    "file_path": "routes.py",
    "line_start": 5,
    "line_end": 5,
    "severity": "high",
    "category": "auth/missing",
    "title": "Unprotected admin route",
    "description": "GET /admin has no auth middleware",
    "code_snippet": "",
    "confidence": 0.95
  }
]}
```

These are the findings.
"""


# ── _safe_json ─────────────────────────────────────────────


class TestSafeJson:
    def test_valid(self) -> None:
        assert _safe_json('{"a": 1}') == {"a": 1}

    def test_invalid(self) -> None:
        assert _safe_json("not json") == {}

    def test_none(self) -> None:
        assert _safe_json(None) == {}  # type: ignore[arg-type]


# ── _map_severity ──────────────────────────────────────────


class TestMapSeverity:
    def test_known(self) -> None:
        assert _map_severity("critical") == Severity.CRITICAL
        assert _map_severity("HIGH") == Severity.HIGH
        assert _map_severity("low") == Severity.LOW
        assert _map_severity("info") == Severity.INFO

    def test_unknown_defaults_medium(self) -> None:
        assert _map_severity("banana") == Severity.MEDIUM


# ── _parse_findings_json ──────────────────────────────────


class TestParseFindingsJson:
    def test_extracts_from_code_block(self) -> None:
        findings = _parse_findings_json(SAMPLE_FINDINGS_BLOCK)
        assert len(findings) == 2
        assert findings[0]["fingerprint"] == "taint:Vuln.java:10:sqli"
        assert findings[1]["category"] == "auth/missing"

    def test_no_json_block(self) -> None:
        assert _parse_findings_json("no findings here") == []

    def test_malformed_json(self) -> None:
        text = "```json\n{bad json}\n```"
        assert _parse_findings_json(text) == []

    def test_missing_findings_key(self) -> None:
        text = '```json\n{"data": []}\n```'
        assert _parse_findings_json(text) == []


# ── _raw_to_finding ────────────────────────────────────────


class TestRawToFinding:
    def test_valid_finding(self) -> None:
        raw = {
            "fingerprint": "fp1",
            "file_path": "a.java",
            "line_start": 10,
            "line_end": 12,
            "severity": "high",
            "category": "taint/sqli",
            "title": "SQL injection",
            "description": "desc",
            "code_snippet": "code",
            "confidence": 0.9,
        }
        f = _raw_to_finding(raw)
        assert f is not None
        assert f.fingerprint == "fp1"
        assert f.severity == Severity.HIGH
        assert f.confidence == 0.9

    def test_no_fingerprint_uses_file_line(self) -> None:
        raw = {"file_path": "b.java", "line_start": 5}
        f = _raw_to_finding(raw)
        assert f is not None
        assert f.fingerprint == "b.java:5"

    def test_empty_returns_none(self) -> None:
        assert _raw_to_finding({}) is None


# ── McpFindingAgent.describe ──────────────────────────────


class TestDescribe:
    def test_metadata(self) -> None:
        meta = McpFindingAgent.describe()
        assert meta.name == "mcp-finding-agent"
        assert meta.version == "0.2.0"
        assert "java" in meta.supported_languages


# ── McpFindingAgent.prepare ───────────────────────────────


class TestPrepare:
    @pytest.mark.asyncio
    async def test_creates_mcp_config(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context("/tmp/test-repo")

        await agent.prepare(ctx)

        assert agent._mcp_config_path is not None
        assert os.path.exists(agent._mcp_config_path)

        with open(agent._mcp_config_path) as f:
            config = json.load(f)

        assert "finding-mcp" in config["mcpServers"]
        assert config["mcpServers"]["finding-mcp"]["args"] == ["/tmp/test-repo"]

        os.unlink(agent._mcp_config_path)


# ── McpFindingAgent.terminate ─────────────────────────────


class TestTerminate:
    @pytest.mark.asyncio
    async def test_removes_config_file(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context()
        await agent.prepare(ctx)
        config_path = agent._mcp_config_path
        assert config_path is not None
        assert os.path.exists(config_path)

        await agent.terminate()

        assert not os.path.exists(config_path)
        assert agent._mcp_config_path is None

    @pytest.mark.asyncio
    async def test_noop_when_not_prepared(self) -> None:
        agent = McpFindingAgent()
        await agent.terminate()
        assert agent._mcp_config_path is None


# ── McpFindingAgent.analyze ───────────────────────────────


def _mock_process(stdout: bytes, stderr: bytes = b"", returncode: int = 0) -> AsyncMock:
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_successful_analysis(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context()
        await agent.prepare(ctx)

        stdout = _claude_json_output(SAMPLE_FINDINGS_BLOCK, cost=0.03)
        mock_proc = _mock_process(stdout)

        with patch("app.agents.mcp_finding_agent.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = AsyncMock()
            mock_aio.subprocess.PIPE = -1

            events: list[LogEvent | AnalysisResult] = []
            async for event in agent.analyze(ctx):
                events.append(event)

        results = [e for e in events if isinstance(e, AnalysisResult)]
        logs = [e for e in events if isinstance(e, LogEvent)]

        assert len(results) == 1
        assert len(results[0].findings) == 2
        assert results[0].cost_usd == 0.03
        assert any(f.category == "taint/sqli" for f in results[0].findings)
        assert any(f.category == "auth/missing" for f in results[0].findings)
        assert len(logs) >= 3

        await agent.terminate()

    @pytest.mark.asyncio
    async def test_claude_failure(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context()
        await agent.prepare(ctx)

        mock_proc = _mock_process(b"", stderr=b"error occurred", returncode=1)

        with patch("app.agents.mcp_finding_agent.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = AsyncMock()
            mock_aio.subprocess.PIPE = -1

            events = [e async for e in agent.analyze(ctx)]

        results = [e for e in events if isinstance(e, AnalysisResult)]
        assert len(results) == 1
        assert results[0].findings == []

        await agent.terminate()

    @pytest.mark.asyncio
    async def test_no_findings_in_output(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context()
        await agent.prepare(ctx)

        stdout = _claude_json_output("I found no vulnerabilities.")
        mock_proc = _mock_process(stdout)

        with patch("app.agents.mcp_finding_agent.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = AsyncMock()
            mock_aio.subprocess.PIPE = -1

            events = [e async for e in agent.analyze(ctx)]

        results = [e for e in events if isinstance(e, AnalysisResult)]
        assert len(results) == 1
        assert results[0].findings == []

        await agent.terminate()

    @pytest.mark.asyncio
    async def test_deduplication(self) -> None:
        dup_block = """```json
{"findings": [
  {"fingerprint": "dup1", "file_path": "a.java", "line_start": 1, "severity": "high",
   "category": "x", "title": "t", "description": "d", "code_snippet": "", "confidence": 0.8},
  {"fingerprint": "dup1", "file_path": "a.java", "line_start": 1, "severity": "high",
   "category": "x", "title": "t", "description": "d", "code_snippet": "", "confidence": 0.8}
]}
```"""
        agent = McpFindingAgent()
        ctx = _make_context()
        await agent.prepare(ctx)

        stdout = _claude_json_output(dup_block)
        mock_proc = _mock_process(stdout)

        with patch("app.agents.mcp_finding_agent.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = AsyncMock()
            mock_aio.subprocess.PIPE = -1

            events = [e async for e in agent.analyze(ctx)]

        results = [e for e in events if isinstance(e, AnalysisResult)]
        assert len(results[0].findings) == 1

        await agent.terminate()
