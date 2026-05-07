"""MCP-based vulnerability analysis agent using finding-mcp."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from securescope_schemas.agent_interface import (
    AgentFinding,
    AgentMetadata,
    AnalysisContext,
    AnalysisResult,
    BaseAgent,
    LogEvent,
    LogLevel,
    Severity,
)

from app.core.config import settings

logger = structlog.get_logger()

FINDING_MCP_CMD = os.environ.get("FINDING_MCP_CMD", settings.finding_mcp_cmd)

SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
}


def _now() -> datetime:
    return datetime.now(UTC)


def _log(msg: str, progress: float | None = None, tokens: int | None = None) -> LogEvent:
    return LogEvent(
        timestamp=_now(),
        level=LogLevel.INFO,
        message=msg,
        progress=progress,
        tokens_used=tokens,
    )


def _map_severity(raw: str) -> Severity:
    return SEVERITY_MAP.get(raw.lower(), Severity.MEDIUM)


def _extract_text(content: Any) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


class McpFindingAgent(BaseAgent):
    """취약점 분석 에이전트 — finding-mcp를 통해 코드베이스를 탐색하고 분석."""

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._context: AnalysisContext | None = None
        self._cm_stdio: Any = None
        self._cm_session: Any = None

    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="mcp-finding-agent",
            version="0.1.0",
            supported_languages=["java", "php", "javascript", "typescript"],
            max_input_size_bytes=500_000_000,
            cost_profile={"per_run_usd": 0.0, "model": "none"},
            description=(
                "finding-mcp 기반 정적 분석 에이전트"
                " — 엔트리포인트, 위험 싱크, 테인트 분석, 인증 커버리지 검사"
            ),
        )

    async def _call(self, tool: str, args: dict[str, Any] | None = None) -> str:
        assert self._session is not None
        result = await self._session.call_tool(tool, args or {})
        return _extract_text(result.content)

    async def prepare(self, context: AnalysisContext) -> None:
        self._context = context
        repo_path = context.scope.repo_path

        server_params = StdioServerParameters(
            command=FINDING_MCP_CMD,
            args=[repo_path],
        )
        self._cm_stdio = stdio_client(server_params)
        read, write = await self._cm_stdio.__aenter__()
        self._cm_session = ClientSession(read, write)
        self._session = await self._cm_session.__aenter__()
        await self._session.initialize()

    async def analyze(self, context: AnalysisContext) -> AsyncIterator[LogEvent | AnalysisResult]:
        assert self._session is not None
        findings: list[AgentFinding] = []
        tokens_used = 0

        # Phase 1: Reconnaissance
        yield _log("코드베이스 정보 수집 중", progress=0.05)
        repo_info_raw = await self._call("get_repo_info")
        repo_info = _safe_json(repo_info_raw)

        yield _log("엔트리포인트 탐색 중", progress=0.10)
        entry_points_raw = await self._call("list_entry_points", {"limit": 200})
        entry_points = _safe_json(entry_points_raw)

        yield _log("위험 싱크 탐색 중", progress=0.15)
        sinks_raw = await self._call("list_dangerous_sinks", {"limit": 200})
        sinks = _safe_json(sinks_raw)

        ep_items = _get_items(entry_points)
        sink_items = _get_items(sinks)

        yield _log(
            f"엔트리포인트 {len(ep_items)}건, 위험 싱크 {len(sink_items)}건 발견",
            progress=0.20,
        )

        # Phase 2: Taint analysis
        yield _log("테인트 분석 실행 중 (Semgrep)", progress=0.25)
        taint_raw = await self._call("run_taint_analysis")
        taint_result = _safe_json(taint_raw)

        analysis_id = taint_result.get("analysis_id", "")
        if analysis_id:
            yield _log("테인트 분석 결과 수집 중", progress=0.35)
            paths_raw = await self._call(
                "get_taint_paths",
                {
                    "analysis_id": analysis_id,
                    "limit": 100,
                },
            )
            taint_paths = _safe_json(paths_raw)

            for item in _get_items(taint_paths):
                finding_id = item.get("finding_id") or item.get("id", "")
                if not finding_id:
                    continue
                detail_raw = await self._call(
                    "get_taint_path_detail",
                    {
                        "analysis_id": analysis_id,
                        "finding_id": str(finding_id),
                    },
                )
                detail = _safe_json(detail_raw)
                af = _taint_to_finding(detail, context.session_id)
                if af:
                    findings.append(af)

            yield _log(f"테인트 분석에서 {len(findings)}건 발견", progress=0.50)

        # Phase 3: Call chain tracing
        yield _log("콜 체인 추적 중", progress=0.55)
        chain_findings_count = 0
        sink_patterns = _unique_sink_patterns(sink_items)
        ep_functions = _unique_ep_functions(ep_items)

        max_traces = min(len(ep_functions) * len(sink_patterns), 50)
        traced = 0
        for ep_func in ep_functions[:10]:
            for sink_pat in sink_patterns[:5]:
                chain_raw = await self._call(
                    "trace_call_chain",
                    {
                        "source_function": ep_func,
                        "sink_pattern": sink_pat,
                        "max_depth": 5,
                    },
                )
                chain = _safe_json(chain_raw)
                chain_items = _get_items(chain)
                for ch in chain_items:
                    af = _chain_to_finding(ch, ep_func, sink_pat)
                    if af:
                        findings.append(af)
                        chain_findings_count += 1
                traced += 1
                if traced >= max_traces:
                    break
            if traced >= max_traces:
                break

        yield _log(f"콜 체인 추적에서 {chain_findings_count}건 발견", progress=0.70)

        # Phase 4: Auth coverage
        yield _log("인증 커버리지 검사 중", progress=0.75)
        auth_raw = await self._call("check_auth_coverage")
        auth_result = _safe_json(auth_raw)
        unprotected = auth_result.get("unprotected_routes") or auth_result.get("unprotected", [])
        for route in unprotected:
            af = _unprotected_route_to_finding(route)
            if af:
                findings.append(af)

        yield _log(f"미인증 라우트 {len(unprotected)}건 발견", progress=0.85)

        # Phase 5: Route mapping
        yield _log("라우트 맵 생성 중", progress=0.90)
        await self._call("map_routes")

        # Deduplicate by fingerprint
        seen: set[str] = set()
        unique_findings: list[AgentFinding] = []
        for f in findings:
            if f.fingerprint not in seen:
                seen.add(f.fingerprint)
                unique_findings.append(f)

        yield _log(
            f"분석 완료 — 총 {len(unique_findings)}건 취약점 발견",
            progress=1.0,
            tokens=tokens_used,
        )

        yield AnalysisResult(
            findings=unique_findings,
            tokens_used=tokens_used,
            cost_usd=0.0,
            raw_output=json.dumps(
                {
                    "repo_info": repo_info,
                    "entry_points_count": len(ep_items),
                    "sinks_count": len(sink_items),
                    "taint_findings": len([f for f in unique_findings if "taint" in f.category]),
                    "chain_findings": chain_findings_count,
                    "unprotected_routes": len(unprotected),
                }
            ),
        )

    async def terminate(self) -> None:
        if self._cm_session:
            await self._cm_session.__aexit__(None, None, None)
        if self._cm_stdio:
            await self._cm_stdio.__aexit__(None, None, None)
        self._session = None


# ── Helper functions ────────────────────────────────────────


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("items") or data.get("results") or data.get("findings", [])
        if isinstance(items, list):
            return items
    if isinstance(data, list):
        return data
    return []


def _unique_sink_patterns(sinks: list[dict[str, Any]]) -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for s in sinks:
        name = s.get("function") or s.get("name") or s.get("symbol", "")
        if name and name not in seen:
            seen.add(name)
            patterns.append(name)
    return patterns


def _unique_ep_functions(eps: list[dict[str, Any]]) -> list[str]:
    funcs: list[str] = []
    seen: set[str] = set()
    for ep in eps:
        name = ep.get("function") or ep.get("name") or ep.get("handler", "")
        if name and name not in seen:
            seen.add(name)
            funcs.append(name)
    return funcs


def _taint_to_finding(detail: dict[str, Any], session_id: UUID) -> AgentFinding | None:
    file_path = detail.get("file") or detail.get("path", "")
    if not file_path:
        return None
    line_start = detail.get("line_start") or detail.get("line", 1)
    line_end = detail.get("line_end") or line_start
    severity = _map_severity(detail.get("severity", "medium"))
    category = f"taint/{detail.get('rule_id', detail.get('check_id', 'unknown'))}"
    title = detail.get("message") or detail.get("rule_id", "Taint flow detected")
    description = detail.get("description") or detail.get("message", "")
    snippet = detail.get("code_snippet") or detail.get("matched_code", "")
    fp = f"taint:{file_path}:{line_start}:{category}"

    return AgentFinding(
        fingerprint=fp,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        severity=severity,
        category=category,
        title=title[:200],
        description=description[:2000],
        code_snippet=snippet[:1000],
        confidence=0.8,
        metadata={"source": "semgrep-taint", "detail": detail},
    )


def _chain_to_finding(chain: dict[str, Any], source: str, sink: str) -> AgentFinding | None:
    path = chain.get("path") or chain.get("chain", [])
    if not path:
        return None
    first = path[0] if isinstance(path, list) and path else chain
    file_path = first.get("file") or first.get("file_path", "")
    line_start = first.get("line") or first.get("line_start", 1)
    fp = f"chain:{source}->{sink}:{file_path}:{line_start}"

    return AgentFinding(
        fingerprint=fp,
        file_path=file_path,
        line_start=line_start,
        line_end=line_start,
        severity=Severity.HIGH,
        category=f"call-chain/{sink}",
        title=f"Data flow from {source} to dangerous sink {sink}",
        description=f"Call chain detected: {source} → {sink}. Path length: {len(path)}",
        code_snippet=json.dumps(path[:5], default=str)[:1000],
        confidence=0.7,
        metadata={"source_function": source, "sink_pattern": sink, "chain": path},
    )


def _unprotected_route_to_finding(route: dict[str, Any] | str) -> AgentFinding | None:
    if isinstance(route, str):
        return AgentFinding(
            fingerprint=f"auth:unprotected:{route}",
            file_path="",
            line_start=1,
            line_end=1,
            severity=Severity.HIGH,
            category="auth/missing",
            title=f"Unprotected route: {route}",
            description=f"Route {route} has no authentication middleware",
            code_snippet="",
            confidence=0.9,
        )
    path = route.get("path") or route.get("route", "")
    method = route.get("method", "GET")
    file_path = route.get("file") or route.get("handler_file", "")
    line = route.get("line") or route.get("line_start", 1)

    return AgentFinding(
        fingerprint=f"auth:unprotected:{method}:{path}",
        file_path=file_path,
        line_start=line,
        line_end=line,
        severity=Severity.HIGH,
        category="auth/missing",
        title=f"Unprotected route: {method} {path}",
        description=f"Route {method} {path} has no authentication middleware",
        code_snippet="",
        confidence=0.9,
        metadata={"method": method, "route": path},
    )
