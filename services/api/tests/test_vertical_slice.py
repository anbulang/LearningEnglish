from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_vertical_slice_flow() -> None:
    children_response = client.get("/v1/children")
    assert children_response.status_code == 200
    children = children_response.json()
    assert children
    child_id = children[0]["id"]

    create_material_response = client.post(
        "/v1/materials",
        json={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-03-25",
            "title": "Animals Around Me",
            "topic": "动物",
            "source_images": ["demo://worksheet-new"],
            "tags": ["动物", "MVP"],
        },
    )
    assert create_material_response.status_code == 201
    created = create_material_response.json()
    material_id = created["material"]["id"]
    job_id = created["job"]["id"]
    assert created["material"]["status"] == "processing"

    job_response = client.get(f"/v1/material-jobs/{job_id}")
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "needs_review"
    assert job["draft_vocabulary"]

    confirm_response = client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={
            "draft_topic": "动物",
        },
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "ready"

    knowledge_response = client.get(f"/v1/knowledge-packs/{material_id}")
    assert knowledge_response.status_code == 200
    knowledge = knowledge_response.json()
    assert knowledge["knowledge_pack"]["vocabulary_items"]

    coaching_response = client.get(f"/v1/parent-coaching/{material_id}")
    assert coaching_response.status_code == 200
    assert coaching_response.json()["steps"]

    tasks_response = client.get(
        "/v1/review-tasks",
        params={"child_id": child_id, "material_id": material_id},
    )
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["items"]
    assert len(tasks) == 3

    speaking_response = client.post(
        "/v1/speaking-attempts",
        json={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "What is this?",
            "transcript": "It is a cat.",
        },
    )
    assert speaking_response.status_code == 201
    assert speaking_response.json()["status"] == "scored"

    session_response = client.post(
        "/v1/practice-sessions",
        json={
            "child_id": child_id,
            "review_task_ids": [task["id"] for task in tasks],
            "score": 92,
            "weak_points": ["bird"],
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["review_task_ids"]

    report_response = client.get("/v1/reports/weekly", params={"child_id": child_id})
    assert report_response.status_code == 200
    report = report_response.json()["report"]
    assert report["completed_sessions"] >= 1
    assert report["speaking_attempts"] >= 1
    assert "bird" in report["weak_items"]
