import type {
  AdminAccessUser,
  AdminActionResult,
  AdminAuditEvent,
  AdminAuditEventsData,
  AdminImpersonationSession,
  AdminImpersonationSessionsData,
  AdminLearningAsset,
  AdminMaterial,
  AdminUserAccount,
  AdminOperationsData,
  AdminOperationsIssue,
  AdminTenantChild,
  AdminTenantDetailData,
  AdminTenantDetailTenant,
  EndAdminImpersonationSessionResult,
  JobStatus,
  MediaStatus,
  ModuleKey,
  ProviderPolicy,
  TenantModuleSetting,
  Tenant,
  MaterialStatus
} from "./types";

export interface AdminDashboardData {
  tenants: Tenant[];
  materials: AdminMaterial[];
  providerPolicies: ProviderPolicy[];
  moduleSettings: TenantModuleSetting[];
}

export interface AdminAccessData {
  currentAdmin: AdminAccessUser;
  permissions: string[];
  auditEvents: AdminAuditEvent[];
}

export interface AdminArchiveMaterialResult {
  requiredPermission: string;
  material: AdminMaterial;
  actionResult?: AdminActionResult;
  auditEvent: AdminAuditEvent;
}

export interface AdminProviderPolicyOverrideResult {
  requiredPermission: string;
  providerPolicy: ProviderPolicy;
  actionResult?: AdminActionResult;
  auditEvent: AdminAuditEvent;
}

export interface AdminTenantModuleToggleResult {
  requiredPermission: string;
  moduleSetting: TenantModuleSetting;
  actionResult?: AdminActionResult;
  auditEvent: AdminAuditEvent;
}

export interface AdminImpersonationSessionResult {
  requiredPermission: string;
  impersonationSession: AdminImpersonationSession;
  auditEvent: AdminAuditEvent;
}

export interface AdminApiOptions {
  apiBaseUrl: string;
  adminToken: string;
  fetchImpl?: typeof fetch;
}

type LoadAdminDashboardOptions = AdminApiOptions;

interface AdminTenantScopedOptions extends AdminApiOptions {
  tenantScope: string;
}

interface ArchiveAdminMaterialOptions extends AdminTenantScopedOptions {
  tenantScope: string;
  materialId: string;
  reason: string;
}

interface RetryAdminMaterialJobOptions extends AdminTenantScopedOptions {
  tenantScope: string;
  jobId: string;
  reason: string;
}

interface OverrideAdminProviderPolicyOptions extends AdminTenantScopedOptions {
  tenantScope: string;
  tenantId: string;
  aiProvider: ProviderPolicy["aiProvider"];
  mediaProvider: ProviderPolicy["mediaProvider"];
  fallbackMode: ProviderPolicy["fallbackMode"];
  monthlyGuardrail: number;
  reason: string;
}

interface ToggleAdminTenantModuleOptions extends AdminTenantScopedOptions {
  tenantScope: string;
  tenantId: string;
  moduleKey: ModuleKey;
  enabled: boolean;
  reason: string;
}

interface StartAdminImpersonationSessionOptions extends AdminTenantScopedOptions {
  tenantScope: string;
  tenantId: string;
  targetParentId: string;
  reason: string;
}

interface AdminTenantDetailOptions extends AdminTenantScopedOptions {
  tenantId: string;
}

export interface AdminAuditEventsOptions extends AdminTenantScopedOptions {
  action?: string;
  resourceType?: string;
  resourceId?: string;
  riskLevel?: string;
  result?: string;
  actorId?: string;
  limit?: number;
  cursor?: string;
}

interface AdminImpersonationSessionsOptions extends AdminTenantScopedOptions {
  status?: "active" | "ended" | "all";
}

interface EndAdminImpersonationSessionOptions extends AdminTenantScopedOptions {
  sessionId: string;
  reason: string;
}

type AdminDashboardPayload = {
  tenants: Array<Record<string, unknown>>;
  materials: Array<Record<string, unknown>>;
  provider_policies: Array<Record<string, unknown>>;
  module_settings?: Array<Record<string, unknown>>;
};

type AdminAccessPayload = {
  current_admin: Record<string, unknown>;
  permissions: unknown[];
  audit_events: Array<Record<string, unknown>>;
};

type AdminTenantAccessContextPayload = {
  current_admin?: Record<string, unknown>;
  recent_audit_events?: Array<Record<string, unknown>>;
};

type AdminArchiveMaterialPayload = {
  required_permission: unknown;
  material: Record<string, unknown>;
  action_result?: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

type AdminProviderPolicyOverridePayload = {
  required_permission: unknown;
  provider_policy: Record<string, unknown>;
  action_result?: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

type AdminTenantModuleTogglePayload = {
  required_permission: unknown;
  module_setting: Record<string, unknown>;
  action_result?: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

type AdminImpersonationSessionPayload = {
  required_permission: unknown;
  impersonation_session: Record<string, unknown>;
  audit_event: Record<string, unknown>;
};

type AdminOperationsPayload = {
  tenant_scope: unknown;
  summary: Record<string, unknown>;
  material_parse_jobs: Record<string, unknown>;
  media_generation: Record<string, unknown>;
  speaking_attempts: Record<string, unknown>;
  provider_configuration: Record<string, unknown>;
  module_toggle_coverage: Record<string, unknown>;
  issues?: Array<Record<string, unknown>>;
};

type AdminTenantDetailPayload = {
  required_permission: unknown;
  tenant: Record<string, unknown>;
  summary: Record<string, unknown>;
  children?: Array<Record<string, unknown>>;
  materials?: Array<Record<string, unknown>>;
  provider_policy?: Record<string, unknown>;
  module_settings?: Array<Record<string, unknown>>;
  weekly_reports?: Record<string, unknown>;
  speaking_attempts?: Record<string, unknown>;
  risk_summary?: Record<string, unknown>;
  audit_event?: Record<string, unknown>;
  access_context?: AdminTenantAccessContextPayload;
};

type AdminAuditEventsPayload = {
  items?: Array<Record<string, unknown>>;
  next_cursor?: unknown;
};

type AdminImpersonationSessionsPayload = {
  required_permission: unknown;
  tenant_scope: unknown;
  status: unknown;
  items?: Array<Record<string, unknown>>;
  audit_event: Record<string, unknown>;
};

type EndAdminImpersonationSessionPayload = {
  required_permission: unknown;
  impersonation_session: Record<string, unknown>;
  action_result: Record<string, unknown>;
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

export async function loadAdminOperations(options: AdminTenantScopedOptions): Promise<AdminOperationsData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/operations?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      headers: { "X-Admin-Token": options.adminToken }
    }
  );
  if (!response.ok) {
    throw new Error(`Admin operations request failed: ${response.status}`);
  }
  return normalizeAdminOperationsPayload((await response.json()) as AdminOperationsPayload);
}

export async function loadAdminTenantDetail(options: AdminTenantDetailOptions): Promise<AdminTenantDetailData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/tenants/${encodeURIComponent(options.tenantId)}?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      headers: { "X-Admin-Token": options.adminToken }
    }
  );
  if (!response.ok) {
    throw new Error(`Admin tenant detail request failed: ${response.status}`);
  }
  return normalizeAdminTenantDetailPayload((await response.json()) as AdminTenantDetailPayload);
}

export async function loadAdminAuditEvents(options: AdminAuditEventsOptions): Promise<AdminAuditEventsData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const params = new URLSearchParams();
  params.set("tenant_scope", options.tenantScope);
  appendOptionalParam(params, "action", options.action);
  appendOptionalParam(params, "resource_type", options.resourceType);
  appendOptionalParam(params, "resource_id", options.resourceId);
  appendOptionalParam(params, "risk_level", options.riskLevel);
  appendOptionalParam(params, "result", options.result);
  appendOptionalParam(params, "actor_id", options.actorId);
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  appendOptionalParam(params, "cursor", options.cursor);
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/audit-events?${params.toString()}`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin audit events request failed: ${response.status}`);
  }
  return normalizeAdminAuditEventsPayload((await response.json()) as AdminAuditEventsPayload);
}

export async function loadAdminImpersonationSessions(
  options: AdminImpersonationSessionsOptions
): Promise<AdminImpersonationSessionsData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const params = new URLSearchParams();
  params.set("tenant_scope", options.tenantScope);
  params.set("status", options.status ?? "active");
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/impersonation-sessions?${params.toString()}`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin impersonation sessions request failed: ${response.status}`);
  }
  return normalizeAdminImpersonationSessionsPayload((await response.json()) as AdminImpersonationSessionsPayload);
}

export async function endAdminImpersonationSession(
  options: EndAdminImpersonationSessionOptions
): Promise<EndAdminImpersonationSessionResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/impersonation-sessions/${encodeURIComponent(options.sessionId)}/end?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
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
    throw new Error(`Admin impersonation session end request failed: ${response.status}`);
  }
  return normalizeEndAdminImpersonationSessionPayload((await response.json()) as EndAdminImpersonationSessionPayload);
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
  const payload = (await response.json().catch(() => undefined)) as AdminArchiveMaterialPayload | undefined;
  if (!response.ok) {
    if (payload?.action_result && payload.audit_event && payload.material) {
      return normalizeAdminArchiveMaterialPayload(payload);
    }
    throw new Error(`Admin retry material job request failed: ${response.status}`);
  }
  if (!payload) {
    throw new Error("Admin retry material job request returned an empty payload");
  }
  return normalizeAdminArchiveMaterialPayload(payload);
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

export async function toggleAdminTenantModule(
  options: ToggleAdminTenantModuleOptions
): Promise<AdminTenantModuleToggleResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/tenants/${encodeURIComponent(options.tenantId)}/modules/${encodeURIComponent(options.moduleKey)}?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": options.adminToken
      },
      body: JSON.stringify({
        enabled: options.enabled,
        reason: options.reason
      })
    }
  );
  if (!response.ok) {
    throw new Error(`Admin tenant module toggle request failed: ${response.status}`);
  }
  return normalizeAdminTenantModuleTogglePayload((await response.json()) as AdminTenantModuleTogglePayload);
}

export async function startAdminImpersonationSession(
  options: StartAdminImpersonationSessionOptions
): Promise<AdminImpersonationSessionResult> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${apiBaseUrl}/v1/admin/impersonation-sessions?tenant_scope=${encodeURIComponent(options.tenantScope)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": options.adminToken
      },
      body: JSON.stringify({
        tenant_id: options.tenantId,
        target_parent_id: options.targetParentId,
        reason: options.reason
      })
    }
  );
  if (!response.ok) {
    throw new Error(`Admin impersonation session request failed: ${response.status}`);
  }
  return normalizeAdminImpersonationSessionPayload((await response.json()) as AdminImpersonationSessionPayload);
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
    providerPolicies: payload.provider_policies.map((policy) => normalizeProviderPolicyPayload(policy)),
    moduleSettings: (payload.module_settings ?? []).map((setting) => normalizeTenantModuleSettingPayload(setting))
  };
}

export function normalizeAdminArchiveMaterialPayload(payload: AdminArchiveMaterialPayload): AdminArchiveMaterialResult {
  const actionResult = optionalActionResult(payload.action_result);
  return {
    requiredPermission: stringValue(payload.required_permission),
    material: normalizeAdminMaterialPayload(payload.material),
    ...(actionResult ? { actionResult } : {}),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminProviderPolicyOverridePayload(
  payload: AdminProviderPolicyOverridePayload
): AdminProviderPolicyOverrideResult {
  const actionResult = optionalActionResult(payload.action_result);
  return {
    requiredPermission: stringValue(payload.required_permission),
    providerPolicy: normalizeProviderPolicyPayload(payload.provider_policy),
    ...(actionResult ? { actionResult } : {}),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminTenantModuleTogglePayload(payload: AdminTenantModuleTogglePayload): AdminTenantModuleToggleResult {
  const actionResult = optionalActionResult(payload.action_result);
  return {
    requiredPermission: stringValue(payload.required_permission),
    moduleSetting: normalizeTenantModuleSettingPayload(payload.module_setting),
    ...(actionResult ? { actionResult } : {}),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminImpersonationSessionPayload(
  payload: AdminImpersonationSessionPayload
): AdminImpersonationSessionResult {
  return {
    requiredPermission: stringValue(payload.required_permission),
    impersonationSession: normalizeAdminImpersonationSession(payload.impersonation_session),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminOperationsPayload(payload: AdminOperationsPayload): AdminOperationsData {
  return {
    tenantScope: stringValue(payload.tenant_scope),
    summary: recordValue(payload.summary),
    materialParseJobs: recordValue(payload.material_parse_jobs),
    mediaGeneration: recordValue(payload.media_generation),
    speakingAttempts: recordValue(payload.speaking_attempts),
    providerConfiguration: recordValue(payload.provider_configuration),
    moduleToggleCoverage: recordValue(payload.module_toggle_coverage),
    issues: (payload.issues ?? []).map((issue) => normalizeAdminOperationsIssuePayload(issue))
  };
}

export function normalizeAdminTenantDetailPayload(payload: AdminTenantDetailPayload): AdminTenantDetailData {
  return {
    requiredPermission: stringValue(payload.required_permission),
    tenant: normalizeAdminTenantDetailTenant(payload.tenant),
    summary: recordValue(payload.summary),
    children: (payload.children ?? []).map((child) => normalizeAdminTenantChildPayload(child)),
    materials: (payload.materials ?? []).map((material) => normalizeAdminMaterialPayload(material)),
    providerPolicy: normalizeProviderPolicyPayload(payload.provider_policy ?? {}),
    moduleSettings: (payload.module_settings ?? []).map((setting) => normalizeTenantModuleSettingPayload(setting)),
    weeklyReports: recordValue(payload.weekly_reports),
    speakingAttempts: recordValue(payload.speaking_attempts),
    riskSummary: recordValue(payload.risk_summary),
    ...(payload.audit_event ? { auditEvent: normalizeAdminAuditEventPayload(payload.audit_event) } : {}),
    ...(payload.access_context ? { accessContext: normalizeAdminTenantAccessContextPayload(payload.access_context) } : {})
  };
}

export function normalizeAdminAuditEventsPayload(payload: AdminAuditEventsPayload): AdminAuditEventsData {
  return {
    items: (payload.items ?? []).map((event) => normalizeAdminAuditEventPayload(event)),
    nextCursor: stringValue(payload.next_cursor)
  };
}

export function normalizeAdminImpersonationSessionsPayload(
  payload: AdminImpersonationSessionsPayload
): AdminImpersonationSessionsData {
  return {
    requiredPermission: stringValue(payload.required_permission),
    tenantScope: stringValue(payload.tenant_scope),
    status: stringValue(payload.status) as AdminImpersonationSessionsData["status"],
    items: (payload.items ?? []).map((session) => normalizeAdminImpersonationSession(session)),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeEndAdminImpersonationSessionPayload(
  payload: EndAdminImpersonationSessionPayload
): EndAdminImpersonationSessionResult {
  return {
    requiredPermission: stringValue(payload.required_permission),
    impersonationSession: normalizeAdminImpersonationSession(payload.impersonation_session),
    actionResult: normalizeAdminActionResultPayload(payload.action_result),
    auditEvent: normalizeAdminAuditEventPayload(payload.audit_event)
  };
}

export function normalizeAdminAccessPayload(payload: AdminAccessPayload): AdminAccessData {
  return {
    currentAdmin: normalizeAdminAccessUserPayload(payload.current_admin),
    permissions: payload.permissions.map((item) => stringValue(item)).filter(Boolean),
    auditEvents: payload.audit_events.map((event) => normalizeAdminAuditEventPayload(event))
  };
}

function normalizeAdminTenantAccessContextPayload(
  payload: AdminTenantAccessContextPayload
): AdminTenantDetailData["accessContext"] {
  return {
    currentAdmin: normalizeAdminAccessUserPayload(recordValue(payload.current_admin)),
    recentAuditEvents: (payload.recent_audit_events ?? []).map((event) => normalizeAdminAuditEventPayload(event))
  };
}

function normalizeAdminAccessUserPayload(payload: Record<string, unknown>): AdminAccessUser {
  return {
    id: stringValue(payload.id),
    displayName: stringValue(payload.display_name),
    email: stringValue(payload.email),
    role: stringValue(payload.role),
    status: stringValue(payload.status)
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
    warnings: stringArrayValue(material.warnings)
  };
}

function normalizeAdminOperationsIssuePayload(issue: Record<string, unknown>): AdminOperationsIssue {
  const relatedResource = recordValue(issue.related_resource);
  return {
    id: stringValue(issue.id),
    severity: stringValue(issue.severity) as AdminOperationsIssue["severity"],
    statusLabel: stringValue(issue.status_label),
    reason: stringValue(issue.reason),
    recommendedAction: stringValue(issue.recommended_action),
    requiredPermission: optionalStringValue(issue.required_permission),
    relatedResource: {
      type: stringValue(relatedResource.type),
      id: stringValue(relatedResource.id),
      tenantId: optionalStringValue(relatedResource.tenant_id),
      materialId: optionalStringValue(relatedResource.material_id),
      childId: optionalStringValue(relatedResource.child_id)
    },
    source: stringValue(issue.source) as AdminOperationsIssue["source"]
  };
}

function normalizeAdminTenantDetailTenant(tenant: Record<string, unknown>): AdminTenantDetailTenant {
  return {
    id: stringValue(tenant.id),
    name: stringValue(tenant.name),
    tenantType: stringValue(tenant.tenant_type) as Tenant["tenantType"],
    status: stringValue(tenant.status) as Tenant["status"],
    region: stringValue(tenant.region),
    ownerContact: stringValue(tenant.owner_contact) || stringValue(tenant.phone_number),
    tier: stringValue(tenant.tier),
    createdAt: stringValue(tenant.created_at),
    activeParents: numberValue(tenant.active_parents),
    children: numberValue(tenant.children),
    displayName: stringValue(tenant.display_name),
    avatarUrl: stringValue(tenant.avatar_url),
    phoneNumber: stringValue(tenant.phone_number),
    phoneVerifiedAt: stringValue(tenant.phone_verified_at),
    wechatUnionId: stringValue(tenant.wechat_union_id),
    wechatOpenId: stringValue(tenant.wechat_open_id),
    updatedAt: stringValue(tenant.updated_at)
  };
}

function normalizeAdminTenantChildPayload(child: Record<string, unknown>): AdminTenantChild {
  return {
    id: stringValue(child.id),
    name: stringValue(child.name),
    age: numberValue(child.age),
    level: stringValue(child.level),
    learningGoal: stringValue(child.learning_goal),
    preferredReviewDurationMinutes: numberValue(child.preferred_review_duration_minutes),
    parentNotes: stringValue(child.parent_notes),
    latestWeeklyReportId: stringValue(child.latest_weekly_report_id),
    speakingAttempts: numberValue(child.speaking_attempts)
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

function normalizeAdminImpersonationSession(session: Record<string, unknown>): AdminImpersonationSession {
  return {
    id: stringValue(session.id),
    tenantId: stringValue(session.tenant_id),
    targetParentId: stringValue(session.target_parent_id),
    actorId: stringValue(session.actor_id),
    status: stringValue(session.status) as AdminImpersonationSession["status"],
    reason: stringValue(session.reason),
    expiresAt: stringValue(session.expires_at),
    createdAt: stringValue(session.created_at),
    endedAt: stringValue(session.ended_at),
    updatedAt: stringValue(session.updated_at),
    tenantDisplayName: stringValue(session.tenant_display_name),
    targetParentDisplayName: stringValue(session.target_parent_display_name)
  };
}

function normalizeAdminActionResultPayload(payload: Record<string, unknown>): AdminActionResult {
  return {
    action: stringValue(payload.action),
    status: stringValue(payload.status) as AdminActionResult["status"],
    resourceType: stringValue(payload.resource_type),
    resourceId: stringValue(payload.resource_id),
    tenantId: stringValue(payload.tenant_id),
    message: stringValue(payload.message)
  };
}

function optionalActionResult(payload: Record<string, unknown> | undefined): AdminActionResult | undefined {
  return payload ? normalizeAdminActionResultPayload(payload) : undefined;
}

function normalizeTenantModuleSettingPayload(setting: Record<string, unknown>): TenantModuleSetting {
  return {
    tenantId: stringValue(setting.tenant_id),
    moduleKey: stringValue(setting.module_key) as ModuleKey,
    enabled: booleanValue(setting.enabled),
    source: stringValue(setting.source) as TenantModuleSetting["source"]
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

function booleanValue(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function recordValue(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function arrayValue(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => item !== null && typeof item === "object") : [];
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => stringValue(item)).filter(Boolean) : [];
}

function appendOptionalParam(params: URLSearchParams, key: string, value: string | undefined): void {
  if (value) {
    params.set(key, value);
  }
}

export interface AdminLearningAssetsData {
  tenantScope: string;
  items: AdminLearningAsset[];
  total: number;
}

interface AdminLearningAssetsOptions extends AdminTenantScopedOptions {
  materialId?: string;
  mediaStatus?: string;
  limit?: number;
}

type AdminLearningAssetsPayload = {
  tenant_scope?: unknown;
  items?: Array<Record<string, unknown>>;
  total?: unknown;
};

export async function loadAdminLearningAssets(options: AdminLearningAssetsOptions): Promise<AdminLearningAssetsData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const params = new URLSearchParams();
  params.set("tenant_scope", options.tenantScope);
  appendOptionalParam(params, "material_id", options.materialId);
  appendOptionalParam(params, "media_status", options.mediaStatus);
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/learning-assets?${params.toString()}`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin learning assets request failed: ${response.status}`);
  }
  return normalizeAdminLearningAssetsPayload((await response.json()) as AdminLearningAssetsPayload);
}

export function normalizeAdminLearningAssetsPayload(payload: AdminLearningAssetsPayload): AdminLearningAssetsData {
  return {
    tenantScope: stringValue(payload.tenant_scope),
    items: (payload.items ?? []).map((item) => normalizeAdminLearningAssetPayload(item)),
    total: numberValue(payload.total)
  };
}

function normalizeAdminLearningAssetPayload(asset: Record<string, unknown>): AdminLearningAsset {
  return {
    id: stringValue(asset.id),
    materialId: stringValue(asset.material_id),
    materialTitle: stringValue(asset.material_title),
    materialStatus: stringValue(asset.material_status) as MaterialStatus,
    tenantId: stringValue(asset.tenant_id),
    parentName: stringValue(asset.parent_name),
    childName: stringValue(asset.child_name),
    text: stringValue(asset.text),
    kind: stringValue(asset.kind),
    translation: stringValue(asset.translation),
    primaryAccent: stringValue(asset.primary_accent),
    mediaStatus: stringValue(asset.media_status) as MediaStatus,
    generatedImageStatus: stringValue(asset.generated_image_status),
    generatedImageUrl: stringValue(asset.generated_image_url),
    ttsUsStatus: stringValue(asset.tts_us_status),
    ttsUsUrl: stringValue(asset.tts_us_url),
    ttsUkStatus: stringValue(asset.tts_uk_status),
    ttsUkUrl: stringValue(asset.tts_uk_url),
    updatedAt: stringValue(asset.updated_at)
  };
}

export interface AdminUsersData {
  tenantScope: string;
  items: AdminUserAccount[];
  total: number;
}

interface AdminUsersOptions extends AdminTenantScopedOptions {
  level?: string;
  limit?: number;
}

type AdminUsersPayload = {
  tenant_scope?: unknown;
  items?: Array<Record<string, unknown>>;
  total?: unknown;
};

export async function loadAdminUsers(options: AdminUsersOptions): Promise<AdminUsersData> {
  const apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const params = new URLSearchParams();
  params.set("tenant_scope", options.tenantScope);
  appendOptionalParam(params, "level", options.level);
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  const response = await fetchImpl(`${apiBaseUrl}/v1/admin/users?${params.toString()}`, {
    headers: { "X-Admin-Token": options.adminToken }
  });
  if (!response.ok) {
    throw new Error(`Admin users request failed: ${response.status}`);
  }
  return normalizeAdminUsersPayload((await response.json()) as AdminUsersPayload);
}

export function normalizeAdminUsersPayload(payload: AdminUsersPayload): AdminUsersData {
  return {
    tenantScope: stringValue(payload.tenant_scope),
    items: (payload.items ?? []).map((item) => normalizeAdminUserAccountPayload(item)),
    total: numberValue(payload.total)
  };
}

function normalizeAdminUserAccountPayload(row: Record<string, unknown>): AdminUserAccount {
  return {
    childId: stringValue(row.child_id),
    childName: stringValue(row.child_name),
    age: numberValue(row.age),
    level: stringValue(row.level),
    learningGoal: stringValue(row.learning_goal),
    preferredReviewDurationMinutes: numberValue(row.preferred_review_duration_minutes),
    parentNotes: stringValue(row.parent_notes),
    tenantId: stringValue(row.tenant_id),
    parentName: stringValue(row.parent_name),
    materialsCount: numberValue(row.materials_count),
    speakingAttempts: numberValue(row.speaking_attempts),
    latestWeeklyReportId: stringValue(row.latest_weekly_report_id),
    createdAt: stringValue(row.created_at)
  };
}
