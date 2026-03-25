from __future__ import annotations

from celery import shared_task


@shared_task(name="materials.enhance_images")
def enhance_images(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "enhanced"}


@shared_task(name="materials.run_ocr")
def run_ocr(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "ocr_complete"}


@shared_task(name="knowledge.parse_material")
def parse_material(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "parsed"}


@shared_task(name="review.generate_tasks")
def generate_review_tasks(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "review_tasks_generated"}


@shared_task(name="speaking.generate_tts")
def generate_tts(material_id: str) -> dict[str, str]:
    return {"material_id": material_id, "status": "tts_generated"}


@shared_task(name="speaking.score_attempt")
def score_attempt(attempt_id: str) -> dict[str, str]:
    return {"attempt_id": attempt_id, "status": "scored"}


@shared_task(name="reporting.aggregate_weekly_report")
def aggregate_weekly_report(child_id: str) -> dict[str, str]:
    return {"child_id": child_id, "status": "aggregated"}
