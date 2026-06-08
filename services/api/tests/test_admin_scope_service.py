from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from conftest import configure_test_environment


configure_test_environment("learning-english-api-admin-scope-")

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.db.models import ParentAccountModel  # noqa: E402
from app.services.admin.scope import ensure_admin_tenant_scope, get_tenant_or_404, normalize_tenant_scope  # noqa: E402


def _seed_tenant(tenant_id: str) -> None:
    init_db()
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(
            ParentAccountModel(
                id=tenant_id,
                display_name=f"Tenant {tenant_id}",
                avatar_url="",
                phone_number=f"138{tenant_id[-8:]}",
                phone_verified_at=now,
                wechat_union_id=f"wechat_union_{tenant_id}",
                wechat_open_id=f"wechat_open_{tenant_id}",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()


def test_normalize_tenant_scope_keeps_all_scope() -> None:
    assert normalize_tenant_scope("all") == "all"


def test_normalize_tenant_scope_strips_whitespace() -> None:
    assert normalize_tenant_scope(" tenant_123 ") == "tenant_123"


def test_get_tenant_or_404_returns_in_scope_tenant() -> None:
    _seed_tenant("tenant_scope_in")

    with SessionLocal() as db:
        tenant = get_tenant_or_404(db, "tenant_scope_in", "tenant_scope_in")

    assert tenant.id == "tenant_scope_in"


def test_get_tenant_or_404_uses_no_disclosure_for_out_of_scope_tenant() -> None:
    _seed_tenant("tenant_scope_visible")
    _seed_tenant("tenant_scope_hidden")

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc:
            get_tenant_or_404(db, "tenant_scope_visible", "tenant_scope_hidden")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Tenant not found"


def test_get_tenant_or_404_all_scope_can_read_any_tenant() -> None:
    _seed_tenant("tenant_scope_all")

    with SessionLocal() as db:
        tenant = get_tenant_or_404(db, "all", "tenant_scope_all")

    assert tenant.id == "tenant_scope_all"


def test_ensure_admin_tenant_scope_rejects_missing_scope() -> None:
    init_db()

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc:
            ensure_admin_tenant_scope(db, "tenant_scope_missing")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Tenant scope not found"
