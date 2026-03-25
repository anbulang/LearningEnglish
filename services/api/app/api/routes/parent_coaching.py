from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import ParentCoachingScript
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/parent-coaching", tags=["parent-coaching"])


@router.get("/{material_id}", response_model=ParentCoachingScript)
def get_parent_coaching_script(
    material_id: str,
    store: InMemoryStore = Depends(get_store),
) -> ParentCoachingScript:
    script = store.parent_coaching_scripts.get(material_id)
    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent coaching script not available yet",
        )
    return script
