"""add tenant provider policies

Revision ID: 20260525_0005
Revises: 20260525_0004
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0005"
down_revision = "20260525_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_provider_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("ai_provider", sa.String(length=32), nullable=False),
        sa.Column("media_provider", sa.String(length=32), nullable=False),
        sa.Column("fallback_mode", sa.String(length=64), nullable=False),
        sa.Column("monthly_guardrail", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["parent_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index("ix_tenant_provider_policies_tenant_id", "tenant_provider_policies", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_provider_policies_tenant_id", table_name="tenant_provider_policies")
    op.drop_table("tenant_provider_policies")
