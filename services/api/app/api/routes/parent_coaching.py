from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, ParentCoachingScriptModel
from app.models.contracts import MaterialStatus, ParentCoachingScript
from app.services.mappers import parent_coaching_script_from_model

router = APIRouter(prefix="/parent-coaching", tags=["parent-coaching"])


@router.get("/{material_id}", response_model=ParentCoachingScript)
def get_parent_coaching_script(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ParentCoachingScript:
    row = db.execute(
        select(ParentCoachingScriptModel)
        .join(CourseMaterialModel, CourseMaterialModel.id == ParentCoachingScriptModel.material_id)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            ParentCoachingScriptModel.material_id == material_id,
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent coaching script not available yet",
        )
    return parent_coaching_script_from_model(row)
