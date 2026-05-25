import { describe, expect, it, vi } from "vitest";
import {
  archiveAdminMaterial,
  loadAdminAccess,
  loadAdminDashboard,
  normalizeAdminAccessPayload,
  normalizeAdminDashboardPayload
} from "./adminApi";

const apiPayload = {
  tenants: [
    {
      id: "parent_1",
      name: "微信家长test",
      tenant_type: "pilot_family",
      status: "active",
      region: "local",
      owner_contact: "13800138110",
      tier: "pilot",
      created_at: "2026-05-25T10:00:00+00:00",
      active_parents: 1,
      children: 1
    }
  ],
  materials: [
    {
      id: "material_1",
      tenant_id: "parent_1",
      parent_name: "微信家长test",
      child_name: "Mia Wang",
      child_age: 6,
      title: "Colors Mini Test",
      page_count: 1,
      job_id: "job_1",
      confidence_summary: "上传完成，等待 OCR 与解析。",
      ocr_confidence: 0.72,
      source_pages: [{ page_index: 1, thumbnail_url: "http://testserver/uploads/page.jpg", source_type: "camera" }],
      material_status: "processing",
      job_status: "processing",
      provider: "stub",
      learning_assets: 0,
      media_status: "pending",
      sla_minutes: 12,
      updated_at: "2026-05-25T10:05:00+00:00",
      warnings: []
    }
  ],
  provider_policies: [
    {
      tenant_id: "global",
      ai_provider: "stub",
      media_provider: "mock",
      fallback_mode: "global_stub",
      monthly_guardrail: 0,
      source: "global_default"
    }
  ]
};

const accessPayload = {
  current_admin: {
    id: "admin_local",
    display_name: "Local Platform Admin",
    email: "admin@learningenglish.local",
    role: "Platform Owner",
    status: "active"
  },
  permissions: ["admin.dashboard.read", "admin.audit.read"],
  audit_events: [
    {
      id: "audit_1",
      actor_id: "admin_local",
      actor_role: "Platform Owner",
      tenant_scope: "all",
      action: "admin.dashboard.read",
      resource_type: "admin_dashboard",
      resource_id: "dashboard",
      risk_level: "low",
      result: "success",
      reason: "",
      trace_id: "req_12345678",
      created_at: "2026-05-25T10:06:00+00:00"
    }
  ]
};

describe("admin API client", () => {
  it("normalizes backend snake_case payloads into admin domain data", () => {
    const normalized = normalizeAdminDashboardPayload(apiPayload);

    expect(normalized.tenants[0]).toMatchObject({
      id: "parent_1",
      tenantType: "pilot_family",
      ownerContact: "13800138110",
      activeParents: 1,
      createdAt: "2026-05-25T10:00:00+00:00"
    });
    expect(normalized.materials[0]).toMatchObject({
      id: "material_1",
      tenantId: "parent_1",
      childName: "Mia Wang",
      pageCount: 1,
      jobId: "job_1",
      materialStatus: "processing",
      mediaStatus: "pending",
      sourcePages: [{ pageIndex: 1, thumbnailUrl: "http://testserver/uploads/page.jpg", sourceType: "camera" }]
    });
    expect(normalized.providerPolicies[0]).toMatchObject({
      tenantId: "global",
      aiProvider: "stub",
      mediaProvider: "mock",
      fallbackMode: "global_stub",
      monthlyGuardrail: 0
    });
  });

  it("loads the all-tenant dashboard with the configured admin token", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => apiPayload
    });

    const result = await loadAdminDashboard({
      apiBaseUrl: "http://127.0.0.1:8000",
      adminToken: "local-admin-token",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/dashboard?tenant_scope=all", {
      headers: { "X-Admin-Token": "local-admin-token" }
    });
    expect(result.materials).toHaveLength(1);
  });

  it("normalizes admin access and audit events", () => {
    const normalized = normalizeAdminAccessPayload(accessPayload);

    expect(normalized.currentAdmin).toMatchObject({
      id: "admin_local",
      displayName: "Local Platform Admin",
      role: "Platform Owner"
    });
    expect(normalized.permissions).toContain("admin.audit.read");
    expect(normalized.auditEvents[0]).toMatchObject({
      actorId: "admin_local",
      tenantScope: "all",
      action: "admin.dashboard.read",
      resourceType: "admin_dashboard",
      traceId: "req_12345678"
    });
  });

  it("loads admin access with the configured admin token", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => accessPayload
    });

    const result = await loadAdminAccess({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/access?tenant_scope=all", {
      headers: { "X-Admin-Token": "local-admin-token" }
    });
    expect(result.auditEvents).toHaveLength(1);
  });

  it("archives an admin material with tenant scope and reason", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.material.archive",
        material: apiPayload.materials[0],
        audit_event: accessPayload.audit_events[0]
      })
    });

    const result = await archiveAdminMaterial({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      materialId: "material_1",
      reason: "Duplicate worksheet uploaded by parent.",
      fetchImpl
    });

    expect(result.requiredPermission).toBe("admin.material.archive");
    expect(result.material.id).toBe("material_1");
    expect(result.auditEvent.action).toBe("admin.dashboard.read");
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/materials/material_1/archive?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({ reason: "Duplicate worksheet uploaded by parent." })
    });
  });
});
