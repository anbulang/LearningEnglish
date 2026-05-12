"""add learning assets

Revision ID: 20260512_0003
Revises: 20260505_0002
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_0003"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "course_materials",
        sa.Column("learning_assets", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "material_parse_jobs",
        sa.Column("draft_learning_assets", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("material_parse_jobs", "draft_learning_assets")
    op.drop_column("course_materials", "learning_assets")
