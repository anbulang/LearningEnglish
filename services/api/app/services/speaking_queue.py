from __future__ import annotations

import logging

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def enqueue_speaking_attempt_job(attempt_id: str) -> None:
    if get_settings().app_env == "testing":
        logger.info("test environment skipped speaking attempt enqueue %s", attempt_id)
        return
    try:
        from workers_app.celery_app import celery_app
    except ImportError as exc:
        raise RuntimeError("Celery is required to enqueue speaking attempt jobs") from exc
    celery_app.send_task("speaking.score_attempt", args=[attempt_id], queue="learning_english")
    logger.info("enqueued speaking attempt job %s", attempt_id)
