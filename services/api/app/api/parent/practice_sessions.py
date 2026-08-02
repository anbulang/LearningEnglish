from datetime import datetime, timedelta, timezone

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
from app.services.shared.review_scheduling import sm2_schedule
from app.services.shared.review_scoring import score_review_session, score_review_task

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

    now = datetime.now(timezone.utc)
    # Authoritative path: derive score + weak points from the child's actual
    # per-task answers, and reschedule each answered task via SM-2 (correct →
    # longer interval, miss → due again tomorrow). Fall back to the client-supplied
    # score/weak_points (and terminal 'completed') only when no answers were sent.
    if payload.task_results:
        results_by_id = {r.task_id: r for r in payload.task_results}
        scored: list[tuple[bool, str]] = []
        for task in tasks:
            result = results_by_id.get(task.id)
            if result is None:
                continue
            correct, item = score_review_task(
                task_type=task.task_type,
                content=task.content_json or {},
                answer=result.answer,
                answers=result.answers,
            )
            scored.append((correct, item))
            plan = sm2_schedule(
                correct=correct,
                repetitions=task.repetitions or 0,
                ease_factor=task.ease_factor or 2.5,
                interval_days=task.interval_days or 0,
            )
            task.repetitions = plan.repetitions
            task.ease_factor = plan.ease_factor
            task.interval_days = plan.interval_days
            task.last_reviewed_at = now
            task.due_date = now + timedelta(days=plan.interval_days)
            # stays 'pending' so it re-surfaces in 今日待复习 once due again
            task.status = ReviewTaskStatus.pending.value
            db.add(task)
        score, weak_points = score_review_session(scored)
    else:
        score, weak_points = payload.score, list(payload.weak_points)
        for task in tasks:
            task.status = ReviewTaskStatus.completed.value
            db.add(task)

    session = PracticeSessionModel(
        child_id=payload.child_id,
        review_task_ids=payload.review_task_ids,
        score=score,
        weak_points=weak_points,
    )
    db.add(session)

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
    report.weak_items = list(dict.fromkeys([*(report.weak_items or []), *weak_points]))
    db.add(report)

    db.commit()
    db.refresh(session)
    return practice_session_from_model(session)
