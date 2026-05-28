"""add admin audit search indexes

Revision ID: 20260529_0008
Revises: 20260525_0007
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op


revision = "20260529_0008"
down_revision = "20260525_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_admin_audit_events_tenant_scope_created_id",
        "admin_audit_events",
        ["tenant_scope", "created_at", "id"],
    )
    op.create_index(
        "ix_admin_audit_events_actor_id_created_id",
        "admin_audit_events",
        ["actor_id", "created_at", "id"],
    )
    op.create_index(
        "ix_admin_audit_events_action_created_id",
        "admin_audit_events",
        ["action", "created_at", "id"],
    )
    op.create_index(
        "ix_admin_audit_events_result_created_id",
        "admin_audit_events",
        ["result", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_events_result_created_id", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_action_created_id", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_actor_id_created_id", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_tenant_scope_created_id", table_name="admin_audit_events")
