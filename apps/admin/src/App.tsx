import { useEffect, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import {
  archiveAdminMaterial,
  loadAdminAccess,
  loadAdminDashboard,
  type AdminAccessData,
  type AdminDashboardData
} from "./domain/adminApi";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import type { MessageKey } from "./i18n/messages";
import { AuditAccess } from "./pages/AuditAccess";
import { CommandCenter } from "./pages/CommandCenter";
import { ContentPipeline } from "./pages/ContentPipeline";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { TenantDetail } from "./pages/TenantDetail";

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

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [tenantScope, setTenantScope] = useState<TenantScope>("all");
  const [activePage, setActivePage] = useState<PageKey>("command");
  const [dashboardData, setDashboardData] = useState<AdminDashboardData>({
    tenants: mockTenants,
    materials: mockMaterials,
    providerPolicies: mockProviderPolicies
  });
  const [accessData, setAccessData] = useState<AdminAccessData | null>(null);
  const [dataMode, setDataMode] = useState<"mock" | "live">("mock");
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
      try {
        const data = await loadAdminDashboard({
          apiBaseUrl,
          adminToken
        });
        const access = await loadAdminAccess({
          apiBaseUrl,
          adminToken
        });
        if (isCancelled) {
          return;
        }
        setDashboardData(data);
        setAccessData(access);
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
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, []);

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
            auditEvents: [result.auditEvent, ...current.auditEvents.filter((event) => event.id !== result.auditEvent.id)]
          }
        : current
    );
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
        />
      )}
      {activePage === "tenants" && (
        <TenantDetail
          language={language}
          tenantId={selectedTenantId}
          tenants={dashboardData.tenants}
          materials={dashboardData.materials}
          policies={dashboardData.providerPolicies}
          isAllTenantPreview={tenantScope === "all"}
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
        />
      )}
      {activePage === "audit" && <AuditAccess language={language} accessData={accessData} dataMode={dataMode} />}
      {activePage !== "command" && activePage !== "tenants" && activePage !== "pipeline" && activePage !== "audit" && (
        <PlaceholderPage language={language} title={t(pageTitles[activePage])} />
      )}
    </AppShell>
  );
}
