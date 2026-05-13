from __future__ import annotations

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, MaterialParseJobModel
from app.models.contracts import JobStatus, MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-test-")


def _mark_job_needs_review(material_id: str, job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.needs_review.value
        job.draft_title = "Animals Around Me"
        job.draft_topic = "动物"
        job.draft_vocabulary = ["cat", "dog", "bird"]
        job.draft_sentences = ["What is this?", "It is a cat."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "pronunciation_text": "queen",
                "image_prompt": "A friendly queen for a phonics worksheet.",
                "primary_accent": "us",
            },
            {
                "id": "asset_sentence_queen",
                "text": "A queen can sing.",
                "kind": "sentence",
                "translation": "女王会唱歌。",
                "source_page_index": 1,
                "pronunciation_text": "A queen can sing.",
                "image_prompt": "A queen singing.",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                "tts_uk_url": "http://testserver/mock-media/hn014/tts/uk/queen.m4a",
                "primary_accent": "uk",
            },
        ]
        job.confidence_summary = "测试已模拟 worker 完成识别。"
        material.status = MaterialStatus.needs_review.value
        material.topic = "动物"
        material.ocr_text = "cat dog bird What is this? It is a cat."
        db.add_all([job, material])
        db.commit()


def test_vertical_slice_flow(api_client, monkeypatch) -> None:
    enqueued_media_material_ids: list[str] = []
    monkeypatch.setattr(
        "app.api.routes.material_jobs.enqueue_learning_asset_media_job",
        lambda material_id: enqueued_media_material_ids.append(material_id),
    )

    health_response = api_client.get("/healthz", headers={"x-request-id": "req_test_1"})
    assert health_response.status_code == 200
    assert health_response.headers["x-request-id"] == "req_test_1"

    headers, refresh_token = auth_headers(api_client)

    me_response = api_client.get("/v1/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["parent_account"]["phone_number"] == "13800138000"

    child_response = api_client.post(
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
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    create_material_response = api_client.post(
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
    assert create_material_response.status_code == 201
    created = create_material_response.json()
    material_id = created["material"]["id"]
    job_id = created["job"]["id"]
    assert created["material"]["status"] == "processing"

    material_detail_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_detail_response.status_code == 200
    assert material_detail_response.json()["material"]["id"] == material_id

    job_response = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "processing"

    _mark_job_needs_review(material_id, job_id)

    confirm_response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_topic": "动物"},
        headers=headers,
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "ready"
    assert enqueued_media_material_ids == [material_id]

    material_detail_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_detail_response.status_code == 200
    confirmed_assets = material_detail_response.json()["material"]["learning_assets"]
    assert [asset["id"] for asset in confirmed_assets] == ["asset_queen", "asset_sentence_queen"]

    knowledge_response = api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers)
    assert knowledge_response.status_code == 200
    knowledge = knowledge_response.json()
    assert knowledge["knowledge_pack"]["vocabulary_items"][0]["word"] == "queen"
    assert knowledge["knowledge_pack"]["vocabulary_items"][0]["meaning_cn"] == "女王"
    assert knowledge["knowledge_pack"]["sentence_patterns"][0]["sentence"] == "A queen can sing."
    assert knowledge["knowledge_pack"]["sentence_patterns"][0]["meaning_cn"] == "女王会唱歌。"

    coaching_response = api_client.get(f"/v1/parent-coaching/{material_id}", headers=headers)
    assert coaching_response.status_code == 200
    assert coaching_response.json()["steps"]

    tasks_response = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id, "material_id": material_id},
        headers=headers,
    )
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["items"]
    assert len(tasks) == 2
    assert {task["task_type"] for task in tasks} == {"flashcard"}
    assert {task["content_json"]["asset_id"] for task in tasks} == {"asset_queen", "asset_sentence_queen"}

    speaking_response = api_client.post(
        "/v1/speaking-attempts",
        json={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "What is this?",
            "transcript": "It is a cat.",
        },
        headers=headers,
    )
    assert speaking_response.status_code == 201
    assert speaking_response.json()["status"] == "scored"

    session_response = api_client.post(
        "/v1/practice-sessions",
        json={
            "child_id": child_id,
            "review_task_ids": [task["id"] for task in tasks],
            "score": 92,
            "weak_points": ["bird"],
        },
        headers=headers,
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["review_task_ids"]

    report_response = api_client.get("/v1/reports/weekly", params={"child_id": child_id}, headers=headers)
    assert report_response.status_code == 200
    report = report_response.json()["report"]
    assert report["completed_sessions"] >= 1
    assert report["speaking_attempts"] >= 1
    assert "bird" in report["weak_items"]

    refresh_response = api_client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["status"] == "authenticated"
