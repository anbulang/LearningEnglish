import { useEffect, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { ConfirmProvider, ThemeProvider, ToastProvider } from "./components/providers";
import {
  archiveAdminMaterial,
  endAdminImpersonationSession,
  loadAdminAccess,
  loadAdminAuditEvents,
  loadAdminDashboard,
  loadAdminImpersonationSessions,
  loadAdminLearningAssets,
  loadAdminLearningOutcomes,
  loadAdminOperations,
  loadAdminTenantDetail,
  loadAdminUsers,
  overrideAdminProviderPolicy,
  retryAdminMaterialJob,
  startAdminImpersonationSession,
  toggleAdminTenantModule,
  type AdminAccessData,
  type AdminDashboardData,
  type AdminLearningAssetsData,
  type AdminUsersData
} from "./domain/adminApi";
import {
  mockLearningAssets,
  mockMaterials,
  mockModuleSettings,
  mockOperationsData,
  mockProviderPolicies,
  mockTenants,
  mockUsers
} from "./domain/mockData";
import type {
  AdminAuditEvent,
  AdminAuditEventsData,
  AdminImpersonationSessionsData,
  AdminLearningOutcomesData,
  AdminOperationsData,
  AdminOperationsIssue,
  Language,
  ModuleKey,
  TenantScope
} from "./domain/types";
import { type AuditEventFilters, type ImpersonationInput, type ProviderPolicyOverrideInput } from "./pages/contracts";
import { AuditAccess } from "./pages/AuditAccess";
import { CommandCenter } from "./pages/CommandCenter";
import { ContentPipeline } from "./pages/ContentPipeline";
import { CostToken } from "./pages/CostToken";
import { Infrastructure } from "./pages/Infrastructure";
import { LearningAssets } from "./pages/LearningAssets";
import { LearningOutcomes } from "./pages/LearningOutcomes";
import { ProviderOps } from "./pages/ProviderOps";
import { Tenants } from "./pages/Tenants";
import { UsersChildren } from "./pages/UsersChildren";

function prependAuditEvent(events: AdminAuditEvent[], auditEvent: AdminAuditEvent): AdminAuditEvent[] {
  return [auditEvent, ...events.filter((event) => event.id !== auditEvent.id)];
}

function pruneOperationIssues(
  current: AdminOperationsData | null,
  matches: (issue: AdminOperationsIssue) => boolean
): AdminOperationsData | null {
  return current ? { ...current, issues: current.issues.filter((issue) => !matches(issue)) } : current;
}

function apiConfig(): { apiBaseUrl: string; adminToken: string } | null {
  const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
  if (!apiBaseUrl || typeof fetch === "undefined") {
    return null;
  }
  const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
  return { apiBaseUrl, adminToken };
}

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const [dataMode, setDataMode] = useState<"mock" | "live">("mock");
  const [dashboardData, setDashboardData] = useState<AdminDashboardData>({
    tenants: mockTenants,
    materials: mockMaterials,
    providerPolicies: mockProviderPolicies,
    moduleSettings: mockModuleSettings
  });
  const [operationsData, setOperationsData] = useState<AdminOperationsData | null>(mockOperationsData);
  const [auditEventsPage, setAuditEventsPage] = useState<AdminAuditEventsData | null>(null);
  const [impersonationSessions, setImpersonationSessions] = useState<AdminImpersonationSessionsData | null>(null);
  const [accessData, setAccessData] = useState<AdminAccessData | null>(null);
  const [learningAssetsData, setLearningAssetsData] = useState<AdminLearningAssetsData>({
    tenantScope: "all",
    items: mockLearningAssets,
    total: mockLearningAssets.length
  });
  const [usersData, setUsersData] = useState<AdminUsersData>({
    tenantScope: "all",
    items: mockUsers,
    total: mockUsers.length
  });
  const [learningOutcomesData, setLearningOutcomesData] = useState<AdminLearningOutcomesData | null>(null);

  const live = dataMode === "live";

  // Bootstrap: dashboard (flips to live mode) + access permissions.
  useEffect(() => {
    const config = apiConfig();
    if (!config) {
      return;
    }
    let isCancelled = false;
    void (async () => {
      try {
        const data = await loadAdminDashboard(config);
        if (isCancelled) {
          return;
        }
        setDashboardData(data);
        setDataMode("live");
        setTenantScope((current) =>
          current === "all" || data.tenants.some((tenant) => tenant.id === current) ? current : "all"
        );
      } catch {
        if (!isCancelled) {
          setDataMode("mock");
          setAccessData(null);
        }
        return;
      }
      try {
        const access = await loadAdminAccess(config);
        if (!isCancelled) {
          setAccessData(access);
        }
      } catch {
        if (!isCancelled) {
          setAccessData(null);
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, []);

  // Operations snapshot, refreshed on scope change.
  useEffect(() => {
    const config = apiConfig();
    if (!config) {
      setOperationsData(mockOperationsData);
      return;
    }
    let isCancelled = false;
    setOperationsData(null);
    void (async () => {
      try {
        const operations = await loadAdminOperations({ ...config, tenantScope });
        if (!isCancelled) {
          setOperationsData(operations);
        }
      } catch {
        if (!isCancelled) {
          setOperationsData(null);
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [tenantScope]);

  // Audit + impersonation sessions, loaded when the audit screen is active.
  useEffect(() => {
    setAuditEventsPage(null);
    setImpersonationSessions(null);
    if (activePage !== "audit") {
      return;
    }
    const config = apiConfig();
    if (!config) {
      return;
    }
    let isCancelled = false;
    void (async () => {
      const auditRequest = loadAdminAuditEvents({ ...config, tenantScope, limit: 25 })
        .then((page) => !isCancelled && setAuditEventsPage(page))
        .catch(() => !isCancelled && setAuditEventsPage(null));
      const sessionsRequest = loadAdminImpersonationSessions({ ...config, tenantScope, status: "all" })
        .then((sessions) => !isCancelled && setImpersonationSessions(sessions))
        .catch(() => !isCancelled && setImpersonationSessions(null));
      await Promise.all([auditRequest, sessionsRequest]);
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, tenantScope]);

  // Learning assets, loaded when the assets screen is active.
  useEffect(() => {
    if (activePage !== "assets") {
      return;
    }
    const config = apiConfig();
    if (!config) {
      return;
    }
    let isCancelled = false;
    void (async () => {
      try {
        const assets = await loadAdminLearningAssets({ ...config, tenantScope });
        if (!isCancelled) {
          setLearningAssetsData(assets);
        }
      } catch {
        if (!isCancelled) {
          setLearningAssetsData({ tenantScope, items: [], total: 0 });
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, tenantScope]);

  // Learning outcomes trend, loaded when the outcomes screen is active.
  useEffect(() => {
    if (activePage !== "outcomes") {
      return;
    }
    const config = apiConfig();
    if (!config) {
      return;
    }
    let isCancelled = false;
    void (async () => {
      try {
        const outcomes = await loadAdminLearningOutcomes({ ...config, tenantScope, weeks: 8 });
        if (!isCancelled) {
          setLearningOutcomesData(outcomes);
        }
      } catch {
        if (!isCancelled) {
          setLearningOutcomesData(null);
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, tenantScope]);

  // Users, loaded when the users screen is active.
  useEffect(() => {
    if (activePage !== "users") {
      return;
    }
    const config = apiConfig();
    if (!config) {
      return;
    }
    let isCancelled = false;
    void (async () => {
      try {
        const users = await loadAdminUsers({ ...config, tenantScope });
        if (!isCancelled) {
          setUsersData(users);
        }
      } catch {
        if (!isCancelled) {
          setUsersData({ tenantScope, items: [], total: 0 });
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, tenantScope]);

  async function handleArchiveMaterial(materialId: string, reason: string) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin archive API is not configured");
    }
    const result = await archiveAdminMaterial({ ...config, tenantScope, materialId, reason });
    setDashboardData((current) => ({
      ...current,
      materials: current.materials.map((material) => (material.id === result.material.id ? result.material : material))
    }));
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    setOperationsData((current) =>
      pruneOperationIssues(
        current,
        (issue) => issue.relatedResource.id === result.material.id || issue.relatedResource.materialId === result.material.id
      )
    );
  }

  async function handleRetryMaterialJob(jobId: string, reason: string) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin retry API is not configured");
    }
    const result = await retryAdminMaterialJob({ ...config, tenantScope, jobId, reason });
    setDashboardData((current) => ({
      ...current,
      materials: current.materials.map((material) => (material.id === result.material.id ? result.material : material))
    }));
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    if (result.actionResult?.status === "failed") {
      throw new Error(result.actionResult.message || "Material retry action failed");
    }
    setOperationsData((current) =>
      pruneOperationIssues(
        current,
        (issue) => issue.relatedResource.id === jobId || issue.relatedResource.materialId === result.material.id
      )
    );
  }

  async function handleSubmitOperationIssueAction(issue: AdminOperationsIssue, reason: string) {
    if (issue.recommendedAction === "retry_material_job" && issue.relatedResource.type === "material_parse_job") {
      await handleRetryMaterialJob(issue.relatedResource.id, reason);
      return;
    }
    if (issue.recommendedAction === "archive_material") {
      await handleArchiveMaterial(issue.relatedResource.materialId ?? issue.relatedResource.id, reason);
      return;
    }
    throw new Error(`Unsupported admin operation action: ${issue.recommendedAction}`);
  }

  async function handleLoadAuditEvents(filters: AuditEventFilters) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin audit API is not configured");
    }
    const result = await loadAdminAuditEvents({
      ...config,
      tenantScope: filters.tenantScope,
      actorId: filters.actorId,
      action: filters.action,
      resourceType: filters.resourceType,
      resourceId: filters.resourceId,
      riskLevel: filters.riskLevel,
      result: filters.result,
      cursor: filters.cursor,
      limit: 25
    });
    setAuditEventsPage(result);
    return result;
  }

  async function handleStartImpersonation(input: ImpersonationInput) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin impersonation API is not configured");
    }
    const result = await startAdminImpersonationSession({
      ...config,
      tenantScope,
      tenantId: input.tenantId,
      targetParentId: input.targetParentId,
      reason: input.reason
    });
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    setImpersonationSessions((current) =>
      current
        ? {
            ...current,
            items: [result.impersonationSession, ...current.items.filter((session) => session.id !== result.impersonationSession.id)],
            auditEvent: result.auditEvent
          }
        : current
    );
  }

  async function handleEndImpersonationSession(sessionId: string, reason: string) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin impersonation API is not configured");
    }
    const result = await endAdminImpersonationSession({ ...config, tenantScope, sessionId, reason });
    setImpersonationSessions((current) =>
      current
        ? {
            ...current,
            items: current.items.map((session) => {
              if (session.id !== result.impersonationSession.id) {
                return session;
              }
              return result.actionResult.status === "noop" ? session : result.impersonationSession;
            }),
            auditEvent: result.auditEvent
          }
        : current
    );
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    return result;
  }

  async function handleToggleTenantModule(tenantId: string, moduleKey: ModuleKey, enabled: boolean, reason: string) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin tenant module API is not configured");
    }
    const result = await toggleAdminTenantModule({ ...config, tenantScope, tenantId, moduleKey, enabled, reason });
    setDashboardData((current) => {
      const exists = current.moduleSettings.some(
        (setting) => setting.tenantId === result.moduleSetting.tenantId && setting.moduleKey === result.moduleSetting.moduleKey
      );
      return {
        ...current,
        moduleSettings: exists
          ? current.moduleSettings.map((setting) =>
              setting.tenantId === result.moduleSetting.tenantId && setting.moduleKey === result.moduleSetting.moduleKey
                ? result.moduleSetting
                : setting
            )
          : [...current.moduleSettings, result.moduleSetting]
      };
    });
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    if (result.actionResult?.status === "failed") {
      throw new Error(result.actionResult.message || "Tenant module toggle failed");
    }
  }

  async function handleLoadTenantDetail(tenantId: string) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin tenant detail API is not configured");
    }
    return loadAdminTenantDetail({ ...config, tenantScope, tenantId });
  }

  async function handleOverrideProviderPolicy(input: ProviderPolicyOverrideInput) {
    const config = apiConfig();
    if (!config) {
      throw new Error("Admin provider policy API is not configured");
    }
    const result = await overrideAdminProviderPolicy({
      ...config,
      tenantScope,
      tenantId: input.tenantId,
      aiProvider: input.aiProvider,
      mediaProvider: input.mediaProvider,
      fallbackMode: input.fallbackMode,
      monthlyGuardrail: input.monthlyGuardrail,
      reason: input.reason
    });
    setDashboardData((current) => {
      const exists = current.providerPolicies.some((policy) => policy.tenantId === result.providerPolicy.tenantId);
      return {
        ...current,
        providerPolicies: exists
          ? current.providerPolicies.map((policy) =>
              policy.tenantId === result.providerPolicy.tenantId ? result.providerPolicy : policy
            )
          : [...current.providerPolicies, result.providerPolicy]
      };
    });
    setAccessData((current) => (current ? { ...current, auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent) } : current));
    setAuditEventsPage((current) => (current ? { ...current, items: prependAuditEvent(current.items, result.auditEvent) } : current));
    if (result.actionResult?.status === "failed") {
      throw new Error(result.actionResult.message || "Provider policy override failed");
    }
  }

  return (
    <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <AppShell
            activePage={activePage}
            language={language}
            tenantScope={tenantScope}
            tenants={dashboardData.tenants}
            dataMode={dataMode}
            onLanguageChange={setLanguage}
            onTenantScopeChange={setTenantScope}
            onPageChange={setActivePage}
          >
            {activePage === "command" && (
              <CommandCenter
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                operations={live ? operationsData : null}
                permissions={accessData?.permissions ?? []}
                onIssueAction={
                  live && operationsData?.tenantScope === tenantScope ? handleSubmitOperationIssueAction : undefined
                }
                onNavigate={setActivePage}
              />
            )}
            {activePage === "tenants" && (
              <Tenants
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                liveTenants={live ? dashboardData.tenants : null}
                materials={live ? dashboardData.materials : []}
                moduleSettings={live ? dashboardData.moduleSettings : []}
                onToggleModule={live ? handleToggleTenantModule : undefined}
                onLoadTenantDetail={live ? handleLoadTenantDetail : undefined}
              />
            )}
            {activePage === "pipeline" && (
              <ContentPipeline
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                materials={live ? dashboardData.materials : []}
                onRetryJob={live ? handleRetryMaterialJob : undefined}
              />
            )}
            {activePage === "assets" && (
              <LearningAssets
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                liveAssets={live ? learningAssetsData.items : null}
              />
            )}
            {activePage === "outcomes" && (
              <LearningOutcomes
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                data={live ? learningOutcomesData : null}
              />
            )}
            {activePage === "users" && (
              <UsersChildren
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                liveUsers={live ? usersData.items : null}
                onStartImpersonation={live ? handleStartImpersonation : undefined}
              />
            )}
            {activePage === "providers" && (
              <ProviderOps
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                providerPolicies={live ? dashboardData.providerPolicies : []}
                liveTenants={live ? dashboardData.tenants : null}
                onOverridePolicy={live ? handleOverrideProviderPolicy : undefined}
              />
            )}
            {activePage === "cost" && (
              <CostToken language={language} tenantScope={tenantScope} dataMode={dataMode} />
            )}
            {activePage === "infrastructure" && (
              <Infrastructure
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                operations={live ? operationsData : null}
              />
            )}
            {activePage === "audit" && (
              <AuditAccess
                language={language}
                tenantScope={tenantScope}
                dataMode={dataMode}
                accessData={accessData}
                auditEventsPage={auditEventsPage}
                impersonationSessions={impersonationSessions}
                onLoadAuditEvents={live ? handleLoadAuditEvents : undefined}
                onStartImpersonation={live ? handleStartImpersonation : undefined}
                onEndImpersonationSession={live ? handleEndImpersonationSession : undefined}
              />
            )}
          </AppShell>
        </ConfirmProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
