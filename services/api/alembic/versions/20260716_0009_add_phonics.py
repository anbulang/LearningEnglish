"""add phonics curriculum tables

Revision ID: 20260716_0009
Revises: 20260529_0008
Create Date: 2026-07-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260716_0009"
down_revision = "20260529_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phonics_units",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("unit_code", sa.String(length=32), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("subtitle", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("level", sa.String(length=8), nullable=False, server_default="1"),
        sa.Column("content_version", sa.String(length=16), nullable=False, server_default="1"),
        sa.Column("content_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("media_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("media_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_phonics_units_unit_code", "phonics_units", ["unit_code"], unique=True)
    op.create_index("ix_phonics_units_sequence_order", "phonics_units", ["sequence_order"])

    op.create_table(
        "phonics_sound_cards",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("card_type", sa.String(length=16), nullable=False, server_default="consonant"),
        sa.Column("letter", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("phoneme", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("keyword", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("keyword_cn", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("articulation_cue", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("common_spellings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("speakable_sound", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("example_words", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("content_version", sa.String(length=16), nullable=False, server_default="1"),
        sa.Column("sound_audio_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("sound_audio_object_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("sound_tts_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("keyword_audio_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("keyword_audio_object_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("keyword_tts_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "child_phonics_progress",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("unit_id", sa.String(length=64), sa.ForeignKey("phonics_units.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="unlocked"),
        sa.Column("decoding_accuracy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("first_sound_accuracy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("grapheme_scores", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("blended_words", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("child_id", "unit_id", name="uq_child_phonics_progress_child_unit"),
    )
    op.create_index("ix_child_phonics_progress_child_id", "child_phonics_progress", ["child_id"])
    op.create_index("ix_child_phonics_progress_unit_id", "child_phonics_progress", ["unit_id"])

    op.create_table(
        "phonics_attempts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("unit_id", sa.String(length=64), sa.ForeignKey("phonics_units.id"), nullable=False),
        sa.Column("step", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("practice_type", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("target_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("item_results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("audio_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("audio_object_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("audio_content_type", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("audio_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audio_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transcript", sa.Text(), nullable=False, server_default=""),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("word_feedback", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("failure_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scored"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_phonics_attempts_child_id", "phonics_attempts", ["child_id"])
    op.create_index("ix_phonics_attempts_unit_id", "phonics_attempts", ["unit_id"])


def downgrade() -> None:
    op.drop_index("ix_phonics_attempts_unit_id", table_name="phonics_attempts")
    op.drop_index("ix_phonics_attempts_child_id", table_name="phonics_attempts")
    op.drop_table("phonics_attempts")
    op.drop_index("ix_child_phonics_progress_unit_id", table_name="child_phonics_progress")
    op.drop_index("ix_child_phonics_progress_child_id", table_name="child_phonics_progress")
    op.drop_table("child_phonics_progress")
    op.drop_table("phonics_sound_cards")
    op.drop_index("ix_phonics_units_sequence_order", table_name="phonics_units")
    op.drop_index("ix_phonics_units_unit_code", table_name="phonics_units")
    op.drop_table("phonics_units")
