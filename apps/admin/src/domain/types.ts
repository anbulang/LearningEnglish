export type Language = "zh" | "en";
export type TenantScope = "all" | string;

export type TenantType = "school" | "organization" | "pilot_family" | "internal";
export type TenantStatus = "active" | "warning" | "suspended";

export interface Tenant {
  id: string;
  name: string;
  tenantType: TenantType;
  status: TenantStatus;
  region: string;
  ownerContact: string;
  tier: string;
  createdAt: string;
  activeParents: number;
  children: number;
}

export type MaterialStatus = "uploaded" | "processing" | "needs_review" | "ready" | "failed" | "archived";
export type JobStatus = "queued" | "processing" | "needs_review" | "ready" | "failed";
export type MediaStatus = "pending" | "processing" | "ready" | "failed";

export interface SourcePage {
  pageIndex: number;
  thumbnailUrl: string;
  sourceType: "camera" | "gallery";
}

export interface AdminMaterial {
  id: string;
  tenantId: string;
  parentName: string;
  childName: string;
  childAge: number;
  title: string;
  pageCount: number;
  jobId: string;
  confidenceSummary: string;
  ocrConfidence: number;
  sourcePages: SourcePage[];
  materialStatus: MaterialStatus;
  jobStatus: JobStatus;
  provider: "stub" | "doubao";
  learningAssets: number;
  mediaStatus: MediaStatus;
  slaMinutes: number;
  updatedAt: string;
  warnings: string[];
}

export interface ProviderPolicy {
  tenantId: "global" | string;
  tier?: string;
  aiProvider: "stub" | "doubao";
  mediaProvider: "mock" | "real";
  fallbackMode: "global_stub" | "auto_to_mock" | "per_tenant";
  monthlyGuardrail: number;
  source: "global_default" | "tenant_override" | "tier_default" | "emergency_global";
}

export type ModuleKey = "worksheet_import" | "ai_review" | "media_pipeline" | "speaking_score" | "weekly_reports";

export interface TenantModuleSetting {
  tenantId: string;
  moduleKey: ModuleKey;
  enabled: boolean;
  source: "global_default" | "tenant_override";
}

export interface TenantHealthRow {
  tenant: Tenant;
  blockedJobs: number;
  mediaFailures: number;
  healthScore: number;
}

export interface LifecycleCounts {
  upload: number;
  parse: number;
  parentReview: number;
  knowledgePack: number;
  media: number;
  ready: number;
  failed: number;
}

export interface AdminUser {
  id: string;
  name: string;
  role: "Platform Owner" | "Support Admin" | "Content QA" | "Provider Operator" | "Read-only Auditor";
}

export interface AdminAccessUser {
  id: string;
  displayName: string;
  email: string;
  role: string;
  status: string;
}

export interface AdminAuditEvent {
  id: string;
  actorId: string;
  actorRole: string;
  tenantScope: string;
  action: string;
  resourceType: string;
  resourceId: string;
  riskLevel: "low" | "medium" | "high";
  result: "success" | "failed";
  reason: string;
  traceId: string;
  createdAt: string;
}
