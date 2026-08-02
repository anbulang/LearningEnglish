import { describe, expect, it, vi } from "vitest";
import {
  archiveAdminMaterial,
  endAdminImpersonationSession,
  loadAdminAuditEvents,
  loadAdminAccess,
  loadAdminDashboard,
  loadAdminImpersonationSessions,
  loadAdminLearningAssets,
  loadAdminLearningOutcomes,
  loadAdminOperations,
  loadAdminTenantDetail,
  loadAdminUsers,
  normalizeAdminAccessPayload,
  normalizeAdminDashboardPayload,
  normalizeAdminLearningAssetsPayload,
  normalizeAdminLearningOutcomesPayload,
  normalizeAdminUsersPayload,
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
    active_parents: 1,
    children: 1,
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

  it("maps failed admin material retry payloads returned with service errors", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        required_permission: "admin.material.retry",
        detail: "Material retry enqueue failed",
        material: {
          ...apiPayload.materials[0],
          material_status: "failed",
          job_status: "failed",
          warnings: ["识别任务排队失败：redis unavailable"]
        },
        action_result: {
          action: "retry_material_job",
          status: "failed",
          resource_type: "material_parse_job",
          resource_id: "job_1",
          tenant_id: "parent_1",
          message: "Material retry enqueue failed."
        },
        audit_event: {
          ...accessPayload.audit_events[0],
          action: "admin.material_job.retry",
          resource_type: "material_parse_job",
          resource_id: "job_1",
          result: "failed"
        }
      })
    });

    const result = await retryAdminMaterialJob({
      apiBaseUrl: "http://127.0.0.1:8000/",
      adminToken: "local-admin-token",
      tenantScope: "all",
      jobId: "job_1",
      reason: "Queue broker is recovering.",
      fetchImpl
    });

    expect(result.material.jobStatus).toBe("failed");
    expect(result.material.warnings).toContain("识别任务排队失败：redis unavailable");
    expect(result.actionResult?.status).toBe("failed");
    expect(result.auditEvent.result).toBe("failed");
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
    expect(result.tenant).toMatchObject({
      id: "parent_1",
      tenantType: "pilot_family",
      ownerContact: "13800138110",
      activeParents: 1,
      children: 1
    });
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

describe("loadAdminLearningAssets", () => {
  it("normalizes the learning asset payload", () => {
    const result = normalizeAdminLearningAssetsPayload({
      tenant_scope: "all",
      items: [
        {
          id: "asset_1",
          material_id: "material_1",
          material_title: "Colors",
          material_status: "ready",
          tenant_id: "parent_1",
          parent_name: "Emily",
          child_name: "Tom",
          text: "queen",
          kind: "word",
          translation: "女王",
          primary_accent: "us",
          media_status: "ready",
          generated_image_status: "ready",
          generated_image_url: "http://testserver/img.png",
          tts_us_status: "ready",
          tts_us_url: "http://testserver/us.mp3",
          tts_uk_status: "ready",
          tts_uk_url: "http://testserver/uk.mp3",
          updated_at: "2026-06-10T08:00:00+00:00"
        }
      ],
      total: 1
    });

    expect(result.total).toBe(1);
    expect(result.items[0]).toMatchObject({
      id: "asset_1",
      materialId: "material_1",
      materialTitle: "Colors",
      tenantId: "parent_1",
      childName: "Tom",
      text: "queen",
      kind: "word",
      translation: "女王",
      primaryAccent: "us",
      mediaStatus: "ready",
      ttsUkUrl: "http://testserver/uk.mp3"
    });
  });

  it("requests the endpoint with tenant scope and media filter", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tenant_scope: "parent_1", items: [], total: 0 })
    });

    await loadAdminLearningAssets({
      apiBaseUrl: "http://api.test/",
      adminToken: "tok",
      tenantScope: "parent_1",
      mediaStatus: "ready",
      fetchImpl: fetchImpl as unknown as typeof fetch
    });

    const calledUrl = fetchImpl.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/v1/admin/learning-assets?");
    expect(calledUrl).toContain("tenant_scope=parent_1");
    expect(calledUrl).toContain("media_status=ready");
  });
});

describe("loadAdminLearningOutcomes", () => {
  it("normalizes the learning outcomes payload", () => {
    const result = normalizeAdminLearningOutcomesPayload({
      tenant_scope: "all",
      weeks: 8,
      points: [
        {
          week_start: "2026-07-20",
          week_end: "2026-07-26",
          completed_sessions: 1,
          reviewed_words: 2,
          speaking_attempts: 1,
          weak_item_count: 1,
          active_children: 1
        }
      ],
      summary: {
        children_in_scope: 2,
        active_children_latest: 2,
        completed_sessions: 6,
        reviewed_words: 13,
        speaking_attempts: 4,
        weak_items: ["dog", "cat", "sun"]
      }
    });

    expect(result.tenantScope).toBe("all");
    expect(result.weeks).toBe(8);
    expect(result.points[0]).toMatchObject({
      weekStart: "2026-07-20",
      weekEnd: "2026-07-26",
      completedSessions: 1,
      reviewedWords: 2,
      speakingAttempts: 1,
      weakItemCount: 1,
      activeChildren: 1
    });
    expect(result.summary).toMatchObject({
      childrenInScope: 2,
      activeChildrenLatest: 2,
      completedSessions: 6,
      reviewedWords: 13,
      speakingAttempts: 4,
      weakItems: ["dog", "cat", "sun"]
    });
  });

  it("requests the endpoint with tenant scope and weeks", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tenant_scope: "parent_1", weeks: 8, points: [], summary: {} })
    });

    await loadAdminLearningOutcomes({
      apiBaseUrl: "http://api.test/",
      adminToken: "tok",
      tenantScope: "parent_1",
      weeks: 8,
      fetchImpl: fetchImpl as unknown as typeof fetch
    });

    const calledUrl = fetchImpl.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/v1/admin/learning-outcomes?");
    expect(calledUrl).toContain("tenant_scope=parent_1");
    expect(calledUrl).toContain("weeks=8");
  });
});

describe("loadAdminUsers", () => {
  it("normalizes the users payload", () => {
    const result = normalizeAdminUsersPayload({
      tenant_scope: "all",
      items: [
        {
          child_id: "child_1",
          child_name: "Tom",
          age: 6,
          level: "starter",
          learning_goal: "稳定复习",
          preferred_review_duration_minutes: 10,
          parent_notes: "动物主题",
          tenant_id: "parent_1",
          parent_name: "Emily",
          materials_count: 4,
          speaking_attempts: 6,
          latest_weekly_report_id: "report_1",
          created_at: "2026-03-18T08:00:00+00:00"
        }
      ],
      total: 1
    });

    expect(result.total).toBe(1);
    expect(result.items[0]).toMatchObject({
      childId: "child_1",
      childName: "Tom",
      age: 6,
      level: "starter",
      learningGoal: "稳定复习",
      preferredReviewDurationMinutes: 10,
      tenantId: "parent_1",
      parentName: "Emily",
      materialsCount: 4,
      speakingAttempts: 6,
      latestWeeklyReportId: "report_1"
    });
  });

  it("requests the endpoint with tenant scope and level filter", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tenant_scope: "parent_1", items: [], total: 0 })
    });

    await loadAdminUsers({
      apiBaseUrl: "http://api.test/",
      adminToken: "tok",
      tenantScope: "parent_1",
      level: "mover",
      fetchImpl: fetchImpl as unknown as typeof fetch
    });

    const calledUrl = fetchImpl.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/v1/admin/users?");
    expect(calledUrl).toContain("tenant_scope=parent_1");
    expect(calledUrl).toContain("level=mover");
  });
});
