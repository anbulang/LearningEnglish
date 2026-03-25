from uuid import uuid4

from fastapi import APIRouter, Depends

from app.core.config import get_store
from app.models.contracts import ChildProfile, ChildProfileCreate
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/children", tags=["children"])


@router.get("", response_model=list[ChildProfile])
def list_children(store: InMemoryStore = Depends(get_store)) -> list[ChildProfile]:
    return list(store.children.values())


@router.post("", response_model=ChildProfile)
def create_child(
    payload: ChildProfileCreate,
    store: InMemoryStore = Depends(get_store),
) -> ChildProfile:
    child = ChildProfile(
        id=f"child_{uuid4().hex[:8]}",
        name=payload.name,
        avatar_url="",
        age=payload.age,
        level=payload.level,
        learning_goal=payload.learning_goal,
        preferred_review_duration_minutes=payload.preferred_review_duration_minutes,
        parent_notes=payload.parent_notes,
    )
    store.children[child.id] = child
    return child
