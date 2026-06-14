import { useEffect, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import {
  archiveAdminMaterial,
  endAdminImpersonationSession,
  loadAdminAccess,
  loadAdminAuditEvents,
  loadAdminDashboard,
  loadAdminImpersonationSessions,
  loadAdminLearningAssets,
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
  AdminOperationsData,
  AdminOperationsIssue,
  AdminTenantDetailData,
  Language,
  TenantScope
} from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import type { MessageKey } from "./i18n/messages";
import { AuditAccess, type AuditEventFilters } from "./pages/AuditAccess";
import { CommandCenter } from "./pages/CommandCenter";
import { ContentPipeline } from "./pages/ContentPipeline";
import { LearningAssets } from "./pages/LearningAssets";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { UsersChildren } from "./pages/UsersChildren";
import { ProviderOps, type ProviderPolicyOverrideInput } from "./pages/ProviderOps";
import { TenantDetail, type TenantModuleToggleInput } from "./pages/TenantDetail";

const pageTitles: Record<PageKey, MessageKey> = {
  command: "page.commandCenter.title",
  tenants: "page.tenantDetail.title",
  users: "page.usersChildren.title",
  pipeline: "page.contentPipeline.title",
  assets: "page.learningAssets.title",
  outcomes: "page.learningOutcomes.title",
  providers: "page.providerOps.title",
  infrastructure: "page.infrastructure.title",
  audit: "page.auditAccess.title",
  developer: "page.developerApi.title"
};

function prependAuditEvent(events: AdminAuditEvent[], auditEvent: AdminAuditEvent): AdminAuditEvent[] {
  return [auditEvent, ...events.filter((event) => event.id !== auditEvent.id)];
}

function pruneOperationIssues(
  current: AdminOperationsData | null,
  matches: (issue: AdminOperationsIssue) => boolean
): AdminOperationsData | null {
  return current
    ? {
        ...current,
        issues: current.issues.filter((issue) => !matches(issue))
      }
    : current;
}

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const [dashboardData, setDashboardData] = useState<AdminDashboardData>({
    tenants: mockTenants,
    materials: mockMaterials,
    providerPolicies: mockProviderPolicies,
    moduleSettings: mockModuleSettings
  });
  const [operationsData, setOperationsData] = useState<AdminOperationsData | null>(mockOperationsData);
  const [tenantDetailData, setTenantDetailData] = useState<AdminTenantDetailData | null>(null);
  const [auditEventsPage, setAuditEventsPage] = useState<AdminAuditEventsData | null>(null);
  const [impersonationSessions, setImpersonationSessions] = useState<AdminImpersonationSessionsData | null>(null);
  const [accessData, setAccessData] = useState<AdminAccessData | null>(null);
  const [dataMode, setDataMode] = useState<"mock" | "live">("mock");
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
  const t = createTranslator(language);
  const selectedTenantId = tenantScope === "all" ? dashboardData.tenants[0]?.id ?? "" : tenantScope;

  useEffect(() => {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    void (async () => {
      let data: AdminDashboardData;
      try {
        data = await loadAdminDashboard({
          apiBaseUrl,
          adminToken
        });
        if (isCancelled) {
          return;
        }
        setDashboardData(data);
        setDataMode("live");
        setTenantScope((currentScope) => {
          if (currentScope === "all" || data.tenants.some((tenant) => tenant.id === currentScope)) {
            return currentScope;
          }
          return "all";
        });
      } catch {
        if (!isCancelled) {
          setDataMode("mock");
          setAccessData(null);
        }
        return;
      }

      try {
        const access = await loadAdminAccess({
          apiBaseUrl,
          adminToken
        });
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

  useEffect(() => {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      setOperationsData(mockOperationsData);
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    setOperationsData(null);
    void (async () => {
      try {
        const operations = await loadAdminOperations({
          apiBaseUrl,
          adminToken,
          tenantScope
        });
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

  useEffect(() => {
    setTenantDetailData(null);
    if (activePage !== "tenants" || !selectedTenantId) {
      return;
    }
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    void (async () => {
      try {
        const detail = await loadAdminTenantDetail({
          apiBaseUrl,
          adminToken,
          tenantScope,
          tenantId: selectedTenantId
        });
        if (!isCancelled) {
          setTenantDetailData(detail);
        }
      } catch {
        if (!isCancelled) {
          setTenantDetailData(null);
        }
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, selectedTenantId, tenantScope]);

  useEffect(() => {
    setAuditEventsPage(null);
    setImpersonationSessions(null);
    if (activePage !== "audit") {
      return;
    }
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    void (async () => {
      const auditRequest = loadAdminAuditEvents({
        apiBaseUrl,
        adminToken,
        tenantScope,
        limit: 25
      })
        .then((auditPage) => {
          if (!isCancelled) {
            setAuditEventsPage(auditPage);
          }
        })
        .catch(() => {
          if (!isCancelled) {
            setAuditEventsPage(null);
          }
        });
      const sessionsRequest = loadAdminImpersonationSessions({
        apiBaseUrl,
        adminToken,
        tenantScope,
        status: "all"
      })
        .then((sessions) => {
          if (!isCancelled) {
            setImpersonationSessions(sessions);
          }
        })
        .catch(() => {
          if (!isCancelled) {
            setImpersonationSessions(null);
          }
        });
      await Promise.all([auditRequest, sessionsRequest]);
    })();
    return () => {
      isCancelled = true;
    };
  }, [activePage, tenantScope]);

  useEffect(() => {
    if (activePage !== "assets") {
      return;
    }
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    void (async () => {
      try {
        const assets = await loadAdminLearningAssets({
          apiBaseUrl,
          adminToken,
          tenantScope
        });
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

  useEffect(() => {
    if (activePage !== "users") {
      return;
    }
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      return;
    }
    let isCancelled = false;
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    void (async () => {
      try {
        const users = await loadAdminUsers({ apiBaseUrl, adminToken, tenantScope });
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
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin archive API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await archiveAdminMaterial({
      apiBaseUrl,
      adminToken,
      tenantScope,
      materialId,
      reason
    });
    setDashboardData((current) => ({
      ...current,
      materials: current.materials.map((material) => (material.id === result.material.id ? result.material : material))
    }));
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
    setOperationsData((current) =>
      pruneOperationIssues(
        current,
        (issue) =>
          issue.relatedResource.id === result.material.id ||
          issue.relatedResource.materialId === result.material.id
      )
    );
  }

  async function handleRetryMaterialJob(jobId: string, reason: string) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin retry API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await retryAdminMaterialJob({
      apiBaseUrl,
      adminToken,
      tenantScope,
      jobId,
      reason
    });
    setDashboardData((current) => ({
      ...current,
      materials: current.materials.map((material) => (material.id === result.material.id ? result.material : material))
    }));
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
    if (result.actionResult?.status === "failed") {
      throw new Error(result.actionResult.message || "Material retry action failed");
    }
    setOperationsData((current) =>
      pruneOperationIssues(
        current,
        (issue) =>
          issue.relatedResource.id === jobId ||
          issue.relatedResource.materialId === result.material.id
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

  async function handleOverrideProviderPolicy(input: ProviderPolicyOverrideInput) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin provider policy API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await overrideAdminProviderPolicy({
      apiBaseUrl,
      adminToken,
      tenantScope,
      tenantId: input.tenantId,
      aiProvider: input.aiProvider,
      mediaProvider: input.mediaProvider,
      fallbackMode: input.fallbackMode,
      monthlyGuardrail: input.monthlyGuardrail,
      reason: input.reason
    });
    setDashboardData((current) => ({
      ...current,
      providerPolicies: [
        ...current.providerPolicies.filter(
          (policy) => !(policy.tenantId === result.providerPolicy.tenantId && policy.source === "tenant_override")
        ),
        result.providerPolicy
      ]
    }));
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
  }

  async function handleToggleTenantModule(input: TenantModuleToggleInput) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin tenant module API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await toggleAdminTenantModule({
      apiBaseUrl,
      adminToken,
      tenantScope,
      tenantId: input.tenantId,
      moduleKey: input.moduleKey,
      enabled: input.enabled,
      reason: input.reason
    });
    setDashboardData((current) => ({
      ...current,
      moduleSettings: [
        ...current.moduleSettings.filter(
          (setting) =>
            !(setting.tenantId === result.moduleSetting.tenantId && setting.moduleKey === result.moduleSetting.moduleKey)
        ),
        result.moduleSetting
      ]
    }));
    setTenantDetailData((current) =>
      current && current.tenant.id === result.moduleSetting.tenantId
        ? {
            ...current,
            moduleSettings: [
              ...current.moduleSettings.filter(
                (setting) =>
                  !(
                    setting.tenantId === result.moduleSetting.tenantId &&
                    setting.moduleKey === result.moduleSetting.moduleKey
                  )
              ),
              result.moduleSetting
            ]
          }
        : current
    );
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
  }

  async function handleLoadAuditEvents(filters: AuditEventFilters) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin audit API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await loadAdminAuditEvents({
      apiBaseUrl,
      adminToken,
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

  async function handleStartImpersonation(input: { tenantId: string; targetParentId: string; reason: string }) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin impersonation API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await startAdminImpersonationSession({
      apiBaseUrl,
      adminToken,
      tenantScope,
      tenantId: input.tenantId,
      targetParentId: input.targetParentId,
      reason: input.reason
    });
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
    setImpersonationSessions((current) =>
      current
        ? {
            ...current,
            items: [
              result.impersonationSession,
              ...current.items.filter((session) => session.id !== result.impersonationSession.id)
            ],
            auditEvent: result.auditEvent
          }
        : current
    );
  }

  async function handleEndImpersonationSession(sessionId: string, reason: string) {
    const apiBaseUrl = import.meta.env.VITE_ADMIN_API_BASE_URL?.trim();
    if (!apiBaseUrl || typeof fetch === "undefined") {
      throw new Error("Admin impersonation API is not configured");
    }
    const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN?.trim() || "local-admin-token";
    const result = await endAdminImpersonationSession({
      apiBaseUrl,
      adminToken,
      tenantScope,
      sessionId,
      reason
    });
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
    setAccessData((current) =>
      current
        ? {
            ...current,
            auditEvents: prependAuditEvent(current.auditEvents, result.auditEvent)
          }
        : current
    );
    setAuditEventsPage((current) =>
      current
        ? {
            ...current,
            items: prependAuditEvent(current.items, result.auditEvent)
          }
        : current
    );
    return result;
  }

  return (
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
          tenants={dashboardData.tenants}
          materials={dashboardData.materials}
          operationsData={dataMode === "live" ? operationsData ?? undefined : mockOperationsData}
          adminPermissions={accessData?.permissions ?? []}
          onSubmitIssueAction={
            dataMode === "live" && operationsData?.tenantScope === tenantScope ? handleSubmitOperationIssueAction : undefined
          }
        />
      )}
      {activePage === "tenants" && (
        <TenantDetail
          language={language}
          tenantId={selectedTenantId}
          tenants={dashboardData.tenants}
          materials={dashboardData.materials}
          policies={dashboardData.providerPolicies}
          moduleSettings={dashboardData.moduleSettings}
          tenantDetailData={tenantDetailData}
          isAllTenantPreview={tenantScope === "all"}
          dataMode={dataMode}
          onToggleTenantModule={dataMode === "live" ? handleToggleTenantModule : undefined}
        />
      )}
      {activePage === "pipeline" && (
        <ContentPipeline
          language={language}
          tenantScope={tenantScope}
          tenants={dashboardData.tenants}
          materials={dashboardData.materials}
          dataMode={dataMode}
          onArchiveMaterial={dataMode === "live" ? handleArchiveMaterial : undefined}
          onRetryMaterialJob={dataMode === "live" ? handleRetryMaterialJob : undefined}
        />
      )}
      {activePage === "users" && (
        <UsersChildren
          language={language}
          tenantScope={tenantScope}
          tenants={dashboardData.tenants}
          users={dataMode === "live" ? usersData.items : mockUsers}
          dataMode={dataMode}
        />
      )}
      {activePage === "assets" && (
        <LearningAssets
          language={language}
          tenantScope={tenantScope}
          tenants={dashboardData.tenants}
          assets={dataMode === "live" ? learningAssetsData.items : mockLearningAssets}
          dataMode={dataMode}
        />
      )}
      {activePage === "audit" && (
        <AuditAccess
          language={language}
          accessData={accessData}
          dataMode={dataMode}
          tenants={dashboardData.tenants}
          tenantScope={tenantScope}
          auditEventsPage={auditEventsPage}
          impersonationSessions={impersonationSessions}
          onLoadAuditEvents={dataMode === "live" ? handleLoadAuditEvents : undefined}
          onStartImpersonation={dataMode === "live" ? handleStartImpersonation : undefined}
          onEndImpersonationSession={dataMode === "live" ? handleEndImpersonationSession : undefined}
        />
      )}
      {activePage === "providers" && (
        <ProviderOps
          language={language}
          tenantScope={tenantScope}
          tenants={dashboardData.tenants}
          materials={dashboardData.materials}
          policies={dashboardData.providerPolicies}
          dataMode={dataMode}
          onOverrideProviderPolicy={dataMode === "live" ? handleOverrideProviderPolicy : undefined}
        />
      )}
      {activePage !== "command" &&
        activePage !== "tenants" &&
        activePage !== "users" &&
        activePage !== "pipeline" &&
        activePage !== "assets" &&
        activePage !== "audit" &&
        activePage !== "providers" && (
        <PlaceholderPage language={language} title={t(pageTitles[activePage])} />
      )}
    </AppShell>
  );
}
