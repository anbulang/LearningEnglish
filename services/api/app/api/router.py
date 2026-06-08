from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.parent import router as parent_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(parent_router)
api_router.include_router(admin_router)
