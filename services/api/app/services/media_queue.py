from __future__ import annotations

import logging
import os

from app.services.job_queue import _default_result_backend

logger = logging.getLogger(__name__)


def enqueue_learning_asset_media_job(material_id: str) -> None:
    if os.getenv("APP_ENV") == "testing":
        logger.info("test environment skipped learning asset media enqueue %s", material_id)
        return

    try:
        from celery import Celery
    except ModuleNotFoundError as exc:
        raise RuntimeError("Celery is required to enqueue learning asset media jobs") from exc

    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or _default_result_backend(broker_url)
    celery_app = Celery("learning_english_api", broker=broker_url, backend=result_backend)
    celery_app.conf.update(task_default_queue="learning_english")
    celery_app.send_task("materials.process_learning_asset_media", args=[material_id], queue="learning_english")
    logger.info("enqueued learning asset media job %s", material_id)
