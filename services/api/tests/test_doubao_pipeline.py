from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.core.settings import get_settings
from app.models.contracts import CourseMaterial, JobStatus, MaterialImageRecord, MaterialParseJob
from app.services.pipeline import (
    DashScopeProviderError,
    DoubaoLanguageParsingProvider,
    DoubaoProviderError,
    DoubaoVisionOCRProvider,
    QwenLanguageParsingProvider,
    QwenVisionOCRProvider,
    _fallback_learning_assets,
    build_pipeline_service,
)


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
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": content}],
                }
            ]
        },
    )


def _dashscope_chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                    }
                }
            ]
        },
    )


def _client_for_response(
    response: httpx.Response,
    *,
    expected_content_types: list[str] | None = None,
    inspect_content=None,
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/responses"
        payload = json.loads(request.content)
        assert payload["model"]
        if expected_content_types is not None:
            content = payload["input"][0]["content"]
            assert [item["type"] for item in content] == expected_content_types
        if inspect_content is not None:
            inspect_content(payload["input"][0]["content"])
        return response

    return httpx.Client(transport=httpx.MockTransport(handler))


def _dashscope_client_for_response(
    response: httpx.Response,
    *,
    inspect_payload=None,
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/compatible-mode/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"]
        if inspect_payload is not None:
            inspect_payload(payload)
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
        "image_records": [
            {
                "page_index": 1,
                "image_title": "Animals page",
                "ocr_text": "cat dog bird",
                "vocabulary": ["cat", "dog", "bird"],
                "sentences": ["What is this?", "It is a cat."],
                "details": ["图片中包含动物词汇和问答句型。"],
            }
        ],
        "warnings": ["图片略有倾斜，已提取主要内容。"],
        "confidence_summary": "识别结果较清晰，建议家长检查 bird。",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(
            _completion_response(json.dumps(payload, ensure_ascii=False)),
            expected_content_types=["input_text", "input_text", "input_text", "input_image"],
        ),
    )

    draft = provider.extract(_material(), [worksheet])

    assert draft.title == "Animals Around Me"
    assert draft.topic == "动物"
    assert draft.vocabulary == ["cat", "dog", "bird"]
    assert draft.sentences == ["What is this?", "It is a cat."]
    assert len(draft.image_records) == 1
    assert draft.image_records[0].image_title == "Animals page"
    assert draft.image_records[0].vocabulary == ["cat", "dog", "bird"]
    assert draft.image_records[0].details == ["图片中包含动物词汇和问答句型。"]
    assert "bird" in draft.confidence_summary


def test_doubao_vision_provider_extracts_json_from_wrapped_response(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    payload = {
        "ocr_text": "Find the queen. Quick!",
        "title": "Quick!",
        "topic": "Qq phonics",
        "vocabulary": ["queen"],
        "sentences": ["Find the queen. Quick!"],
        "warnings": [],
        "confidence_summary": "识别清晰。",
    }
    wrapped = (
        "下面是结构化结果：\n"
        "```json\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "```\n"
        "请家长确认。"
    )
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(wrapped)),
    )

    draft = provider.extract(_material(), [worksheet])

    assert draft.title == "Quick!"
    assert draft.vocabulary == ["queen"]


def test_qwen_vision_provider_extracts_structured_ocr_draft(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    payload = {
        "ocr_text": "A rabbit can hop fast.",
        "title": "Run, Hop, Go!",
        "topic": "Rr phonics",
        "vocabulary": ["rabbit", "hop"],
        "sentences": ["A rabbit can hop fast."],
        "image_records": [
            {
                "page_index": 1,
                "image_title": "Rabbit page",
                "ocr_text": "A rabbit can hop fast.",
                "vocabulary": ["rabbit", "hop"],
                "sentences": ["A rabbit can hop fast."],
                "details": ["图片中有一只跳跃的兔子。"],
            }
        ],
        "learning_assets": [
            {
                "text": "A rabbit can hop fast.",
                "kind": "sentence",
                "translation": "兔子可以跳得很快。",
                "source_page_index": 1,
                "source_visual_description": "兔子向前跳跃。",
                "pronunciation_text": "A rabbit can hop fast.",
                "image_prompt": "A colorful rabbit hopping fast.",
                "difficulty": "easy",
                "teaching_note": "注意 rabbit 和 hop 的发音。",
            }
        ],
        "warnings": [],
        "confidence_summary": "百炼识别到 1 个核心句子。",
    }

    def inspect_payload(request_payload: dict) -> None:
        assert request_payload["model"] == "qwen-vl-test"
        content = request_payload["messages"][1]["content"]
        assert [item["type"] for item in content] == ["text", "text", "image_url"]
        assert "image_records 数量必须等于输入图片数量" in content[0]["text"]
        assert "source_bbox 必须返回" in content[0]["text"]
        assert "不要返回空值" in content[0]["text"]
        assert content[2]["image_url"]["url"].startswith("data:image")

    provider = QwenVisionOCRProvider(
        api_key="dashscope-key",
        base_url="https://dashscope.test/compatible-mode/v1",
        model="qwen-vl-test",
        client=_dashscope_client_for_response(
            _dashscope_chat_response(json.dumps(payload, ensure_ascii=False)),
            inspect_payload=inspect_payload,
        ),
    )

    draft = provider.extract(_material(), [worksheet])

    assert draft.title == "Run, Hop, Go!"
    assert draft.topic == "Rr phonics"
    assert draft.vocabulary == ["rabbit", "hop"]
    assert draft.sentences == ["A rabbit can hop fast."]
    assert draft.image_records[0].image_title == "Rabbit page"
    assert draft.learning_assets[0].text == "A rabbit can hop fast."
    assert draft.learning_assets[0].source_bbox is not None
    assert draft.confidence_summary == "百炼识别到 1 个核心句子。"


def test_qwen_vision_provider_keeps_record_for_each_uploaded_image(tmp_path: Path) -> None:
    first_page = tmp_path / "page-1.jpg"
    second_page = tmp_path / "page-2.jpg"
    first_page.write_bytes(b"fake-page-1")
    second_page.write_bytes(b"fake-page-2")
    payload = {
        "ocr_text": "A horse can run fast. Find the queen. Quick!",
        "title": "Storybook",
        "topic": "phonics",
        "vocabulary": ["horse", "queen"],
        "sentences": ["A horse can run fast.", "Find the queen."],
        "image_records": [
            {
                "page_index": 1,
                "image_title": "Run, Hop, Go!",
                "ocr_text": "A horse can run fast.",
                "vocabulary": ["horse"],
                "sentences": ["A horse can run fast."],
                "details": ["第一页识别成功。"],
            }
        ],
        "learning_assets": [],
        "warnings": ["第二页识别结果缺失，已使用整体内容补齐。"],
    }
    provider = QwenVisionOCRProvider(
        api_key="dashscope-key",
        base_url="https://dashscope.test/compatible-mode/v1",
        model="qwen-vl-test",
        client=_dashscope_client_for_response(_dashscope_chat_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(_material(), [first_page, second_page])

    assert [record.page_index for record in draft.image_records] == [1, 2]
    assert draft.image_records[0].image_title == "Run, Hop, Go!"
    assert draft.image_records[1].image_title == "Storybook 第 2 页"
    assert draft.image_records[1].vocabulary == ["horse", "queen"]
    assert draft.image_records[1].sentences == ["A horse can run fast.", "Find the queen."]


def test_qwen_vision_provider_rejects_invalid_json(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    provider = QwenVisionOCRProvider(
        api_key="dashscope-key",
        base_url="https://dashscope.test/compatible-mode/v1",
        model="qwen-vl-test",
        client=_dashscope_client_for_response(_dashscope_chat_response("not json")),
    )

    with pytest.raises(DashScopeProviderError, match="valid JSON"):
        provider.extract(_material(), [worksheet])


def test_qwen_language_provider_parses_knowledge_pack() -> None:
    payload = {
        "topic": "Rr phonics",
        "lesson_summary": "练习 rabbit 和 hop。",
        "review_recommendation": "先跟读句子，再做口语练习。",
        "vocabulary_items": [{"word": "rabbit", "meaning_cn": "兔子"}],
        "sentence_patterns": [
            {
                "sentence": "A rabbit can hop fast.",
                "meaning_cn": "兔子可以跳得很快。",
                "usage_type": "sentence",
            }
        ],
    }
    provider = QwenLanguageParsingProvider(
        api_key="dashscope-key",
        base_url="https://dashscope.test/compatible-mode/v1",
        model="qwen-plus-test",
        client=_dashscope_client_for_response(_dashscope_chat_response(json.dumps(payload, ensure_ascii=False))),
    )

    pack = provider.generate_knowledge_pack(_material(), _job())

    assert pack.topic == "Rr phonics"
    assert [item.word for item in pack.vocabulary_items] == ["rabbit"]
    assert [item.sentence for item in pack.sentence_patterns] == ["A rabbit can hop fast."]


def test_build_pipeline_service_uses_qwen_vision_and_language_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "qwen")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")
    monkeypatch.setenv("DASHSCOPE_COMPATIBLE_BASE_URL", "https://dashscope.test/compatible-mode/v1")
    monkeypatch.setenv("QWEN_VISION_MODEL", "qwen-vl-test")
    monkeypatch.setenv("QWEN_MODEL", "qwen-plus-test")
    get_settings.cache_clear()

    service = build_pipeline_service()

    assert isinstance(service.ocr_provider, QwenVisionOCRProvider)
    assert isinstance(service.parsing_provider, QwenLanguageParsingProvider)
    assert service.ocr_provider.base_url == "https://dashscope.test/compatible-mode/v1"
    assert service.ocr_provider.model == "qwen-vl-test"
    assert service.parsing_provider.model == "qwen-plus-test"
    get_settings.cache_clear()


def test_build_pipeline_service_rejects_qwen_without_dashscope_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "qwen")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        build_pipeline_service()

    get_settings.cache_clear()


def test_doubao_vision_provider_normalizes_list_title_and_topic(tmp_path: Path) -> None:
    worksheet = tmp_path / "worksheet.jpg"
    worksheet.write_bytes(b"fake-image")
    payload = {
        "ocr_text": "A horse can run fast. Find the queen. Quick!",
        "title": ["Run, Hop, Go!", "Quick!"],
        "topic": ["Phonics: Rr", "Phonics: Qq"],
        "vocabulary": ["run", "queen"],
        "sentences": ["A horse can run fast.", "Find the queen. Quick!"],
        "warnings": [],
        "confidence_summary": "识别清晰。",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(
            _completion_response(json.dumps(payload, ensure_ascii=False)),
            expected_content_types=["input_text", "input_text", "input_text", "input_image"],
        ),
    )

    draft = provider.extract(_material(), [worksheet])

    assert draft.title == "Run, Hop, Go! / Quick!"
    assert draft.topic == "Phonics: Rr / Phonics: Qq"


def test_doubao_vision_provider_sends_page_labels_between_multiple_images(tmp_path: Path) -> None:
    first = tmp_path / "rr.jpg"
    second = tmp_path / "qq.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    payload = {
        "ocr_text": "A horse can run fast. Find the queen. Quick!",
        "title": "Phonics storybooks",
        "topic": "Rr / Qq",
        "vocabulary": ["run", "queen"],
        "sentences": ["A horse can run fast.", "Find the queen."],
        "image_records": [
            {"page_index": 1, "image_title": "Rr page", "ocr_text": "Rr", "vocabulary": ["run"], "sentences": []},
            {"page_index": 2, "image_title": "Qq page", "ocr_text": "Qq", "vocabulary": ["queen"], "sentences": []},
        ],
        "warnings": [],
        "confidence_summary": "识别清晰。",
    }

    def inspect_content(content: list[dict[str, str]]) -> None:
        assert [item["type"] for item in content] == [
            "input_text",
            "input_text",
            "input_text",
            "input_image",
            "input_text",
            "input_image",
        ]
        assert "第 1 页" in content[2]["text"]
        assert "第 2 页" in content[4]["text"]
        assert content[3]["image_url"].startswith("data:image")
        assert content[5]["image_url"].startswith("data:image")

    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(
            _completion_response(json.dumps(payload, ensure_ascii=False)),
            inspect_content=inspect_content,
        ),
    )

    draft = provider.extract(_material(), [first, second])

    assert [record.page_index for record in draft.image_records] == [1, 2]
    assert [record.image_title for record in draft.image_records] == ["Rr page", "Qq page"]


def test_doubao_extracts_learning_assets_with_bbox(tmp_path: Path) -> None:
    first = tmp_path / "qq.jpg"
    second = tmp_path / "rr.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    payload = {
        "ocr_text": "Find the queen. A rabbit can hop fast.",
        "title": "Qq Rr Storybook",
        "topic": "phonics",
        "vocabulary": ["queen", "rabbit"],
        "sentences": ["Find the queen.", "A rabbit can hop fast."],
        "warnings": [],
        "confidence_summary": "high",
        "image_records": [
            {"page_index": 1, "image_title": "Qq page", "vocabulary": ["queen"], "sentences": ["Find the queen."]},
            {
                "page_index": 2,
                "image_title": "Rr page",
                "vocabulary": ["rabbit"],
                "sentences": ["A rabbit can hop fast."],
            },
        ],
        "learning_assets": [
            {
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "source_bbox": {"x": 0.05, "y": 0.14, "width": 0.43, "height": 0.35},
                "source_visual_description": "迷宫里的女王。",
                "pronunciation_text": "queen",
                "image_prompt": "参考讲义女王线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子找女王并读 queen。",
            },
            {
                "text": "A rabbit can hop fast.",
                "kind": "sentence",
                "translation": "兔子能跳得很快。",
                "source_page_index": 2,
                "source_bbox": {"x": 0.51, "y": 0.16, "width": 0.43, "height": 0.33},
                "source_visual_description": "跳跃的兔子。",
                "pronunciation_text": "A rabbit can hop fast.",
                "image_prompt": "参考讲义兔子跳跃线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子模仿兔子跳并跟读。",
            },
        ],
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(_material(), [first, second])

    assert [asset.text for asset in draft.learning_assets] == ["queen", "A rabbit can hop fast."]
    assert draft.learning_assets[0].source_bbox is not None
    assert draft.learning_assets[0].source_bbox.x == 0.05
    assert draft.learning_assets[1].source_page_index == 2


def test_doubao_learning_assets_clamps_page_index_and_bbox_overflow(tmp_path: Path) -> None:
    first = tmp_path / "qq.jpg"
    second = tmp_path / "rr.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    payload = {
        "ocr_text": "Find the queen. Find the duck.",
        "title": "Qq Storybook",
        "topic": "phonics",
        "vocabulary": ["queen", "duck"],
        "sentences": ["Find the queen.", "Find the duck."],
        "warnings": [],
        "confidence_summary": "high",
        "learning_assets": [
            {
                "text": "queen",
                "kind": "word",
                "source_page_index": 99,
                "source_bbox": {"x": 0.9, "y": 0.8, "width": 0.5, "height": 0.5},
            },
            {
                "text": "duck",
                "kind": "word",
                "source_page_index": "not-a-page",
                "source_bbox": {"x": 1.2, "y": -0.2, "width": 0.5, "height": 0.5},
            },
        ],
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(_material(), [first, second])

    queen_bbox = draft.learning_assets[0].source_bbox
    duck_bbox = draft.learning_assets[1].source_bbox
    assert queen_bbox is not None
    assert duck_bbox is not None
    assert draft.learning_assets[0].source_page_index == 2
    assert draft.learning_assets[1].source_page_index == 1
    assert queen_bbox.x == 0.9
    assert queen_bbox.width == pytest.approx(0.1)
    assert queen_bbox.x + queen_bbox.width <= 1.0
    assert queen_bbox.y == 0.8
    assert queen_bbox.height == pytest.approx(0.2)
    assert queen_bbox.y + queen_bbox.height <= 1.0
    assert duck_bbox.x == 1.0
    assert duck_bbox.width == 0.0
    assert duck_bbox.y == 0.0
    assert duck_bbox.height == 0.5


def test_doubao_empty_learning_assets_falls_back_to_material_title(tmp_path: Path) -> None:
    worksheet = tmp_path / "blank.jpg"
    worksheet.write_bytes(b"blank-image")
    payload = {
        "ocr_text": "",
        "title": "",
        "topic": "",
        "vocabulary": [],
        "sentences": [],
        "learning_assets": [],
        "warnings": [],
        "confidence_summary": "未识别到明确词句。",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(_material(), [worksheet])

    assert len(draft.learning_assets) == 1
    assert draft.learning_assets[0].text == "Animals Around Me"
    assert draft.learning_assets[0].source_page_index == 1
    assert draft.learning_assets[0].pronunciation_text == "Animals Around Me"


def test_doubao_image_records_recover_bad_page_index_and_clamp_to_uploaded_pages(tmp_path: Path) -> None:
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    material = _material().model_copy(
        update={
            "image_records": [
                MaterialImageRecord(id="image_first", page_index=1, url="https://cdn.test/first.jpg"),
                MaterialImageRecord(id="image_second", page_index=2, url="https://cdn.test/second.jpg"),
            ]
        }
    )
    payload = {
        "ocr_text": "Find the queen. Find the duck.",
        "title": "Qq Storybook",
        "topic": "phonics",
        "vocabulary": ["queen", "duck"],
        "sentences": ["Find the queen.", "Find the duck."],
        "image_records": [
            {"page_index": "page 1", "image_title": "Recovered page", "vocabulary": ["queen"]},
            {"page_index": 99, "image_title": "Clamped page", "vocabulary": ["duck"]},
        ],
        "warnings": [],
        "confidence_summary": "high",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(material, [first, second])

    assert [record.page_index for record in draft.image_records] == [1, 2]
    assert [record.image_title for record in draft.image_records] == ["Recovered page", "Clamped page"]
    assert [record.url for record in draft.image_records] == ["https://cdn.test/first.jpg", "https://cdn.test/second.jpg"]


def test_doubao_image_records_fallback_preserves_multiple_source_images(tmp_path: Path) -> None:
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    material = _material().model_copy(
        update={
            "source_images": ["https://cdn.test/first.jpg", "https://cdn.test/second.jpg"],
            "source_image_keys": ["materials/first.jpg", "materials/second.jpg"],
        }
    )
    payload = {
        "ocr_text": "Find the queen. Find the duck.",
        "title": "Qq Storybook",
        "topic": "phonics",
        "vocabulary": ["queen", "duck"],
        "sentences": ["Find the queen.", "Find the duck."],
        "image_records": [],
        "warnings": [],
        "confidence_summary": "high",
    }
    provider = DoubaoVisionOCRProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-vision-test",
        client=_client_for_response(_completion_response(json.dumps(payload, ensure_ascii=False))),
    )

    draft = provider.extract(material, [first, second])

    assert [record.page_index for record in draft.image_records] == [1, 2]
    assert [record.url for record in draft.image_records] == [
        "https://cdn.test/first.jpg",
        "https://cdn.test/second.jpg",
    ]
    assert [record.object_key for record in draft.image_records] == ["materials/first.jpg", "materials/second.jpg"]


def test_learning_assets_fallback_uses_vocabulary_and_sentences() -> None:
    assets = _fallback_learning_assets(
        _material(),
        vocabulary=["queen", "duck"],
        sentences=["Find the queen."],
    )

    assert [asset.text for asset in assets] == ["queen", "duck", "Find the queen."]
    assert all(asset.source_page_index >= 1 for asset in assets)
    assert all(asset.source_bbox is not None for asset in assets)
    assert all(asset.pronunciation_text for asset in assets)
    assert len(assets) <= 20


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
        client=_client_for_response(
            _completion_response(json.dumps(payload, ensure_ascii=False)),
            expected_content_types=["input_text", "input_text"],
        ),
    )

    pack = provider.generate_knowledge_pack(_material(), _job())
    tasks = provider.generate_review_tasks(_material(), pack)

    assert pack.topic == "动物"
    assert [item.word for item in pack.vocabulary_items] == ["cat", "dog", "bird"]
    assert [item.sentence for item in pack.sentence_patterns] == ["What is this?", "It is a cat."]
    assert {task.task_type.value for task in tasks} == {"flashcard", "listen_choice", "match_choice"}


def test_doubao_provider_disables_environment_proxy_by_default(monkeypatch) -> None:
    captured_trust_env: list[bool] = []

    class FakeClient:
        def __init__(self, *, timeout: int, trust_env: bool) -> None:
            captured_trust_env.append(trust_env)

        def post(self, *args, **kwargs) -> httpx.Response:
            return _completion_response(
                json.dumps(
                    {
                        "topic": "动物",
                        "lesson_summary": "本课练习动物词汇。",
                        "review_recommendation": "先看图说词，再跟读句子。",
                        "vocabulary_items": [],
                        "sentence_patterns": [],
                    },
                    ensure_ascii=False,
                )
            )

        def close(self) -> None:
            pass

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setattr(httpx, "Client", FakeClient)
    provider = DoubaoLanguageParsingProvider(
        api_key="ark-key",
        base_url="https://ark.test/api/v3",
        model_or_endpoint="doubao-text-test",
        trust_env=False,
    )

    provider.generate_knowledge_pack(_material(), _job())

    assert captured_trust_env == [False]
