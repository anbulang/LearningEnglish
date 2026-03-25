from datetime import datetime, timezone
from uuid import uuid4

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import (
    CourseMaterial,
    CourseMaterialCreate,
    JobStatus,
    MaterialCreateResponse,
    MaterialParseJob,
    MaterialStatus,
)
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[CourseMaterial])
def list_materials(
    child_id: Optional[str] = None,
    store: InMemoryStore = Depends(get_store),
) -> list[CourseMaterial]:
    items = list(store.materials.values())
    if child_id:
        items = [item for item in items if item.child_id == child_id]
    return sorted(items, key=lambda item: item.lesson_date, reverse=True)


@router.get("/{material_id}", response_model=CourseMaterial)
def get_material(
    material_id: str,
    store: InMemoryStore = Depends(get_store),
) -> CourseMaterial:
    material = store.materials.get(material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


@router.post("", response_model=MaterialCreateResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: CourseMaterialCreate,
    store: InMemoryStore = Depends(get_store),
) -> MaterialCreateResponse:
    if payload.child_id not in store.children:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

    material = CourseMaterial(
        id=f"material_{uuid4().hex[:8]}",
        child_id=payload.child_id,
        teacher_name=payload.teacher_name,
        lesson_date=payload.lesson_date,
        title=payload.title,
        topic=payload.topic,
        status=MaterialStatus.processing,
        source_images=payload.source_images,
        pdf_url=f"demo://{payload.title.lower().replace(' ', '-')}.pdf",
        ocr_text="",
        tags=payload.tags,
    )
    job = MaterialParseJob(
        id=f"job_{uuid4().hex[:8]}",
        material_id=material.id,
        status=JobStatus.processing,
        confidence_summary="",
        warnings=[],
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        draft_title="",
        draft_topic="",
        draft_vocabulary=[],
        draft_sentences=[],
    )
    store.materials[material.id] = material
    store.material_jobs[job.id] = job
    return MaterialCreateResponse(material=material, job=job)
