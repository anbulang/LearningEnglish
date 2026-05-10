from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_pipeline_service, get_storage
from app.core.db import get_db
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentAccountModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
    StoredAssetModel,
)
from app.models.contracts import JobStatus, MaterialParseConfirmRequest, MaterialParseJob, MaterialStatus
from app.services.mappers import course_material_from_model, material_job_from_model
from app.services.pipeline import ProviderBackedPipelineService

router = APIRouter(prefix="/material-jobs", tags=["material-jobs"])


@router.get("/{job_id}", response_model=MaterialParseJob)
def get_material_job(
    job_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    pipeline: ProviderBackedPipelineService = Depends(get_pipeline_service),
    storage=Depends(get_storage),
) -> MaterialParseJob:
    job, material = _get_owned_job(db, current_parent.id, job_id)
    if job.status in {JobStatus.queued.value, JobStatus.processing.value}:
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
            db.refresh(job)
            return material_job_from_model(job)
        job.status = prepared.status.value
        job.finished_at = prepared.finished_at
        job.draft_title = prepared.draft_title
        job.draft_topic = prepared.draft_topic
        job.draft_vocabulary = prepared.draft_vocabulary
        job.draft_sentences = prepared.draft_sentences
        job.draft_image_records = [item.model_dump() for item in prepared.draft_image_records]
        job.confidence_summary = prepared.confidence_summary
        job.warnings = prepared.warnings
        material.status = MaterialStatus.needs_review.value
        material.ocr_text = " ".join(prepared.draft_vocabulary + prepared.draft_sentences)
        material.topic = prepared.draft_topic or material.topic
        material.image_records = [item.model_dump() for item in prepared.draft_image_records]
        db.add_all([job, material])
        db.commit()
        db.refresh(job)
    return material_job_from_model(job)


@router.post("/{job_id}/confirm", response_model=MaterialParseJob)
def confirm_material_job(
    job_id: str,
    payload: MaterialParseConfirmRequest,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    pipeline: ProviderBackedPipelineService = Depends(get_pipeline_service),
) -> MaterialParseJob:
    job, material = _get_owned_job(db, current_parent.id, job_id)
    prepared = material_job_from_model(job)
    if job.status in {JobStatus.queued.value, JobStatus.processing.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is still processing")
    if job.status == JobStatus.failed.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job failed; retry before confirming")

    prepared = prepared.model_copy(
        update={
            "status": JobStatus.ready,
            "draft_title": payload.draft_title or prepared.draft_title,
            "draft_topic": payload.draft_topic or prepared.draft_topic,
            "draft_vocabulary": payload.draft_vocabulary or prepared.draft_vocabulary,
            "draft_sentences": payload.draft_sentences or prepared.draft_sentences,
        }
    )
    material_contract = course_material_from_model(material)
    knowledge_pack, review_tasks, coaching_script = pipeline.build_knowledge_assets(material_contract, prepared)

    job.status = JobStatus.ready.value
    job.draft_title = prepared.draft_title
    job.draft_topic = prepared.draft_topic
    job.draft_vocabulary = prepared.draft_vocabulary
    job.draft_sentences = prepared.draft_sentences
    material.status = MaterialStatus.ready.value
    material.title = prepared.draft_title or material.title
    material.topic = prepared.draft_topic or material.topic
    material.ocr_text = " ".join(prepared.draft_vocabulary + prepared.draft_sentences)
    material.image_records = [item.model_dump() for item in prepared.draft_image_records]

    db.add_all([job, material])
    db.execute(delete(KnowledgePackModel).where(KnowledgePackModel.material_id == material.id))
    db.execute(delete(ParentCoachingScriptModel).where(ParentCoachingScriptModel.material_id == material.id))
    db.execute(delete(ReviewTaskModel).where(ReviewTaskModel.material_id == material.id))
    db.add(
        KnowledgePackModel(
            id=knowledge_pack.id,
            material_id=material.id,
            topic=knowledge_pack.topic,
            difficulty_band=knowledge_pack.difficulty_band.value,
            lesson_summary=knowledge_pack.lesson_summary,
            review_recommendation=knowledge_pack.review_recommendation,
            vocabulary_items=[item.model_dump() for item in knowledge_pack.vocabulary_items],
            sentence_patterns=[item.model_dump() for item in knowledge_pack.sentence_patterns],
        )
    )
    db.add(
        ParentCoachingScriptModel(
            id=coaching_script.id,
            material_id=material.id,
            title=coaching_script.title,
            intro=coaching_script.intro,
            steps=[step.model_dump() for step in coaching_script.steps],
        )
    )
    for task in review_tasks:
        db.add(
            ReviewTaskModel(
                id=task.id,
                child_id=task.child_id,
                material_id=task.material_id,
                task_type=task.task_type.value,
                difficulty=task.difficulty,
                content_json=task.content_json,
                due_date=task.due_date,
                status=task.status.value,
            )
        )
    db.commit()
    db.refresh(job)
    return material_job_from_model(job)


@router.post("/{job_id}/retry", response_model=MaterialParseJob)
def retry_material_job(
    job_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MaterialParseJob:
    job, material = _get_owned_job(db, current_parent.id, job_id)
    job.status = JobStatus.processing.value
    job.warnings = []
    job.confidence_summary = "任务已重新排队。"
    job.finished_at = None
    job.draft_image_records = material.image_records or []
    material.status = MaterialStatus.processing.value
    db.add_all([job, material])
    db.commit()
    db.refresh(job)
    return material_job_from_model(job)


def _get_owned_job(db: Session, parent_account_id: str, job_id: str) -> tuple[MaterialParseJobModel, CourseMaterialModel]:
    stmt = (
        select(MaterialParseJobModel, CourseMaterialModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == MaterialParseJobModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(MaterialParseJobModel.id == job_id, ChildProfileModel.parent_account_id == parent_account_id)
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")
    return row[0], row[1]
