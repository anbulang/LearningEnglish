from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_pipeline_service, get_store
from app.models.contracts import (
    JobStatus,
    MaterialParseConfirmRequest,
    MaterialParseJob,
    MaterialStatus,
)
from app.repositories.in_memory import InMemoryStore
from app.services.pipeline import DemoPipelineService

router = APIRouter(prefix="/material-jobs", tags=["material-jobs"])


@router.get("/{job_id}", response_model=MaterialParseJob)
def get_material_job(
    job_id: str,
    store: InMemoryStore = Depends(get_store),
    pipeline: DemoPipelineService = Depends(get_pipeline_service),
) -> MaterialParseJob:
    job = store.material_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")

    material = store.materials[job.material_id]
    if job.status in {JobStatus.queued, JobStatus.processing}:
        job = pipeline.prepare_job(material, job)
        material = material.model_copy(
            update={
                "status": MaterialStatus.needs_review,
                "ocr_text": " ".join(job.draft_vocabulary + job.draft_sentences),
                "topic": job.draft_topic or material.topic,
            }
        )
        store.materials[material.id] = material
        store.material_jobs[job.id] = job
    return job


@router.post("/{job_id}/confirm", response_model=MaterialParseJob)
def confirm_material_job(
    job_id: str,
    payload: MaterialParseConfirmRequest,
    store: InMemoryStore = Depends(get_store),
    pipeline: DemoPipelineService = Depends(get_pipeline_service),
) -> MaterialParseJob:
    job = store.material_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")

    material = store.materials[job.material_id]
    if job.status in {JobStatus.queued, JobStatus.processing}:
        job = pipeline.prepare_job(material, job)

    job = job.model_copy(
        update={
            "status": JobStatus.ready,
            "draft_title": payload.draft_title or job.draft_title,
            "draft_topic": payload.draft_topic or job.draft_topic,
            "draft_vocabulary": payload.draft_vocabulary or job.draft_vocabulary,
            "draft_sentences": payload.draft_sentences or job.draft_sentences,
        }
    )
    material = material.model_copy(
        update={
            "title": job.draft_title or material.title,
            "topic": job.draft_topic or material.topic,
            "ocr_text": " ".join(job.draft_vocabulary + job.draft_sentences),
            "status": MaterialStatus.ready,
        }
    )
    knowledge_pack, review_tasks, coaching_script = pipeline.build_knowledge_assets(material, job)

    store.material_jobs[job.id] = job
    store.materials[material.id] = material
    store.knowledge_packs[material.id] = knowledge_pack
    store.parent_coaching_scripts[material.id] = coaching_script
    for task_id, task in list(store.review_tasks.items()):
        if task.material_id == material.id:
            del store.review_tasks[task_id]
    for task in review_tasks:
        store.review_tasks[task.id] = task

    return job


@router.post("/{job_id}/retry", response_model=MaterialParseJob)
def retry_material_job(
    job_id: str,
    store: InMemoryStore = Depends(get_store),
) -> MaterialParseJob:
    job = store.material_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")

    material = store.materials[job.material_id]
    retried_job = job.model_copy(
        update={
            "status": JobStatus.processing,
            "warnings": [],
            "confidence_summary": "任务已重新排队。",
        }
    )
    retried_material = material.model_copy(update={"status": MaterialStatus.processing})
    store.material_jobs[job.id] = retried_job
    store.materials[material.id] = retried_material
    return retried_job
