from __future__ import annotations

import sys
from pathlib import Path

from celery import shared_task
from sqlalchemy import select


API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))

from app.core.db import SessionLocal
from app.db.models import ChildProfileModel, CourseMaterialModel, MaterialParseJobModel, StoredAssetModel, WeeklyReportModel
from app.models.contracts import JobStatus, MaterialStatus
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
        prepared = pipeline.prepare_job(
            course_material_from_model(material),
            material_job_from_model(job),
            local_paths=local_paths,
        )
        job.status = prepared.status.value
        job.finished_at = prepared.finished_at
        job.draft_title = prepared.draft_title
        job.draft_topic = prepared.draft_topic
        job.draft_vocabulary = prepared.draft_vocabulary
        job.draft_sentences = prepared.draft_sentences
        job.confidence_summary = prepared.confidence_summary
        job.warnings = prepared.warnings
        material.status = MaterialStatus.needs_review.value
        material.ocr_text = " ".join(prepared.draft_vocabulary + prepared.draft_sentences)
        material.topic = prepared.draft_topic or material.topic
        db.add_all([job, material])
        db.commit()
        return {"job_id": job.id, "status": job.status}
    finally:
        db.close()


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
