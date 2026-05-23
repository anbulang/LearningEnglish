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
from app.services.learning_asset_media import (
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
        "MEDIA_TTS_MODEL",
        "MEDIA_TTS_US_VOICE",
        "MEDIA_TTS_UK_VOICE",
        "MEDIA_REQUEST_TIMEOUT_SECONDS",
        "MEDIA_HTTP_TRUST_ENV",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
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


def test_media_provider_bundle_close_closes_unique_providers_once() -> None:
    shared_provider = CloseableProvider()
    bundle = MediaProviderBundle(image_provider=shared_provider, tts_provider=shared_provider, mode="mock")

    bundle.close()

    assert shared_provider.close_count == 1
