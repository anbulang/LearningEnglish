from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_auth_service
from app.core.readiness import readiness_report
from app.core.settings import PilotAllowlistEntry, get_settings
from app.services.parent.auth import PilotWhitelistIdentityProvider

ALLOWLIST_JSON = (
    '[{"code":"fam-001","display_name":"林家","phone":"13800000001"},'
    '{"code":"fam-002","display_name":"赵家","phone":"13800000002"}]'
)


@pytest.fixture(autouse=True)
def clear_caches():
    get_settings.cache_clear()
    get_auth_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_auth_service.cache_clear()


def _component(report: dict, name: str) -> dict:
    return next(c for c in report["components"] if c["component"] == name)


def _report(monkeypatch, **env) -> dict:
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return readiness_report(get_settings())


# ── Readiness identity guard ──────────────────────────────────────


def test_production_with_dev_identity_is_not_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        APP_ENV="production",
        IDENTITY_PROVIDER="dev",
        PUBLIC_BASE_URL="https://api.example.com",
        AI_PROVIDER="stub",
        MEDIA_PROVIDER="mock",
        SPEECH_PROVIDER="stub",
        SPEECH_ASSESSMENT_PROVIDER="stub",
    )
    assert _component(report, "identity")["ready"] is False
    assert report["ready"] is False


def test_production_with_pilot_and_allowlist_is_ready(monkeypatch) -> None:
    report = _report(
        monkeypatch,
        APP_ENV="production",
        IDENTITY_PROVIDER="pilot",
        PILOT_ALLOWLIST_JSON=ALLOWLIST_JSON,
        PUBLIC_BASE_URL="https://api.example.com",
        AI_PROVIDER="stub",
        MEDIA_PROVIDER="mock",
        SPEECH_PROVIDER="stub",
        SPEECH_ASSESSMENT_PROVIDER="stub",
    )
    assert _component(report, "identity")["ready"] is True
    assert report["ready"] is True


def test_pilot_without_allowlist_is_not_ready(monkeypatch) -> None:
    report = _report(monkeypatch, IDENTITY_PROVIDER="pilot", PILOT_ALLOWLIST_JSON=None)
    assert _component(report, "identity")["ready"] is False


def test_dev_identity_outside_production_is_ready(monkeypatch) -> None:
    report = _report(monkeypatch, APP_ENV="testing", IDENTITY_PROVIDER="dev")
    assert _component(report, "identity")["ready"] is True


# ── Pilot provider unit ───────────────────────────────────────────


def test_pilot_provider_maps_allowlisted_code_to_stable_identity() -> None:
    allow = (PilotAllowlistEntry(code="fam-001", display_name="林家", phone="13800000001"),)
    provider = PilotWhitelistIdentityProvider(allow)
    first = provider.exchange("fam-001")
    second = provider.exchange(" fam-001 ")  # trimmed
    assert first.union_id == "pilot_fam-001" == second.union_id
    assert first.phone_number == "13800000001"
    assert first.phone_pre_verified is True
    assert first.display_name == "林家"


def test_pilot_provider_rejects_unknown_code() -> None:
    provider = PilotWhitelistIdentityProvider(
        (PilotAllowlistEntry(code="fam-001", display_name="", phone=""),)
    )
    with pytest.raises(ValueError):
        provider.exchange("stranger")


# ── End-to-end via the API in pilot mode ──────────────────────────


@pytest.fixture
def pilot_client(monkeypatch):
    # Pilot identity active; keep APP_ENV=testing so the production boot guard
    # does not engage (it would require a public domain + real provider keys).
    monkeypatch.setenv("IDENTITY_PROVIDER", "pilot")
    monkeypatch.setenv("PILOT_ALLOWLIST_JSON", ALLOWLIST_JSON)
    get_settings.cache_clear()
    get_auth_service.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        yield client


def _login(client: TestClient, code: str):
    return client.post("/v1/auth/wechat/login", json={"auth_code": code})


def test_pilot_login_skips_binding(pilot_client) -> None:
    response = _login(pilot_client, "fam-001")
    assert response.status_code == 200
    payload = response.json()
    # Pre-verified allowlist phone → straight to authenticated, no OTP bind step.
    assert payload["status"] == "authenticated"
    assert payload["tokens"]["access_token"]
    assert payload["parent_account"]["phone_number"] == "13800000001"


def test_pilot_login_rejects_unknown_code(pilot_client) -> None:
    response = _login(pilot_client, "stranger")
    assert response.status_code == 403


def test_pilot_families_are_isolated(pilot_client) -> None:
    # Family 1 logs in and creates a child.
    r1 = _login(pilot_client, "fam-001")
    p1 = r1.json()
    assert p1["status"] == "authenticated"
    h1 = {"Authorization": f"Bearer {p1['tokens']['access_token']}"}
    created = pilot_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "更喜欢看图认词",
        },
        headers=h1,
    )
    assert created.status_code == 201

    # Family 2 is a different account that cannot see family 1's child.
    r2 = _login(pilot_client, "fam-002")
    p2 = r2.json()
    assert p2["status"] == "authenticated"
    assert p2["parent_account"]["id"] != p1["parent_account"]["id"]
    h2 = {"Authorization": f"Bearer {p2['tokens']['access_token']}"}
    me2 = pilot_client.get("/v1/me", headers=h2)
    assert me2.status_code == 200
    assert me2.json()["children"] == []
