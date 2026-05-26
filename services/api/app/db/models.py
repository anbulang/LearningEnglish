from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ParentAccountModel(Base):
    __tablename__ = "parent_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"parent_{uuid4().hex[:12]}")
    display_name: Mapped[str] = mapped_column(String(255), default="")
    avatar_url: Mapped[str] = mapped_column(Text, default="")
    phone_number: Mapped[str] = mapped_column(String(32), default="")
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    wechat_union_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    wechat_open_id: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"session_{uuid4().hex[:12]}")
    parent_account_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), index=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AdminUserModel(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active")
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AdminAuditEventModel(Base):
    __tablename__ = "admin_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"audit_{uuid4().hex[:12]}")
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_role: Mapped[str] = mapped_column(String(128))
    tenant_scope: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str] = mapped_column(String(128))
    resource_id: Mapped[str] = mapped_column(String(128))
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    result: Mapped[str] = mapped_column(String(32), default="success")
    reason: Mapped[str] = mapped_column(Text, default="")
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminImpersonationSessionModel(Base):
    __tablename__ = "admin_impersonation_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"imp_{uuid4().hex[:12]}")
    tenant_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    target_parent_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TenantProviderPolicyModel(Base):
    __tablename__ = "tenant_provider_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"policy_{uuid4().hex[:12]}")
    tenant_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), unique=True, index=True)
    ai_provider: Mapped[str] = mapped_column(String(32), default="stub")
    media_provider: Mapped[str] = mapped_column(String(32), default="mock")
    fallback_mode: Mapped[str] = mapped_column(String(64), default="global_stub")
    monthly_guardrail: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(64), default="tenant_override")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TenantModuleSettingModel(Base):
    __tablename__ = "tenant_module_settings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"module_{uuid4().hex[:12]}")
    tenant_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    module_key: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(64), default="tenant_override")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PhoneBindingModel(Base):
    __tablename__ = "phone_bindings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"binding_{uuid4().hex[:12]}")
    parent_account_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    otp_code: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChildProfileModel(Base):
    __tablename__ = "child_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"child_{uuid4().hex[:12]}")
    parent_account_id: Mapped[str] = mapped_column(ForeignKey("parent_accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str] = mapped_column(Text, default="")
    age: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(128))
    learning_goal: Mapped[str] = mapped_column(Text)
    preferred_review_duration_minutes: Mapped[int] = mapped_column(Integer, default=10)
    parent_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StoredAssetModel(Base):
    __tablename__ = "stored_assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"asset_{uuid4().hex[:12]}")
    owner_type: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    bucket: Mapped[str] = mapped_column(String(128))
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CourseMaterialModel(Base):
    __tablename__ = "course_materials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"material_{uuid4().hex[:12]}")
    child_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), index=True)
    teacher_name: Mapped[str] = mapped_column(String(255), default="")
    lesson_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    source_images: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_image_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    normalized_image_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    pdf_url: Mapped[str] = mapped_column(Text, default="")
    pdf_key: Mapped[str] = mapped_column(Text, default="")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_records: Mapped[list[dict]] = mapped_column(JSON, default=list)
    learning_assets: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MaterialParseJobModel(Base):
    __tablename__ = "material_parse_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"job_{uuid4().hex[:12]}")
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    confidence_summary: Mapped[str] = mapped_column(Text, default="")
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    draft_title: Mapped[str] = mapped_column(String(255), default="")
    draft_topic: Mapped[str] = mapped_column(String(255), default="")
    draft_vocabulary: Mapped[list[str]] = mapped_column(JSON, default=list)
    draft_sentences: Mapped[list[str]] = mapped_column(JSON, default=list)
    draft_image_records: Mapped[list[dict]] = mapped_column(JSON, default=list)
    draft_learning_assets: Mapped[list[dict]] = mapped_column(JSON, default=list)


class KnowledgePackModel(Base):
    __tablename__ = "knowledge_packs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"knowledge_{uuid4().hex[:12]}")
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(255))
    difficulty_band: Mapped[str] = mapped_column(String(64))
    lesson_summary: Mapped[str] = mapped_column(Text)
    review_recommendation: Mapped[str] = mapped_column(Text)
    vocabulary_items: Mapped[list[dict]] = mapped_column(JSON, default=list)
    sentence_patterns: Mapped[list[dict]] = mapped_column(JSON, default=list)


class ReviewTaskModel(Base):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"task_{uuid4().hex[:12]}")
    child_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(64))
    difficulty: Mapped[str] = mapped_column(String(64))
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="pending")


class PracticeSessionModel(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"session_{uuid4().hex[:12]}")
    child_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), index=True)
    review_task_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    weak_points: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeakingAttemptModel(Base):
    __tablename__ = "speaking_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"attempt_{uuid4().hex[:12]}")
    child_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), index=True)
    review_task_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    learning_asset_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    prompt_text: Mapped[str] = mapped_column(Text)
    target_text: Mapped[str] = mapped_column(Text, default="")
    audio_url: Mapped[str] = mapped_column(Text, default="")
    audio_object_key: Mapped[str] = mapped_column(Text, default="")
    audio_content_type: Mapped[str] = mapped_column(String(255), default="")
    audio_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    audio_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str] = mapped_column(Text, default="")
    pronunciation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fluency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")
    word_feedback: Mapped[list[dict]] = mapped_column(JSON, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(64), default="")
    raw_result: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ParentCoachingScriptModel(Base):
    __tablename__ = "parent_coaching_scripts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"coach_{uuid4().hex[:12]}")
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    intro: Mapped[str] = mapped_column(Text)
    steps: Mapped[list[dict]] = mapped_column(JSON, default=list)


class WeeklyReportModel(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"report_{uuid4().hex[:12]}")
    child_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), unique=True, index=True)
    week_start: Mapped[date] = mapped_column(Date)
    week_end: Mapped[date] = mapped_column(Date)
    completed_sessions: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_words: Mapped[int] = mapped_column(Integer, default=0)
    speaking_attempts: Mapped[int] = mapped_column(Integer, default=0)
    weak_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
