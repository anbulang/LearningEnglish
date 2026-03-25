from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import (
    SpeakingAttempt,
    SpeakingAttemptCreate,
    SpeakingAttemptStatus,
)
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/speaking-attempts", tags=["speaking-attempts"])


@router.get("", response_model=list[SpeakingAttempt])
def list_speaking_attempts(
    child_id: Optional[str] = None,
    material_id: Optional[str] = None,
    store: InMemoryStore = Depends(get_store),
) -> list[SpeakingAttempt]:
    items = list(store.speaking_attempts.values())
    if child_id:
        items = [item for item in items if item.child_id == child_id]
    if material_id:
        items = [item for item in items if item.material_id == material_id]
    return items


@router.post("", response_model=SpeakingAttempt, status_code=status.HTTP_201_CREATED)
def create_speaking_attempt(
    payload: SpeakingAttemptCreate,
    store: InMemoryStore = Depends(get_store),
) -> SpeakingAttempt:
    if payload.child_id not in store.children:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    if payload.material_id not in store.materials:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    transcript = payload.transcript or "It is a cat."
    attempt = SpeakingAttempt(
        id=f"attempt_{uuid4().hex[:8]}",
        child_id=payload.child_id,
        material_id=payload.material_id,
        prompt_text=payload.prompt_text,
        audio_url="demo://speaking-attempt.m4a",
        transcript=transcript,
        pronunciation_score=0.86,
        feedback="Great job! 可以把 cat 的尾音收得更清楚一点。",
        status=SpeakingAttemptStatus.scored,
    )
    store.speaking_attempts[attempt.id] = attempt

    report = store.weekly_reports.get(payload.child_id)
    if report is not None:
        store.weekly_reports[payload.child_id] = report.model_copy(
            update={"speaking_attempts": report.speaking_attempts + 1}
        )

    return attempt
