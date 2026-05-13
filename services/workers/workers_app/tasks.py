from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from celery import shared_task
from sqlalchemy import select


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
    StoredAssetModel,
    WeeklyReportModel,
)
from app.models.contracts import JobStatus, LearningAsset, MaterialStatus, MediaGenerationStatus, PrimaryAccent
from app.services.learning_asset_media import HN014MockMediaProvider
from app.services.mappers import course_material_from_model, material_job_from_model
from app.services.pipeline import build_pipeline_service
from app.services.storage import get_storage_service


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
            job.status = JobStatus.failed.value
            job.finished_at = None
            job.confidence_summary = f"处理失败：{exc}"
            job.warnings = [f"处理失败：{exc}", "请检查 AI provider 配置或稍后重试。"]
            material.status = MaterialStatus.failed.value
            db.add_all([job, material])
            db.commit()
            return {"job_id": job.id, "status": job.status}
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


@shared_task(name="materials.process_learning_asset_media")
def process_learning_asset_media(material_id: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, material_id)
        if material is None:
            return {"material_id": material_id, "status": "missing"}
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
        material.learning_assets = [asset.model_dump(mode="json") for asset in processing_assets]
        db.add(material)
        db.commit()

        try:
            provider = HN014MockMediaProvider(public_base_url=get_settings().public_base_url)
            updated_assets = provider.apply(processing_assets)
            status_value = "ready" if all(
                asset.generated_image_status == MediaGenerationStatus.ready
                and asset.tts_us_status == MediaGenerationStatus.ready
                and asset.tts_uk_status == MediaGenerationStatus.ready
                for asset in updated_assets
            ) else "partial"
        except Exception:
            updated_assets = [
                asset.model_copy(
                    update={
                        "generated_image_status": MediaGenerationStatus.failed,
                        "tts_us_status": MediaGenerationStatus.failed,
                        "tts_uk_status": MediaGenerationStatus.failed,
                    }
                )
                for asset in processing_assets
            ]
            status_value = "failed"

        current_material = db.get(CourseMaterialModel, material_id)
        current_assets = [
            LearningAsset(**item)
            for item in ((current_material.learning_assets if current_material is not None else None) or [])
        ]
        updated_assets = _merge_generated_media_updates(updated_assets, current_assets)
        material.learning_assets = [asset.model_dump(mode="json") for asset in updated_assets]
        db.add(material)
        _backfill_generated_media(db, material.id, updated_assets)
        db.commit()
        return {"material_id": material_id, "status": status_value}
    finally:
        db.close()


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
                    "tts_us_status": generated.tts_us_status,
                    "tts_us_url": generated.tts_us_url,
                    "tts_us_object_key": generated.tts_us_object_key,
                    "tts_uk_status": generated.tts_uk_status,
                    "tts_uk_url": generated.tts_uk_url,
                    "tts_uk_object_key": generated.tts_uk_object_key,
                }
            )
        )
    return merged


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


@shared_task(name="speaking.score_attempt")
def score_attempt(attempt_id: str) -> dict[str, str]:
    return {"attempt_id": attempt_id, "status": "scored"}
