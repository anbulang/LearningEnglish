from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.db.models import (
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
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


def _seed_ready_derivatives(material_id: str, job_id: str, child_id: str) -> None:
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
                id="knowledge_delete",
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
                id="coach_delete",
                material_id=material_id,
                title="亲子陪练",
                intro="和孩子一起读 rabbit。",
                steps=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id="task_delete",
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


def test_delete_material_archives_material_and_removes_visible_derivatives(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-owner")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)

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
        assert db.get(KnowledgePackModel, "knowledge_delete") is None
        assert db.get(ParentCoachingScriptModel, "coach_delete") is None
        assert db.get(ReviewTaskModel, "task_delete") is None


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
