from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.settings import get_settings
from app.db.models import ChildProfileModel, CourseMaterialModel, MaterialParseJobModel, ParentAccountModel

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin token")
    if x_admin_token != get_settings().admin_api_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")


@router.get("/dashboard")
def get_admin_dashboard(
    tenant_scope: str = Query(..., min_length=1),
    _: None = Depends(require_admin_token),
    db: Session = Depends(get_db),
) -> dict:
    tenants = db.scalars(select(ParentAccountModel).order_by(ParentAccountModel.created_at.asc())).all()
    tenant_ids = {tenant.id for tenant in tenants}
    if tenant_scope != "all" and tenant_scope not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant scope not found")

    scoped_tenants = tenants if tenant_scope == "all" else [tenant for tenant in tenants if tenant.id == tenant_scope]
    scoped_tenant_ids = {tenant.id for tenant in scoped_tenants}
    children = db.scalars(
        select(ChildProfileModel).where(ChildProfileModel.parent_account_id.in_(scoped_tenant_ids or [""]))
    ).all()
    child_by_id = {child.id: child for child in children}
    parent_by_id = {tenant.id: tenant for tenant in scoped_tenants}
    children_by_parent = _count_children_by_parent(children)
    material_rows = db.execute(
        select(CourseMaterialModel, ChildProfileModel, ParentAccountModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .join(ParentAccountModel, ParentAccountModel.id == ChildProfileModel.parent_account_id)
        .where(ChildProfileModel.parent_account_id.in_(scoped_tenant_ids or [""]))
        .order_by(CourseMaterialModel.updated_at.desc())
    ).all()
    material_ids = [row[0].id for row in material_rows]
    jobs = db.scalars(select(MaterialParseJobModel).where(MaterialParseJobModel.material_id.in_(material_ids or [""]))).all()
    job_by_material = {job.material_id: job for job in jobs}
    materials = [
        _admin_material_payload(material, child, parent, job_by_material.get(material.id))
        for material, child, parent in material_rows
    ]

    return {
        "tenants": [_admin_tenant_payload(tenant, children_by_parent.get(tenant.id, 0), materials) for tenant in scoped_tenants],
        "materials": materials,
        "provider_policies": [_global_provider_policy()],
    }


def _count_children_by_parent(children: list[ChildProfileModel]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for child in children:
        counts[child.parent_account_id] = counts.get(child.parent_account_id, 0) + 1
    return counts


def _admin_tenant_payload(parent: ParentAccountModel, child_count: int, materials: list[dict]) -> dict:
    tenant_materials = [material for material in materials if material["tenant_id"] == parent.id]
    has_blocker = any(
        material["material_status"] == "failed" or material["job_status"] == "failed" or material["sla_minutes"] > 180
        for material in tenant_materials
    )
    return {
        "id": parent.id,
        "name": parent.display_name or _fallback_parent_name(parent),
        "tenant_type": "pilot_family",
        "status": "warning" if has_blocker else "active",
        "region": "local",
        "owner_contact": parent.phone_number,
        "tier": "pilot",
        "created_at": _iso(parent.created_at),
        "active_parents": 1,
        "children": child_count,
    }


def _admin_material_payload(
    material: CourseMaterialModel,
    child: ChildProfileModel,
    parent: ParentAccountModel,
    job: Optional[MaterialParseJobModel],
) -> dict:
    image_records = list(material.image_records or [])
    learning_assets = list(material.learning_assets or [])
    updated_at = material.updated_at or material.created_at
    return {
        "id": material.id,
        "tenant_id": parent.id,
        "parent_name": parent.display_name or _fallback_parent_name(parent),
        "child_name": child.name,
        "child_age": child.age,
        "title": material.title,
        "page_count": len(image_records) or len(material.source_images or []),
        "job_id": job.id if job else "",
        "confidence_summary": job.confidence_summary if job else "",
        "ocr_confidence": _ocr_confidence(job),
        "source_pages": [_source_page_payload(item) for item in image_records],
        "material_status": material.status,
        "job_status": job.status if job else "queued",
        "provider": _admin_provider(),
        "learning_assets": len(learning_assets),
        "media_status": _media_status(learning_assets),
        "sla_minutes": _elapsed_minutes(updated_at),
        "updated_at": _iso(updated_at),
        "warnings": list(job.warnings or []) if job else [],
    }


def _source_page_payload(item: dict) -> dict:
    return {
        "page_index": item.get("page_index", 0),
        "thumbnail_url": item.get("url", ""),
        "source_type": item.get("source_type", "gallery"),
    }


def _media_status(learning_assets: list[dict]) -> str:
    if not learning_assets:
        return "pending"
    statuses = [
        str(asset.get(key, "pending"))
        for asset in learning_assets
        for key in ("generated_image_status", "tts_us_status", "tts_uk_status")
    ]
    if any(item == "failed" for item in statuses):
        return "failed"
    if statuses and all(item == "ready" for item in statuses):
        return "ready"
    if any(item == "processing" for item in statuses):
        return "processing"
    return "pending"


def _ocr_confidence(job: Optional[MaterialParseJobModel]) -> float:
    if job is None:
        return 0.0
    if job.status == "failed":
        return 0.0
    if job.status == "ready":
        return 0.95
    if job.draft_image_records or job.draft_vocabulary or job.draft_sentences:
        return 0.72
    return 0.0


def _admin_provider() -> str:
    return "doubao" if get_settings().ai_provider == "doubao" else "stub"


def _global_provider_policy() -> dict:
    settings = get_settings()
    return {
        "tenant_id": "global",
        "ai_provider": "doubao" if settings.ai_provider == "doubao" else "stub",
        "media_provider": "real" if settings.media_provider == "real" else "mock",
        "fallback_mode": "global_stub" if settings.ai_provider != "doubao" else "auto_to_mock",
        "monthly_guardrail": 0,
        "source": "global_default",
    }


def _elapsed_minutes(value: datetime) -> int:
    normalized = value
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - normalized.astimezone(timezone.utc)).total_seconds() // 60))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _fallback_parent_name(parent: ParentAccountModel) -> str:
    if parent.phone_number:
        return f"Family {parent.phone_number[-4:]}"
    return parent.id
