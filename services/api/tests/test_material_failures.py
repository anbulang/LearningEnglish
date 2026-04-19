from __future__ import annotations

from app.core.db import SessionLocal
from app.db.models import MaterialParseJobModel
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-materials-")


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


def _create_material(api_client, headers: dict[str, str], child_id: str) -> tuple[str, str]:
    response = api_client.post(
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
    assert response.status_code == 201
    payload = response.json()
    return payload["material"]["id"], payload["job"]["id"]


def test_material_routes_require_auth(api_client) -> None:
    response = api_client.get("/v1/materials")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


def test_create_material_rejects_missing_child(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="missing-child-parent")
    response = api_client.post(
        "/v1/materials",
        data={
            "child_id": "child_missing",
            "teacher_name": "Emma",
            "lesson_date": "2026-03-25",
            "title": "Animals Around Me",
            "topic": "动物",
        },
        files=[("files", ("worksheet.txt", b"cat dog bird", "text/plain"))],
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Child not found"


def test_cross_parent_material_access_returns_not_found(api_client) -> None:
    headers_a, _ = auth_headers(api_client, auth_code="owner-parent")
    child_id = _create_child(api_client, headers_a)
    material_id, _ = _create_material(api_client, headers_a, child_id)

    headers_b, _ = auth_headers(api_client, auth_code="other-parent")
    response = api_client.get(f"/v1/materials/{material_id}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["detail"] == "Material not found"


def test_confirm_processing_job_returns_conflict(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="confirm-processing-parent")
    child_id = _create_child(api_client, headers)
    _, job_id = _create_material(api_client, headers, child_id)

    response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_topic": "动物"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Job is still processing"


def test_knowledge_pack_is_not_available_before_confirmation(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="knowledge-pending-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    response = api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge pack not available yet"


def test_parent_coaching_is_not_available_before_confirmation(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="coach-pending-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    response = api_client.get(f"/v1/parent-coaching/{material_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Parent coaching script not available yet"


def test_retry_missing_job_returns_not_found(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="retry-missing-parent")
    response = api_client.post("/v1/material-jobs/job_missing/retry", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Material job not found"


def test_retry_failed_job_requeues_processing(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="retry-failed-parent")
    child_id = _create_child(api_client, headers)
    _, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = "failed"
        db.add(job)
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/retry", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
