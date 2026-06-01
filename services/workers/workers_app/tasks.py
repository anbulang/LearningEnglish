from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Optional

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session


API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
    StoredAssetModel,
    WeeklyReportModel,
)
from app.models.contracts import (
    JobStatus,
    LearningAsset,
    MaterialStatus,
    MediaGenerationStatus,
    PrimaryAccent,
    SpeakingAttemptStatus,
)
from app.services.shared.learning_asset_media import MediaProviderConfigurationError, build_media_provider_bundle
from app.services.shared.mappers import course_material_from_model, material_job_from_model
from app.services.shared.pipeline import build_pipeline_service
from app.services.shared.speaking_assessment import (
    SpeechAssessmentError,
    build_speech_assessment_audio_url,
    build_speech_assessment_provider,
)
from app.services.shared.storage import get_storage_service


@shared_task(name="materials.process_material_job")
def process_material_job(job_id: str) -> dict[str, str]:
    pipeline = build_pipeline_service()
    storage = get_storage_service()
    db = SessionLocal()
    try:
        row = db.execute(
            select(MaterialParseJobModel, CourseMaterialModel)
            .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
            .where(MaterialParseJobModel.id == job_id)
        ).first()
        if row is None:
            raise ValueError("Material job not found")
        job, material = row
        if material.status == MaterialStatus.archived.value:
            return {"job_id": job.id, "status": "archived"}
        if job.status not in {JobStatus.queued.value, JobStatus.processing.value}:
            return {"job_id": job.id, "status": job.status}

        asset_rows = db.scalars(
            select(StoredAssetModel).where(
                StoredAssetModel.owner_type == "material",
                StoredAssetModel.owner_id == material.id,
            )
        ).all()
        local_paths = [storage.resolve_local_path(asset) for asset in asset_rows]
        try:
            prepared = pipeline.prepare_job(
                course_material_from_model(material),
                material_job_from_model(job),
                local_paths=local_paths,
            )
        except Exception as exc:
            db.refresh(material)
            if material.status == MaterialStatus.archived.value:
                return {"job_id": job.id, "status": "archived"}
            job.status = JobStatus.failed.value
            job.finished_at = None
            job.confidence_summary = f"处理失败：{exc}"
            job.warnings = [f"处理失败：{exc}", "请检查 AI provider 配置或稍后重试。"]
            material.status = MaterialStatus.failed.value
            db.add_all([job, material])
            db.commit()
            return {"job_id": job.id, "status": job.status}
        db.refresh(material)
        if material.status == MaterialStatus.archived.value:
            return {"job_id": job.id, "status": "archived"}
        job.status = prepared.status.value
        job.finished_at = prepared.finished_at
        job.draft_title = prepared.draft_title
        job.draft_topic = prepared.draft_topic
        job.draft_vocabulary = prepared.draft_vocabulary
        job.draft_sentences = prepared.draft_sentences
        job.draft_image_records = [item.model_dump() for item in prepared.draft_image_records]
        job.draft_learning_assets = [item.model_dump(mode="json") for item in prepared.draft_learning_assets]
        job.confidence_summary = prepared.confidence_summary
        job.warnings = prepared.warnings
        material.status = MaterialStatus.needs_review.value
        material.ocr_text = " ".join(prepared.draft_vocabulary + prepared.draft_sentences)
        material.topic = prepared.draft_topic or material.topic
        material.image_records = [item.model_dump() for item in prepared.draft_image_records]
        db.add_all([job, material])
        db.commit()
        return {"job_id": job.id, "status": job.status}
    finally:
        db.close()


@shared_task(name="speaking.score_attempt")
def score_speaking_attempt(attempt_id: str) -> dict[str, str]:
    db = SessionLocal()
    provider = None
    try:
        row = db.execute(
            select(SpeakingAttemptModel, CourseMaterialModel)
            .join(CourseMaterialModel, CourseMaterialModel.id == SpeakingAttemptModel.material_id)
            .where(SpeakingAttemptModel.id == attempt_id)
        ).first()
        if row is None:
            return {"attempt_id": attempt_id, "status": "missing"}
        attempt, material = row
        if material.status == MaterialStatus.archived.value:
            return {"attempt_id": attempt.id, "status": "archived"}
        if attempt.status not in {
            SpeakingAttemptStatus.queued.value,
            SpeakingAttemptStatus.recording_uploaded.value,
        }:
            return {"attempt_id": attempt.id, "status": attempt.status}

        attempt.status = SpeakingAttemptStatus.transcribing.value
        db.add(attempt)
        db.commit()

        storage = get_storage_service()
        audio_asset = db.scalar(
            select(StoredAssetModel).where(
                StoredAssetModel.owner_type == "speaking_attempt",
                StoredAssetModel.owner_id == attempt.id,
                StoredAssetModel.object_key == attempt.audio_object_key,
            )
        )
        if audio_asset is None:
            raise SpeechAssessmentError("录音文件不存在。")
        audio_path = storage.resolve_local_path(audio_asset)
        settings = get_settings()
        assessment_audio_url = build_speech_assessment_audio_url(
            stored_audio_url=attempt.audio_url,
            object_key=attempt.audio_object_key,
            public_base_url=settings.speech_assessment_audio_public_base_url,
        )
        provider = build_speech_assessment_provider()
        result = provider.assess(
            audio_path=audio_path,
            audio_url=assessment_audio_url,
            target_text=attempt.target_text or attempt.prompt_text,
            prompt_text=attempt.prompt_text,
            attempt_id=attempt.id,
            accent=settings.speech_assessment_default_accent,
        )

        db.refresh(material)
        if material.status == MaterialStatus.archived.value:
            return {"attempt_id": attempt.id, "status": "archived"}
        attempt.status = SpeakingAttemptStatus.scored.value
        attempt.transcript = result.transcript
        attempt.overall_score = result.overall_score
        attempt.pronunciation_score = result.pronunciation_score
        attempt.accuracy_score = result.accuracy_score
        attempt.fluency_score = result.fluency_score
        attempt.completeness_score = result.completeness_score
        attempt.feedback = result.feedback
        attempt.word_feedback = [item.model_dump(mode="json") for item in result.word_feedback]
        attempt.suggestions = result.suggestions
        attempt.provider = result.provider
        attempt.raw_result = result.raw_result
        attempt.failure_reason = ""
        _update_speaking_report(db, attempt)
        db.add(attempt)
        db.commit()
        return {"attempt_id": attempt.id, "status": attempt.status}
    except Exception as exc:
        attempt = db.get(SpeakingAttemptModel, attempt_id)
        if attempt is not None:
            attempt.status = SpeakingAttemptStatus.failed.value
            attempt.failure_reason = f"口语评分失败：{exc}"
            attempt.feedback = "口语评分失败，请稍后重试。"
            db.add(attempt)
            db.commit()
        return {"attempt_id": attempt_id, "status": "failed"}
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
        db.close()


@shared_task(name="materials.process_learning_asset_media")
def process_learning_asset_media(material_id: str) -> dict[str, str]:
    db = SessionLocal()
    bundle = None
    try:
        material = db.get(CourseMaterialModel, material_id)
        if material is None:
            return {"material_id": material_id, "status": "missing"}
        if material.status == MaterialStatus.archived.value:
            return {"material_id": material_id, "status": "archived"}
        assets = [LearningAsset(**item) for item in (material.learning_assets or [])]
        if not assets:
            return {"material_id": material_id, "status": "empty"}

        processing_assets = [
            asset.model_copy(
                update={
                    "generated_image_status": MediaGenerationStatus.processing,
                    "tts_us_status": MediaGenerationStatus.processing,
                    "tts_uk_status": MediaGenerationStatus.processing,
                }
            )
            for asset in assets
        ]
        db.refresh(material)
        if material.status == MaterialStatus.archived.value:
            return {"material_id": material_id, "status": "archived"}
        material.learning_assets = [asset.model_dump(mode="json") for asset in processing_assets]
        db.add(material)
        db.commit()

        storage = get_storage_service()
        source_assets = db.scalars(
            select(StoredAssetModel)
            .where(
                StoredAssetModel.owner_type == "material",
                StoredAssetModel.owner_id == material.id,
            )
            .order_by(StoredAssetModel.created_at, StoredAssetModel.id)
        ).all()
        try:
            bundle = build_media_provider_bundle()
        except MediaProviderConfigurationError:
            return _fail_media_bundle_build(
                db,
                material,
                material_id,
                assets,
                _MEDIA_CONFIGURATION_ERROR_MESSAGE,
            )
        except Exception:
            return _fail_media_bundle_build(
                db,
                material,
                material_id,
                assets,
                "媒体生成失败，请稍后重试或联系老师。",
            )
        updated_assets: list[LearningAsset] = []
        try:
            if _should_apply_mock_manifest(bundle):
                updated_assets = bundle.image_provider.apply(processing_assets)
            else:
                with tempfile.TemporaryDirectory(prefix=f"media-{material_id}-") as temp_dir:
                    work_dir = Path(temp_dir)
                    for asset in processing_assets:
                        reference_image_path = _build_reference_image(asset, source_assets, work_dir, storage=storage)
                        updated_asset = asset

                        try:
                            generated_image = bundle.image_provider.generate(
                                asset,
                                _image_prompt(asset),
                                reference_image_path,
                            )
                            _ensure_material_not_archived(db, material.id)
                            image_asset = _save_generated_media_asset(
                                db,
                                storage,
                                owner_id=material.id,
                                object_key=_media_object_key(
                                    material.id,
                                    asset.id,
                                    "image",
                                    generated_image.extension,
                                ),
                                content_type=generated_image.content_type,
                                payload=generated_image.payload,
                            )
                            updated_asset = updated_asset.model_copy(
                                update={
                                    "generated_image_status": MediaGenerationStatus.ready,
                                    "generated_image_url": image_asset.url,
                                    "generated_image_object_key": image_asset.object_key,
                                    "generated_image_error": "",
                                }
                            )
                        except _ArchivedDuringMediaGeneration:
                            raise
                        except Exception as exc:
                            updated_asset = updated_asset.model_copy(
                                update={
                                    "generated_image_status": MediaGenerationStatus.failed,
                                    "generated_image_error": f"图片生成失败：{exc}",
                                }
                            )

                        for accent in ("us", "uk"):
                            try:
                                generated_audio = bundle.tts_provider.synthesize(
                                    _pronunciation_text(asset),
                                    accent,
                                )
                                _ensure_material_not_archived(db, material.id)
                                audio_asset = _save_generated_media_asset(
                                    db,
                                    storage,
                                    owner_id=material.id,
                                    object_key=_media_object_key(
                                        material.id,
                                        asset.id,
                                        f"tts-{accent}",
                                        generated_audio.extension,
                                    ),
                                    content_type=generated_audio.content_type,
                                    payload=generated_audio.payload,
                                )
                                updated_asset = updated_asset.model_copy(
                                    update={
                                        f"tts_{accent}_status": MediaGenerationStatus.ready,
                                        f"tts_{accent}_url": audio_asset.url,
                                        f"tts_{accent}_object_key": audio_asset.object_key,
                                        f"tts_{accent}_error": "",
                                    }
                                )
                            except _ArchivedDuringMediaGeneration:
                                raise
                            except Exception as exc:
                                updated_asset = updated_asset.model_copy(
                                    update={
                                        f"tts_{accent}_status": MediaGenerationStatus.failed,
                                        f"tts_{accent}_error": f"{accent.upper()} 音频生成失败：{exc}",
                                    }
                                )

                        updated_assets.append(updated_asset)
            status_value = _status_for_assets(updated_assets)
        except _ArchivedDuringMediaGeneration:
            return {"material_id": material_id, "status": "archived"}
        finally:
            bundle.close()

        db.expire_all()
        current_material = db.get(CourseMaterialModel, material_id)
        if current_material is not None and current_material.status == MaterialStatus.archived.value:
            return {"material_id": material_id, "status": "archived"}
        current_assets = [
            LearningAsset(**item)
            for item in ((current_material.learning_assets if current_material is not None else None) or [])
        ]
        updated_assets = _merge_generated_media_updates(updated_assets, current_assets)
        target_material = current_material or material
        target_material.learning_assets = [asset.model_dump(mode="json") for asset in updated_assets]
        db.add(target_material)
        _backfill_generated_media(db, target_material.id, updated_assets)
        db.commit()
        return {"material_id": material_id, "status": status_value}
    finally:
        db.close()


def _update_speaking_report(db: Session, attempt: SpeakingAttemptModel) -> None:
    child = db.get(ChildProfileModel, attempt.child_id)
    if child is None:
        return
    report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == attempt.child_id))
    if report is None:
        week_start = child.created_at.date()
        report = WeeklyReportModel(
            child_id=attempt.child_id,
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            recommended_actions=["保持每周至少完成一次口语跟读。"],
        )
        db.add(report)
    report.speaking_attempts = (report.speaking_attempts or 0) + 1
    weak_words = [
        item.get("word", "")
        for item in (attempt.word_feedback or [])
        if item.get("status") == "needs_practice" and item.get("word")
    ]
    report.weak_items = list(dict.fromkeys([*(report.weak_items or []), *weak_words]))
    db.add(report)


class _ArchivedDuringMediaGeneration(Exception):
    pass


_MEDIA_CONFIGURATION_ERROR_MESSAGE = "媒体生成配置失败，请检查服务端媒体 provider 配置后重试。"


def _should_apply_mock_manifest(bundle) -> bool:
    return getattr(bundle, "mode", "") == "mock" and callable(getattr(bundle.image_provider, "apply", None))


def _ensure_material_not_archived(db, material_id: str) -> None:
    db.expire_all()
    material = db.get(CourseMaterialModel, material_id)
    if material is not None and material.status == MaterialStatus.archived.value:
        raise _ArchivedDuringMediaGeneration()


def _fail_media_bundle_build(
    db,
    material: CourseMaterialModel,
    material_id: str,
    assets: list[LearningAsset],
    message: str,
) -> dict[str, str]:
    db.expire_all()
    current_material = db.get(CourseMaterialModel, material_id)
    if current_material is not None and current_material.status == MaterialStatus.archived.value:
        return {"material_id": material_id, "status": "archived"}
    current_assets = [
        LearningAsset(**item)
        for item in ((current_material.learning_assets if current_material is not None else None) or [])
    ]
    failed_assets = _mark_all_media_failed(assets, message)
    target_material = current_material or material
    target_material.learning_assets = [
        asset.model_dump(mode="json")
        for asset in _merge_generated_media_updates(failed_assets, current_assets)
    ]
    db.add(target_material)
    db.commit()
    return {"material_id": material_id, "status": "failed"}


def _mark_all_media_failed(assets: list[LearningAsset], message: str) -> list[LearningAsset]:
    return [
        asset.model_copy(
            update={
                **_failed_media_update(
                    asset.generated_image_status,
                    status_key="generated_image_status",
                    error_key="generated_image_error",
                    message=message,
                ),
                **_failed_media_update(
                    asset.tts_us_status,
                    status_key="tts_us_status",
                    error_key="tts_us_error",
                    message=message,
                ),
                **_failed_media_update(
                    asset.tts_uk_status,
                    status_key="tts_uk_status",
                    error_key="tts_uk_error",
                    message=message,
                ),
            }
        )
        for asset in assets
    ]


def _failed_media_update(
    status: MediaGenerationStatus,
    *,
    status_key: str,
    error_key: str,
    message: str,
) -> dict[str, object]:
    if status == MediaGenerationStatus.ready:
        return {}
    return {
        status_key: MediaGenerationStatus.failed,
        error_key: message,
    }


def _save_generated_media_asset(
    db,
    storage,
    *,
    owner_id: str,
    object_key: str,
    content_type: str,
    payload: bytes,
) -> StoredAssetModel:
    saved = storage.save_bytes(
        owner_type="generated_media",
        owner_id=owner_id,
        object_key=object_key,
        content_type=content_type,
        payload=payload,
    )
    existing = db.scalar(select(StoredAssetModel).where(StoredAssetModel.object_key == saved.object_key))
    if existing is None:
        db.add(saved)
        return saved
    existing.owner_type = saved.owner_type
    existing.owner_id = saved.owner_id
    existing.bucket = saved.bucket
    existing.content_type = saved.content_type
    existing.size_bytes = saved.size_bytes
    existing.url = saved.url
    db.add(existing)
    return existing


def _backfill_generated_media(db, material_id: str, assets: list[LearningAsset]) -> None:
    asset_by_id = {asset.id: asset for asset in assets}
    asset_by_text = {asset.text.strip().lower(): asset for asset in assets if asset.text.strip()}

    knowledge_pack = db.scalar(select(KnowledgePackModel).where(KnowledgePackModel.material_id == material_id))
    if knowledge_pack is not None:
        vocabulary_items = []
        for item in knowledge_pack.vocabulary_items or []:
            asset = asset_by_text.get(str(item.get("word", "")).strip().lower())
            vocabulary_items.append(_with_generated_media(item, asset))
        sentence_patterns = []
        for item in knowledge_pack.sentence_patterns or []:
            asset = asset_by_text.get(str(item.get("sentence", "")).strip().lower())
            sentence_patterns.append(_with_generated_media(item, asset))
        knowledge_pack.vocabulary_items = vocabulary_items
        knowledge_pack.sentence_patterns = sentence_patterns
        db.add(knowledge_pack)

    review_tasks = db.scalars(select(ReviewTaskModel).where(ReviewTaskModel.material_id == material_id)).all()
    for task in review_tasks:
        content = dict(task.content_json or {})
        asset = asset_by_id.get(str(content.get("asset_id", "")))
        if asset is None:
            asset = asset_by_text.get(str(content.get("text") or content.get("word") or "").strip().lower())
        task.content_json = _with_generated_media(content, asset)
        db.add(task)


def _merge_generated_media_updates(
    generated_assets: list[LearningAsset],
    current_assets: list[LearningAsset],
) -> list[LearningAsset]:
    current_by_id = {asset.id: asset for asset in current_assets}
    merged: list[LearningAsset] = []
    for generated in generated_assets:
        current = current_by_id.get(generated.id)
        if current is None:
            merged.append(generated)
            continue
        merged.append(
            current.model_copy(
                update={
                    "translation": generated.translation or current.translation,
                    "kind": generated.kind or current.kind,
                    "source_page_index": generated.source_page_index,
                    "source_bbox": generated.source_bbox or current.source_bbox,
                    "source_visual_description": generated.source_visual_description
                    or current.source_visual_description,
                    "generated_image_status": generated.generated_image_status,
                    "generated_image_url": generated.generated_image_url,
                    "generated_image_object_key": generated.generated_image_object_key,
                    "generated_image_error": generated.generated_image_error,
                    "tts_us_status": generated.tts_us_status,
                    "tts_us_url": generated.tts_us_url,
                    "tts_us_object_key": generated.tts_us_object_key,
                    "tts_us_error": generated.tts_us_error,
                    "tts_uk_status": generated.tts_uk_status,
                    "tts_uk_url": generated.tts_uk_url,
                    "tts_uk_object_key": generated.tts_uk_object_key,
                    "tts_uk_error": generated.tts_uk_error,
                }
            )
        )
    return merged


def _image_prompt(asset: LearningAsset) -> str:
    if asset.image_prompt.strip():
        return asset.image_prompt.strip()
    details = [f"Create a child-friendly English learning flashcard image for: {asset.text}."]
    if asset.translation.strip():
        details.append(f"Chinese meaning: {asset.translation}.")
    if asset.source_visual_description.strip():
        details.append(f"Use this worksheet context: {asset.source_visual_description}.")
    details.append("Avoid text labels in the image; make the concept clear and safe for young learners.")
    return " ".join(details)


def _pronunciation_text(asset: LearningAsset) -> str:
    return asset.pronunciation_text.strip() or asset.text.strip()


def _media_object_key(material_id: str, asset_id: str, stem: str, extension: str) -> str:
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    return f"generated/media/{material_id}/{asset_id}/{stem}{normalized_extension}"


def _build_reference_image(asset: LearningAsset, source_assets: list[StoredAssetModel], work_dir: Path, *, storage) -> Optional[Path]:
    if asset.source_bbox is None:
        return None
    try:
        from app.services.shared.media_reference import build_reference_image
    except ImportError:
        return None

    return build_reference_image(asset, source_assets, work_dir, storage=storage)


def _status_for_assets(assets: list[LearningAsset]) -> str:
    statuses = [
        status
        for asset in assets
        for status in (asset.generated_image_status, asset.tts_us_status, asset.tts_uk_status)
    ]
    if statuses and all(status == MediaGenerationStatus.ready for status in statuses):
        return "ready"
    if any(status == MediaGenerationStatus.ready for status in statuses):
        return "partial"
    return "failed"


def _with_generated_media(item: dict, asset: Optional[LearningAsset]) -> dict:
    if asset is None:
        return dict(item)
    updated = dict(item)
    if asset.generated_image_url:
        updated["image_url"] = asset.generated_image_url
    audio_url = _primary_accent_audio_url(asset)
    if audio_url:
        updated["audio_url"] = audio_url
    return updated


def _primary_accent_audio_url(asset: LearningAsset) -> str:
    if asset.primary_accent == PrimaryAccent.uk:
        return asset.tts_uk_url or asset.tts_us_url
    return asset.tts_us_url or asset.tts_uk_url


@shared_task(name="reporting.aggregate_weekly_report")
def aggregate_weekly_report(child_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == child_id))
        child = db.scalar(select(ChildProfileModel).where(ChildProfileModel.id == child_id))
        if report is None or child is None:
            return {"child_id": child_id, "status": "missing"}
        report.recommended_actions = [
            "继续保持每周至少两次复习。",
            f"优先复习薄弱项：{', '.join((report.weak_items or [])[:3]) or '暂无'}。",
        ]
        db.add(report)
        db.commit()
        return {"child_id": child_id, "status": "aggregated"}
    finally:
        db.close()


@shared_task(name="materials.enhance_images")
def enhance_images(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "enhanced"}


@shared_task(name="materials.run_ocr")
def run_ocr(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "ocr_complete"}


@shared_task(name="knowledge.parse_material")
def parse_material(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "parsed"}


@shared_task(name="review.generate_tasks")
def generate_review_tasks(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "review_tasks_generated"}


@shared_task(name="speaking.generate_tts")
def generate_tts(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "tts_generated"}
