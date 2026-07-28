"""add per-child phonics accent + per-accent sound-card audio

Revision ID: 20260728_0010
Revises: 20260716_0009
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260728_0010"
down_revision = "20260716_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "child_profiles",
        sa.Column("accent", sa.String(length=8), nullable=False, server_default="us"),
    )
    op.add_column(
        "phonics_sound_cards",
        sa.Column("audio_variants", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("phonics_sound_cards", "audio_variants")
    op.drop_column("child_profiles", "accent")
