from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.admin_identity import AdminActor
from app.services.admin_permissions import ADMIN_PERMISSIONS, require_any_permission, require_permission


def _actor(permissions: list[str]) -> AdminActor:
    return AdminActor(
        id="admin_ops",
        display_name="Ops",
        email="ops@example.com",
        role="Operations",
        status="active",
        permissions=permissions,
    )


def test_require_permission_allows_exact_permission() -> None:
    require_permission(_actor(["admin.operations.read"]), "admin.operations.read")


def test_require_permission_allows_wildcard() -> None:
    require_permission(_actor(["*"]), "admin.operations.read")


def test_require_permission_raises_stable_detail() -> None:
    with pytest.raises(HTTPException) as exc:
        require_permission(_actor(["admin.dashboard.read"]), "admin.operations.read")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Missing admin.operations.read permission"


def test_require_any_permission_allows_first_matching_permission() -> None:
    require_any_permission(_actor(["admin.dashboard.read"]), ["admin.operations.read", "admin.dashboard.read"])


def test_require_any_permission_raises_stable_detail() -> None:
    with pytest.raises(HTTPException) as exc:
        require_any_permission(_actor(["admin.audit.read"]), ["admin.operations.read", "admin.dashboard.read"])

    assert exc.value.status_code == 403
    assert exc.value.detail == "Missing one of admin.operations.read, admin.dashboard.read permissions"


def test_admin_permissions_include_phase_three_entries() -> None:
    assert "admin.operations.read" in ADMIN_PERMISSIONS
    assert "admin.impersonation.end" in ADMIN_PERMISSIONS
