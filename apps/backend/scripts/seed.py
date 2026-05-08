"""Seed script for local development.

Usage:
    cd apps/backend && python scripts/seed.py
"""

import asyncio
import uuid

from app.core.database import async_session_factory, engine
from app.models.agent import Agent
from app.models.base import Base
from app.models.preset import Preset
from app.models.project import Project
from app.models.user import Role, User
from app.services.seed_presets import BUILTIN_PRESETS

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
LEAD_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
REVIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
HUNTING_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
CLAUDE_CODE_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000012")


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        existing = await session.get(User, ADMIN_ID)
        if existing is not None:
            print("Seed data already exists, skipping.")
            return

        users = [
            User(id=ADMIN_ID, email="admin@securescope.dev", name="관리자", role=Role.ADMIN),
            User(id=LEAD_ID, email="lead@securescope.dev", name="팀 리드", role=Role.LEAD),
            User(
                id=REVIEWER_ID, email="reviewer@securescope.dev", name="검수자", role=Role.REVIEWER
            ),
        ]
        session.add_all(users)

        agent = Agent(
            id=AGENT_ID,
            name="securescope-default",
            version="0.1.0",
            metadata_={"description": "기본 정적 분석 에이전트"},
        )
        hunting_agent = Agent(
            id=HUNTING_AGENT_ID,
            name="hunting-agent",
            version="1.0.0",
            metadata_={"description": "Anthropic API 직접 호출 — opentarget/openresearch 스킬 기반 헌팅"},
        )
        claude_code_agent = Agent(
            id=CLAUDE_CODE_AGENT_ID,
            name="claude-code",
            version="1.0.0",
            metadata_={"description": "Claude Code CLI 직접 실행 — 하위 쉘에서 코드 분석 및 헌팅 수행"},
        )
        session.add(agent)
        session.add(hunting_agent)
        session.add(claude_code_agent)

        for bp in BUILTIN_PRESETS:
            preset = Preset(agent_id=AGENT_ID, **bp)
            session.add(preset)

        hunting_presets = [
            Preset(
                agent_id=HUNTING_AGENT_ID,
                name="OpenTarget 헌팅",
                version_sha="builtin-v1",
                prompt_template="opentarget 스킬 기반 타겟 디스커버리 파이프라인",
                ruleset={"skill": "opentarget", "session_type": "target_discovery"},
                timeout_seconds=3600,
                max_retries=2,
                is_shared=True,
            ),
            Preset(
                agent_id=HUNTING_AGENT_ID,
                name="OpenResearch 헌팅",
                version_sha="builtin-v1",
                prompt_template="openresearch 스킬 기반 제로데이 헌팅 파이프라인",
                ruleset={"skill": "openresearch", "session_type": "zero_day_hunting"},
                timeout_seconds=7200,
                max_retries=2,
                is_shared=True,
            ),
        ]
        session.add_all(hunting_presets)

        project = Project(
            name="sample-webapp",
            gitlab_project_id="example/sample-webapp",
            owner_id=LEAD_ID,
        )
        session.add(project)

        await session.commit()
        total_presets = len(BUILTIN_PRESETS) + len(hunting_presets)
        print(f"Seeded: 3 users, 3 agents, {total_presets} presets, 1 project")
        print(f"Admin user ID: {ADMIN_ID}")
        print(f"Use header: X-User-Id: {ADMIN_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
