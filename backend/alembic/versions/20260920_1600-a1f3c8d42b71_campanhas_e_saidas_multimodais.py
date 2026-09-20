"""campanhas e saidas multimodais

Revision ID: a1f3c8d42b71
Revises: c4e8a1b90d2f
Create Date: 2026-09-20 16:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1f3c8d42b71"
down_revision: str | None = "c4e8a1b90d2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column(
            "destination",
            sa.Enum(
                "INSTAGRAM",
                "TIKTOK",
                "TIKTOK_SHOP",
                name="campaigndestination",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("outputs_requested", JSONType, nullable=False),
        sa.Column("failed_outputs", JSONType, nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "GENERATING",
                "REVIEW",
                "APPROVED",
                "FAILED",
                "ARCHIVED",
                name="campaignstatus",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("brief", JSONType, nullable=False),
        sa.Column("generation_context", JSONType, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_campaigns_business_id_businesses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_campaigns_job_id_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_campaigns_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaigns")),
    )
    op.create_index(op.f("ix_campaigns_business_id"), "campaigns", ["business_id"])
    op.create_index(op.f("ix_campaigns_destination"), "campaigns", ["destination"])
    op.create_index(op.f("ix_campaigns_job_id"), "campaigns", ["job_id"])
    op.create_index(op.f("ix_campaigns_product_id"), "campaigns", ["product_id"])
    op.create_index(op.f("ix_campaigns_status"), "campaigns", ["status"])

    op.add_column("contents", sa.Column("campaign_id", sa.Uuid(), nullable=True))
    op.add_column("contents", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_contents_campaign_id"), "contents", ["campaign_id"])
    op.create_index(op.f("ix_contents_product_id"), "contents", ["product_id"])
    op.create_foreign_key(
        op.f("fk_contents_campaign_id_campaigns"),
        "contents",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_contents_product_id_products"),
        "contents",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("assets", sa.Column("duration_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "duration_seconds")
    op.drop_constraint(op.f("fk_contents_product_id_products"), "contents", type_="foreignkey")
    op.drop_constraint(op.f("fk_contents_campaign_id_campaigns"), "contents", type_="foreignkey")
    op.drop_index(op.f("ix_contents_product_id"), table_name="contents")
    op.drop_index(op.f("ix_contents_campaign_id"), table_name="contents")
    op.drop_column("contents", "product_id")
    op.drop_column("contents", "campaign_id")
    op.drop_index(op.f("ix_campaigns_status"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_product_id"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_job_id"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_destination"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_business_id"), table_name="campaigns")
    op.drop_table("campaigns")
