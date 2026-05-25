import { useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { EmptyPhase } from "./components/ui";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import type { MessageKey } from "./i18n/messages";
import { CommandCenter } from "./pages/CommandCenter";
import { ContentPipeline } from "./pages/ContentPipeline";
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
  const t = createTranslator(language);
  const selectedTenantId = tenantScope === "all" ? mockTenants[0]?.id ?? "" : tenantScope;

  return (
    <AppShell
      activePage={activePage}
      language={language}
      tenantScope={tenantScope}
      tenants={mockTenants}
      onLanguageChange={setLanguage}
      onTenantScopeChange={setTenantScope}
      onPageChange={setActivePage}
    >
      {activePage === "command" && (
        <CommandCenter language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      )}
      {activePage === "tenants" && (
        <TenantDetail
          language={language}
          tenantId={selectedTenantId}
          tenants={mockTenants}
          materials={mockMaterials}
          policies={mockProviderPolicies}
          isAllTenantPreview={tenantScope === "all"}
        />
      )}
      {activePage === "pipeline" && (
        <ContentPipeline language={language} tenantScope={tenantScope} tenants={mockTenants} materials={mockMaterials} />
      )}
      {activePage !== "command" && activePage !== "tenants" && activePage !== "pipeline" && (
        <>
          <section className="page-header">
            <p className="eyebrow">Phase 1 mock prototype</p>
            <h1>{t(pageTitles[activePage])}</h1>
            <p>{t("placeholder.phase1")}</p>
          </section>
          <EmptyPhase title={t(pageTitles[activePage])} detail={t("placeholder.phase1")} />
        </>
      )}
    </AppShell>
  );
}
