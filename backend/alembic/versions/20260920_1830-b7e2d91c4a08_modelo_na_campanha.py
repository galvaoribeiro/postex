"""modelo persistida e vinculada a campanha

Revision ID: b7e2d91c4a08
Revises: a1f3c8d42b71
Create Date: 2026-09-20 18:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2d91c4a08"
down_revision: str | None = "a1f3c8d42b71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("model_asset_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_campaigns_model_asset_id"),
        "campaigns",
        ["model_asset_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_campaigns_model_asset_id_assets"),
        "campaigns",
        "assets",
        ["model_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_campaigns_model_asset_id_assets"),
        "campaigns",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_campaigns_model_asset_id"), table_name="campaigns")
    op.drop_column("campaigns", "model_asset_id")
