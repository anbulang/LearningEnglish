"""add SM-2 spaced-repetition state to review tasks

Revision ID: 20260731_0011
Revises: 20260728_0010
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260731_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_tasks", sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("review_tasks", sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"))
    op.add_column("review_tasks", sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("review_tasks", sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("review_tasks", "last_reviewed_at")
    op.drop_column("review_tasks", "interval_days")
    op.drop_column("review_tasks", "ease_factor")
    op.drop_column("review_tasks", "repetitions")
