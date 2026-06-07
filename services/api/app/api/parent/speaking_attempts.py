from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_storage
from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, SpeakingAttemptModel
from app.models.contracts import MaterialStatus, SpeakingAttempt, SpeakingAttemptStatus
from app.services.shared.mappers import speaking_attempt_from_model
from app.services.shared.speaking_queue import enqueue_speaking_attempt_job

router = APIRouter(prefix="/speaking-attempts", tags=["speaking-attempts"])

_ALLOWED_AUDIO_TYPES = {
    "audio/aac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-m4a",
    "application/octet-stream",
}


@router.get("", response_model=list[SpeakingAttempt])
def list_speaking_attempts(
    child_id: Optional[str] = None,
    material_id: Optional[str] = None,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[SpeakingAttempt]:
    stmt = (
        select(SpeakingAttemptModel)
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .join(CourseMaterialModel, CourseMaterialModel.id == SpeakingAttemptModel.material_id)
        .where(
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    if child_id:
        stmt = stmt.where(SpeakingAttemptModel.child_id == child_id)
    if material_id:
        stmt = stmt.where(SpeakingAttemptModel.material_id == material_id)
    items = db.scalars(stmt.order_by(SpeakingAttemptModel.created_at.desc())).all()
    return [speaking_attempt_from_model(item) for item in items]


@router.post("", response_model=SpeakingAttempt, status_code=status.HTTP_201_CREATED)
def create_speaking_attempt(
    child_id: str = Form(...),
    material_id: str = Form(...),
    prompt_text: str = Form(...),
    target_text: str = Form(""),
    review_task_id: str = Form(""),
    learning_asset_id: str = Form(""),
    audio_duration_ms: int = Form(0),
    audio: UploadFile = File(...),
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
) -> SpeakingAttempt:
    child = _get_owned_child(db, current_parent.id, child_id)
    material = _get_owned_material(db, child.id, material_id)
    _validate_audio_upload(audio)
    prompt = prompt_text.strip() or "跟读这句话。"
    attempt = SpeakingAttemptModel(
        id=f"attempt_{uuid4().hex[:12]}",
        child_id=child.id,
        material_id=material.id,
        review_task_id=review_task_id.strip(),
        learning_asset_id=learning_asset_id.strip(),
        prompt_text=prompt,
        target_text=target_text.strip() or prompt,
        audio_duration_ms=max(audio_duration_ms, 0),
        status=SpeakingAttemptStatus.recording_uploaded.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()
    audio.file.seek(0)
    stored = storage.save_upload("speaking_attempt", attempt.id, audio)
    attempt.audio_url = stored.url
    attempt.audio_object_key = stored.object_key
    attempt.audio_content_type = stored.content_type
    attempt.audio_size_bytes = stored.size_bytes
    db.add(stored)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    enqueue_speaking_attempt_job(attempt.id)
    return speaking_attempt_from_model(attempt)


@router.get("/{attempt_id}", response_model=SpeakingAttempt)
def get_speaking_attempt(
    attempt_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> SpeakingAttempt:
    attempt = _get_owned_attempt(db, current_parent.id, attempt_id)
    return speaking_attempt_from_model(attempt)


@router.post("/{attempt_id}/retry", response_model=SpeakingAttempt)
def retry_speaking_attempt(
    attempt_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> SpeakingAttempt:
    attempt = _get_owned_attempt(db, current_parent.id, attempt_id)
    if attempt.status != SpeakingAttemptStatus.failed.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed speaking attempts can be retried",
        )
    attempt.status = SpeakingAttemptStatus.recording_uploaded.value
    attempt.failure_reason = ""
    attempt.updated_at = datetime.now(timezone.utc)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    enqueue_speaking_attempt_job(attempt.id)
    return speaking_attempt_from_model(attempt)


def _get_owned_child(db: Session, parent_id: str, child_id: str) -> ChildProfileModel:
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == child_id,
            ChildProfileModel.parent_account_id == parent_id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return child


def _get_owned_material(db: Session, child_id: str, material_id: str) -> CourseMaterialModel:
    material = db.scalar(
        select(CourseMaterialModel).where(
            CourseMaterialModel.id == material_id,
            CourseMaterialModel.child_id == child_id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def _get_owned_attempt(db: Session, parent_id: str, attempt_id: str) -> SpeakingAttemptModel:
    attempt = db.scalar(
        select(SpeakingAttemptModel)
        .join(ChildProfileModel, ChildProfileModel.id == SpeakingAttemptModel.child_id)
        .join(CourseMaterialModel, CourseMaterialModel.id == SpeakingAttemptModel.material_id)
        .where(
            SpeakingAttemptModel.id == attempt_id,
            ChildProfileModel.parent_account_id == parent_id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaking attempt not found")
    return attempt


def _validate_audio_upload(audio: UploadFile) -> None:
    content_type = audio.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported audio type")
    position = audio.file.tell()
    audio.file.seek(0, 2)
    size_bytes = audio.file.tell()
    audio.file.seek(position)
    if size_bytes > get_settings().speaking_audio_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file too large")
