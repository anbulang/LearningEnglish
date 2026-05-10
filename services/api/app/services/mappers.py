from __future__ import annotations

from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ParentCoachingScriptModel,
    PracticeSessionModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
    StoredAssetModel,
    WeeklyReportModel,
)
from app.models.contracts import (
    ChildProfile,
    CourseMaterial,
    DifficultyBand,
    JobStatus,
    KnowledgePack,
    MaterialImageRecord,
    MaterialParseJob,
    ParentAccount,
    ParentCoachingScript,
    ParentCoachingStep,
    PracticeSession,
    ReviewTask,
    ReviewTaskStatus,
    SentencePattern,
    SpeakingAttempt,
    SpeakingAttemptStatus,
    StoredAsset,
    TaskType,
    VocabularyItem,
    WeeklyReport,
)


def parent_account_from_model(model: ParentAccountModel) -> ParentAccount:
    return ParentAccount(
        id=model.id,
        display_name=model.display_name,
        avatar_url=model.avatar_url,
        phone_number=model.phone_number,
        phone_verified_at=model.phone_verified_at,
        wechat_union_id=model.wechat_union_id,
        wechat_open_id=model.wechat_open_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def child_profile_from_model(model: ChildProfileModel) -> ChildProfile:
    return ChildProfile(
        id=model.id,
        parent_account_id=model.parent_account_id,
        name=model.name,
        avatar_url=model.avatar_url,
        age=model.age,
        level=model.level,
        learning_goal=model.learning_goal,
        preferred_review_duration_minutes=model.preferred_review_duration_minutes,
        parent_notes=model.parent_notes,
    )


def stored_asset_from_model(model: StoredAssetModel) -> StoredAsset:
    return StoredAsset(
        id=model.id,
        owner_type=model.owner_type,
        owner_id=model.owner_id,
        bucket=model.bucket,
        object_key=model.object_key,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        url=model.url,
        created_at=model.created_at,
    )


def course_material_from_model(model: CourseMaterialModel, parse_job_id: str = "") -> CourseMaterial:
    return CourseMaterial(
        id=model.id,
        child_id=model.child_id,
        parse_job_id=parse_job_id,
        teacher_name=model.teacher_name,
        lesson_date=model.lesson_date,
        title=model.title,
        topic=model.topic,
        status=model.status,
        source_images=model.source_images or [],
        source_image_keys=model.source_image_keys or [],
        normalized_image_keys=model.normalized_image_keys or [],
        pdf_url=model.pdf_url,
        pdf_key=model.pdf_key,
        file_size_bytes=model.file_size_bytes,
        uploaded_at=model.uploaded_at,
        ocr_text=model.ocr_text,
        tags=model.tags or [],
        image_records=[MaterialImageRecord(**item) for item in (model.image_records or [])],
    )


def material_job_from_model(model: MaterialParseJobModel) -> MaterialParseJob:
    return MaterialParseJob(
        id=model.id,
        material_id=model.material_id,
        status=JobStatus(model.status),
        confidence_summary=model.confidence_summary,
        warnings=model.warnings or [],
        started_at=model.started_at,
        finished_at=model.finished_at,
        draft_title=model.draft_title,
        draft_topic=model.draft_topic,
        draft_vocabulary=model.draft_vocabulary or [],
        draft_sentences=model.draft_sentences or [],
        draft_image_records=[MaterialImageRecord(**item) for item in (model.draft_image_records or [])],
    )


def knowledge_pack_from_model(model: KnowledgePackModel) -> KnowledgePack:
    return KnowledgePack(
        id=model.id,
        material_id=model.material_id,
        topic=model.topic,
        difficulty_band=DifficultyBand(model.difficulty_band),
        lesson_summary=model.lesson_summary,
        review_recommendation=model.review_recommendation,
        vocabulary_items=[VocabularyItem(**item) for item in (model.vocabulary_items or [])],
        sentence_patterns=[SentencePattern(**item) for item in (model.sentence_patterns or [])],
    )


def review_task_from_model(model: ReviewTaskModel) -> ReviewTask:
    return ReviewTask(
        id=model.id,
        child_id=model.child_id,
        material_id=model.material_id,
        task_type=TaskType(model.task_type),
        difficulty=model.difficulty,
        content_json=model.content_json or {},
        due_date=model.due_date,
        status=ReviewTaskStatus(model.status),
    )


def practice_session_from_model(model: PracticeSessionModel) -> PracticeSession:
    return PracticeSession(
        id=model.id,
        child_id=model.child_id,
        review_task_ids=model.review_task_ids or [],
        started_at=model.started_at,
        completed_at=model.completed_at,
        score=model.score,
        weak_points=model.weak_points or [],
    )


def speaking_attempt_from_model(model: SpeakingAttemptModel) -> SpeakingAttempt:
    return SpeakingAttempt(
        id=model.id,
        child_id=model.child_id,
        material_id=model.material_id,
        prompt_text=model.prompt_text,
        audio_url=model.audio_url,
        transcript=model.transcript,
        pronunciation_score=model.pronunciation_score,
        feedback=model.feedback,
        status=SpeakingAttemptStatus(model.status),
    )


def parent_coaching_script_from_model(model: ParentCoachingScriptModel) -> ParentCoachingScript:
    return ParentCoachingScript(
        id=model.id,
        material_id=model.material_id,
        title=model.title,
        intro=model.intro,
        steps=[ParentCoachingStep(**item) for item in (model.steps or [])],
    )


def weekly_report_from_model(model: WeeklyReportModel) -> WeeklyReport:
    return WeeklyReport(
        id=model.id,
        child_id=model.child_id,
        week_start=model.week_start,
        week_end=model.week_end,
        completed_sessions=model.completed_sessions,
        reviewed_words=model.reviewed_words,
        speaking_attempts=model.speaking_attempts,
        weak_items=model.weak_items or [],
        recommended_actions=model.recommended_actions or [],
    )
