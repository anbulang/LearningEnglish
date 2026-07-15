from __future__ import annotations

import pytest

from app.core.readiness import readiness_report
from app.core.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _report(monkeypatch, **env) -> dict:
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return readiness_report(get_settings())


def _component(report: dict, name: str) -> dict:
    return next(c for c in report["components"] if c["component"] == name)


def test_stub_and_mock_providers_are_ready(monkeypatch) -> None:
    # conftest already pins AI=stub, MEDIA=mock, SPEECH=stub, APP_ENV=testing
    report = _report(monkeypatch)
    assert report["ready"] is True
    assert all(c["ready"] for c in report["components"])


def test_qwen_without_dashscope_key_is_not_ready(monkeypatch) -> None:
    report = _report(monkeypatch, AI_PROVIDER="qwen", DASHSCOPE_API_KEY="")
    ai = _component(report, "ai")
    assert ai["ready"] is False
    assert "DASHSCOPE_API_KEY" in ai["missing"]
    assert report["ready"] is False


def test_qwen_with_dashscope_key_is_ready(monkeypatch) -> None:
    report = _report(monkeypatch, AI_PROVIDER="qwen", DASHSCOPE_API_KEY="sk-test")
    assert _component(report, "ai")["ready"] is True


def test_doubao_without_ark_key_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        AI_PROVIDER="doubao",
        ARK_API_KEY="",
        DOUBAO_VISION_MODEL_OR_ENDPOINT="ep-v",
        DOUBAO_TEXT_MODEL_OR_ENDPOINT="ep-t",
    )
    ai = _component(report, "ai")
    assert ai["ready"] is False
    assert "ARK_API_KEY" in ai["missing"]


def test_real_media_dashscope_without_key_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        MEDIA_PROVIDER="real",
        MEDIA_IMAGE_PROVIDER="dashscope",
        MEDIA_TTS_PROVIDER="dashscope",
        DASHSCOPE_API_KEY="",
    )
    media = _component(report, "media")
    assert media["ready"] is False
    assert "DASHSCOPE_API_KEY" in media["missing"]


def test_speech_dashscope_without_key_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        SPEECH_PROVIDER="dashscope",
        SPEECH_ASSESSMENT_PROVIDER="dashscope",
        DASHSCOPE_API_KEY="",
    )
    speech = _component(report, "speech")
    assert speech["ready"] is False
    assert "DASHSCOPE_API_KEY" in speech["missing"]


def test_production_with_localhost_public_base_url_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        APP_ENV="production",
        PUBLIC_BASE_URL="http://localhost:8000",
        # keep providers ready so only the URL guard trips
        AI_PROVIDER="stub",
        MEDIA_PROVIDER="mock",
        SPEECH_PROVIDER="stub",
        SPEECH_ASSESSMENT_PROVIDER="stub",
    )
    url = _component(report, "public_base_url")
    assert url["ready"] is False
    assert report["ready"] is False


def test_production_with_private_ip_public_base_url_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        APP_ENV="production",
        PUBLIC_BASE_URL="http://192.168.1.20:8000",
        AI_PROVIDER="stub",
        MEDIA_PROVIDER="mock",
        SPEECH_PROVIDER="stub",
        SPEECH_ASSESSMENT_PROVIDER="stub",
    )
    assert _component(report, "public_base_url")["ready"] is False


def test_production_with_public_domain_is_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        APP_ENV="production",
        PUBLIC_BASE_URL="https://api.example.com",
        AI_PROVIDER="qwen",
        DASHSCOPE_API_KEY="sk-test",
        MEDIA_PROVIDER="real",
        MEDIA_IMAGE_PROVIDER="dashscope",
        MEDIA_TTS_PROVIDER="dashscope",
        SPEECH_PROVIDER="dashscope",
        SPEECH_ASSESSMENT_PROVIDER="dashscope",
        # production also requires a non-stub identity provider
        IDENTITY_PROVIDER="pilot",
        PILOT_ALLOWLIST_JSON='[{"code":"fam-001","display_name":"A","phone":"13800000001"}]',
    )
    assert report["ready"] is True


def test_localhost_outside_production_is_ready(monkeypatch) -> None:
    report = _report(monkeypatch, APP_ENV="development", PUBLIC_BASE_URL="http://localhost:8000")
    assert _component(report, "public_base_url")["ready"] is True


def test_readyz_endpoint_returns_200_when_ready(api_client) -> None:
    response = api_client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert {c["component"] for c in body["components"]} == {"ai", "media", "speech", "identity", "public_base_url"}
