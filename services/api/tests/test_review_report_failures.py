from __future__ import annotations

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, MaterialParseJobModel
from app.models.contracts import JobStatus, MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-review-")


def _create_child(api_client, headers: dict[str, str]) -> str:
    response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "更喜欢看图认词",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_ready_material(api_client, headers: dict[str, str], child_id: str) -> tuple[str, list[str]]:
    create_material = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-03-25",
            "title": "Animals Around Me",
            "topic": "动物",
            "tags": "动物,MVP",
        },
        files=[("files", ("worksheet.txt", b"cat dog bird\nWhat is this?\nIt is a cat.", "text/plain"))],
        headers=headers,
    )
    payload = create_material.json()
    material_id = payload["material"]["id"]
    job_id = payload["job"]["id"]

    job = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    with SessionLocal() as db:
        job_model = db.get(MaterialParseJobModel, job_id)
        material_model = db.get(CourseMaterialModel, material_id)
        assert job_model is not None
        assert material_model is not None
        job_model.status = JobStatus.needs_review.value
        job_model.draft_title = "Animals Around Me"
        job_model.draft_topic = "动物"
        job_model.draft_vocabulary = ["cat", "dog", "bird"]
        job_model.draft_sentences = ["What is this?", "It is a cat."]
        material_model.status = MaterialStatus.needs_review.value
        db.add_all([job_model, material_model])
        db.commit()
    confirm = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={"draft_topic": "动物"}, headers=headers)
    assert confirm.status_code == 200

    tasks = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id, "material_id": material_id},
        headers=headers,
    )
    assert tasks.status_code == 200
    task_ids = [item["id"] for item in tasks.json()["items"]]
    return material_id, task_ids


def test_review_and_report_routes_require_auth(api_client) -> None:
    review = api_client.get("/v1/review-tasks")
    assert review.status_code == 401
    assert review.json()["detail"] == "Missing access token"

    report = api_client.get("/v1/reports/weekly", params={"child_id": "child_missing"})
    assert report.status_code == 401
    assert report.json()["detail"] == "Missing access token"


def test_practice_session_rejects_unknown_task(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="bad-practice-parent")
    child_id = _create_child(api_client, headers)

    response = api_client.post(
        "/v1/practice-sessions",
        json={
            "child_id": child_id,
            "review_task_ids": ["task_missing"],
            "score": 90,
            "weak_points": [],
        },
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "One or more review tasks were not found"


def test_speaking_attempt_rejects_unknown_material(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="bad-speaking-parent")
    child_id = _create_child(api_client, headers)

    response = api_client.post(
        "/v1/speaking-attempts",
        json={
            "child_id": child_id,
            "material_id": "material_missing",
            "prompt_text": "What is this?",
            "transcript": "It is a cat.",
        },
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Material not found"


def test_weekly_report_rejects_unknown_child(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="missing-report-parent")
    response = api_client.get("/v1/reports/weekly", params={"child_id": "child_missing"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Child not found"


def test_review_tasks_filter_returns_created_tasks(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="review-filter-parent")
    child_id = _create_child(api_client, headers)
    _, task_ids = _create_ready_material(api_client, headers, child_id)

    response = api_client.get("/v1/review-tasks", params={"child_id": child_id}, headers=headers)
    assert response.status_code == 200
    returned_ids = [item["id"] for item in response.json()["items"]]
    assert set(task_ids).issubset(set(returned_ids))
