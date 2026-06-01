from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, ParentAccountModel, WeeklyReportModel
from app.models.contracts import ChildProfile, ChildProfileCreate
from app.services.shared.mappers import child_profile_from_model

router = APIRouter(prefix="/children", tags=["children"])


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
    )
    db.add(child)
    db.flush()
    report = WeeklyReportModel(
        child_id=child.id,
        week_start=child.created_at.date(),
        week_end=child.created_at.date() + timedelta(days=6),
        recommended_actions=[
            "上传第一份讲义，开始生成复习包。",
            "先做 5-10 分钟轻量复习，建立节奏。",
        ],
    )
    db.add(report)
    db.commit()
    db.refresh(child)
    return child_profile_from_model(child)
