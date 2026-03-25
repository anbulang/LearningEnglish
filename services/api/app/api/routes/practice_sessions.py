from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import PracticeSession, PracticeSessionCreate, ReviewTaskStatus
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/practice-sessions", tags=["practice-sessions"])


@router.post("", response_model=PracticeSession, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    payload: PracticeSessionCreate,
    store: InMemoryStore = Depends(get_store),
) -> PracticeSession:
    if payload.child_id not in store.children:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

    tasks = []
    for task_id in payload.review_task_ids:
        task = store.review_tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}")
        tasks.append(task)

    session = PracticeSession(
        id=f"session_{uuid4().hex[:8]}",
        child_id=payload.child_id,
        review_task_ids=payload.review_task_ids,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        score=payload.score,
        weak_points=payload.weak_points,
    )
    store.practice_sessions[session.id] = session

    for task in tasks:
        store.review_tasks[task.id] = task.model_copy(update={"status": ReviewTaskStatus.completed})

    report = store.weekly_reports.get(payload.child_id)
    if report is not None:
        reviewed_words = report.reviewed_words + len(payload.review_task_ids)
        weak_items = list(dict.fromkeys([*report.weak_items, *payload.weak_points]))
        store.weekly_reports[payload.child_id] = report.model_copy(
            update={
                "completed_sessions": report.completed_sessions + 1,
                "reviewed_words": reviewed_words,
                "weak_items": weak_items,
            }
        )

    return session
