from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.db.models import CourseMaterialModel, KnowledgePackModel, MaterialParseJobModel, ReviewTaskModel
from app.core.config import get_pipeline_service
from app.models.contracts import JobStatus, MaterialStatus
from app.services.pipeline import ProviderBackedPipelineService, StubOCRProvider
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


def test_create_material_enqueues_background_job(api_client, monkeypatch) -> None:
    enqueued_job_ids: list[str] = []
    monkeypatch.setattr(
        "app.api.parent.materials.enqueue_material_job",
        lambda job_id: enqueued_job_ids.append(job_id),
    )
    headers, _ = auth_headers(api_client, auth_code="enqueue-parent")
    child_id = _create_child(api_client, headers)

    _, job_id = _create_material(api_client, headers, child_id)

    assert enqueued_job_ids == [job_id]


def test_create_material_returns_failed_job_when_enqueue_fails(api_client, monkeypatch) -> None:
    def fail_enqueue(job_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.parent.materials.enqueue_material_job", fail_enqueue)
    headers, _ = auth_headers(api_client, auth_code="enqueue-fail-parent")
    child_id = _create_child(api_client, headers)

    response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-05-01",
            "title": "Storybook",
            "topic": "Phonics",
            "tags": "phonics",
            "file_sources": ["gallery"],
        },
        files=[("files", ("worksheet.txt", b"cat dog bird", "text/plain"))],
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["job"]["status"] == "failed"
    assert "排队失败" in payload["job"]["warnings"][0]
    assert payload["material"]["status"] == "failed"


def test_material_job_queue_uses_redis_url_for_result_backend(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeCelery:
        def __init__(self, name: str, *, broker: str, backend: str) -> None:
            captured["name"] = name
            captured["broker"] = broker
            captured["backend"] = backend
            self.conf = self

        def update(self, **kwargs) -> None:
            captured["queue"] = kwargs["task_default_queue"]

        def send_task(self, name: str, *, args: list[str], queue: str) -> None:
            captured["task"] = name
            captured["args"] = ",".join(args)
            captured["send_queue"] = queue

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
    monkeypatch.setitem(__import__("sys").modules, "celery", type("CeleryModule", (), {"Celery": FakeCelery}))

    from app.services.job_queue import enqueue_material_job

    enqueue_material_job("job_test")

    assert captured["broker"] == "redis://redis:6379/0"
    assert captured["backend"] == "redis://redis:6379/1"
    assert captured["task"] == "materials.process_material_job"


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
    enqueued_job_ids: list[str] = []
    from app.api.parent import material_jobs

    original_enqueue = material_jobs.enqueue_material_job
    material_jobs.enqueue_material_job = lambda job_id: enqueued_job_ids.append(job_id)
    headers, _ = auth_headers(api_client, auth_code="retry-failed-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        job.status = "failed"
        job.draft_learning_assets = [{"id": "stale_asset", "text": "stale", "kind": "word"}]
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
            }
        ]
        db.add(job)
        db.add(material)
        db.commit()

    try:
        response = api_client.post(f"/v1/material-jobs/{job_id}/retry", headers=headers)
    finally:
        material_jobs.enqueue_material_job = original_enqueue
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert response.json()["draft_learning_assets"][0]["id"] == "asset_queen"
    assert enqueued_job_ids == [job_id]

    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "processing"
    assert material_response.json()["material"]["parse_job_id"] == job_id


def test_confirm_job_persists_learning_assets_and_enqueues_media_job(api_client, monkeypatch) -> None:
    enqueued_material_ids: list[str] = []
    monkeypatch.setattr(
        "app.api.parent.material_jobs.enqueue_learning_asset_media_job",
        lambda material_id: enqueued_material_ids.append(material_id),
    )
    headers, _ = auth_headers(api_client, auth_code="confirm-assets-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Queen"
        job.draft_topic = "Phonics Qq"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["A queen can sing."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
            }
        ]
        material.status = MaterialStatus.needs_review.value
        db.add_all([job, material])
        db.commit()

    response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_topic": "Phonics Qq"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.ready.value
    assert enqueued_material_ids == [material_id]
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    assets = material_response.json()["material"]["learning_assets"]
    assert assets[0]["id"] == "asset_queen"
    assert assets[0]["translation"] == "女王"


def test_confirm_ready_job_is_idempotent(api_client, monkeypatch) -> None:
    enqueued_material_ids: list[str] = []
    monkeypatch.setattr(
        "app.api.parent.material_jobs.enqueue_learning_asset_media_job",
        lambda material_id: enqueued_material_ids.append(material_id),
    )
    headers, _ = auth_headers(api_client, auth_code="confirm-ready-idempotent-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.ready.value
        job.draft_title = "Ready Qq"
        job.draft_topic = "Phonics Qq"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
            }
        ]
        material.status = MaterialStatus.ready.value
        material.title = "Ready Qq"
        material.topic = "Phonics Qq"
        material.learning_assets = job.draft_learning_assets
        db.add_all([job, material])
        db.add(
            KnowledgePackModel(
                id="knowledge_existing",
                material_id=material_id,
                topic="Phonics Qq",
                difficulty_band="repeat",
                lesson_summary="已确认。",
                review_recommendation="继续复习。",
                vocabulary_items=[],
                sentence_patterns=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id="task_existing",
                child_id=child_id,
                material_id=material_id,
                task_type="flashcard",
                difficulty="easy",
                content_json={"asset_id": "asset_queen", "word": "queen"},
                due_date=datetime.now(timezone.utc),
                status="completed",
            )
        )
        db.commit()

    response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_title": "Changed Title"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.ready.value
    assert enqueued_material_ids == []
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        assert material.title == "Ready Qq"
        review_tasks = db.query(ReviewTaskModel).filter_by(material_id=material_id).all()
        assert [task.id for task in review_tasks] == ["task_existing"]
        assert review_tasks[0].status == "completed"
        assert db.get(KnowledgePackModel, "knowledge_existing") is not None


def test_confirm_job_keeps_course_ready_when_media_enqueue_fails(api_client, monkeypatch) -> None:
    def fail_enqueue(material_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.parent.material_jobs.enqueue_learning_asset_media_job", fail_enqueue)
    headers, _ = auth_headers(api_client, auth_code="confirm-media-enqueue-fail-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Queen"
        job.draft_topic = "Phonics Qq"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
            }
        ]
        material.status = MaterialStatus.needs_review.value
        db.add_all([job, material])
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={}, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert "媒体生成排队失败" in payload["warnings"][0]
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    material_payload = material_response.json()["material"]
    assert material_payload["status"] == "ready"
    assert material_payload["learning_assets"][0]["generated_image_status"] == "failed"
    assert material_payload["learning_assets"][0]["tts_us_status"] == "failed"
    assert material_payload["learning_assets"][0]["tts_uk_status"] == "failed"


def test_confirm_job_marks_media_enqueue_errors_on_learning_assets(api_client, monkeypatch) -> None:
    def fail_enqueue(material_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.parent.material_jobs.enqueue_learning_asset_media_job", fail_enqueue)
    headers, _ = auth_headers(api_client, auth_code="confirm-media-error-backfill-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Queen"
        job.draft_topic = "Phonics Qq"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
            }
        ]
        material.status = MaterialStatus.needs_review.value
        db.add_all([job, material])
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={}, headers=headers)

    assert response.status_code == 200
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    asset = material_response.json()["material"]["learning_assets"][0]
    assert asset["generated_image_status"] == "failed"
    assert "媒体生成排队失败" in asset["generated_image_error"]
    assert asset["tts_us_status"] == "failed"
    assert "媒体生成排队失败" in asset["tts_us_error"]
    assert asset["tts_uk_status"] == "failed"
    assert "媒体生成排队失败" in asset["tts_uk_error"]


def test_update_learning_asset_primary_accent(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="primary-accent-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
                "tts_us_status": "ready",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                "tts_uk_status": "ready",
                "tts_uk_url": "http://testserver/mock-media/hn014/tts/uk/queen.m4a",
            }
        ]
        db.add(
            KnowledgePackModel(
                id="knowledge_primary_accent",
                material_id=material_id,
                topic="Phonics Qq",
                difficulty_band="repeat",
                lesson_summary="复习 queen。",
                review_recommendation="先听音再跟读。",
                vocabulary_items=[
                    {
                        "id": "word_queen",
                        "knowledge_pack_id": "knowledge_primary_accent",
                        "word": "queen",
                        "meaning_cn": "女王",
                        "image_url": "",
                        "audio_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                        "example_sentence": "",
                    }
                ],
                sentence_patterns=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id="task_primary_accent",
                child_id=child_id,
                material_id=material_id,
                task_type="flashcard",
                difficulty="easy",
                content_json={
                    "asset_id": "asset_queen",
                    "word": "queen",
                    "audio_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                },
                due_date=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.add(material)
        db.commit()

    response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_queen/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )

    assert response.status_code == 200
    asset = response.json()["material"]["learning_assets"][0]
    assert asset["id"] == "asset_queen"
    assert asset["primary_accent"] == "uk"
    with SessionLocal() as db:
        knowledge_pack = db.get(KnowledgePackModel, "knowledge_primary_accent")
        assert knowledge_pack is not None
        assert knowledge_pack.vocabulary_items[0]["audio_url"] == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"
        review_task = db.get(ReviewTaskModel, "task_primary_accent")
        assert review_task is not None
        assert review_task.content_json["audio_url"] == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"

    missing_response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_missing/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )
    assert missing_response.status_code == 404


def test_update_primary_accent_rejects_unavailable_audio(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="primary-accent-unavailable-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
                "tts_us_status": "ready",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                "tts_uk_status": "failed",
                "tts_uk_error": "英式发音生成失败",
            }
        ]
        db.add(material)
        db.commit()

    response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_queen/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "英式发音暂不可用"


def test_update_primary_accent_allows_legacy_audio_urls_without_status(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="primary-accent-legacy-audio-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
                "tts_uk_url": "http://testserver/mock-media/hn014/tts/uk/queen.m4a",
            }
        ]
        db.add(material)
        db.commit()

    response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_queen/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )

    assert response.status_code == 200
    asset = response.json()["material"]["learning_assets"][0]
    assert asset["id"] == "asset_queen"
    assert asset["primary_accent"] == "uk"


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
    assert payload["status"] == JobStatus.processing.value
    assert payload["confidence_summary"] == "上传完成，等待 OCR 与解析。"

    material_response = api_client.get(f"/v1/materials/{upload_response.json()['material']['id']}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "processing"
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


def test_confirm_job_does_not_wait_for_language_provider(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="confirm-fast-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = JobStatus.needs_review.value
        job.draft_title = "Run, Hop, Go!"
        job.draft_topic = "Phonics Rr"
        job.draft_vocabulary = ["run", "hop", "go"]
        job.draft_sentences = ["A horse can run fast."]
        db.add(job)
        db.commit()

    class FailingLanguageProvider:
        def generate_knowledge_pack(self, *args, **kwargs):
            raise RuntimeError("external language provider should not be called during confirm")

        def generate_review_tasks(self, *args, **kwargs):
            raise RuntimeError("external language provider should not be called during confirm")

    app.dependency_overrides[get_pipeline_service] = lambda: ProviderBackedPipelineService(
        ocr_provider=StubOCRProvider(),
        parsing_provider=FailingLanguageProvider(),
    )
    try:
        response = api_client.post(
            f"/v1/material-jobs/{job_id}/confirm",
            json={
                "draft_title": "Run, Hop, Go!",
                "draft_topic": "Phonics Rr",
                "draft_vocabulary": ["run", "hop", "go"],
                "draft_sentences": ["A horse can run fast."],
            },
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_pipeline_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.ready.value

    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "ready"
