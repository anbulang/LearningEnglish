from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from fastapi import HTTPException, status


ADMIN_DASHBOARD_READ = "admin.dashboard.read"
ADMIN_OPERATIONS_READ = "admin.operations.read"
ADMIN_TENANT_READ = "admin.tenant.read"
ADMIN_MATERIAL_READ = "admin.material.read"
ADMIN_MATERIAL_ARCHIVE = "admin.material.archive"
ADMIN_MATERIAL_RETRY = "admin.material.retry"
ADMIN_TENANT_MODULE_TOGGLE = "admin.tenant.module.toggle"
ADMIN_PROVIDER_OVERRIDE = "admin.provider.override"
ADMIN_IMPERSONATION_START = "admin.impersonation.start"
ADMIN_IMPERSONATION_READ = "admin.impersonation.read"
ADMIN_IMPERSONATION_END = "admin.impersonation.end"
ADMIN_AUDIT_READ = "admin.audit.read"

ADMIN_PERMISSIONS = [
    ADMIN_DASHBOARD_READ,
    ADMIN_OPERATIONS_READ,
    ADMIN_TENANT_READ,
    ADMIN_MATERIAL_READ,
    ADMIN_MATERIAL_ARCHIVE,
    ADMIN_MATERIAL_RETRY,
    ADMIN_TENANT_MODULE_TOGGLE,
    ADMIN_PROVIDER_OVERRIDE,
    ADMIN_IMPERSONATION_START,
    ADMIN_IMPERSONATION_READ,
    ADMIN_IMPERSONATION_END,
    ADMIN_AUDIT_READ,
]


class AdminPermissionActor(Protocol):
    permissions: list[str]


def has_permission(actor: AdminPermissionActor, permission: str) -> bool:
    return "*" in actor.permissions or permission in actor.permissions


def require_permission(actor: AdminPermissionActor, permission: str) -> None:
    if not has_permission(actor, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing {permission} permission")


def require_any_permission(actor: AdminPermissionActor, permissions: Sequence[str]) -> None:
    if any(has_permission(actor, permission) for permission in permissions):
        return
    joined = ", ".join(permissions)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing one of {joined} permissions")
