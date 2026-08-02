from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, ParentAccountModel
from app.models.contracts import ChildProfile, ChildProfileCreate, ChildProfileUpdate
from app.services.shared.mappers import child_profile_from_model
from app.services.shared.weekly_report import get_or_create_current_week_report

router = APIRouter(prefix="/children", tags=["children"])

_ALLOWED_ACCENTS = {"us", "uk"}


def _normalize_accent(value: str) -> str:
    accent = (value or "us").strip().lower()
    if accent not in _ALLOWED_ACCENTS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="accent must be 'us' or 'uk'")
    return accent


@router.get("", response_model=list[ChildProfile])
def list_children(
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[ChildProfile]:
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id == current_parent.id).order_by(ChildProfileModel.created_at)
    ).all()
    return [child_profile_from_model(child) for child in children]


@router.post("", response_model=ChildProfile, status_code=status.HTTP_201_CREATED)
def create_child(
    payload: ChildProfileCreate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildProfile:
    child = ChildProfileModel(
        parent_account_id=current_parent.id,
        name=payload.name,
        avatar_url="",
        age=payload.age,
        level=payload.level,
        learning_goal=payload.learning_goal,
        preferred_review_duration_minutes=payload.preferred_review_duration_minutes,
        parent_notes=payload.parent_notes,
        accent=_normalize_accent(payload.accent),
    )
    db.add(child)
    db.flush()
    get_or_create_current_week_report(
        db,
        child.id,
        recommended_actions=[
            "上传第一份讲义，开始生成复习包。",
            "先做 5-10 分钟轻量复习，建立节奏。",
        ],
    )
    db.commit()
    db.refresh(child)
    return child_profile_from_model(child)


@router.patch("/{child_id}", response_model=ChildProfile)
def update_child(
    child_id: str,
    payload: ChildProfileUpdate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildProfile:
    child = db.get(ChildProfileModel, child_id)
    if child is None or child.parent_account_id != current_parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="child not found")
    if payload.name is not None:
        child.name = payload.name
    if payload.age is not None:
        child.age = payload.age
    if payload.level is not None:
        child.level = payload.level
    if payload.learning_goal is not None:
        child.learning_goal = payload.learning_goal
    if payload.preferred_review_duration_minutes is not None:
        child.preferred_review_duration_minutes = payload.preferred_review_duration_minutes
    if payload.parent_notes is not None:
        child.parent_notes = payload.parent_notes
    if payload.accent is not None:
        child.accent = _normalize_accent(payload.accent)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child_profile_from_model(child)
