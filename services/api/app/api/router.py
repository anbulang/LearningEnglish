from fastapi import APIRouter

from app.api.routes.children import router as children_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.material_jobs import router as material_jobs_router
from app.api.routes.materials import router as materials_router
from app.api.routes.practice_sessions import router as practice_sessions_router
from app.api.routes.reports import router as reports_router
from app.api.routes.review_tasks import router as review_tasks_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(children_router)
api_router.include_router(materials_router)
api_router.include_router(material_jobs_router)
api_router.include_router(knowledge_router)
api_router.include_router(review_tasks_router)
api_router.include_router(practice_sessions_router)
api_router.include_router(reports_router)
