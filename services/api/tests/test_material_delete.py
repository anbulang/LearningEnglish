from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.db.models import (
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
    WeeklyReportModel,
)
from app.models.contracts import JobStatus, MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-material-delete-")


def _create_child(api_client, headers: dict[str, str], name: str = "Mia") -> str:
    response = api_client.post(
        "/v1/children",
        json={
            "name": name,
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "喜欢看图复习",
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
            "lesson_date": "2026-05-15",
            "title": "Run, Hop, Go!",
            "topic": "Phonics Rr",
            "tags": "phonics",
        },
        files=[("files", ("worksheet.txt", b"A rabbit can hop fast.", "text/plain"))],
        headers=headers,
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["material"]["id"], payload["job"]["id"]


def _seed_ready_derivatives(material_id: str, job_id: str, child_id: str) -> tuple[str, str, str]:
    knowledge_id = f"knowledge_{material_id}"
    coach_id = f"coach_{material_id}"
    task_id = f"task_{material_id}"
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        job = db.get(MaterialParseJobModel, job_id)
        assert material is not None
        assert job is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_rabbit",
                "text": "rabbit",
                "kind": "word",
                "translation": "兔子",
                "primary_accent": "us",
            }
        ]
        job.status = JobStatus.ready.value
        db.add_all([material, job])
        db.add(
            KnowledgePackModel(
                id=knowledge_id,
                material_id=material_id,
                topic="Phonics Rr",
                difficulty_band="repeat",
                lesson_summary="复习 rabbit。",
                review_recommendation="先看图再跟读。",
                vocabulary_items=[],
                sentence_patterns=[],
            )
        )
        db.add(
            ParentCoachingScriptModel(
                id=coach_id,
                material_id=material_id,
                title="亲子陪练",
                intro="和孩子一起读 rabbit。",
                steps=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id=task_id,
                child_id=child_id,
                material_id=material_id,
                task_type="flashcard",
                difficulty="easy",
                content_json={"asset_id": "asset_rabbit", "word": "rabbit"},
                due_date=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()
    return knowledge_id, coach_id, task_id


def test_delete_material_archives_material_and_removes_visible_derivatives(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-owner")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    knowledge_id, coach_id, task_id = _seed_ready_derivatives(material_id, job_id, child_id)

    response = api_client.delete(f"/v1/materials/{material_id}", headers=headers)

    assert response.status_code == 204
    list_response = api_client.get("/v1/materials", headers=headers)
    assert list_response.status_code == 200
    assert material_id not in [item["id"] for item in list_response.json()]
    assert api_client.get(f"/v1/materials/{material_id}", headers=headers).status_code == 404
    assert api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers).status_code == 404
    assert api_client.get(f"/v1/parent-coaching/{material_id}", headers=headers).status_code == 404
    tasks_response = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id, "material_id": material_id},
        headers=headers,
    )
    assert tasks_response.status_code == 200
    assert tasks_response.json()["items"] == []

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        assert material.status == MaterialStatus.archived.value
        assert db.get(MaterialParseJobModel, job_id) is not None
        assert db.get(KnowledgePackModel, knowledge_id) is None
        assert db.get(ParentCoachingScriptModel, coach_id) is None
        assert db.get(ReviewTaskModel, task_id) is None


def test_delete_material_is_parent_scoped_and_idempotent(api_client) -> None:
    owner_headers, _ = auth_headers(api_client, auth_code="delete-owner-scoped")
    child_id = _create_child(api_client, owner_headers)
    material_id, job_id = _create_material(api_client, owner_headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)

    other_headers, _ = auth_headers(api_client, auth_code="delete-other-parent")
    other_response = api_client.delete(f"/v1/materials/{material_id}", headers=other_headers)
    assert other_response.status_code == 404

    first_delete = api_client.delete(f"/v1/materials/{material_id}", headers=owner_headers)
    second_delete = api_client.delete(f"/v1/materials/{material_id}", headers=owner_headers)
    assert first_delete.status_code == 204
    assert second_delete.status_code == 204


def test_archived_material_blocks_job_and_primary_accent_routes(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-archived-job-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        job = db.get(MaterialParseJobModel, job_id)
        assert material is not None
        assert job is not None
        material.status = MaterialStatus.archived.value
        material.learning_assets = [
            {
                "id": "asset_rabbit",
                "text": "rabbit",
                "kind": "word",
                "translation": "兔子",
                "primary_accent": "us",
            }
        ]
        job.status = JobStatus.needs_review.value
        db.add_all([material, job])
        db.commit()

    assert api_client.get(f"/v1/material-jobs/{job_id}", headers=headers).status_code == 404
    confirm_response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_title": "Run, Hop, Go!"},
        headers=headers,
    )
    assert confirm_response.status_code == 404
    assert api_client.post(f"/v1/material-jobs/{job_id}/retry", headers=headers).status_code == 404
    accent_response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_rabbit/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )
    assert accent_response.status_code == 404


def test_archived_material_rejects_speaking_attempt(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-archived-speaking-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        report = db.query(WeeklyReportModel).filter_by(child_id=child_id).one()
        assert material is not None
        material.status = MaterialStatus.archived.value
        initial_speaking_attempts = report.speaking_attempts
        db.add(material)
        db.commit()

    response = api_client.post(
        "/v1/speaking-attempts",
        json={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "Read rabbit aloud.",
            "transcript": "rabbit",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Material not found"
    with SessionLocal() as db:
        attempts = db.query(SpeakingAttemptModel).filter_by(child_id=child_id, material_id=material_id).all()
        report = db.query(WeeklyReportModel).filter_by(child_id=child_id).one()
        assert attempts == []
        assert report.speaking_attempts == initial_speaking_attempts


def test_review_tasks_route_filters_archived_material_even_if_task_row_exists(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-archived-task-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.archived.value
        db.add(material)
        db.commit()

    response = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(item["material_id"] != material_id for item in response.json()["items"])
