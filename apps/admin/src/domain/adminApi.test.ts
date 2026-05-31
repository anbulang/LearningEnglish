import { describe, expect, it, vi } from "vitest";
import {
  archiveAdminMaterial,
  endAdminImpersonationSession,
  loadAdminAuditEvents,
  loadAdminAccess,
  loadAdminDashboard,
  loadAdminImpersonationSessions,
  loadAdminOperations,
  loadAdminTenantDetail,
  normalizeAdminAccessPayload,
  normalizeAdminDashboardPayload,
  overrideAdminProviderPolicy,
  retryAdminMaterialJob,
  startAdminImpersonationSession,
  toggleAdminTenantModule
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
  ],
  module_settings: [
    {
      tenant_id: "parent_1",
      module_key: "speaking_score",
      enabled: true,
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

const actionResultPayload = {
  action: "end_impersonation_session",
  status: "success",
  resource_type: "admin_impersonation_session",
  resource_id: "imp_123",
  tenant_id: "parent_1",
  message: "Impersonation session ended."
};

const operationsPayload = {
  tenant_scope: "all",
  summary: {
    tenant_count: 2,
    materials: 8,
    material_parse_jobs: 6,
    media_failures: 3,
    speaking_attempts: 4,
    severity: "critical",
    issue_count: 1
  },
  material_parse_jobs: {
    total: 6,
    failed: 2,
    running: 1,
    latest_failed: [{ id: "job_1", tenant_id: "parent_1", status: "failed" }]
  },
  media_generation: {
    failure_signals: { total: 3 }
  },
  speaking_attempts: {
    total: 4,
    latest_failed: []
  },
  provider_configuration: {
    runtime: { readiness: { ai_provider_ready: true } }
  },
  module_toggle_coverage: {
    tenant_count: 2
  },
  issues: [
    {
      id: "issue_material_job_job_1_failed",
      severity: "critical",
      status_label: "Parse failed",
      reason: "OCR provider timeout",
      recommended_action: "retry_material_job",
      required_permission: "admin.material.retry",
      related_resource: {
        type: "material_parse_job",
        id: "job_1",
        tenant_id: "parent_1",
        material_id: "material_1"
      },
      source: "database_snapshot"
    }
  ],
  audit_event: accessPayload.audit_events[0],
  access_context: {
    current_admin: accessPayload.current_admin,
    recent_audit_events: accessPayload.audit_events
  }
};

const tenantDetailPayload = {
  required_permission: "admin.tenant.read",
  tenant: {
    id: "parent_1",
    name: "微信家长test",
    display_name: "微信家长test",
    status: "warning",
    tenant_type: "pilot_family",
    region: "local",
    tier: "pilot",
    owner_contact: "13800138110",
    created_at: "2026-05-25T10:00:00+00:00",
    updated_at: "2026-05-25T10:05:00+00:00"
  },
  summary: {
    children: 1,
    materials: 1,
    failed_materials: 1
  },
  children: [
    {
      id: "child_1",
      name: "Mia Wang",
      age: 6,
      level: "starter",
      latest_weekly_report_id: "report_1",
      speaking_attempts: 3
    }
  ],
  materials: [apiPayload.materials[0]],
  provider_policy: apiPayload.provider_policies[0],
  module_settings: apiPayload.module_settings,
  weekly_reports: {
    latest: [],
    aggregate: { completed_sessions: 3 }
  },
  speaking_attempts: {
    latest: [],
    by_status: { failed: 1 }
  },
  risk_summary: {
    risk_level: "high",
    reasons: ["Material parse failed"]
  },
  audit_event: accessPayload.audit_events[0],
  access_context: {
    current_admin: accessPayload.current_admin,
    recent_audit_events: accessPayload.audit_events
  }
};

const auditEventsPayload = {
  items: accessPayload.audit_events,
  next_cursor: "2026-05-25T10:06:00+00:00|audit_1"
};

const impersonationSessionPayload = {
  id: "imp_123",
  tenant_id: "parent_1",
  target_parent_id: "parent_1",
  actor_id: "admin_local",
  status: "active",
  reason: "Support is reproducing parent-reported upload issue.",
  expires_at: "2026-05-25T10:36:00+00:00",
  created_at: "2026-05-25T10:06:00+00:00",
  ended_at: "",
  updated_at: "2026-05-25T10:06:00+00:00",
  tenant_display_name: "微信家长test",
  target_parent_display_name: "微信家长test"
};

const impersonationSessionsPayload = {
  required_permission: "admin.impersonation.read",
  tenant_scope: "all",
  status: "all",
  items: [impersonationSessionPayload],
  audit_event: accessPayload.audit_events[0]
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
    expect(normalized.moduleSettings[0]).toMatchObject({
      tenantId: "parent_1",
      moduleKey: "speaking_score",
      enabled: true,
      source: "global_default"
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

  it("retries an admin material job with tenant scope and reason", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.material.retry",
        material: { ...apiPayload.materials[0], material_status: "processing", job_status: "processing" },
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.material_job.retry",
          resource_type: "material_parse_job",
          resource_id: "job_1",
          reason: "OCR provider recovered."
        }
      })
    });

    const result = await retryAdminMaterialJob({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      jobId: "job_1",
      reason: "OCR provider recovered.",
      fetchImpl
    });

    expect(result.requiredPermission).toBe("admin.material.retry");
    expect(result.material.jobStatus).toBe("processing");
    expect(result.auditEvent.action).toBe("admin.material_job.retry");
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/material-jobs/job_1/retry?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({ reason: "OCR provider recovered." })
    });
  });

  it("overrides an admin provider policy with tenant scope and reason", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.provider.override",
        provider_policy: {
          tenant_id: "parent_1",
          ai_provider: "doubao",
          media_provider: "real",
          fallback_mode: "per_tenant",
          monthly_guardrail: 500,
          source: "tenant_override"
        },
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.provider_policy.override",
          resource_type: "tenant_provider_policy",
          resource_id: "parent_1",
          reason: "Pilot tenant approved for real media provider."
        }
      })
    });

    const result = await overrideAdminProviderPolicy({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      tenantId: "parent_1",
      aiProvider: "doubao",
      mediaProvider: "real",
      fallbackMode: "per_tenant",
      monthlyGuardrail: 500,
      reason: "Pilot tenant approved for real media provider.",
      fetchImpl
    });

    expect(result.requiredPermission).toBe("admin.provider.override");
    expect(result.providerPolicy).toMatchObject({
      tenantId: "parent_1",
      aiProvider: "doubao",
      mediaProvider: "real",
      source: "tenant_override"
    });
    expect(result.auditEvent.action).toBe("admin.provider_policy.override");
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/providers/policies?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({
        tenant_id: "parent_1",
        ai_provider: "doubao",
        media_provider: "real",
        fallback_mode: "per_tenant",
        monthly_guardrail: 500,
        reason: "Pilot tenant approved for real media provider."
      })
    });
  });

  it("toggles a tenant module with tenant scope and reason", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.tenant.module.toggle",
        module_setting: {
          tenant_id: "parent_1",
          module_key: "speaking_score",
          enabled: false,
          source: "tenant_override"
        },
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.tenant_module.toggle",
          resource_type: "tenant_module_setting",
          resource_id: "parent_1:speaking_score",
          reason: "Pilot tenant requested speaking score pause."
        }
      })
    });

    const result = await toggleAdminTenantModule({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      tenantId: "parent_1",
      moduleKey: "speaking_score",
      enabled: false,
      reason: "Pilot tenant requested speaking score pause.",
      fetchImpl
    });

    expect(result.requiredPermission).toBe("admin.tenant.module.toggle");
    expect(result.moduleSetting).toMatchObject({
      tenantId: "parent_1",
      moduleKey: "speaking_score",
      enabled: false,
      source: "tenant_override"
    });
    expect(result.auditEvent.action).toBe("admin.tenant_module.toggle");
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/tenants/parent_1/modules/speaking_score?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({
        enabled: false,
        reason: "Pilot tenant requested speaking score pause."
      })
    });
  });

  it("starts a supervised impersonation session without returning parent tokens", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.impersonation.start",
        impersonation_session: {
          id: "imp_123",
          tenant_id: "parent_1",
          target_parent_id: "parent_1",
          actor_id: "admin_local",
          status: "active",
          reason: "Support is reproducing parent-reported upload issue.",
          expires_at: "2026-05-25T10:36:00+00:00",
          created_at: "2026-05-25T10:06:00+00:00"
        },
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.impersonation.start",
          resource_type: "admin_impersonation_session",
          resource_id: "imp_123",
          reason: "Support is reproducing parent-reported upload issue."
        }
      })
    });

    const result = await startAdminImpersonationSession({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      tenantId: "parent_1",
      targetParentId: "parent_1",
      reason: "Support is reproducing parent-reported upload issue.",
      fetchImpl
    });

    expect(result.requiredPermission).toBe("admin.impersonation.start");
    expect(result.impersonationSession).toMatchObject({
      id: "imp_123",
      tenantId: "parent_1",
      targetParentId: "parent_1",
      actorId: "admin_local",
      status: "active"
    });
    expect(JSON.stringify(result)).not.toContain("access_token");
    expect(result.auditEvent.action).toBe("admin.impersonation.start");
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/impersonation-sessions?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({
        tenant_id: "parent_1",
        target_parent_id: "parent_1",
        reason: "Support is reproducing parent-reported upload issue."
      })
    });
  });

  it("loads admin operations and maps issues", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => operationsPayload
    });

    const result = await loadAdminOperations({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/operations?tenant_scope=all", {
      headers: { "X-Admin-Token": "local-admin-token" }
    });
    expect(result.summary.severity).toBe("critical");
    expect(result.materialParseJobs.latest_failed).toHaveLength(1);
    expect(result.issues[0]).toMatchObject({
      id: "issue_material_job_job_1_failed",
      statusLabel: "Parse failed",
      recommendedAction: "retry_material_job",
      requiredPermission: "admin.material.retry",
      relatedResource: {
        type: "material_parse_job",
        id: "job_1",
        tenantId: "parent_1"
      },
      source: "database_snapshot"
    });
  });

  it("loads admin tenant detail and maps nested data", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => tenantDetailPayload
    });

    const result = await loadAdminTenantDetail({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      tenantId: "parent_1",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/tenants/parent_1?tenant_scope=all", {
      headers: { "X-Admin-Token": "local-admin-token" }
    });
    expect(result.requiredPermission).toBe("admin.tenant.read");
    expect(result.tenant).toMatchObject({ id: "parent_1", tenantType: "pilot_family", ownerContact: "13800138110" });
    expect(result.children[0]).toMatchObject({ id: "child_1", name: "Mia Wang" });
    expect(result.materials[0]).toMatchObject({ id: "material_1", tenantId: "parent_1" });
    expect(result.providerPolicy.tenantId).toBe("global");
    expect(result.riskSummary.risk_level).toBe("high");
    expect(result.accessContext?.currentAdmin.id).toBe("admin_local");
    expect(result.accessContext?.recentAuditEvents[0].id).toBe("audit_1");
  });

  it("loads admin audit events with filters and maps next cursor", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => auditEventsPayload
    });

    const result = await loadAdminAuditEvents({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "parent_1",
      action: "admin.material_job.retry",
      resourceType: "material_parse_job",
      resourceId: "job_1",
      riskLevel: "high",
      result: "failed",
      actorId: "admin_local",
      limit: 25,
      cursor: "cursor_1",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/admin/audit-events?tenant_scope=parent_1&action=admin.material_job.retry&resource_type=material_parse_job&resource_id=job_1&risk_level=high&result=failed&actor_id=admin_local&limit=25&cursor=cursor_1",
      { headers: { "X-Admin-Token": "local-admin-token" } }
    );
    expect(result.items[0].resourceType).toBe("admin_dashboard");
    expect(result.nextCursor).toBe("2026-05-25T10:06:00+00:00|audit_1");
  });

  it("loads admin impersonation sessions", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => impersonationSessionsPayload
    });

    const result = await loadAdminImpersonationSessions({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      status: "all",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/impersonation-sessions?tenant_scope=all&status=all", {
      headers: { "X-Admin-Token": "local-admin-token" }
    });
    expect(result.requiredPermission).toBe("admin.impersonation.read");
    expect(result.items[0]).toMatchObject({
      id: "imp_123",
      tenantId: "parent_1",
      tenantDisplayName: "微信家长test",
      updatedAt: "2026-05-25T10:06:00+00:00"
    });
    expect(result.auditEvent.action).toBe("admin.dashboard.read");
  });

  it("ends an admin impersonation session with reason and maps action result", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        required_permission: "admin.impersonation.end",
        impersonation_session: {
          ...impersonationSessionPayload,
          status: "ended",
          ended_at: "2026-05-25T10:16:00+00:00"
        },
        action_result: actionResultPayload,
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.impersonation.end",
          resource_type: "admin_impersonation_session",
          resource_id: "imp_123"
        }
      })
    });

    const result = await endAdminImpersonationSession({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      sessionId: "imp_123",
      reason: "Support handoff complete.",
      fetchImpl
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/impersonation-sessions/imp_123/end?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({ reason: "Support handoff complete." })
    });
    expect(result.requiredPermission).toBe("admin.impersonation.end");
    expect(result.impersonationSession.status).toBe("ended");
    expect(result.actionResult).toMatchObject({
      action: "end_impersonation_session",
      status: "success",
      resourceType: "admin_impersonation_session",
      resourceId: "imp_123",
      tenantId: "parent_1"
    });
    expect(result.auditEvent.action).toBe("admin.impersonation.end");
  });
});
