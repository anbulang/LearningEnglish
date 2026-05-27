from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.settings import get_settings
from app.models.contracts import LearningAsset, MediaGenerationStatus


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_learning_asset_includes_media_error_fields() -> None:
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        generated_image_status=MediaGenerationStatus.failed,
        generated_image_error="图片生成失败：provider timeout",
        tts_us_status=MediaGenerationStatus.failed,
        tts_us_error="美式发音生成失败：provider timeout",
        tts_uk_status=MediaGenerationStatus.ready,
        tts_uk_url="http://testserver/uploads/generated/media/material_1/asset_queen/tts-uk.mp3",
    )

    payload = asset.model_dump(mode="json")

    assert payload["generated_image_error"] == "图片生成失败：provider timeout"
    assert payload["tts_us_error"] == "美式发音生成失败：provider timeout"
    assert payload["tts_uk_error"] == ""
    assert LearningAsset(**payload).tts_uk_url.endswith("/tts-uk.mp3")


def test_media_provider_settings_default_to_dashscope_real_values(monkeypatch) -> None:
    monkeypatch.delenv("MEDIA_PROVIDER", raising=False)
    monkeypatch.delenv("MEDIA_IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("MEDIA_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("MEDIA_IMAGE_MODEL", raising=False)
    monkeypatch.delenv("MEDIA_IMAGE_EDIT_MODEL", raising=False)
    monkeypatch.delenv("MEDIA_TTS_MODEL", raising=False)
    monkeypatch.delenv("MEDIA_TTS_US_VOICE", raising=False)
    monkeypatch.delenv("MEDIA_TTS_UK_VOICE", raising=False)
    monkeypatch.delenv("MEDIA_REQUEST_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("MEDIA_HTTP_TRUST_ENV", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    settings = get_settings()

    assert settings.media_provider == "real"
    assert settings.media_image_provider == "dashscope"
    assert settings.media_tts_provider == "dashscope"
    assert settings.media_image_model == "wan2.6-image"
    assert settings.media_image_edit_model == "wanx2.1-imageedit"
    assert settings.media_tts_model == "cosyvoice-v3-flash"
    assert settings.media_tts_us_voice == "longanyang"
    assert settings.media_tts_uk_voice == "longanhuan"
    assert settings.media_request_timeout_seconds == 180
    assert settings.media_http_trust_env is False
    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_media_provider_settings_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_MODEL", "gpt-image-1.5")
    monkeypatch.setenv("MEDIA_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("MEDIA_TTS_US_VOICE", "marin")
    monkeypatch.setenv("MEDIA_TTS_UK_VOICE", "fable")
    monkeypatch.setenv("MEDIA_REQUEST_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("MEDIA_HTTP_TRUST_ENV", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.test/v1")

    settings = get_settings()

    assert settings.media_provider == "real"
    assert settings.media_image_model == "gpt-image-1.5"
    assert settings.media_tts_model == "gpt-4o-mini-tts"
    assert settings.media_tts_us_voice == "marin"
    assert settings.media_tts_uk_voice == "fable"
    assert settings.media_request_timeout_seconds == 90
    assert settings.media_http_trust_env is True
    assert settings.openai_api_key == "sk-test"
    assert settings.openai_base_url == "https://api.openai.test/v1"
