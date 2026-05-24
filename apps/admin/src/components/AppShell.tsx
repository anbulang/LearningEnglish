import {
  BarChart3,
  BookOpenCheck,
  Boxes,
  Building2,
  ClipboardList,
  Code2,
  Database,
  Home,
  ShieldCheck,
  Users,
  type LucideIcon
} from "lucide-react";
import type { ReactNode } from "react";
import type { Language, Tenant, TenantScope } from "../domain/types";
import { createTranslator } from "../i18n/i18n";
import type { MessageKey } from "../i18n/messages";

export type PageKey =
  | "command"
  | "tenants"
  | "users"
  | "pipeline"
  | "assets"
  | "outcomes"
  | "providers"
  | "infrastructure"
  | "audit"
  | "developer";

interface AppShellProps {
  children: ReactNode;
  activePage: PageKey;
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  onLanguageChange: (language: Language) => void;
  onTenantScopeChange: (scope: TenantScope) => void;
  onPageChange: (page: PageKey) => void;
}

const navItems: { key: PageKey; label: MessageKey; icon: LucideIcon }[] = [
  { key: "command", label: "nav.commandCenter", icon: Home },
  { key: "tenants", label: "nav.tenants", icon: Building2 },
  { key: "users", label: "nav.usersChildren", icon: Users },
  { key: "pipeline", label: "nav.contentPipeline", icon: ClipboardList },
  { key: "assets", label: "nav.learningAssets", icon: Boxes },
  { key: "outcomes", label: "nav.learningOutcomes", icon: BarChart3 },
  { key: "providers", label: "nav.providerOps", icon: BookOpenCheck },
  { key: "infrastructure", label: "nav.infrastructure", icon: Database },
  { key: "audit", label: "nav.auditAccess", icon: ShieldCheck },
  { key: "developer", label: "nav.developerApi", icon: Code2 }
];

export function AppShell(props: AppShellProps) {
  const t = createTranslator(props.language);

  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <div className="brand-mark">LE</div>
        <nav className="sidebar-nav" aria-label="Admin navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={props.activePage === item.key ? "nav-item active" : "nav-item"}
                onClick={() => props.onPageChange(item.key)}
              >
                <Icon size={18} />
                <span>{t(item.label)}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="admin-frame">
        <header className="topbar">
          <strong>LearningEnglish Admin</strong>
          <select value={props.tenantScope} onChange={(event) => props.onTenantScopeChange(event.target.value as TenantScope)}>
            <option value="all">{t("top.allTenants")}</option>
            {props.tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
          <span className="status-chip success">{t("top.production")}</span>
          <div className="language-toggle" aria-label="Language">
            <button className={props.language === "zh" ? "active" : ""} onClick={() => props.onLanguageChange("zh")}>
              中文
            </button>
            <button className={props.language === "en" ? "active" : ""} onClick={() => props.onLanguageChange("en")}>
              English
            </button>
          </div>
          <span className="status-chip success">{t("top.healthy")}</span>
          <button className="ghost-button">{t("top.openapi")}</button>
        </header>
        <main className="page-content">{props.children}</main>
      </div>
    </div>
  );
}
