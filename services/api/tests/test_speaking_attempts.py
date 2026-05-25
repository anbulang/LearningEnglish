from __future__ import annotations

from datetime import date

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, SpeakingAttemptModel, StoredAssetModel
from app.models.contracts import MaterialStatus
from app.models.contracts import SpeakingAttempt, SpeakingAttemptStatus, SpeakingWordFeedback
from conftest import auth_headers


def test_speaking_attempt_contract_includes_scoring_details() -> None:
    attempt = SpeakingAttempt(
        id="attempt_test",
        child_id="child_test",
        material_id="material_test",
        review_task_id="task_test",
        learning_asset_id="asset_test",
        prompt_text="跟读：A rabbit can hop fast.",
        target_text="A rabbit can hop fast.",
        audio_url="http://testserver/uploads/speaking_attempt/attempt_test/input.m4a",
        audio_object_key="speaking_attempt/attempt_test/input.m4a",
        audio_content_type="audio/mp4",
        audio_size_bytes=1024,
        audio_duration_ms=3200,
        transcript="A rabbit can hop fast.",
        pronunciation_score=0.86,
        overall_score=88,
        accuracy_score=91,
        fluency_score=82,
        completeness_score=95,
        feedback="整体读得很清楚。",
        word_feedback=[
            SpeakingWordFeedback(word="rabbit", score=92, status="good", tip="读得清楚。"),
            SpeakingWordFeedback(word="hop", score=74, status="needs_practice", tip="注意 h 的轻出气。"),
        ],
        suggestions=["再跟读一次 hop。"],
        provider="stub",
        raw_result={"source": "test"},
        failure_reason="",
        status=SpeakingAttemptStatus.scored,
    )

    payload = attempt.model_dump(mode="json")

    assert payload["target_text"] == "A rabbit can hop fast."
    assert payload["overall_score"] == 88
    assert payload["word_feedback"][1]["status"] == "needs_practice"
    assert payload["audio_object_key"] == "speaking_attempt/attempt_test/input.m4a"


def _create_child_and_material(api_client, headers: dict[str, str]) -> tuple[str, str]:
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "喜欢看图复习",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]
    material = CourseMaterialModel(
        child_id=child_id,
        teacher_name="Emma",
        lesson_date=date(2026, 5, 25),
        title="Run, Hop, Go!",
        topic="Phonics Rr",
        status=MaterialStatus.ready.value,
        learning_assets=[
            {
                "id": "asset_rabbit",
                "text": "A rabbit can hop fast.",
                "kind": "sentence",
                "translation": "兔子能跳得很快。",
                "pronunciation_text": "A rabbit can hop fast.",
                "primary_accent": "us",
            }
        ],
    )
    with SessionLocal() as db:
        db.add(material)
        db.commit()
        db.refresh(material)
        return child_id, material.id


def test_create_speaking_attempt_uploads_audio_and_enqueues(api_client, monkeypatch) -> None:
    headers, _ = auth_headers(api_client, auth_code="speaking-upload-parent")
    child_id, material_id = _create_child_and_material(api_client, headers)
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.routes.speaking_attempts.enqueue_speaking_attempt_job", enqueued.append)

    response = api_client.post(
        "/v1/speaking-attempts",
        data={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "跟读：A rabbit can hop fast.",
            "target_text": "A rabbit can hop fast.",
            "learning_asset_id": "asset_rabbit",
            "audio_duration_ms": "3100",
        },
        files={"audio": ("rabbit.m4a", b"fake-audio", "audio/mp4")},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "recording_uploaded"
    assert payload["audio_url"].startswith("http://testserver/uploads/speaking_attempt/")
    assert payload["audio_object_key"].startswith("speaking_attempt/")
    assert payload["audio_size_bytes"] == len(b"fake-audio")
    assert enqueued == [payload["id"]]
    with SessionLocal() as db:
        stored = db.query(StoredAssetModel).filter_by(owner_type="speaking_attempt", owner_id=payload["id"]).one()
        assert stored.object_key == payload["audio_object_key"]


def test_create_speaking_attempt_rejects_archived_material(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="speaking-archived-parent")
    child_id, material_id = _create_child_and_material(api_client, headers)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.archived.value
        db.add(material)
        db.commit()

    response = api_client.post(
        "/v1/speaking-attempts",
        data={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "跟读：A rabbit can hop fast.",
            "target_text": "A rabbit can hop fast.",
        },
        files={"audio": ("rabbit.m4a", b"fake-audio", "audio/mp4")},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Material not found"


def test_create_speaking_attempt_rejects_unsupported_audio_type(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="speaking-audio-type-parent")
    child_id, material_id = _create_child_and_material(api_client, headers)

    response = api_client.post(
        "/v1/speaking-attempts",
        data={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "跟读：A rabbit can hop fast.",
            "target_text": "A rabbit can hop fast.",
        },
        files={"audio": ("rabbit.txt", b"fake-audio", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported audio type"


def test_get_speaking_attempt_requires_owner(api_client, monkeypatch) -> None:
    owner_headers, _ = auth_headers(api_client, auth_code="speaking-owner-parent")
    child_id, material_id = _create_child_and_material(api_client, owner_headers)
    monkeypatch.setattr("app.api.routes.speaking_attempts.enqueue_speaking_attempt_job", lambda attempt_id: None)
    create_response = api_client.post(
        "/v1/speaking-attempts",
        data={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "跟读：A rabbit can hop fast.",
            "target_text": "A rabbit can hop fast.",
        },
        files={"audio": ("rabbit.m4a", b"fake-audio", "audio/mp4")},
        headers=owner_headers,
    )
    assert create_response.status_code == 201
    other_headers, _ = auth_headers(api_client, auth_code="speaking-other-parent")

    response = api_client.get(f"/v1/speaking-attempts/{create_response.json()['id']}", headers=other_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Speaking attempt not found"


def test_retry_speaking_attempt_requeues_failed_attempt(api_client, monkeypatch) -> None:
    headers, _ = auth_headers(api_client, auth_code="speaking-retry-parent")
    child_id, material_id = _create_child_and_material(api_client, headers)
    attempt = SpeakingAttemptModel(
        child_id=child_id,
        material_id=material_id,
        prompt_text="跟读：A rabbit can hop fast.",
        target_text="A rabbit can hop fast.",
        audio_url="http://testserver/uploads/speaking_attempt/attempt_retry/rabbit.m4a",
        audio_object_key="speaking_attempt/attempt_retry/rabbit.m4a",
        audio_content_type="audio/mp4",
        audio_size_bytes=10,
        status=SpeakingAttemptStatus.failed.value,
        failure_reason="评分失败",
    )
    with SessionLocal() as db:
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        attempt_id = attempt.id
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.routes.speaking_attempts.enqueue_speaking_attempt_job", enqueued.append)

    response = api_client.post(f"/v1/speaking-attempts/{attempt_id}/retry", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "recording_uploaded"
    assert payload["failure_reason"] == ""
    assert enqueued == [attempt_id]
