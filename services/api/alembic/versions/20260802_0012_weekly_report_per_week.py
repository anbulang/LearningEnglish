"""rekey weekly_reports to one row per (child, ISO week)

Drops the single-report-per-child unique index and replaces it with a composite
unique on (child_id, week_start), enabling multi-week parent trends. child_id
keeps a plain (non-unique) index for FK lookups.

Revision ID: 20260802_0012
Revises: 20260731_0011
Create Date: 2026-08-02
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0012"
down_revision = "20260731_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_weekly_reports_child_id", table_name="weekly_reports")
    op.create_index("ix_weekly_reports_child_id", "weekly_reports", ["child_id"], unique=False)
    op.create_unique_constraint(
        "uq_weekly_reports_child_week", "weekly_reports", ["child_id", "week_start"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_weekly_reports_child_week", "weekly_reports", type_="unique")
    op.drop_index("ix_weekly_reports_child_id", table_name="weekly_reports")
    op.create_index("ix_weekly_reports_child_id", "weekly_reports", ["child_id"], unique=True)
