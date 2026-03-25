from typing import Optional

from fastapi import APIRouter, Depends

from app.core.config import get_store
from app.models.contracts import ReviewTaskListResponse
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/review-tasks", tags=["review-tasks"])


@router.get("", response_model=ReviewTaskListResponse)
def list_review_tasks(
    child_id: Optional[str] = None,
    material_id: Optional[str] = None,
    store: InMemoryStore = Depends(get_store),
) -> ReviewTaskListResponse:
    items = list(store.review_tasks.values())
    if child_id:
        items = [item for item in items if item.child_id == child_id]
    if material_id:
        items = [item for item in items if item.material_id == material_id]
    return ReviewTaskListResponse(items=items)
