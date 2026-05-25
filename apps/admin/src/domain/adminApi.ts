import type {
  AdminAccessUser,
  AdminAuditEvent,
  AdminMaterial,
  JobStatus,
  MediaStatus,
  ProviderPolicy,
  Tenant,
  MaterialStatus
} from "./types";

export interface AdminDashboardData {
  tenants: Tenant[];
  materials: AdminMaterial[];
  providerPolicies: ProviderPolicy[];
}

export interface AdminAccessData {
  currentAdmin: AdminAccessUser;
  permissions: string[];
  auditEvents: AdminAuditEvent[];
}

export interface AdminArchiveMaterialResult {
  requiredPermission: string;
  material: AdminMaterial;
  auditEvent: AdminAuditEvent;
}

export interface AdminProviderPolicyOverrideResult {
  requiredPermission: string;
  providerPolicy: ProviderPolicy;
  auditEvent: AdminAuditEvent;
}

interface LoadAdminDashboardOptions {
  apiBaseUrl: string;
  adminToken: string;
  fetchImpl?: typeof fetch;
}

interface ArchiveAdminMaterialOptions extends LoadAdminDashboardOptions {
  tenantScope: string;
  materialId: string;
  reason: string;
}

interface RetryAdminMaterialJobOptions extends LoadAdminDashboardOptions {
  tenantScope: string;
  jobId: string;
  reason: string;
}

interface OverrideAdminProviderPolicyOptions extends LoadAdminDashboardOptions {
  tenantScope: string;
  tenantId: string;
  aiProvider: ProviderPolicy["aiProvider"];
  mediaProvider: ProviderPolicy["mediaProvider"];
  fallbackMode: ProviderPolicy["fallbackMode"];
  monthlyGuardrail: number;
  reason: string;
}

type AdminDashboardPayload = {
  tenants: Array<Record<string, unknown>>;
  materials: Array<Record<string, unknown>>;
  provider_policies: Array<Record<string, unknown>>;
};

type AdminAccessPayload = {
  current_admin: Record<string, unknown>;
  permissions: unknown[];
  audit_events: Array<Record<string, unknown>>;
};

type AdminArchiveMaterialPayload = {
  required_permission: unknown;
  material: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

type AdminProviderPolicyOverridePayload = {
  required_permission: unknown;
  provider_policy: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

export async function loadAdminDashboard(options: LoadAdminDashboardOptions): Promise<AdminDashboardData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/dashboard?tenant_scope=all`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin dashboard request failed: ${response.status}`);
  }
  return normalizeAdminDashboardPayload((await response.json()) as AdminDashboardPayload);
}

export async function loadAdminAccess(options: LoadAdminDashboardOptions): Promise<AdminAccessData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/access?tenant_scope=all`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin access request failed: ${response.status}`);
  }
  return normalizeAdminAccessPayload((await response.json()) as AdminAccessPayload);
}

export async function archiveAdminMaterial(options: ArchiveAdminMaterialOptions): Promise<AdminArchiveMaterialResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/materials/${encodeURIComponent(options.materialId)}/archive?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": options.adminToken
      },
      body: JSON.stringify({ reason: options.reason })
    }
  );
  if (!response.ok) {
    throw new Error(`Admin archive material request failed: ${response.status}`);
  }
  return normalizeAdminArchiveMaterialPayload((await response.json()) as AdminArchiveMaterialPayload);
}

export async function retryAdminMaterialJob(options: RetryAdminMaterialJobOptions): Promise<AdminArchiveMaterialResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/material-jobs/${encodeURIComponent(options.jobId)}/retry?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": options.adminToken
      },
      body: JSON.stringify({ reason: options.reason })
    }
  );
  if (!response.ok) {
    throw new Error(`Admin retry material job request failed: ${response.status}`);
  }
  return normalizeAdminArchiveMaterialPayload((await response.json()) as AdminArchiveMaterialPayload);
}

export async function overrideAdminProviderPolicy(
  options: OverrideAdminProviderPolicyOptions
): Promise<AdminProviderPolicyOverrideResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/providers/policies?tenant_scope=${encodeURIComponent(options.tenantScope)}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": options.adminToken
    },
    body: JSON.stringify({
      tenant_id: options.tenantId,
      ai_provider: options.aiProvider,
      media_provider: options.mediaProvider,
      fallback_mode: options.fallbackMode,
      monthly_guardrail: options.monthlyGuardrail,
      reason: options.reason
    })
  });
  if (!response.ok) {
    throw new Error(`Admin provider policy override request failed: ${response.status}`);
  }
  return normalizeAdminProviderPolicyOverridePayload((await response.json()) as AdminProviderPolicyOverridePayload);
}

export function normalizeAdminDashboardPayload(payload: AdminDashboardPayload): AdminDashboardData {
  return {
    tenants: payload.tenants.map((tenant) => ({
      id: stringValue(tenant.id),
      name: stringValue(tenant.name),
      tenantType: stringValue(tenant.tenant_type) as Tenant["tenantType"],
      status: stringValue(tenant.status) as Tenant["status"],
      region: stringValue(tenant.region),
      ownerContact: stringValue(tenant.owner_contact),
      tier: stringValue(tenant.tier),
      createdAt: stringValue(tenant.created_at),
      activeParents: numberValue(tenant.active_parents),
      children: numberValue(tenant.children)
    })),
    materials: payload.materials.map((material) => normalizeAdminMaterialPayload(material)),
    providerPolicies: payload.provider_policies.map((policy) => normalizeProviderPolicyPayload(policy))
  };
}

export function normalizeAdminArchiveMaterialPayload(payload: AdminArchiveMaterialPayload): AdminArchiveMaterialResult {
  return {
    requiredPermission: stringValue(payload.required_permission),
    material: normalizeAdminMaterialPayload(payload.material),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminProviderPolicyOverridePayload(
  payload: AdminProviderPolicyOverridePayload
): AdminProviderPolicyOverrideResult {
  return {
    requiredPermission: stringValue(payload.required_permission),
    providerPolicy: normalizeProviderPolicyPayload(payload.provider_policy),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminAccessPayload(payload: AdminAccessPayload): AdminAccessData {
  return {
    currentAdmin: {
      id: stringValue(payload.current_admin.id),
      displayName: stringValue(payload.current_admin.display_name),
      email: stringValue(payload.current_admin.email),
      role: stringValue(payload.current_admin.role),
      status: stringValue(payload.current_admin.status)
    },
    permissions: payload.permissions.map((item) => stringValue(item)).filter(Boolean),
    auditEvents: payload.audit_events.map((event) => normalizeAdminAuditEventPayload(event))
  };
}

function normalizeAdminMaterialPayload(material: Record<string, unknown>): AdminMaterial {
  return {
    id: stringValue(material.id),
    tenantId: stringValue(material.tenant_id),
    parentName: stringValue(material.parent_name),
    childName: stringValue(material.child_name),
    childAge: numberValue(material.child_age),
    title: stringValue(material.title),
    pageCount: numberValue(material.page_count),
    jobId: stringValue(material.job_id),
    confidenceSummary: stringValue(material.confidence_summary),
    ocrConfidence: numberValue(material.ocr_confidence),
    sourcePages: arrayValue(material.source_pages).map((page) => ({
      pageIndex: numberValue(page.page_index),
      thumbnailUrl: stringValue(page.thumbnail_url),
      sourceType: stringValue(page.source_type) as AdminMaterial["sourcePages"][number]["sourceType"]
    })),
    materialStatus: stringValue(material.material_status) as MaterialStatus,
    jobStatus: stringValue(material.job_status) as JobStatus,
    provider: stringValue(material.provider) as AdminMaterial["provider"],
    learningAssets: numberValue(material.learning_assets),
    mediaStatus: stringValue(material.media_status) as MediaStatus,
    slaMinutes: numberValue(material.sla_minutes),
    updatedAt: stringValue(material.updated_at),
    warnings: arrayValue(material.warnings).map((item) => stringValue(item))
  };
}

function normalizeAdminAuditEventPayload(event: Record<string, unknown>): AdminAuditEvent {
  return {
    id: stringValue(event.id),
    actorId: stringValue(event.actor_id),
    actorRole: stringValue(event.actor_role),
    tenantScope: stringValue(event.tenant_scope),
    action: stringValue(event.action),
    resourceType: stringValue(event.resource_type),
    resourceId: stringValue(event.resource_id),
    riskLevel: stringValue(event.risk_level) as AdminAuditEvent["riskLevel"],
    result: stringValue(event.result) as AdminAuditEvent["result"],
    reason: stringValue(event.reason),
    traceId: stringValue(event.trace_id),
    createdAt: stringValue(event.created_at)
  };
}

function normalizeProviderPolicyPayload(policy: Record<string, unknown>): ProviderPolicy {
  return {
    tenantId: stringValue(policy.tenant_id),
    tier: optionalStringValue(policy.tier),
    aiProvider: stringValue(policy.ai_provider) as ProviderPolicy["aiProvider"],
    mediaProvider: stringValue(policy.media_provider) as ProviderPolicy["mediaProvider"],
    fallbackMode: stringValue(policy.fallback_mode) as ProviderPolicy["fallbackMode"],
    monthlyGuardrail: numberValue(policy.monthly_guardrail),
    source: stringValue(policy.source) as ProviderPolicy["source"]
  };
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function optionalStringValue(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function arrayValue(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object") : [];
}
