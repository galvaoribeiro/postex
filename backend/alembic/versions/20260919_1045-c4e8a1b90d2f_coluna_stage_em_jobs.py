"""coluna stage em jobs

Revision ID: c4e8a1b90d2f
Revises: 7a70d684f67f
Create Date: 2026-09-19 10:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c4e8a1b90d2f"
down_revision: str | None = "7a70d684f67f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("stage", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "stage")
