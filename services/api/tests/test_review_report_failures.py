from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.db import SessionLocal
from app.db.models import (
    CourseMaterialModel,
    MaterialParseJobModel,
    PracticeSessionModel,
    ReviewTaskModel,
    SpeakingAttemptModel,
)
from app.models.contracts import JobStatus, MaterialStatus, ReviewTaskStatus, SpeakingAttemptStatus, TaskType
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
        data={
            "child_id": child_id,
            "material_id": "material_missing",
            "prompt_text": "What is this?",
            "target_text": "It is a cat.",
        },
        files={"audio": ("answer.m4a", b"fake-audio", "audio/mp4")},
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Material not found"


def test_weekly_report_rejects_unknown_child(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="missing-report-parent")
    response = api_client.get("/v1/reports/weekly", params={"child_id": "child_missing"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Child not found"


def test_weekly_report_includes_learning_asset_mastery(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="asset-mastery-report-parent")
    child_id = _create_child(api_client, headers)
    with SessionLocal() as db:
        material = CourseMaterialModel(
            id="material_report_assets",
            child_id=child_id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 25),
            title="Run, Hop, Go!",
            topic="Phonics Rr",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_rabbit",
                    "text": "rabbit",
                    "kind": "word",
                    "translation": "兔子",
                    "generated_image_url": "https://cdn.test/rabbit.png",
                    "tts_us_url": "https://cdn.test/rabbit-us.mp3",
                    "primary_accent": "us",
                },
                {
                    "id": "asset_sentence",
                    "text": "A rabbit can hop fast.",
                    "kind": "sentence",
                    "translation": "兔子能跳得很快。",
                    "generated_image_url": "https://cdn.test/rabbit-hop.png",
                    "primary_accent": "us",
                },
            ],
        )
        completed_task = ReviewTaskModel(
            id="task_report_rabbit",
            child_id=child_id,
            material_id=material.id,
            task_type=TaskType.flashcard.value,
            difficulty="easy",
            content_json={"asset_id": "asset_rabbit", "text": "rabbit", "prompt": "看图跟读：rabbit"},
            due_date=datetime.now(timezone.utc),
            status=ReviewTaskStatus.completed.value,
        )
        pending_task = ReviewTaskModel(
            id="task_report_sentence",
            child_id=child_id,
            material_id=material.id,
            task_type=TaskType.speaking_prompt.value,
            difficulty="repeat",
            content_json={
                "asset_id": "asset_sentence",
                "text": "A rabbit can hop fast.",
                "prompt": "跟读句子：A rabbit can hop fast.",
            },
            due_date=datetime.now(timezone.utc),
            status=ReviewTaskStatus.pending.value,
        )
        session = PracticeSessionModel(
            child_id=child_id,
            review_task_ids=[completed_task.id],
            score=86,
            weak_points=["A rabbit can hop fast."],
        )
        attempt = SpeakingAttemptModel(
            id="attempt_report_rabbit",
            child_id=child_id,
            material_id=material.id,
            learning_asset_id="asset_rabbit",
            prompt_text="Read rabbit aloud.",
            target_text="rabbit",
            audio_url="https://cdn.test/attempt.m4a",
            audio_object_key="speaking/attempt.m4a",
            transcript="rabbit",
            pronunciation_score=0.91,
            overall_score=92,
            accuracy_score=93,
            fluency_score=90,
            completeness_score=95,
            feedback="rabbit 读得清楚。",
            status=SpeakingAttemptStatus.scored.value,
        )
        db.add_all([material, completed_task, pending_task, session, attempt])
        db.commit()

    response = api_client.get("/v1/reports/weekly", params={"child_id": child_id}, headers=headers)

    assert response.status_code == 200
    report = response.json()["report"]
    assert "2 个学习资产" in report["report_summary"]
    assert report["material_summaries"] == [
        {
            "material_id": "material_report_assets",
            "title": "Run, Hop, Go!",
            "topic": "Phonics Rr",
            "asset_count": 2,
            "completed_review_tasks": 1,
            "pending_review_tasks": 1,
            "speaking_attempts": 1,
            "average_speaking_score": 92.0,
        }
    ]
    by_asset = {item["asset_id"]: item for item in report["asset_mastery"]}
    assert by_asset["asset_rabbit"]["mastery_status"] == "mastered"
    assert by_asset["asset_rabbit"]["completed_review_tasks"] == 1
    assert by_asset["asset_rabbit"]["speaking_attempts"] == 1
    assert by_asset["asset_rabbit"]["best_speaking_score"] == 92.0
    assert by_asset["asset_sentence"]["mastery_status"] == "needs_practice"
    assert by_asset["asset_sentence"]["weak_points"] == ["A rabbit can hop fast."]


def test_review_tasks_filter_returns_created_tasks(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="review-filter-parent")
    child_id = _create_child(api_client, headers)
    _, task_ids = _create_ready_material(api_client, headers, child_id)

    response = api_client.get("/v1/review-tasks", params={"child_id": child_id}, headers=headers)
    assert response.status_code == 200
    returned_ids = [item["id"] for item in response.json()["items"]]
    assert set(task_ids).issubset(set(returned_ids))
