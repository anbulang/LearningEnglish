import { useMemo, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { mockMaterials, mockTenants } from "./domain/mockData";
import type { Language, TenantScope } from "./domain/types";
import { createTranslator } from "./i18n/i18n";
import type { MessageKey } from "./i18n/messages";

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
  const scopedMaterials = useMemo(
    () => (tenantScope === "all" ? mockMaterials : mockMaterials.filter((material) => material.tenantId === tenantScope)),
    [tenantScope]
  );

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
      <section className="page-header">
        <p className="eyebrow">Phase 1 mock prototype</p>
        <h1>{t(pageTitles[activePage])}</h1>
        <p>{activePage === "command" ? t("page.commandCenter.subtitle") : t("placeholder.phase1")}</p>
      </section>
      {activePage === "command" ? (
        <section className="surface">
          <strong>{scopedMaterials.length}</strong> materials in current scope
        </section>
      ) : (
        <section className="surface">{t("placeholder.phase1")}</section>
      )}
    </AppShell>
  );
}
