"""Add hunting workflow fields to analysis_sessions and findings.

Revision ID: 003
Revises: 002
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_sessions",
        sa.Column(
            "session_type",
            sa.String(30),
            nullable=False,
            server_default="static_analysis",
        ),
    )
    op.add_column(
        "analysis_sessions",
        sa.Column("current_phase", sa.String(50), nullable=True),
    )
    op.add_column(
        "analysis_sessions",
        sa.Column("phase_data", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("extras", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "extras")
    op.drop_column("analysis_sessions", "phase_data")
    op.drop_column("analysis_sessions", "current_phase")
    op.drop_column("analysis_sessions", "session_type")
