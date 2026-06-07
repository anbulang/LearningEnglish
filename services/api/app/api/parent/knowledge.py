from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_parent
from app.core.db import get_db
from app.db.models import ChildProfileModel, CourseMaterialModel, KnowledgePackModel, ParentAccountModel
from app.models.contracts import KnowledgePackDetailResponse, MaterialStatus
from app.services.shared.mappers import course_material_from_model, knowledge_pack_from_model

router = APIRouter(prefix="/knowledge-packs", tags=["knowledge-packs"])


@router.get("/{material_id}", response_model=KnowledgePackDetailResponse)
def get_knowledge_pack_detail(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> KnowledgePackDetailResponse:
    stmt = (
        select(CourseMaterialModel, KnowledgePackModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .outerjoin(KnowledgePackModel, KnowledgePackModel.material_id == CourseMaterialModel.id)
        .where(
            CourseMaterialModel.id == material_id,
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    material, knowledge_pack = row
    if knowledge_pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge pack not available yet")
    return KnowledgePackDetailResponse(
        material=course_material_from_model(material),
        knowledge_pack=knowledge_pack_from_model(knowledge_pack),
    )
