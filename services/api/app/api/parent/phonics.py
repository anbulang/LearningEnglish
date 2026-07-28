from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.config import get_storage
from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import ChildProfileModel, ParentAccountModel, PhonicsAttemptModel, PhonicsUnitModel
from app.models.contracts import (
    PhonicsAttempt,
    PhonicsAttemptResponse,
    PhonicsProgressResponse,
    PhonicsTapAttemptCreate,
    PhonicsUnitDetailResponse,
    PhonicsUnitListResponse,
)
from app.services.parent import phonics as phonics_service
from app.services.shared.mappers import phonics_attempt_from_model
from app.services.shared.phonics_queue import enqueue_phonics_attempt_job

router = APIRouter(prefix="/phonics", tags=["phonics"])

_ALLOWED_AUDIO_TYPES = {
    "audio/aac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-m4a",
    "application/octet-stream",
}


@router.get("/units", response_model=PhonicsUnitListResponse)
def list_phonics_units(
    child_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PhonicsUnitListResponse:
    _get_owned_child(db, current_parent.id, child_id)
    return phonics_service.list_units(db, child_id)


@router.get("/progress", response_model=PhonicsProgressResponse)
def get_phonics_progress(
    child_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PhonicsProgressResponse:
    _get_owned_child(db, current_parent.id, child_id)
    return phonics_service.get_progress(db, child_id)


@router.get("/units/{unit_id}", response_model=PhonicsUnitDetailResponse)
def get_phonics_unit(
    unit_id: str,
    child_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PhonicsUnitDetailResponse:
    _get_owned_child(db, current_parent.id, child_id)
    detail = phonics_service.get_unit_detail(db, child_id, unit_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phonics unit not found")
    return detail


@router.post("/attempts", response_model=PhonicsAttemptResponse, status_code=status.HTTP_201_CREATED)
def create_tap_attempt(
    payload: PhonicsTapAttemptCreate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PhonicsAttemptResponse:
    _get_owned_child(db, current_parent.id, payload.child_id)
    result = phonics_service.record_tap_attempt(db, payload.child_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phonics unit not found")
    return result


@router.post("/attempts/audio", response_model=PhonicsAttempt, status_code=status.HTTP_201_CREATED)
def create_word_attempt(
    child_id: str = Form(...),
    unit_id: str = Form(...),
    target_text: str = Form(...),
    step: str = Form("blending"),
    audio_duration_ms: int = Form(0),
    audio: UploadFile = File(...),
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
) -> PhonicsAttempt:
    _get_owned_child(db, current_parent.id, child_id)
    unit = db.get(PhonicsUnitModel, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phonics unit not found")
    _validate_audio_upload(audio)
    attempt = PhonicsAttemptModel(
        id=f"phattempt_{uuid4().hex[:12]}",
        child_id=child_id,
        unit_id=unit.id,
        step=step.strip() or "blending",
        practice_type="blend_word_asr",
        target_text=target_text.strip(),
        audio_duration_ms=max(audio_duration_ms, 0),
        status="recording_uploaded",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()
    audio.file.seek(0)
    stored = storage.save_upload("phonics_attempt", attempt.id, audio)
    attempt.audio_url = stored.url
    attempt.audio_object_key = stored.object_key
    attempt.audio_content_type = stored.content_type
    attempt.audio_size_bytes = stored.size_bytes
    db.add(stored)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    enqueue_phonics_attempt_job(attempt.id)
    return phonics_attempt_from_model(attempt)


@router.get("/attempts/{attempt_id}", response_model=PhonicsAttempt)
def get_phonics_attempt(
    attempt_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PhonicsAttempt:
    attempt = _get_owned_attempt(db, current_parent.id, attempt_id)
    return phonics_attempt_from_model(attempt)


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


def _get_owned_attempt(db: Session, parent_id: str, attempt_id: str) -> PhonicsAttemptModel:
    attempt = db.scalar(
        select(PhonicsAttemptModel)
        .join(ChildProfileModel, ChildProfileModel.id == PhonicsAttemptModel.child_id)
        .where(
            PhonicsAttemptModel.id == attempt_id,
            ChildProfileModel.parent_account_id == parent_id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phonics attempt not found")
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
