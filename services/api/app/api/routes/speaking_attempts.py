from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, SpeakingAttemptModel, WeeklyReportModel
from app.models.contracts import SpeakingAttempt, SpeakingAttemptCreate, SpeakingAttemptStatus
from app.services.mappers import speaking_attempt_from_model

router = APIRouter(prefix="/speaking-attempts", tags=["speaking-attempts"])


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
        .where(ChildProfileModel.parent_account_id == current_parent.id)
    )
    if child_id:
        stmt = stmt.where(SpeakingAttemptModel.child_id == child_id)
    if material_id:
        stmt = stmt.where(SpeakingAttemptModel.material_id == material_id)
    items = db.scalars(stmt.order_by(SpeakingAttemptModel.created_at.desc())).all()
    return [speaking_attempt_from_model(item) for item in items]


@router.post("", response_model=SpeakingAttempt, status_code=status.HTTP_201_CREATED)
def create_speaking_attempt(
    payload: SpeakingAttemptCreate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> SpeakingAttempt:
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == payload.child_id,
            ChildProfileModel.parent_account_id == current_parent.id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    material = db.scalar(
        select(CourseMaterialModel).where(
            CourseMaterialModel.id == payload.material_id,
            CourseMaterialModel.child_id == payload.child_id,
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    transcript = payload.transcript or "It is a cat."
    attempt = SpeakingAttemptModel(
        child_id=payload.child_id,
        material_id=payload.material_id,
        prompt_text=payload.prompt_text,
        audio_url="demo://speaking-attempt.m4a",
        transcript=transcript,
        pronunciation_score=0.86,
        feedback="Great job! 可以把 cat 的尾音收得更清楚一点。",
        status=SpeakingAttemptStatus.scored.value,
    )
    db.add(attempt)

    report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == payload.child_id))
    if report is not None:
        report.speaking_attempts += 1
        db.add(report)

    db.commit()
    db.refresh(attempt)
    return speaking_attempt_from_model(attempt)
