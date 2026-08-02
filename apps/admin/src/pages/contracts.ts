/*
 * Prop contracts for the 10 console screens. Single source of truth shared by
 * App.tsx (which supplies the props) and each page (which consumes them).
 *
 * Every page is mock-first: it renders the design's Console* view models from
 * mock seeds by default, and overlays live `/v1/admin` data when `dataMode` is
 * "live" and the corresponding live prop is non-null.
 */
import type { PageKey } from "../components/AppShell";
import type { AdminAccessData } from "../domain/adminApi";
import type {
  AdminAuditEventsData,
  AdminImpersonationSession,
  AdminImpersonationSessionsData,
  AdminLearningAsset,
  AdminLearningOutcomesData,
  AdminMaterial,
  AdminOperationsData,
  AdminOperationsIssue,
  AdminTenantDetailData,
  AdminUserAccount,
  AIProvider,
  EndAdminImpersonationSessionResult,
  Language,
  ModuleKey,
  ProviderPolicy,
  Tenant,
  TenantModuleSetting,
  TenantScope
} from "../domain/types";

export interface BasePageProps {
  language: Language;
  tenantScope: TenantScope;
  dataMode: "mock" | "live";
}

export interface CommandCenterProps extends BasePageProps {
  operations: AdminOperationsData | null;
  permissions: string[];
  onIssueAction?: (issue: AdminOperationsIssue, reason: string) => Promise<void>;
  onNavigate: (page: PageKey) => void;
}

export interface TenantsProps extends BasePageProps {
  liveTenants: Tenant[] | null;
  materials: AdminMaterial[];
  /** Per-tenant module settings from the live dashboard (empty in mock mode). */
  moduleSettings: TenantModuleSetting[];
  /** Live module enable/disable — POST /v1/admin/tenants/{id}/modules/{key}. */
  onToggleModule?: (tenantId: string, moduleKey: ModuleKey, enabled: boolean, reason: string) => Promise<void>;
  /** Live tenant deep-dive — GET /v1/admin/tenants/{id}. */
  onLoadTenantDetail?: (tenantId: string) => Promise<AdminTenantDetailData>;
}

export interface ContentPipelineProps extends BasePageProps {
  materials: AdminMaterial[];
  onRetryJob?: (jobId: string, reason: string) => Promise<void>;
}

export interface LearningAssetsProps extends BasePageProps {
  liveAssets: AdminLearningAsset[] | null;
}

export interface LearningOutcomesProps extends BasePageProps {
  /** Live multi-week trend from GET /v1/admin/learning-outcomes (null in mock mode). */
  data: AdminLearningOutcomesData | null;
}

export interface ImpersonationInput {
  tenantId: string;
  targetParentId: string;
  reason: string;
}

export interface UsersChildrenProps extends BasePageProps {
  liveUsers: AdminUserAccount[] | null;
  onStartImpersonation?: (input: ImpersonationInput) => Promise<void>;
}

export interface ProviderPolicyOverrideInput {
  tenantId: string;
  aiProvider: AIProvider;
  mediaProvider: ProviderPolicy["mediaProvider"];
  fallbackMode: ProviderPolicy["fallbackMode"];
  monthlyGuardrail: number;
  reason: string;
}

// Provider Ops: the connector CRUD (endpoint/apiKey/model/add/delete/self-check)
// is a prototype with no backend. The one real capability is a per-tenant
// provider *policy* override (ai/media provider, fallback, monthly guardrail) —
// read via `providerPolicies`, written via `onOverridePolicy`.
export interface ProviderOpsProps extends BasePageProps {
  /** Live provider policies from the dashboard (global default + tenant overrides). */
  providerPolicies: ProviderPolicy[];
  /** Live tenant list, for choosing the override target (null in mock mode). */
  liveTenants: Tenant[] | null;
  /** Live policy override — POST /v1/admin/providers/policies. */
  onOverridePolicy?: (input: ProviderPolicyOverrideInput) => Promise<void>;
}

export type CostTokenProps = BasePageProps;

export interface InfrastructureProps extends BasePageProps {
  operations: AdminOperationsData | null;
}

export interface AuditEventFilters {
  tenantScope: TenantScope;
  actorId?: string;
  action?: string;
  resourceType?: string;
  resourceId?: string;
  riskLevel?: string;
  result?: string;
  cursor?: string;
}

export interface AuditAccessProps extends BasePageProps {
  accessData: AdminAccessData | null;
  auditEventsPage: AdminAuditEventsData | null;
  impersonationSessions: AdminImpersonationSessionsData | null;
  onLoadAuditEvents?: (filters: AuditEventFilters) => Promise<AdminAuditEventsData>;
  onStartImpersonation?: (input: ImpersonationInput) => Promise<void>;
  onEndImpersonationSession?: (sessionId: string, reason: string) => Promise<EndAdminImpersonationSessionResult>;
}

export type { AdminImpersonationSession };
