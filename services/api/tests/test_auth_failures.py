from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.db.models import ParentAccountModel, PhoneBindingModel
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-auth-")


def test_wechat_login_requires_auth_code(api_client) -> None:
    response = api_client.post("/v1/auth/wechat/login", json={})
    assert response.status_code == 422
    assert response.json()["detail"] == "auth_code: Field required"


def test_request_otp_rejects_invalid_bind_token(api_client) -> None:
    response = api_client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": "not-a-token", "phone_number": "13800138000"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid bind token"


def test_bind_phone_rejects_expired_otp(api_client) -> None:
    login = api_client.post("/v1/auth/wechat/login", json={"auth_code": "expired-otp-parent"})
    bind_token = login.json()["bind_token"]
    otp = api_client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138000"},
    )
    assert otp.status_code == 200

    with SessionLocal() as db:
        parent = db.scalar(
            select(ParentAccountModel).where(ParentAccountModel.wechat_union_id == "wechat_union_expired-otp-parent")
        )
        binding = db.scalar(
            select(PhoneBindingModel)
            .where(PhoneBindingModel.parent_account_id == parent.id)
            .order_by(PhoneBindingModel.created_at.desc())
        )
        binding.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.add(binding)
        db.commit()

    response = api_client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138000",
            "otp_code": "123456",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "OTP expired"


def test_bind_phone_rejects_wrong_otp(api_client) -> None:
    login = api_client.post("/v1/auth/wechat/login", json={"auth_code": "wrong-otp-parent"})
    bind_token = login.json()["bind_token"]
    otp = api_client.post(
        "/v1/auth/phone/request-otp",
        json={"bind_token": bind_token, "phone_number": "13800138000"},
    )
    assert otp.status_code == 200

    response = api_client.post(
        "/v1/auth/phone/bind",
        json={
            "bind_token": bind_token,
            "phone_number": "13800138000",
            "otp_code": "654321",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "OTP code mismatch"


def test_refresh_rejects_invalid_token(api_client) -> None:
    response = api_client.post("/v1/auth/refresh", json={"refresh_token": "broken-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


def test_me_rejects_invalid_access_token(api_client) -> None:
    response = api_client.get("/v1/me", headers={"Authorization": "Bearer broken-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_logout_accepts_valid_refresh_token(api_client) -> None:
    _, refresh_token = auth_headers(api_client, auth_code="logout-parent")
    response = api_client.post("/v1/auth/logout", json={"refresh_token": refresh_token})
    assert response.status_code == 204
