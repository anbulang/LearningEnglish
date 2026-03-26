from functools import lru_cache

from app.services.auth import AuthService
from app.services.pipeline import build_pipeline_service
from app.services.storage import get_storage_service


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService()


@lru_cache
def get_pipeline_service():
    return build_pipeline_service()


@lru_cache
def get_storage():
    return get_storage_service()
