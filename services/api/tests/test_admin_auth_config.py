from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.admin.routes import require_admin_token
from app.core.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_admin_api_token_has_no_production_default(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    settings = get_settings()

    assert settings.admin_api_token == ""


def test_admin_token_dependency_fails_closed_when_token_is_unconfigured(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_admin_token("local-admin-token")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Admin API token is not configured"
