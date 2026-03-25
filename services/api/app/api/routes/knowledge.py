from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import KnowledgePackDetailResponse
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/knowledge-packs", tags=["knowledge-packs"])


@router.get("/{material_id}", response_model=KnowledgePackDetailResponse)
def get_knowledge_pack_detail(
    material_id: str,
    store: InMemoryStore = Depends(get_store),
) -> KnowledgePackDetailResponse:
    material = store.materials.get(material_id)
    knowledge_pack = store.knowledge_packs.get(material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if knowledge_pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge pack not available yet",
        )
    return KnowledgePackDetailResponse(material=material, knowledge_pack=knowledge_pack)
