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
    # Legacy rows were seeded with week_start = created_at.date() (any weekday).
    # Normalize to the ISO week (Monday..Sunday) BEFORE adding the composite unique,
    # so a later write keyed on Monday doesn't create a duplicate row for the same
    # week. Each child had at most one legacy row, so this can't collide.
    op.execute(
        """
        UPDATE weekly_reports
        SET week_start = (date_trunc('week', week_start::timestamp))::date,
            week_end   = (date_trunc('week', week_start::timestamp))::date + INTERVAL '6 days'
        """
    )
    op.create_unique_constraint(
        "uq_weekly_reports_child_week", "weekly_reports", ["child_id", "week_start"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_weekly_reports_child_week", "weekly_reports", type_="unique")
    # Restoring the per-child unique index requires collapsing multi-week history:
    # keep each child's most recent week, drop the rest (lossy by nature of the rollback).
    op.execute(
        """
        DELETE FROM weekly_reports w
        USING (
            SELECT child_id, MAX(week_start) AS keep_week
            FROM weekly_reports
            GROUP BY child_id
        ) latest
        WHERE w.child_id = latest.child_id
          AND w.week_start <> latest.keep_week
        """
    )
    op.drop_index("ix_weekly_reports_child_id", table_name="weekly_reports")
    op.create_index("ix_weekly_reports_child_id", "weekly_reports", ["child_id"], unique=True)
