from __future__ import annotations

import json

import httpx

from app.core.config import get_pipeline_service
from app.main import app
from app.services.pipeline import DoubaoLanguageParsingProvider, DoubaoVisionOCRProvider, ProviderBackedPipelineService
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-doubao-slice-")


def _client_for_json_payload(payload: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    }
                ]
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fake_doubao_upload_review_confirm_generates_ready_tasks(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="doubao-vertical-parent")
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "稳定复习",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "喜欢动物主题",
        },
        headers=headers,
    )
    child_id = child_response.json()["id"]

    ocr_payload = {
        "ocr_text": "cat dog bird What is this? It is a cat.",
        "title": "Animals Around Me",
        "topic": "动物",
        "vocabulary": ["cat", "dog", "bird"],
        "sentences": ["What is this?", "It is a cat."],
        "warnings": [],
        "confidence_summary": "豆包识别到 3 个核心词和 2 个句型。",
    }
    parse_payload = {
        "topic": "动物",
        "lesson_summary": "本课围绕动物词汇和 What is this? 句型展开。",
        "review_recommendation": "先做词卡，再做听音选图和配对。",
        "vocabulary_items": [
            {"word": "cat", "meaning_cn": "猫", "example_sentence": "It is a cat."},
            {"word": "dog", "meaning_cn": "狗", "example_sentence": "It is a dog."},
            {"word": "bird", "meaning_cn": "鸟", "example_sentence": "It is a bird."},
        ],
        "sentence_patterns": [
            {"sentence": "What is this?", "meaning_cn": "这是什么？", "usage_type": "question"},
            {"sentence": "It is a cat.", "meaning_cn": "它是一只猫。", "usage_type": "answer"},
        ],
    }
    app.dependency_overrides[get_pipeline_service] = lambda: ProviderBackedPipelineService(
        ocr_provider=DoubaoVisionOCRProvider(
            api_key="ark-key",
            base_url="https://ark.test/api/v3",
            model_or_endpoint="doubao-vision-test",
            client=_client_for_json_payload(ocr_payload),
        ),
        parsing_provider=DoubaoLanguageParsingProvider(
            api_key="ark-key",
            base_url="https://ark.test/api/v3",
            model_or_endpoint="doubao-text-test",
            client=_client_for_json_payload(parse_payload),
        ),
    )
    try:
        upload_response = api_client.post(
            "/v1/materials",
            data={
                "child_id": child_id,
                "teacher_name": "Emma",
                "lesson_date": "2026-04-29",
                "title": "Animals Around Me",
                "topic": "动物",
                "tags": "动物,MVP",
            },
            files=[("files", ("worksheet.jpg", b"fake image bytes", "image/jpeg"))],
            headers=headers,
        )
        assert upload_response.status_code == 201
        material_id = upload_response.json()["material"]["id"]
        job_id = upload_response.json()["job"]["id"]

        job_response = api_client.get(f"/v1/material-jobs/{job_id}", headers=headers)
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["status"] == "needs_review"
        assert job["draft_vocabulary"] == ["cat", "dog", "bird"]

        confirm_response = api_client.post(
            f"/v1/material-jobs/{job_id}/confirm",
            json={
                "draft_title": job["draft_title"],
                "draft_topic": job["draft_topic"],
                "draft_vocabulary": job["draft_vocabulary"],
                "draft_sentences": job["draft_sentences"],
            },
            headers=headers,
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "ready"

        knowledge_response = api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers)
        assert knowledge_response.status_code == 200
        pack = knowledge_response.json()["knowledge_pack"]
        assert [item["word"] for item in pack["vocabulary_items"]] == ["cat", "dog", "bird"]

        tasks_response = api_client.get(f"/v1/review-tasks?material_id={material_id}", headers=headers)
        assert tasks_response.status_code == 200
        assert {item["task_type"] for item in tasks_response.json()["items"]} == {
            "flashcard",
            "listen_choice",
            "match_choice",
        }
    finally:
        app.dependency_overrides.pop(get_pipeline_service, None)
