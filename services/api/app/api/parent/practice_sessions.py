from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import (
    ChildProfileModel,
    CourseMaterialModel,
    ParentAccountModel,
    PracticeSessionModel,
    ReviewTaskModel,
    WeeklyReportModel,
)
from app.models.contracts import MaterialStatus, PracticeSession, PracticeSessionCreate, ReviewTaskStatus
from app.services.shared.mappers import practice_session_from_model

router = APIRouter(prefix="/practice-sessions", tags=["practice-sessions"])


@router.post("", response_model=PracticeSession, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    payload: PracticeSessionCreate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> PracticeSession:
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == payload.child_id,
            ChildProfileModel.parent_account_id == current_parent.id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

    tasks = db.scalars(
        select(ReviewTaskModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == ReviewTaskModel.material_id)
        .where(
            ReviewTaskModel.id.in_(payload.review_task_ids or [""]),
            ReviewTaskModel.child_id == payload.child_id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    ).all()
    if len(tasks) != len(payload.review_task_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more review tasks were not found")

    session = PracticeSessionModel(
        child_id=payload.child_id,
        review_task_ids=payload.review_task_ids,
        score=payload.score,
        weak_points=payload.weak_points,
    )
    db.add(session)

    for task in tasks:
        task.status = ReviewTaskStatus.completed.value
        db.add(task)

    report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == payload.child_id))
    if report is None:
        start = child.created_at.date()
        report = WeeklyReportModel(
            child_id=payload.child_id,
            week_start=start,
            week_end=start + timedelta(days=6),
            recommended_actions=["保持每周至少完成两次复习。"],
        )
        db.add(report)
    report.completed_sessions += 1
    report.reviewed_words += len(payload.review_task_ids)
    report.weak_items = list(dict.fromkeys([*(report.weak_items or []), *payload.weak_points]))
    db.add(report)

    db.commit()
    db.refresh(session)
    return practice_session_from_model(session)
