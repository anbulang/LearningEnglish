from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def enqueue_material_job(job_id: str) -> None:
    if os.getenv("APP_ENV") == "testing":
        logger.info("test environment skipped material job enqueue %s", job_id)
        return

    try:
        from celery import Celery
    except ModuleNotFoundError as exc:
        raise RuntimeError("Celery is required to enqueue material jobs") from exc

    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or _default_result_backend(broker_url)
    celery_app = Celery("learning_english_api", broker=broker_url, backend=result_backend)
    celery_app.conf.update(task_default_queue="learning_english")
    celery_app.send_task("materials.process_material_job", args=[job_id], queue="learning_english")
    logger.info("enqueued material job %s", job_id)


def _default_result_backend(broker_url: str) -> str:
    if broker_url.endswith("/0"):
        return f"{broker_url[:-2]}/1"
    return broker_url
