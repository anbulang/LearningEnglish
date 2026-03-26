"""initial mvp schema

Revision ID: 20260327_0001
Revises:
Create Date: 2026-03-27 00:01:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_accounts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("avatar_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("phone_number", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wechat_union_id", sa.String(length=255), nullable=False),
        sa.Column("wechat_open_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parent_accounts_wechat_union_id", "parent_accounts", ["wechat_union_id"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("parent_account_id", sa.String(length=64), sa.ForeignKey("parent_accounts.id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False, server_default=""),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_parent_account_id", "auth_sessions", ["parent_account_id"])
    op.create_index("ix_auth_sessions_refresh_token_hash", "auth_sessions", ["refresh_token_hash"])

    op.create_table(
        "phone_bindings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("parent_account_id", sa.String(length=64), sa.ForeignKey("parent_accounts.id"), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("otp_code", sa.String(length=12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_phone_bindings_parent_account_id", "phone_bindings", ["parent_account_id"])
    op.create_index("ix_phone_bindings_phone_number", "phone_bindings", ["phone_number"])

    op.create_table(
        "child_profiles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("parent_account_id", sa.String(length=64), sa.ForeignKey("parent_accounts.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=128), nullable=False),
        sa.Column("learning_goal", sa.Text(), nullable=False),
        sa.Column("preferred_review_duration_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("parent_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_child_profiles_parent_account_id", "child_profiles", ["parent_account_id"])

    op.create_table(
        "stored_assets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stored_assets_object_key", "stored_assets", ["object_key"], unique=True)
    op.create_index("ix_stored_assets_owner_type", "stored_assets", ["owner_type"])
    op.create_index("ix_stored_assets_owner_id", "stored_assets", ["owner_id"])

    op.create_table(
        "course_materials",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("teacher_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("lesson_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("source_images", sa.JSON(), nullable=False),
        sa.Column("source_image_keys", sa.JSON(), nullable=False),
        sa.Column("normalized_image_keys", sa.JSON(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("pdf_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_course_materials_child_id", "course_materials", ["child_id"])

    op.create_table(
        "material_parse_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("material_id", sa.String(length=64), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("confidence_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draft_title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("draft_topic", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("draft_vocabulary", sa.JSON(), nullable=False),
        sa.Column("draft_sentences", sa.JSON(), nullable=False),
    )
    op.create_index("ix_material_parse_jobs_material_id", "material_parse_jobs", ["material_id"], unique=True)

    op.create_table(
        "knowledge_packs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("material_id", sa.String(length=64), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("difficulty_band", sa.String(length=64), nullable=False),
        sa.Column("lesson_summary", sa.Text(), nullable=False),
        sa.Column("review_recommendation", sa.Text(), nullable=False),
        sa.Column("vocabulary_items", sa.JSON(), nullable=False),
        sa.Column("sentence_patterns", sa.JSON(), nullable=False),
    )
    op.create_index("ix_knowledge_packs_material_id", "knowledge_packs", ["material_id"], unique=True)

    op.create_table(
        "review_tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("material_id", sa.String(length=64), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("difficulty", sa.String(length=64), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_review_tasks_child_id", "review_tasks", ["child_id"])
    op.create_index("ix_review_tasks_material_id", "review_tasks", ["material_id"])

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("review_task_ids", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weak_points", sa.JSON(), nullable=False),
    )
    op.create_index("ix_practice_sessions_child_id", "practice_sessions", ["child_id"])

    op.create_table(
        "speaking_attempts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("material_id", sa.String(length=64), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("transcript", sa.Text(), nullable=False, server_default=""),
        sa.Column("pronunciation_score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_speaking_attempts_child_id", "speaking_attempts", ["child_id"])
    op.create_index("ix_speaking_attempts_material_id", "speaking_attempts", ["material_id"])

    op.create_table(
        "parent_coaching_scripts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("material_id", sa.String(length=64), sa.ForeignKey("course_materials.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("intro", sa.Text(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
    )
    op.create_index("ix_parent_coaching_scripts_material_id", "parent_coaching_scripts", ["material_id"], unique=True)

    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("child_id", sa.String(length=64), sa.ForeignKey("child_profiles.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("completed_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reviewed_words", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speaking_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weak_items", sa.JSON(), nullable=False),
        sa.Column("recommended_actions", sa.JSON(), nullable=False),
    )
    op.create_index("ix_weekly_reports_child_id", "weekly_reports", ["child_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_weekly_reports_child_id", table_name="weekly_reports")
    op.drop_table("weekly_reports")
    op.drop_index("ix_parent_coaching_scripts_material_id", table_name="parent_coaching_scripts")
    op.drop_table("parent_coaching_scripts")
    op.drop_index("ix_speaking_attempts_material_id", table_name="speaking_attempts")
    op.drop_index("ix_speaking_attempts_child_id", table_name="speaking_attempts")
    op.drop_table("speaking_attempts")
    op.drop_index("ix_practice_sessions_child_id", table_name="practice_sessions")
    op.drop_table("practice_sessions")
    op.drop_index("ix_review_tasks_material_id", table_name="review_tasks")
    op.drop_index("ix_review_tasks_child_id", table_name="review_tasks")
    op.drop_table("review_tasks")
    op.drop_index("ix_knowledge_packs_material_id", table_name="knowledge_packs")
    op.drop_table("knowledge_packs")
    op.drop_index("ix_material_parse_jobs_material_id", table_name="material_parse_jobs")
    op.drop_table("material_parse_jobs")
    op.drop_index("ix_course_materials_child_id", table_name="course_materials")
    op.drop_table("course_materials")
    op.drop_index("ix_stored_assets_owner_id", table_name="stored_assets")
    op.drop_index("ix_stored_assets_owner_type", table_name="stored_assets")
    op.drop_index("ix_stored_assets_object_key", table_name="stored_assets")
    op.drop_table("stored_assets")
    op.drop_index("ix_child_profiles_parent_account_id", table_name="child_profiles")
    op.drop_table("child_profiles")
    op.drop_index("ix_phone_bindings_phone_number", table_name="phone_bindings")
    op.drop_index("ix_phone_bindings_parent_account_id", table_name="phone_bindings")
    op.drop_table("phone_bindings")
    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_parent_account_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_parent_accounts_wechat_union_id", table_name="parent_accounts")
    op.drop_table("parent_accounts")
