"""Align schema with current SQLAlchemy models.

Revision ID: 002
Revises: 001
Create Date: 2026-05-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agents: align with Agent model ──
    op.drop_column("agents", "description")
    op.drop_column("agents", "entry_point")
    op.add_column(
        "agents", sa.Column("metadata", postgresql.JSONB(), nullable=True, server_default="{}")
    )
    op.add_column(
        "agents", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.alter_column("agents", "name", type_=sa.String(100))
    op.alter_column("agents", "version", type_=sa.String(50))
    op.create_unique_constraint("uq_agents_name", "agents", ["name"])

    # ── presets: add agent_id FK, version_sha, is_shared; drop description ──
    op.drop_column("presets", "description")
    op.add_column(
        "presets", sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id"), nullable=True)
    )
    op.add_column(
        "presets", sa.Column("version_sha", sa.String(64), nullable=True, server_default="")
    )
    op.add_column(
        "presets", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false")
    )

    # ── analysis_sessions: add priority column ──
    op.add_column(
        "analysis_sessions",
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
    )


def downgrade() -> None:
    op.drop_column("analysis_sessions", "priority")

    op.drop_column("presets", "is_shared")
    op.drop_column("presets", "version_sha")
    op.drop_column("presets", "agent_id")
    op.add_column("presets", sa.Column("description", sa.Text(), nullable=True))

    op.drop_constraint("uq_agents_name", "agents", type_="unique")
    op.alter_column("agents", "version", type_=sa.String(100))
    op.alter_column("agents", "name", type_=sa.String(255))
    op.drop_column("agents", "updated_at")
    op.drop_column("agents", "metadata")
    op.add_column(
        "agents", sa.Column("entry_point", sa.String(500), nullable=False, server_default="")
    )
    op.add_column("agents", sa.Column("description", sa.Text(), nullable=True))
