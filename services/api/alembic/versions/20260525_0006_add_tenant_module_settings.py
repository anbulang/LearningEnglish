"""add tenant module settings

Revision ID: 20260525_0006
Revises: 20260525_0005
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0006"
down_revision = "20260525_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_module_settings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("module_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["parent_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "module_key", name="uq_tenant_module_settings_tenant_module"),
    )
    op.create_index("ix_tenant_module_settings_tenant_id", "tenant_module_settings", ["tenant_id"])
    op.create_index("ix_tenant_module_settings_module_key", "tenant_module_settings", ["module_key"])


def downgrade() -> None:
    op.drop_index("ix_tenant_module_settings_module_key", table_name="tenant_module_settings")
    op.drop_index("ix_tenant_module_settings_tenant_id", table_name="tenant_module_settings")
    op.drop_table("tenant_module_settings")
