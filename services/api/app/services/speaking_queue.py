from __future__ import annotations

import logging
import os

from app.core.settings import get_settings
from app.services.job_queue import _default_result_backend

logger = logging.getLogger(__name__)


def enqueue_speaking_attempt_job(attempt_id: str) -> None:
    if get_settings().app_env == "testing":
        logger.info("test environment skipped speaking attempt enqueue %s", attempt_id)
        return
    try:
        from celery import Celery
    except ImportError as exc:
        raise RuntimeError("Celery is required to enqueue speaking attempt jobs") from exc
    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or _default_result_backend(broker_url)
    celery_app = Celery("learning_english_api", broker=broker_url, backend=result_backend)
    celery_app.conf.update(task_default_queue="learning_english")
    celery_app.send_task("speaking.score_attempt", args=[attempt_id], queue="learning_english")
    logger.info("enqueued speaking attempt job %s", attempt_id)
