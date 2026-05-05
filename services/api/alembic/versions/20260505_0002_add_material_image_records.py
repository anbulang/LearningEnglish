"""add material image records

Revision ID: 20260505_0002
Revises: 20260327_0001
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260505_0002"
down_revision = "20260327_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "course_materials",
        sa.Column("image_records", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "material_parse_jobs",
        sa.Column("draft_image_records", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("material_parse_jobs", "draft_image_records")
    op.drop_column("course_materials", "image_records")
