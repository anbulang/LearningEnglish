from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.core.settings import get_settings
from app.models.contracts import SpeakingWordFeedback
from app.services.shared.speaking_assessment import (
    DashScopeSpeechAssessmentProvider,
    SpeechAssessmentError,
    SpeechAssessmentConfigurationError,
    StubSpeechAssessmentProvider,
    build_speech_assessment_audio_url,
    build_speech_assessment_provider,
)


def test_stub_speech_assessment_scores_target_words(tmp_path: Path) -> None:
    audio_path = tmp_path / "attempt.m4a"
    audio_path.write_bytes(b"fake-audio")
    provider = StubSpeechAssessmentProvider()

    result = provider.assess(
        audio_path=audio_path,
        target_text="A rabbit can hop fast.",
        prompt_text="跟读：A rabbit can hop fast.",
        attempt_id="attempt_test",
        accent="am",
    )

    assert result.provider == "stub"
    assert result.transcript == "A rabbit can hop fast."
    assert result.overall_score >= 80
    assert result.word_feedback
    assert all(isinstance(item, SpeakingWordFeedback) for item in result.word_feedback)


def test_real_speech_provider_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECH_PROVIDER", "dashscope")
    monkeypatch.setenv("SPEECH_ASSESSMENT_PROVIDER", "dashscope")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(SpeechAssessmentConfigurationError):
        build_speech_assessment_provider()

    get_settings.cache_clear()


def test_dashscope_speech_provider_transcribes_and_scores_attempt(tmp_path: Path) -> None:
    audio_path = tmp_path / "attempt.m4a"
    audio_path.write_bytes(b"fake-audio")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request.read()
        requests.append(request)
        if str(request.url) == "https://dashscope.test/api/v1/services/audio/asr/transcription":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            assert request.headers["x-dashscope-async"] == "enable"
            body = json.loads(request.content)
            assert body == {
                "model": "paraformer-v2-test",
                "input": {"file_urls": ["https://cdn.test/attempt.m4a"]},
                "parameters": {
                    "language_hints": ["zh", "en"],
                    "disfluency_removal_enabled": False,
                },
            }
            return httpx.Response(200, json={"output": {"task_id": "task_test", "task_status": "PENDING"}})
        if str(request.url) == "https://dashscope.test/api/v1/tasks/task_test":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "results": [
                            {
                                "file_url": "https://cdn.test/attempt.m4a",
                                "subtask_status": "SUCCEEDED",
                                "transcription_url": "https://result.test/transcription.json",
                            }
                        ],
                    }
                },
            )
        if str(request.url) == "https://result.test/transcription.json":
            return httpx.Response(
                200,
                json={
                    "transcripts": [
                        {
                            "text": "A rabbit can hop fast.",
                            "sentences": [
                                {
                                    "text": "A rabbit can hop fast.",
                                    "words": [
                                        {"text": "A"},
                                        {"text": "rabbit"},
                                        {"text": "can"},
                                        {"text": "hop"},
                                        {"text": "fast"},
                                    ],
                                }
                            ],
                        }
                    ]
                },
            )
        if str(request.url) == "https://dashscope.test/compatible-mode/v1/chat/completions":
            body = json.loads(request.content)
            assert body["model"] == "qwen-plus-test"
            assert body["response_format"] == {"type": "json_object"}
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"overall_score":91,"pronunciation_score":0.9,'
                                    '"accuracy_score":92,"fluency_score":88,'
                                    '"completeness_score":95,"feedback":"读得清楚。",'
                                    '"word_feedback":[{"word":"rabbit","score":92,'
                                    '"status":"good","tip":"rabbit 很清楚。"}],'
                                    '"suggestions":["保持慢速完整跟读。"]}'
                                )
                            }
                        }
                    ]
                },
            )
        return httpx.Response(404, text=str(request.url))

    provider = DashScopeSpeechAssessmentProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        compatible_base_url="https://dashscope.test/compatible-mode/v1",
        asr_model="paraformer-v2-test",
        scoring_model="qwen-plus-test",
        timeout_seconds=30,
        poll_interval_seconds=0,
        max_poll_seconds=30,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )

    result = provider.assess(
        audio_path=audio_path,
        audio_url="https://cdn.test/attempt.m4a",
        target_text="A rabbit can hop fast.",
        prompt_text="跟读：A rabbit can hop fast.",
        attempt_id="attempt_test",
        accent="am",
    )

    assert result.provider == "dashscope"
    assert result.transcript == "A rabbit can hop fast."
    assert result.overall_score == 91
    assert result.pronunciation_score == 0.9
    assert result.word_feedback[0].word == "rabbit"
    assert result.suggestions == ["保持慢速完整跟读。"]
    assert [request.url.path for request in requests] == [
        "/api/v1/services/audio/asr/transcription",
        "/api/v1/tasks/task_test",
        "/transcription.json",
        "/compatible-mode/v1/chat/completions",
    ]


@pytest.mark.parametrize(
    "audio_url",
    [
        "",
        "http://127.0.0.1/uploads/attempt.m4a",
        "http://192.168.2.15/uploads/attempt.m4a",
        "http://testserver/uploads/attempt.m4a",
    ],
)
def test_dashscope_speech_provider_requires_public_audio_url(tmp_path: Path, audio_url: str) -> None:
    audio_path = tmp_path / "attempt.m4a"
    audio_path.write_bytes(b"fake-audio")
    provider = DashScopeSpeechAssessmentProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        compatible_base_url="https://dashscope.test/compatible-mode/v1",
        asr_model="paraformer-v2-test",
        scoring_model="qwen-plus-test",
        timeout_seconds=30,
        poll_interval_seconds=0,
        max_poll_seconds=30,
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )

    with pytest.raises(SpeechAssessmentError, match="public audio URL"):
        provider.assess(
            audio_path=audio_path,
            audio_url=audio_url,
            target_text="A rabbit can hop fast.",
            prompt_text="跟读：A rabbit can hop fast.",
            attempt_id="attempt_test",
            accent="am",
        )


def test_build_speech_assessment_audio_url_uses_public_upload_base_url() -> None:
    url = build_speech_assessment_audio_url(
        stored_audio_url="http://192.168.2.15:8000/uploads/speaking_attempt/attempt_test/input.m4a",
        object_key="speaking_attempt/attempt_test/input.m4a",
        public_base_url="https://public.example.com/learning-english",
    )

    assert url == "https://public.example.com/learning-english/uploads/speaking_attempt/attempt_test/input.m4a"


def test_build_speech_assessment_audio_url_accepts_uploads_base_url() -> None:
    url = build_speech_assessment_audio_url(
        stored_audio_url="http://127.0.0.1:8000/uploads/speaking_attempt/attempt_test/input.m4a",
        object_key="speaking_attempt/attempt_test/input.m4a",
        public_base_url="https://cdn.example.com/uploads/",
    )

    assert url == "https://cdn.example.com/uploads/speaking_attempt/attempt_test/input.m4a"


def test_build_speech_assessment_audio_url_keeps_stored_url_without_public_base() -> None:
    stored_url = "http://127.0.0.1:8000/uploads/speaking_attempt/attempt_test/input.m4a"

    assert (
        build_speech_assessment_audio_url(
            stored_audio_url=stored_url,
            object_key="speaking_attempt/attempt_test/input.m4a",
            public_base_url="",
        )
        == stored_url
    )
