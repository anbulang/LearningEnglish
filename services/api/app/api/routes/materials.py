from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_storage
from app.core.db import get_db
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    MaterialParseJobModel,
    ParentAccountModel,
)
from app.models.contracts import CourseMaterial, JobStatus, MaterialCreateResponse, MaterialDetailResponse, MaterialStatus
from app.services.mappers import course_material_from_model, material_job_from_model

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[CourseMaterial])
def list_materials(
    child_id: Optional[str] = None,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[CourseMaterial]:
    child_ids = db.scalars(
        select(ChildProfileModel.id).where(ChildProfileModel.parent_account_id == current_parent.id)
    ).all()
    stmt = select(CourseMaterialModel).where(CourseMaterialModel.child_id.in_(child_ids or [""]))
    if child_id:
        stmt = stmt.where(CourseMaterialModel.child_id == child_id)
    items = db.scalars(stmt.order_by(CourseMaterialModel.lesson_date.desc())).all()
    latest_job_ids = _latest_job_ids(db, [item.id for item in items])
    return [course_material_from_model(item, parse_job_id=latest_job_ids.get(item.id, "")) for item in items]


@router.get("/{material_id}", response_model=MaterialDetailResponse)
def get_material(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MaterialDetailResponse:
    material = _get_owned_material(db, current_parent.id, material_id)
    latest_job_ids = _latest_job_ids(db, [material.id])
    return MaterialDetailResponse(
        material=course_material_from_model(material, parse_job_id=latest_job_ids.get(material.id, ""))
    )


@router.post("", response_model=MaterialCreateResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    child_id: str = Form(...),
    teacher_name: str = Form("外教课"),
    lesson_date: date = Form(...),
    title: str = Form("待识别讲义"),
    topic: str = Form(""),
    tags: str = Form(""),
    files: list[UploadFile] = File(...),
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
) -> MaterialCreateResponse:
    safe_teacher_name = teacher_name.strip() or "外教课"
    safe_title = title.strip() or "待识别讲义"
    safe_topic = topic.strip()
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == child_id,
            ChildProfileModel.parent_account_id == current_parent.id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one source image is required")

    material = CourseMaterialModel(
        child_id=child_id,
        teacher_name=safe_teacher_name,
        lesson_date=lesson_date,
        title=safe_title,
        topic=safe_topic,
        status=MaterialStatus.processing.value,
        source_images=[],
        source_image_keys=[],
        normalized_image_keys=[],
        tags=[item.strip() for item in tags.split(",") if item.strip()],
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(material)
    db.flush()

    asset_rows: list[StoredAssetModel] = []
    total_size = 0
    for upload in files:
        asset = storage.save_upload("material", material.id, upload)
        db.add(asset)
        db.flush()
        asset_rows.append(asset)
        total_size += asset.size_bytes

    material.source_images = [asset.url for asset in asset_rows]
    material.source_image_keys = [asset.object_key for asset in asset_rows]
    material.normalized_image_keys = [asset.object_key for asset in asset_rows]
    material.file_size_bytes = total_size

    job = MaterialParseJobModel(
        material_id=material.id,
        status=JobStatus.processing.value,
        confidence_summary="上传完成，等待 OCR 与解析。",
        started_at=datetime.now(timezone.utc),
        warnings=[],
        draft_title=safe_title,
        draft_topic=safe_topic,
        draft_vocabulary=[],
        draft_sentences=[],
    )
    db.add(job)
    db.commit()
    db.refresh(material)
    db.refresh(job)
    return MaterialCreateResponse(material=course_material_from_model(material), job=material_job_from_model(job))


def _get_owned_material(db: Session, parent_account_id: str, material_id: str) -> CourseMaterialModel:
    stmt = (
        select(CourseMaterialModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            CourseMaterialModel.id == material_id,
            ChildProfileModel.parent_account_id == parent_account_id,
        )
    )
    material = db.scalar(stmt)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def _latest_job_ids(db: Session, material_ids: list[str]) -> dict[str, str]:
    if not material_ids:
        return {}
    rows = db.execute(
        select(MaterialParseJobModel.material_id, MaterialParseJobModel.id)
        .where(MaterialParseJobModel.material_id.in_(material_ids))
        .order_by(MaterialParseJobModel.started_at.desc())
    ).all()
    result: dict[str, str] = {}
    for material_id, job_id in rows:
        result.setdefault(material_id, job_id)
    return result
