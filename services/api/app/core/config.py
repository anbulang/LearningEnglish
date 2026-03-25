from functools import lru_cache

from app.repositories.in_memory import InMemoryStore
from app.services.pipeline import DemoPipelineService


@lru_cache
def get_store() -> InMemoryStore:
    store = InMemoryStore()
    store.seed()
    return store


@lru_cache
def get_pipeline_service() -> DemoPipelineService:
    return DemoPipelineService()
