"""extend speaking attempts for uploaded audio assessment

Revision ID: 20260525_0004_speaking
Revises: 20260512_0003
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0004_speaking"
down_revision = "20260512_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speaking_attempts", sa.Column("review_task_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("learning_asset_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("target_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("audio_object_key", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "speaking_attempts",
        sa.Column("audio_content_type", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column("speaking_attempts", sa.Column("audio_size_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("speaking_attempts", sa.Column("audio_duration_ms", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("speaking_attempts", sa.Column("overall_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("accuracy_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("fluency_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("completeness_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("word_feedback", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("speaking_attempts", sa.Column("suggestions", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("speaking_attempts", sa.Column("provider", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("raw_result", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("speaking_attempts", sa.Column("failure_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "speaking_attempts",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_speaking_attempts_review_task_id"),
        "speaking_attempts",
        ["review_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_speaking_attempts_learning_asset_id"),
        "speaking_attempts",
        ["learning_asset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_speaking_attempts_learning_asset_id"), table_name="speaking_attempts")
    op.drop_index(op.f("ix_speaking_attempts_review_task_id"), table_name="speaking_attempts")
    op.drop_column("speaking_attempts", "updated_at")
    op.drop_column("speaking_attempts", "failure_reason")
    op.drop_column("speaking_attempts", "raw_result")
    op.drop_column("speaking_attempts", "provider")
    op.drop_column("speaking_attempts", "suggestions")
    op.drop_column("speaking_attempts", "word_feedback")
    op.drop_column("speaking_attempts", "completeness_score")
    op.drop_column("speaking_attempts", "fluency_score")
    op.drop_column("speaking_attempts", "accuracy_score")
    op.drop_column("speaking_attempts", "overall_score")
    op.drop_column("speaking_attempts", "audio_duration_ms")
    op.drop_column("speaking_attempts", "audio_size_bytes")
    op.drop_column("speaking_attempts", "audio_content_type")
    op.drop_column("speaking_attempts", "audio_object_key")
    op.drop_column("speaking_attempts", "target_text")
    op.drop_column("speaking_attempts", "learning_asset_id")
    op.drop_column("speaking_attempts", "review_task_id")
