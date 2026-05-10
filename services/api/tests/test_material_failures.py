from __future__ import annotations

from app.core.db import SessionLocal
from app.db.models import MaterialParseJobModel
from app.core.config import get_pipeline_service
from app.models.contracts import JobStatus
from app.main import app
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
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = "failed"
        db.add(job)
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/retry", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "processing"
    assert material_response.json()["material"]["parse_job_id"] == job_id


def test_polling_job_marks_failed_when_pipeline_errors(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="pipeline-failure-parent")
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "稳定复习",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    child_id = child_response.json()["id"]
    upload_response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-04-29",
            "title": "Animals Around Me",
            "topic": "动物",
            "tags": "动物",
        },
        files=[("files", ("worksheet.jpg", b"fake image bytes", "image/jpeg"))],
        headers=headers,
    )
    job_id = upload_response.json()["job"]["id"]

    class FailingPipeline:
        def prepare_job(self, *args, **kwargs):
            raise RuntimeError("doubao provider returned 500")

    app.dependency_overrides[get_pipeline_service] = lambda: FailingPipeline()
    try:
        response = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
    finally:
        app.dependency_overrides.pop(get_pipeline_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == JobStatus.failed.value
    assert "doubao provider returned 500" in payload["confidence_summary"]
    assert "处理失败" in payload["warnings"][0]

    material_response = api_client.get(f"/v1/materials/{upload_response.json()['material']['id']}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "failed"
    assert material_response.json()["material"]["parse_job_id"] == job_id


def test_confirm_failed_job_requires_retry(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="confirm-failed-parent")
    child_id = _create_child(api_client, headers)
    _, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = JobStatus.failed.value
        db.add(job)
        db.commit()

    response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_topic": "动物"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Job failed; retry before confirming"
