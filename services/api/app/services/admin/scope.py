from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AdminAuditEventModel,
    AdminImpersonationSessionModel,
    ChildProfileModel,
    ParentAccountModel,
    TenantModuleSettingModel,
    TenantProviderPolicyModel,
)


def normalize_tenant_scope(tenant_scope: str) -> str:
    return tenant_scope.strip()


def audit_scope_filter(tenant_scope: str):
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return AdminAuditEventModel.tenant_scope != ""
    return AdminAuditEventModel.tenant_scope.in_(["all", normalized_scope])


def tenant_scope_filter(model: type[Any], tenant_scope: str):
    tenant_column = getattr(model, "tenant_id")
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return tenant_column != ""
    return tenant_column == normalized_scope


def tenant_child_scope_filter(tenant_scope: str):
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return ChildProfileModel.parent_account_id != ""
    return ChildProfileModel.parent_account_id == normalized_scope


def tenant_provider_policy_scope_filter(tenant_scope: str):
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return TenantProviderPolicyModel.tenant_id != ""
    return TenantProviderPolicyModel.tenant_id == normalized_scope


def tenant_module_setting_scope_filter(tenant_scope: str):
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return TenantModuleSettingModel.tenant_id != ""
    return TenantModuleSettingModel.tenant_id == normalized_scope


def impersonation_session_scope_filter(tenant_scope: str):
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return AdminImpersonationSessionModel.tenant_id != ""
    return AdminImpersonationSessionModel.tenant_id == normalized_scope


def ensure_admin_tenant_scope(db: Session, tenant_scope: str) -> None:
    normalized_scope = normalize_tenant_scope(tenant_scope)
    if normalized_scope == "all":
        return
    tenant_count = db.scalar(select(func.count(ParentAccountModel.id)).where(ParentAccountModel.id == normalized_scope))
    if not tenant_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")


def ensure_tenant_in_scope(tenant_scope: str, tenant_id: str, *, detail: str) -> None:
    normalized_scope = normalize_tenant_scope(tenant_scope)
    normalized_tenant_id = tenant_id.strip()
    if normalized_scope != "all" and normalized_scope != normalized_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def get_tenant_or_404(db: Session, tenant_scope: str, tenant_id: str) -> ParentAccountModel:
    normalized_tenant_id = tenant_id.strip()
    if not normalized_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    ensure_tenant_in_scope(tenant_scope, normalized_tenant_id, detail="Tenant not found")
    tenant = db.get(ParentAccountModel, normalized_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
