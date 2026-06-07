from fastapi import APIRouter

from app.api.parent.auth import me_router, router as auth_router
from app.api.parent.children import router as children_router
from app.api.parent.knowledge import router as knowledge_router
from app.api.parent.material_jobs import router as material_jobs_router
from app.api.parent.materials import router as materials_router
from app.api.parent.parent_coaching import router as parent_coaching_router
from app.api.parent.practice_sessions import router as practice_sessions_router
from app.api.parent.reports import router as reports_router
from app.api.parent.review_tasks import router as review_tasks_router
from app.api.parent.speaking_attempts import router as speaking_attempts_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(me_router)
router.include_router(children_router)
router.include_router(materials_router)
router.include_router(material_jobs_router)
router.include_router(knowledge_router)
router.include_router(review_tasks_router)
router.include_router(practice_sessions_router)
router.include_router(speaking_attempts_router)
router.include_router(parent_coaching_router)
router.include_router(reports_router)
