import type { AdminMaterial, JobStatus, MediaStatus, ProviderPolicy, Tenant, MaterialStatus } from "./types";

export interface AdminDashboardData {
  tenants: Tenant[];
  materials: AdminMaterial[];
  providerPolicies: ProviderPolicy[];
}

interface LoadAdminDashboardOptions {
  apiBaseUrl: string;
  adminToken: string;
  fetchImpl?: typeof fetch;
}

type AdminDashboardPayload = {
  tenants: Array<Record<string, unknown>>;
  materials: Array<Record<string, unknown>>;
  provider_policies: Array<Record<string, unknown>>;
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
    materials: payload.materials.map((material) => ({
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
    })),
    providerPolicies: payload.provider_policies.map((policy) => ({
      tenantId: stringValue(policy.tenant_id),
      tier: optionalStringValue(policy.tier),
      aiProvider: stringValue(policy.ai_provider) as ProviderPolicy["aiProvider"],
      mediaProvider: stringValue(policy.media_provider) as ProviderPolicy["mediaProvider"],
      fallbackMode: stringValue(policy.fallback_mode) as ProviderPolicy["fallbackMode"],
      monthlyGuardrail: numberValue(policy.monthly_guardrail),
      source: stringValue(policy.source) as ProviderPolicy["source"]
    }))
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
