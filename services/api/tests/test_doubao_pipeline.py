from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.models.contracts import CourseMaterial, JobStatus, MaterialParseJob
from app.services.pipeline import DoubaoLanguageParsingProvider, DoubaoProviderError, DoubaoVisionOCRProvider


def _material() -> CourseMaterial:
    return CourseMaterial(
        id="material_test",
        child_id="child_test",
        teacher_name="Emma",
        lesson_date=date(2026, 4, 29),
        title="Animals Around Me",
        topic="动物",
        status="processing",
    )


def _job() -> MaterialParseJob:
    return MaterialParseJob(
        id="job_test",
        material_id="material_test",
        status=JobStatus.needs_review,
        started_at=datetime.now(timezone.utc),
        draft_title="Animals Around Me",
        draft_topic="动物",
        draft_vocabulary=["cat", "dog", "bird"],
        draft_sentences=["What is this?", "It is a cat."],
    )


def _completion_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": content,
                    }
                }
            ]
        },
    )


def _client_for_response(response: httpx.Response) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_doubao_vision_provider_extracts_structured_ocr_draft(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    payload = {
        "ocr_text": "cat dog bird What is this? It is a cat.",
        "title": "Animals Around Me",
        "topic": "动物",
        "vocabulary": ["cat", "dog", "bird"],
        "sentences": ["What is this?", "It is a cat."],
        "warnings": ["图片略有倾斜，已提取主要内容。"],
        "confidence_summary": "识别结果较清晰，建议家长检查 bird。",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(_material(), [worksheet])

    assert draft.title == "Animals Around Me"
    assert draft.topic == "动物"
    assert draft.vocabulary == ["cat", "dog", "bird"]
    assert draft.sentences == ["What is this?", "It is a cat."]
    assert "bird" in draft.confidence_summary


@pytest.mark.parametrize(
    ("response", "expected_message"),
    [
        (_completion_response(""), "empty content"),
        (_completion_response("not-json"), "valid JSON"),
        (httpx.Response(401, json={"error": {"message": "bad key"}}), "401"),
        (httpx.Response(429, json={"error": {"message": "rate limited"}}), "429"),
        (httpx.Response(500, text="server error"), "500"),
    ],
)
def test_doubao_vision_provider_surfaces_readable_failures(
    tmp_path: Path,
    response: httpx.Response,
    expected_message: str,
) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(response),
    )

    with pytest.raises(DoubaoProviderError, match=expected_message):
        provider.extract(_material(), [worksheet])


def test_doubao_vision_provider_surfaces_timeout(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("request timed out", request=request)

    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DoubaoProviderError, match="timeout"):
        provider.extract(_material(), [worksheet])


def test_doubao_language_parser_generates_knowledge_pack_and_review_tasks() -> None:
    payload = {
        "topic": "动物",
        "lesson_summary": "本课练习 cat、dog、bird，并用 What is this? 提问。",
        "review_recommendation": "先词卡跟读，再做听音选择。",
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
    provider = DoubaoLanguageParsingProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-text-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    pack = provider.generate_knowledge_pack(_material(), _job())
    tasks = provider.generate_review_tasks(_material(), pack)

    assert pack.topic == "动物"
    assert [item.word for item in pack.vocabulary_items] == ["cat", "dog", "bird"]
    assert [item.sentence for item in pack.sentence_patterns] == ["What is this?", "It is a cat."]
    assert {task.task_type.value for task in tasks} == {"flashcard", "listen_choice", "match_choice"}
