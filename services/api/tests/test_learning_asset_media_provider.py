from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Callable

import httpx
import pytest

from app.core.settings import get_settings
from app.models.contracts import LearningAsset
from app.services import learning_asset_media as media_module
from app.services.learning_asset_media import (
    DashScopeImageGenerationProvider,
    DashScopeTTSProvider,
    MediaProviderBundle,
    MediaProviderConfigurationError,
    MediaProviderError,
    OpenAIImageGenerationProvider,
    OpenAITTSProvider,
    build_media_provider_bundle,
)


class FakeTransport(httpx.BaseTransport):
    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        return self.handler(request)


class CloseableProvider:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


def _clear_media_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_ENV",
        "MEDIA_PROVIDER",
        "MEDIA_IMAGE_PROVIDER",
        "MEDIA_TTS_PROVIDER",
        "MEDIA_IMAGE_MODEL",
        "MEDIA_IMAGE_EDIT_MODEL",
        "MEDIA_TTS_MODEL",
        "MEDIA_TTS_US_VOICE",
        "MEDIA_TTS_UK_VOICE",
        "MEDIA_REQUEST_TIMEOUT_SECONDS",
        "MEDIA_HTTP_TRUST_ENV",
        "MEDIA_PROVIDER_POLL_INTERVAL_SECONDS",
        "MEDIA_PROVIDER_MAX_POLL_SECONDS",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_real_openai_bundle_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")

    with pytest.raises(MediaProviderConfigurationError):
        build_media_provider_bundle(public_base_url="http://testserver")


def test_testing_environment_uses_mock_bundle_when_media_provider_not_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "mock"
    assert bundle.image_provider is bundle.tts_provider


@pytest.mark.parametrize("media_provider", ["", "   "])
def test_testing_environment_uses_mock_bundle_when_media_provider_is_blank(
    monkeypatch: pytest.MonkeyPatch,
    media_provider: str,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", media_provider)

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "mock"
    assert bundle.image_provider is bundle.tts_provider


def test_testing_environment_explicit_real_bundle_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")

    with pytest.raises(MediaProviderConfigurationError, match="OPENAI_API_KEY"):
        build_media_provider_bundle(public_base_url="http://testserver")


def test_testing_environment_explicit_real_with_whitespace_requires_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", " real ")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")

    with pytest.raises(MediaProviderConfigurationError, match="OPENAI_API_KEY"):
        build_media_provider_bundle(public_base_url="http://testserver")


def test_media_settings_include_dashscope_provider_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.test/api/v1")
    monkeypatch.setenv("MEDIA_IMAGE_EDIT_MODEL", "wanx2.1-imageedit-test")
    monkeypatch.setenv("MEDIA_PROVIDER_POLL_INTERVAL_SECONDS", "3")
    monkeypatch.setenv("MEDIA_PROVIDER_MAX_POLL_SECONDS", "33")

    settings = get_settings()

    assert settings.dashscope_base_url == "https://dashscope.test/api/v1"
    assert settings.media_image_edit_model == "wanx2.1-imageedit-test"
    assert settings.media_provider_poll_interval_seconds == 3
    assert settings.media_provider_max_poll_seconds == 33


def test_bundle_with_openai_image_and_dashscope_tts_builds_real_mixed_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", " real ")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", " OpenAI ")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", " DashScope ")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.test/v1/")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.test/api/v1/")
    monkeypatch.setenv("MEDIA_IMAGE_MODEL", "gpt-image-test")
    monkeypatch.setenv("MEDIA_TTS_MODEL", "cosyvoice-test")
    monkeypatch.setenv("MEDIA_TTS_US_VOICE", "dashscope-us")
    monkeypatch.setenv("MEDIA_TTS_UK_VOICE", "dashscope-uk")

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "real"
    assert isinstance(bundle.image_provider, OpenAIImageGenerationProvider)
    assert isinstance(bundle.tts_provider, DashScopeTTSProvider)
    assert bundle.image_provider.api_key == "sk-openai"
    assert bundle.image_provider.base_url == "https://api.openai.test/v1"
    assert bundle.image_provider.model == "gpt-image-test"
    assert bundle.tts_provider.api_key == "sk-dashscope"
    assert bundle.tts_provider.base_url == "https://dashscope.test/api/v1"
    assert bundle.tts_provider.model == "cosyvoice-test"
    assert bundle.tts_provider.us_voice == "dashscope-us"
    assert bundle.tts_provider.uk_voice == "dashscope-uk"


def test_bundle_with_dashscope_image_and_openai_tts_builds_real_mixed_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "dashscope")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.test/v1/")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.test/api/v1/")
    monkeypatch.setenv("MEDIA_IMAGE_MODEL", "wan2.6-image-test")
    monkeypatch.setenv("MEDIA_IMAGE_EDIT_MODEL", "wanx2.1-imageedit-test")
    monkeypatch.setenv("MEDIA_TTS_MODEL", "gpt-tts-test")
    monkeypatch.setenv("MEDIA_TTS_US_VOICE", "openai-us")
    monkeypatch.setenv("MEDIA_TTS_UK_VOICE", "openai-uk")
    monkeypatch.setenv("MEDIA_PROVIDER_POLL_INTERVAL_SECONDS", "7")
    monkeypatch.setenv("MEDIA_PROVIDER_MAX_POLL_SECONDS", "77")

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "real"
    assert isinstance(bundle.image_provider, DashScopeImageGenerationProvider)
    assert isinstance(bundle.tts_provider, OpenAITTSProvider)
    assert bundle.image_provider.api_key == "sk-dashscope"
    assert bundle.image_provider.base_url == "https://dashscope.test/api/v1"
    assert bundle.image_provider.model == "wan2.6-image-test"
    assert bundle.image_provider.edit_model == "wanx2.1-imageedit-test"
    assert bundle.image_provider.poll_interval_seconds == 7
    assert bundle.image_provider.max_poll_seconds == 77
    assert bundle.tts_provider.api_key == "sk-openai"
    assert bundle.tts_provider.base_url == "https://api.openai.test/v1"
    assert bundle.tts_provider.model == "gpt-tts-test"
    assert bundle.tts_provider.us_voice == "openai-us"
    assert bundle.tts_provider.uk_voice == "openai-uk"


def test_bundle_closes_image_provider_when_tts_provider_build_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    image_provider = CloseableProvider()

    def fail_tts_provider(settings: object) -> object:
        del settings
        raise MediaProviderConfigurationError("tts failed")

    monkeypatch.setattr(media_module, "_build_image_provider", lambda settings: image_provider)
    monkeypatch.setattr(media_module, "_build_tts_provider", fail_tts_provider)

    with pytest.raises(MediaProviderConfigurationError, match="tts failed"):
        build_media_provider_bundle(public_base_url="http://testserver")

    assert image_provider.close_count == 1


@pytest.mark.parametrize(
    ("image_provider", "tts_provider"),
    [
        ("dashscope", "openai"),
        ("openai", "dashscope"),
    ],
)
def test_bundle_with_dashscope_provider_requires_dashscope_api_key_without_leaking_configured_keys(
    monkeypatch: pytest.MonkeyPatch,
    image_provider: str,
    tts_provider: str,
) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", image_provider)
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", tts_provider)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-secret")

    with pytest.raises(MediaProviderConfigurationError, match="DASHSCOPE_API_KEY") as exc_info:
        build_media_provider_bundle(public_base_url="http://testserver")

    assert "sk-openai-secret" not in str(exc_info.value)


def test_dashscope_image_generation_without_reference_creates_task_polls_and_downloads_image() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            assert request.headers["x-dashscope-async"] == "enable"
            body = json.loads(request.content)
            assert body["model"] == "wan2.6-image"
            assert body["input"]["messages"] == [
                {"role": "user", "content": [{"text": "Draw a colorful queen flashcard."}]}
            ]
            assert body["parameters"]["prompt_extend"] is True
            assert body["parameters"]["watermark"] is False
            assert body["parameters"]["max_images"] == 1
            assert body["parameters"]["size"] == "1280*1280"
            assert body["parameters"]["enable_interleave"] is True
            assert "n" not in body["parameters"]
            return httpx.Response(200, json={"output": {"task_id": "task_image_1"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_image_1":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "results": [{"url": "https://dashscope-cdn.test/task_image_1.png"}],
                    }
                },
            )
        if request.url == "https://dashscope-cdn.test/task_image_1.png":
            return httpx.Response(200, content=b"dashscope-image", headers={"content-type": "image/png"})
        raise AssertionError(f"unexpected request: {request.url}")

    transport = FakeTransport(handler)
    client = httpx.Client(transport=transport)
    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=client,
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Draw a colorful queen flashcard.",
        reference_image_path=None,
    )

    assert [request.method for request in transport.requests] == ["POST", "GET", "GET"]
    assert media.payload == b"dashscope-image"
    assert media.content_type == "image/png"
    assert media.extension == ".png"


def test_dashscope_image_generation_reads_official_choices_image_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_image_choices"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_image_choices":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [
                            {
                                "message": {
                                    "content": [
                                        {"image": "https://dashscope-cdn.test/task_image_choices.png"}
                                    ]
                                }
                            }
                        ],
                    }
                },
            )
        if request.url == "https://dashscope-cdn.test/task_image_choices.png":
            return httpx.Response(200, content=b"dashscope-choices-image", headers={"content-type": "image/png"})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Draw a queen.",
        reference_image_path=None,
    )

    assert media.payload == b"dashscope-choices-image"
    assert media.content_type == "image/png"
    assert media.extension == ".png"


def test_dashscope_image_generation_sanitizes_malformed_download_url_errors() -> None:
    malformed_url = "http://dashscope-cdn.test:abc/image.png"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_bad_url"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_bad_url":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [{"message": {"content": [{"image": malformed_url}]}}],
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope image download failed") as exc_info:
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )

    assert malformed_url not in str(exc_info.value)


def test_dashscope_image_generation_missing_image_url_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_missing_url"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_missing_url":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [{"message": {"content": [{"text": "no image here"}]}}],
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope image task response missing image URL"):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_dashscope_image_generation_download_http_error_raises_provider_error() -> None:
    image_url = "https://dashscope-cdn.test/failed-download.png"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_download_failed"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_download_failed":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [{"message": {"content": [{"image": image_url}]}}],
                    }
                },
            )
        if request.url == image_url:
            return httpx.Response(502, text="temporary object store failure")
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope image download failed") as exc_info:
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )

    assert image_url not in str(exc_info.value)


def test_dashscope_image_generation_with_reference_sends_data_url_and_interleave(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image2image/image-synthesis":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            assert request.headers["x-dashscope-async"] == "enable"
            body = json.loads(request.content)
            assert body["model"] == "wanx2.1-imageedit"
            assert body["input"]["function"] == "description_edit"
            prompt_text = body["input"]["prompt"]
            assert "Draw from the reference." in prompt_text
            assert "参考讲义图片" in prompt_text
            assert "彩色教学配图" in prompt_text or "彩色教学图片" in prompt_text
            assert body["input"]["base_image_url"] == "data:image/png;base64,cmVmZXJlbmNlLWJ5dGVz"
            assert body["parameters"]["n"] == 1
            return httpx.Response(200, json={"output": {"task_id": "task_image_2"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_image_2":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "results": [{"url": "https://dashscope-cdn.test/task_image_2.png"}],
                    }
                },
            )
        if request.url == "https://dashscope-cdn.test/task_image_2.png":
            return httpx.Response(200, content=b"dashscope-reference-image", headers={"content-type": "image/png"})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Draw from the reference.",
        reference_image_path=reference_path,
    )

    assert media.payload == b"dashscope-reference-image"
    assert media.content_type == "image/png"
    assert media.extension == ".png"


@pytest.mark.parametrize("task_status", ["FAILED", "CANCELED", "UNKNOWN"])
def test_dashscope_image_generation_terminal_task_status_raises_provider_error(task_status: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_terminal"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_terminal":
            return httpx.Response(200, json={"output": {"task_status": task_status, "message": "not recoverable"}})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope image task failed"):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_dashscope_image_generation_task_failure_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_failed"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_failed":
            return httpx.Response(200, json={"output": {"task_status": "FAILED", "message": "policy rejected"}})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope image task failed"):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_dashscope_image_generation_polling_timeout_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            return httpx.Response(200, json={"output": {"task_id": "task_running"}})
        if request.url == "https://dashscope.test/api/v1/tasks/task_running":
            return httpx.Response(200, json={"output": {"task_status": "RUNNING"}})
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        max_poll_seconds=0,
        client=httpx.Client(transport=FakeTransport(handler)),
        sleep=lambda seconds: None,
    )

    with pytest.raises(MediaProviderError, match="DashScope image task polling timed out"):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_openai_image_generation_without_reference_calls_generations_and_decodes_payload() -> None:
    image_payload = b"image-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.test/v1/images/generations"
        assert request.headers["authorization"] == "Bearer sk-test"
        body = json.loads(request.content)
        assert body == {
            "model": "gpt-image-test",
            "prompt": "Draw a queen.",
            "size": "1024x1024",
        }
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(image_payload).decode()}]})

    transport = FakeTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-image-test",
        client=client,
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Draw a queen.",
        reference_image_path=None,
    )

    assert len(transport.requests) == 1
    assert media.payload == image_payload
    assert media.content_type == "image/png"
    assert media.extension == ".png"


def test_openai_image_generation_with_reference_calls_edits(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-image")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.test/v1/images/edits"
        assert request.headers["authorization"] == "Bearer sk-test"
        assert b'name="model"' in request.content
        assert b"gpt-image-test" in request.content
        assert b'name="prompt"' in request.content
        assert b"Color the reference image." in request.content
        assert b'name="size"' in request.content
        assert b"1024x1024" in request.content
        assert b'name="image[]"' in request.content
        assert b"reference-image" in request.content
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(b"edited").decode()}]})

    transport = FakeTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-image-test",
        client=client,
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Color the reference image.",
        reference_image_path=reference_path,
    )

    assert len(transport.requests) == 1
    assert media.payload == b"edited"
    assert media.content_type == "image/png"
    assert media.extension == ".png"


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (httpx.Response(500, text="server error"), "OpenAI image generation failed"),
        (httpx.Response(200, content=b"not-json"), "OpenAI image generation failed"),
        (httpx.Response(200, json={"data": [{}]}), "OpenAI image response missing data[0].b64_json"),
        (httpx.Response(200, json={"data": [{"b64_json": "not base64"}]}), "OpenAI image response has invalid base64"),
    ],
)
def test_openai_image_generation_wraps_provider_failures(response: httpx.Response, match: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    client = httpx.Client(transport=FakeTransport(handler))
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-image-test",
        client=client,
    )

    with pytest.raises(MediaProviderError, match=re.escape(match)):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_openai_image_generation_wraps_network_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = httpx.Client(transport=FakeTransport(handler))
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-image-test",
        client=client,
    )

    with pytest.raises(MediaProviderError, match="OpenAI image generation failed"):
        provider.generate(
            asset=LearningAsset(id="asset_1", text="queen", kind="word"),
            prompt="Draw a queen.",
            reference_image_path=None,
        )


def test_openai_tts_synthesize_uk_uses_speech_endpoint_and_cedar_voice() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.test/v1/audio/speech"
        assert request.headers["authorization"] == "Bearer sk-test"
        body = json.loads(request.content)
        assert body["model"] == "gpt-4o-mini-tts"
        assert body["voice"] == "cedar"
        assert body["input"] == "queen"
        assert "British English pronunciation" in body["instructions"]
        return httpx.Response(200, content=b"mp3-bytes")

    transport = FakeTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAITTSProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-4o-mini-tts",
        us_voice="coral",
        uk_voice="cedar",
        client=client,
    )

    media = provider.synthesize(text="queen", accent="uk")

    assert len(transport.requests) == 1
    assert media.payload == b"mp3-bytes"
    assert media.content_type == "audio/mpeg"
    assert media.extension == ".mp3"


def test_openai_tts_synthesize_rejects_unknown_accent() -> None:
    provider = OpenAITTSProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-4o-mini-tts",
        us_voice="coral",
        uk_voice="cedar",
        client=httpx.Client(transport=FakeTransport(lambda request: httpx.Response(200, content=b"unused"))),
    )

    with pytest.raises(MediaProviderError, match="Unsupported TTS accent"):
        provider.synthesize(text="queen", accent="au")


def test_openai_tts_synthesize_wraps_http_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    provider = OpenAITTSProvider(
        api_key="sk-test",
        base_url="https://api.openai.test/v1",
        model="gpt-4o-mini-tts",
        us_voice="coral",
        uk_voice="cedar",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="OpenAI TTS generation failed"):
        provider.synthesize(text="queen", accent="uk")


def test_dashscope_tts_synthesize_uses_cosyvoice_and_downloads_audio() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            body = json.loads(request.content)
            assert body == {
                "model": "cosyvoice-v3-flash",
                "input": {
                    "text": "A rabbit can hop fast.",
                    "voice": "uk-voice",
                    "format": "mp3",
                    "language_hints": ["en"],
                },
            }
            return httpx.Response(
                200,
                json={"output": {"finish_reason": "stop", "audio": {"url": "https://result.test/audio.mp3"}}},
            )
        if str(request.url) == "https://result.test/audio.mp3":
            return httpx.Response(200, content=b"mp3-bytes")
        return httpx.Response(404, text=str(request.url))

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    media = provider.synthesize("A rabbit can hop fast.", "uk")

    assert media.payload == b"mp3-bytes"
    assert media.content_type == "audio/mpeg"
    assert media.extension == ".mp3"


def test_dashscope_tts_synthesize_rejects_unknown_accent() -> None:
    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(lambda request: httpx.Response(200, content=b"unused"))),
    )

    with pytest.raises(MediaProviderError, match="Unsupported TTS accent"):
        provider.synthesize("queen", "au")


def test_dashscope_tts_synthesize_requires_voice() -> None:
    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(lambda request: httpx.Response(200, content=b"unused"))),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS voice is not configured"):
        provider.synthesize("queen", "us")


def test_dashscope_tts_synthesize_fails_without_audio_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": {"finish_reason": "stop", "audio": {}}})

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS response missing output.audio.url"):
        provider.synthesize("queen", "us")


def test_dashscope_tts_synthesize_wraps_malformed_generation_url() -> None:
    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test:abc/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(
            transport=FakeTransport(lambda request: pytest.fail(f"unexpected request: {request.url}"))
        ),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS generation failed"):
        provider.synthesize("queen", "us")


@pytest.mark.parametrize("status_code", [500, 502])
def test_dashscope_tts_synthesize_wraps_generation_http_status_failures(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer"
        return httpx.Response(status_code, text="dashscope tts generation failure")

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS generation failed"):
        provider.synthesize("queen", "us")


def test_dashscope_tts_synthesize_wraps_generation_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer"
        return httpx.Response(200, content=b"not-json")

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS generation failed"):
        provider.synthesize("queen", "us")


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"output": None},
        {"output": []},
        {"output": {"audio": None}},
        {"output": {"audio": []}},
        {"output": {"audio": "https://result.test/audio.mp3"}},
    ],
)
def test_dashscope_tts_synthesize_fails_when_audio_url_containers_are_not_objects(payload: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS response missing output.audio.url"):
        provider.synthesize("queen", "us")


def test_dashscope_tts_synthesize_wraps_audio_download_http_error() -> None:
    audio_url = "https://result.test/failed.mp3"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer":
            return httpx.Response(
                200,
                json={"output": {"finish_reason": "stop", "audio": {"url": audio_url}}},
            )
        if str(request.url) == audio_url:
            return httpx.Response(503, text="temporary audio store failure")
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS audio download failed") as exc_info:
        provider.synthesize("queen", "us")

    assert audio_url not in str(exc_info.value)


def test_dashscope_tts_synthesize_wraps_malformed_audio_url() -> None:
    malformed_url = "http://result.test:abc/audio.mp3"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer":
            return httpx.Response(
                200,
                json={"output": {"finish_reason": "stop", "audio": {"url": malformed_url}}},
            )
        raise AssertionError(f"unexpected request: {request.url}")

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS audio download failed") as exc_info:
        provider.synthesize("queen", "us")

    assert malformed_url not in str(exc_info.value)


def test_media_provider_bundle_close_closes_unique_providers_once() -> None:
    shared_provider = CloseableProvider()
    bundle = MediaProviderBundle(image_provider=shared_provider, tts_provider=shared_provider, mode="mock")

    bundle.close()

    assert shared_provider.close_count == 1
