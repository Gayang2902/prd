import json
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from securescope_schemas.agent_interface import AnalysisContext, AnalysisResult, CodeScope, LogEvent
from temporalio import activity

from app.core.config import settings
from app.models.analysis_session import SessionState
from app.workflows.models import EnvHandle

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


async def _ws_broadcast(session_id: UUID, event: dict[str, Any]) -> None:
    global _redis  # noqa: PLW0603
    try:
        if _redis is None:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        channel = f"ws:session:{session_id}"
        payload = json.dumps({"event": event, "exclude_id": None}, ensure_ascii=False)
        await _redis.publish(channel, payload)
    except Exception:
        logger.warning("ws_broadcast_failed", session_id=str(session_id))


@activity.defn(name="provision_isolated_env")
async def provision_isolated_env(session_id: UUID) -> EnvHandle:
    from app.services.k8s import create_analysis_pod

    activity.logger.info("Provisioning isolated env", extra={"session_id": str(session_id)})
    return await create_analysis_pod(session_id)


@activity.defn(name="clone_repository")
async def clone_repository(env: EnvHandle, scope: CodeScope) -> None:
    activity.logger.info(
        "Cloning repository",
        extra={"repo_path": scope.repo_path, "commit": scope.commit_sha},
    )


class ResourceLimitExceededError(RuntimeError):
    pass


@activity.defn(name="run_agent")
async def run_agent(env: EnvHandle, ctx: AnalysisContext) -> AnalysisResult:
    from app.services.agent_registry import get_registry

    registry = get_registry()
    agent_cls = next(iter(registry.values()), None)
    if agent_cls is None:
        raise RuntimeError("No agents registered")

    agent = agent_cls()
    await agent.prepare(ctx)

    limits = ctx.limits
    start_time = time.monotonic()
    accumulated_tokens = 0
    result: AnalysisResult | None = None

    async for event in agent.analyze(ctx):
        if isinstance(event, LogEvent):
            if event.tokens_used is not None:
                accumulated_tokens = event.tokens_used
            activity.heartbeat(
                {
                    "progress": event.progress,
                    "tokens_used": accumulated_tokens,
                }
            )

            elapsed = time.monotonic() - start_time
            if elapsed > limits.max_runtime_seconds:
                await agent.terminate()
                raise ResourceLimitExceededError(
                    f"Runtime limit exceeded: {elapsed:.0f}s > {limits.max_runtime_seconds}s"
                )
            if accumulated_tokens > limits.max_tokens:
                await agent.terminate()
                raise ResourceLimitExceededError(
                    f"Token limit exceeded: {accumulated_tokens} > {limits.max_tokens}"
                )

        elif isinstance(event, AnalysisResult):
            result = event

    if result is None:
        raise RuntimeError("Agent did not produce a result")

    if result.cost_usd > limits.max_cost_usd:
        activity.logger.warn(
            "Cost limit exceeded",
            extra={"cost": result.cost_usd, "limit": limits.max_cost_usd},
        )

    await agent.terminate()
    return result


@activity.defn(name="post_process_findings")
async def post_process_findings(session_id: UUID, result: AnalysisResult) -> int:
    from app.core.database import async_session_factory
    from app.models.analysis_session import AnalysisSession
    from app.models.finding import Finding, RegressionStatus, Severity
    from app.services.fingerprint import compute_fingerprint

    count = 0
    async with async_session_factory() as session:
        for af in result.findings:
            fp = compute_fingerprint(af.file_path, af.code_snippet, af.category)
            finding = Finding(
                session_id=session_id,
                fingerprint=fp,
                file_path=af.file_path,
                line_start=af.line_start,
                line_end=af.line_end,
                severity=Severity(af.severity.value),
                category=af.category,
                title=af.title,
                description=af.description,
                regression_status=RegressionStatus.NEW,
            )
            session.add(finding)
            count += 1

        analysis = await session.get(AnalysisSession, session_id)
        if analysis is not None:
            analysis.token_usage = result.tokens_used
            analysis.cost = Decimal(str(result.cost_usd))

        await session.flush()

        if analysis is not None:
            from app.services.regression import compute_regression_labels

            await compute_regression_labels(session, session_id, analysis.project_id)

        await session.commit()

    activity.logger.info(
        "Saved findings",
        extra={"count": count, "tokens": result.tokens_used, "cost": result.cost_usd},
    )
    return count


@activity.defn(name="record_hunting_phase")
async def record_hunting_phase(session_id: UUID, phase: str, phase_status: str) -> None:
    from app.core.database import async_session_factory
    from app.services.repositories.session import SessionRepository

    async with async_session_factory() as session:
        repo = SessionRepository(session)
        await repo.update_phase_data(session_id, phase, phase_status)
        await session.commit()

    await _ws_broadcast(
        session_id,
        {
            "type": "phase_updated",
            "phase": phase,
            "status": phase_status,
        },
    )

    activity.logger.info(
        "Phase updated",
        extra={"phase": phase, "status": phase_status},
    )


@activity.defn(name="post_process_hunting_findings")
async def post_process_hunting_findings(
    session_id: UUID, result: AnalysisResult, session_type: str
) -> int:
    from app.core.database import async_session_factory
    from app.models.analysis_session import AnalysisSession, SessionType
    from app.models.finding import Finding, RegressionStatus, Severity
    from app.services.fingerprint import compute_fingerprint

    count = 0
    async with async_session_factory() as session:
        for af in result.findings:
            fp = compute_fingerprint(af.file_path, af.code_snippet, af.category)
            extras: dict[str, Any] = {}
            if session_type == SessionType.TARGET_DISCOVERY.value:
                extras["crackability_score"] = getattr(af, "score", 0)
                category = "target_candidate"
            else:
                extras["anomaly_type"] = af.category
                category = af.category

            finding = Finding(
                session_id=session_id,
                fingerprint=fp,
                file_path=af.file_path,
                line_start=af.line_start,
                line_end=af.line_end,
                severity=Severity(af.severity.value),
                category=category,
                title=af.title,
                description=af.description,
                regression_status=RegressionStatus.NEW,
                extras=extras,
            )
            session.add(finding)
            count += 1

        analysis = await session.get(AnalysisSession, session_id)
        if analysis is not None:
            analysis.token_usage = result.tokens_used
            analysis.cost = Decimal(str(result.cost_usd))

        await session.commit()

    activity.logger.info(
        "Saved hunting findings",
        extra={"count": count, "session_type": session_type},
    )
    return count


@activity.defn(name="cleanup_isolated_env")
async def cleanup_isolated_env(env: EnvHandle) -> None:
    from app.services.k8s import delete_analysis_pod

    activity.logger.info("Cleaning up env", extra={"pod_name": env.pod_name})
    await delete_analysis_pod(env)


@activity.defn(name="record_session_state")
async def record_session_state(session_id: UUID, state: str) -> None:
    from app.core.database import async_session_factory
    from app.services.repositories.session import SessionRepository

    actual_state = SessionState(state) if isinstance(state, str) else state

    async with async_session_factory() as session:
        repo = SessionRepository(session)
        analysis = await repo.get(session_id)
        if analysis is None:
            raise RuntimeError(f"Session {session_id} not found")
        await repo.transition(analysis, actual_state)
        await session.commit()

    await _ws_broadcast(
        session_id,
        {
            "type": "state_changed",
            "state": actual_state.value,
        },
    )

    activity.logger.info("Session state updated", extra={"state": actual_state.value})
