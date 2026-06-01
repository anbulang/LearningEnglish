from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, ReviewTaskModel
from app.models.contracts import MaterialStatus, ReviewTaskListResponse
from app.services.mappers import review_task_from_model

router = APIRouter(prefix="/review-tasks", tags=["review-tasks"])


@router.get("", response_model=ReviewTaskListResponse)
def list_review_tasks(
    child_id: Optional[str] = None,
    material_id: Optional[str] = None,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ReviewTaskListResponse:
    stmt = (
        select(ReviewTaskModel)
        .join(ChildProfileModel, ChildProfileModel.id == ReviewTaskModel.child_id)
        .join(CourseMaterialModel, CourseMaterialModel.id == ReviewTaskModel.material_id)
        .where(
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    if child_id:
        stmt = stmt.where(ReviewTaskModel.child_id == child_id)
    if material_id:
        stmt = stmt.where(ReviewTaskModel.material_id == material_id)
    items = db.scalars(stmt.order_by(ReviewTaskModel.due_date)).all()
    return ReviewTaskListResponse(items=[review_task_from_model(item) for item in items])
