"""add admin impersonation sessions

Revision ID: 20260525_0007
Revises: 20260525_0006
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0007"
down_revision = "20260525_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_impersonation_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("target_parent_id", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["parent_accounts.id"]),
        sa.ForeignKeyConstraint(["target_parent_id"], ["parent_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_impersonation_sessions_tenant_id", "admin_impersonation_sessions", ["tenant_id"])
    op.create_index(
        "ix_admin_impersonation_sessions_target_parent_id",
        "admin_impersonation_sessions",
        ["target_parent_id"],
    )
    op.create_index("ix_admin_impersonation_sessions_actor_id", "admin_impersonation_sessions", ["actor_id"])
    op.create_index("ix_admin_impersonation_sessions_status", "admin_impersonation_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_admin_impersonation_sessions_status", table_name="admin_impersonation_sessions")
    op.drop_index("ix_admin_impersonation_sessions_actor_id", table_name="admin_impersonation_sessions")
    op.drop_index("ix_admin_impersonation_sessions_target_parent_id", table_name="admin_impersonation_sessions")
    op.drop_index("ix_admin_impersonation_sessions_tenant_id", table_name="admin_impersonation_sessions")
    op.drop_table("admin_impersonation_sessions")
