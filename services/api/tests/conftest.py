from __future__ import annotations

import sys
from pathlib import Path
from tempfile import mkdtemp

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_test_environment(prefix: str) -> None:
    import os

    test_root = mkdtemp(prefix=prefix)
    os.environ["APP_ENV"] = "testing"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_root}/test.db"
    os.environ["LOCAL_STORAGE_PATH"] = f"{test_root}/uploads"
    os.environ["PUBLIC_BASE_URL"] = "http://testserver"
    os.environ["JWT_SECRET"] = "learning-english-test-secret-at-least-32-bytes"
    os.environ["AI_PROVIDER"] = "stub"
    os.environ["ADMIN_API_TOKEN"] = "local-admin-token"


configure_test_environment("learning-english-api-suite-")


def auth_headers(client: TestClient, auth_code: str = "pilot-parent") -> tuple[dict[str, str], str]:
    login_response = client.post("/v1/auth/wechat/login", json={"auth_code": auth_code})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    if login_payload["status"] == "authenticated":
        tokens = login_payload["tokens"]
        return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens["refresh_token"]

    bind_token = login_payload["bind_token"]
    otp_response = client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138000"},
    )
    assert otp_response.status_code == 200
    otp_payload = otp_response.json()
    bind_response = client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138000",
            "otp_code": otp_payload["debug_code"],
        },
    )
    assert bind_response.status_code == 200
    bind_payload = bind_response.json()
    tokens = bind_payload["tokens"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens["refresh_token"]


@pytest.fixture
def api_client() -> TestClient:
    from app.main import app

    with TestClient(app) as client:
        yield client
