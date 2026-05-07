"""Tests for McpFindingAgent and helper functions."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from securescope_schemas.agent_interface import (
    AnalysisContext,
    AnalysisResult,
    LogEvent,
    Severity,
)

from app.agents.mcp_finding_agent import (
    McpFindingAgent,
    _chain_to_finding,
    _extract_text,
    _get_items,
    _map_severity,
    _safe_json,
    _taint_to_finding,
    _unique_ep_functions,
    _unique_sink_patterns,
    _unprotected_route_to_finding,
)

# ── Helper utilities ───────────────────────────────────────


def _make_context(repo_path: str = "/tmp/repo") -> AnalysisContext:
    scope = SimpleNamespace(repo_path=repo_path)
    return SimpleNamespace(scope=scope, session_id=uuid4())  # type: ignore[return-value]


def _text_content(text: str) -> Any:
    return SimpleNamespace(text=text)


# ── _safe_json ─────────────────────────────────────────────


class TestSafeJson:
    def test_valid_json(self) -> None:
        assert _safe_json('{"a": 1}') == {"a": 1}

    def test_invalid_json(self) -> None:
        assert _safe_json("not json") == {}

    def test_none_input(self) -> None:
        assert _safe_json(None) == {}  # type: ignore[arg-type]


# ── _get_items ─────────────────────────────────────────────


class TestGetItems:
    def test_items_key(self) -> None:
        assert _get_items({"items": [{"a": 1}]}) == [{"a": 1}]

    def test_results_key(self) -> None:
        assert _get_items({"results": [{"b": 2}]}) == [{"b": 2}]

    def test_findings_key(self) -> None:
        assert _get_items({"findings": [{"c": 3}]}) == [{"c": 3}]

    def test_list_input(self) -> None:
        assert _get_items([{"d": 4}]) == [{"d": 4}]  # type: ignore[arg-type]

    def test_empty_dict(self) -> None:
        assert _get_items({}) == []

    def test_non_list_items(self) -> None:
        assert _get_items({"items": "not a list"}) == []


# ── _extract_text ──────────────────────────────────────────


class TestExtractText:
    def test_list_with_text_attr(self) -> None:
        items = [_text_content("hello"), _text_content("world")]
        assert _extract_text(items) == "hello\nworld"

    def test_list_with_strings(self) -> None:
        assert _extract_text(["a", "b"]) == "a\nb"

    def test_mixed_list(self) -> None:
        items = [_text_content("x"), "y"]
        assert _extract_text(items) == "x\ny"

    def test_non_list(self) -> None:
        assert _extract_text(42) == "42"


# ── _map_severity ──────────────────────────────────────────


class TestMapSeverity:
    def test_known_severities(self) -> None:
        assert _map_severity("critical") == Severity.CRITICAL
        assert _map_severity("HIGH") == Severity.HIGH
        assert _map_severity("low") == Severity.LOW
        assert _map_severity("info") == Severity.INFO

    def test_alias_error(self) -> None:
        assert _map_severity("error") == Severity.HIGH

    def test_alias_warning(self) -> None:
        assert _map_severity("warning") == Severity.MEDIUM

    def test_unknown_defaults_medium(self) -> None:
        assert _map_severity("banana") == Severity.MEDIUM


# ── _unique_sink_patterns / _unique_ep_functions ───────────


class TestUniqueLists:
    def test_sink_patterns(self) -> None:
        sinks = [
            {"function": "exec"},
            {"name": "eval"},
            {"function": "exec"},  # duplicate
            {"symbol": "system"},
        ]
        assert _unique_sink_patterns(sinks) == ["exec", "eval", "system"]

    def test_ep_functions(self) -> None:
        eps = [
            {"function": "handleRequest"},
            {"name": "doLogin"},
            {"handler": "processUpload"},
            {"function": "handleRequest"},  # duplicate
        ]
        assert _unique_ep_functions(eps) == ["handleRequest", "doLogin", "processUpload"]

    def test_empty_names_skipped(self) -> None:
        assert _unique_sink_patterns([{"function": ""}, {}]) == []
        assert _unique_ep_functions([{"name": ""}, {}]) == []


# ── _taint_to_finding ─────────────────────────────────────


class TestTaintToFinding:
    def test_valid_detail(self) -> None:
        detail = {
            "file": "src/App.java",
            "line_start": 10,
            "line_end": 12,
            "severity": "high",
            "rule_id": "sqli",
            "message": "SQL injection",
            "description": "User input flows to query",
            "code_snippet": "db.query(input)",
        }
        f = _taint_to_finding(detail, uuid4())
        assert f is not None
        assert f.severity == Severity.HIGH
        assert f.file_path == "src/App.java"
        assert f.line_start == 10
        assert "taint" in f.category
        assert f.confidence == 0.8

    def test_missing_file_returns_none(self) -> None:
        assert _taint_to_finding({}, uuid4()) is None

    def test_fallback_fields(self) -> None:
        detail = {"path": "x.js", "line": 5, "check_id": "xss"}
        f = _taint_to_finding(detail, uuid4())
        assert f is not None
        assert f.file_path == "x.js"
        assert f.line_start == 5
        assert "xss" in f.category


# ── _chain_to_finding ─────────────────────────────────────


class TestChainToFinding:
    def test_valid_chain(self) -> None:
        chain = {
            "path": [
                {"file": "a.java", "line": 1},
                {"file": "b.java", "line": 5},
            ]
        }
        f = _chain_to_finding(chain, "handleReq", "exec")
        assert f is not None
        assert f.severity == Severity.HIGH
        assert "handleReq" in f.title
        assert "exec" in f.title
        assert f.confidence == 0.7

    def test_empty_path_returns_none(self) -> None:
        assert _chain_to_finding({"path": []}, "a", "b") is None
        assert _chain_to_finding({}, "a", "b") is None


# ── _unprotected_route_to_finding ─────────────────────────


class TestUnprotectedRouteToFinding:
    def test_string_route(self) -> None:
        f = _unprotected_route_to_finding("/api/admin")
        assert f is not None
        assert f.severity == Severity.HIGH
        assert "/api/admin" in f.title
        assert f.confidence == 0.9

    def test_dict_route(self) -> None:
        route = {"path": "/users", "method": "POST", "file": "routes.py", "line": 42}
        f = _unprotected_route_to_finding(route)
        assert f is not None
        assert "POST" in f.title
        assert f.line_start == 42


# ── McpFindingAgent.describe ──────────────────────────────


class TestDescribe:
    def test_metadata(self) -> None:
        meta = McpFindingAgent.describe()
        assert meta.name == "mcp-finding-agent"
        assert meta.version == "0.1.0"
        assert "java" in meta.supported_languages


# ── McpFindingAgent.prepare ───────────────────────────────


class TestPrepare:
    @pytest.mark.asyncio
    async def test_prepare_initializes_session(self) -> None:
        agent = McpFindingAgent()
        ctx = _make_context()

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        mock_cm_session = AsyncMock()
        mock_cm_session.__aenter__ = AsyncMock(return_value=mock_session)

        mock_cm_stdio = AsyncMock()
        mock_cm_stdio.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))

        with (
            patch("app.agents.mcp_finding_agent.stdio_client", return_value=mock_cm_stdio),
            patch("app.agents.mcp_finding_agent.ClientSession", return_value=mock_cm_session),
        ):
            await agent.prepare(ctx)

        assert agent._session is mock_session
        mock_session.initialize.assert_awaited_once()


# ── McpFindingAgent.terminate ─────────────────────────────


class TestTerminate:
    @pytest.mark.asyncio
    async def test_terminate_cleans_up(self) -> None:
        agent = McpFindingAgent()
        agent._cm_session = AsyncMock()
        agent._cm_stdio = AsyncMock()
        agent._session = AsyncMock()

        await agent.terminate()

        agent._cm_session.__aexit__.assert_awaited_once()
        agent._cm_stdio.__aexit__.assert_awaited_once()
        assert agent._session is None

    @pytest.mark.asyncio
    async def test_terminate_noop_when_not_prepared(self) -> None:
        agent = McpFindingAgent()
        await agent.terminate()
        assert agent._session is None


# ── McpFindingAgent.analyze (full pipeline) ───────────────


def _mock_call_tool_factory(responses: dict[str, str]) -> AsyncMock:
    """Build a call_tool mock that returns JSON based on tool name."""

    async def _call_tool(tool: str, args: dict[str, Any] | None = None) -> Any:
        raw = responses.get(tool, "{}")
        return SimpleNamespace(content=[_text_content(raw)])

    return AsyncMock(side_effect=_call_tool)


class TestAnalyzePipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline(self) -> None:
        responses = {
            "get_repo_info": json.dumps({"name": "test-repo", "language": "java"}),
            "list_entry_points": json.dumps(
                {"items": [{"function": "handleReq"}, {"function": "doLogin"}]}
            ),
            "list_dangerous_sinks": json.dumps({"items": [{"function": "exec"}]}),
            "run_taint_analysis": json.dumps({"analysis_id": "abc123"}),
            "get_taint_paths": json.dumps({"items": [{"finding_id": "f1"}, {"finding_id": "f2"}]}),
            "get_taint_path_detail": json.dumps(
                {
                    "file": "Vuln.java",
                    "line_start": 10,
                    "severity": "high",
                    "rule_id": "sqli",
                    "message": "SQL injection",
                }
            ),
            "trace_call_chain": json.dumps(
                {
                    "items": [
                        {"path": [{"file": "a.java", "line": 1}, {"file": "b.java", "line": 5}]}
                    ]
                }
            ),
            "check_auth_coverage": json.dumps({"unprotected_routes": ["/api/admin"]}),
            "map_routes": json.dumps({"routes": []}),
        }

        agent = McpFindingAgent()
        agent._session = AsyncMock()
        agent._session.call_tool = _mock_call_tool_factory(responses)

        ctx = _make_context()
        events: list[LogEvent | AnalysisResult] = []
        async for event in agent.analyze(ctx):
            events.append(event)

        log_events = [e for e in events if isinstance(e, LogEvent)]
        results = [e for e in events if isinstance(e, AnalysisResult)]

        assert len(results) == 1
        assert len(log_events) >= 5
        assert results[0].findings
        assert any(f.category.startswith("taint/") for f in results[0].findings)
        assert any(f.category.startswith("auth/") for f in results[0].findings)

    @pytest.mark.asyncio
    async def test_pipeline_no_taint_analysis_id(self) -> None:
        responses = {
            "get_repo_info": "{}",
            "list_entry_points": json.dumps({"items": []}),
            "list_dangerous_sinks": json.dumps({"items": []}),
            "run_taint_analysis": "{}",
            "check_auth_coverage": json.dumps({"unprotected_routes": []}),
            "map_routes": "{}",
        }

        agent = McpFindingAgent()
        agent._session = AsyncMock()
        agent._session.call_tool = _mock_call_tool_factory(responses)

        ctx = _make_context()
        events = [e async for e in agent.analyze(ctx)]
        results = [e for e in events if isinstance(e, AnalysisResult)]

        assert len(results) == 1
        assert results[0].findings == []

    @pytest.mark.asyncio
    async def test_deduplication(self) -> None:
        responses = {
            "get_repo_info": "{}",
            "list_entry_points": json.dumps({"items": [{"function": "fn1"}]}),
            "list_dangerous_sinks": json.dumps({"items": [{"function": "sink1"}]}),
            "run_taint_analysis": json.dumps({"analysis_id": "x"}),
            "get_taint_paths": json.dumps({"items": [{"finding_id": "f1"}, {"finding_id": "f2"}]}),
            "get_taint_path_detail": json.dumps(
                {"file": "a.java", "line_start": 10, "rule_id": "sqli", "message": "dup"}
            ),
            "trace_call_chain": "{}",
            "check_auth_coverage": json.dumps({"unprotected_routes": []}),
            "map_routes": "{}",
        }

        agent = McpFindingAgent()
        agent._session = AsyncMock()
        agent._session.call_tool = _mock_call_tool_factory(responses)

        ctx = _make_context()
        events = [e async for e in agent.analyze(ctx)]
        results = [e for e in events if isinstance(e, AnalysisResult)]

        taint_findings = [f for f in results[0].findings if "taint" in f.category]
        assert len(taint_findings) == 1
