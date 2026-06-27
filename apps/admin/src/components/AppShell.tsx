import type { CSSProperties, ReactNode } from "react";
import { TONE_TOKENS, type Tone } from "../domain/consoleData";
import type { Language, Tenant, TenantScope } from "../domain/types";
import { createTranslator } from "../i18n/i18n";
import type { MessageKey } from "../i18n/messages";
import { IconSearch } from "./icons";
import { useTheme } from "./providers";

export type PageKey =
  | "command"
  | "tenants"
  | "pipeline"
  | "assets"
  | "outcomes"
  | "users"
  | "providers"
  | "cost"
  | "infrastructure"
  | "audit";

interface AppShellProps {
  children: ReactNode;
  activePage: PageKey;
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  dataMode?: "mock" | "live";
  onLanguageChange: (language: Language) => void;
  onTenantScopeChange: (scope: TenantScope) => void;
  onPageChange: (page: PageKey) => void;
}

interface NavItem {
  key: PageKey;
  label: MessageKey;
  badge?: { text: string; tone: Tone };
}

const NAV_GROUPS: { group: MessageKey; items: NavItem[] }[] = [
  {
    group: "navgroup.main",
    items: [
      { key: "command", label: "nav.commandCenter" },
      { key: "tenants", label: "nav.tenants" },
      { key: "pipeline", label: "nav.contentPipeline", badge: { text: "37", tone: "warning" } }
    ]
  },
  {
    group: "navgroup.content",
    items: [
      { key: "assets", label: "nav.learningAssets" },
      { key: "outcomes", label: "nav.learningOutcomes" },
      { key: "users", label: "nav.usersChildren" }
    ]
  },
  {
    group: "navgroup.ops",
    items: [
      { key: "providers", label: "nav.providerOps" },
      { key: "cost", label: "nav.cost", badge: { text: "↓60%", tone: "success" } },
      { key: "infrastructure", label: "nav.infrastructure" },
      { key: "audit", label: "nav.auditAccess" }
    ]
  }
];

const HEADER_H = 57;

export function AppShell(props: AppShellProps) {
  const t = createTranslator(props.language);
  const { theme, toggleTheme } = useTheme();
  const knownTenantIds = new Set(props.tenants.map((tenant) => tenant.id));

  function handleTenantScopeChange(value: string) {
    if (value === "all" || knownTenantIds.has(value)) {
      props.onTenantScopeChange(value);
    }
  }

  return (
    <div
      data-theme={theme}
      style={{
        fontFamily: "'Noto Sans SC',system-ui,-apple-system,sans-serif",
        background: "var(--bg)",
        color: "var(--text)",
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        letterSpacing: ".1px"
      }}
    >
      <aside
        style={{
          width: 250,
          flex: "none",
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          height: "100vh",
          position: "sticky",
          top: 0,
          display: "flex",
          flexDirection: "column"
        }}
      >
        <div
          style={{
            height: HEADER_H,
            flex: "none",
            display: "flex",
            alignItems: "center",
            gap: 11,
            padding: "0 18px",
            borderBottom: "1px solid var(--border)"
          }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              background: "var(--brand)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--brand-fg)",
              fontWeight: 700,
              fontSize: 15,
              boxShadow: "var(--shadow-sm)"
            }}
          >
            L
          </div>
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
            <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)" }}>LearningEnglish</span>
            <span style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: ".3px" }}>{t("shell.brandSub")}</span>
          </div>
        </div>

        <nav aria-label={t("shell.nav")} style={{ flex: 1, overflowY: "auto", padding: "12px 0" }}>
          {NAV_GROUPS.map((group) => (
            <div key={group.group}>
              <div
                style={{
                  fontSize: 10.5,
                  fontWeight: 600,
                  letterSpacing: ".8px",
                  color: "var(--text-3)",
                  padding: "14px 20px 6px"
                }}
              >
                {t(group.group)}
              </div>
              {group.items.map((item) => {
                const active = props.activePage === item.key;
                return (
                  <button
                    key={item.key}
                    type="button"
                    aria-current={active ? "page" : undefined}
                    onClick={() => props.onPageChange(item.key)}
                    className={active ? undefined : "le-hover-soft"}
                    style={{
                      position: "relative",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      width: "calc(100% - 20px)",
                      padding: "8px 12px",
                      margin: "1px 10px",
                      borderRadius: 7,
                      border: "none",
                      cursor: "pointer",
                      fontSize: 13.5,
                      fontWeight: active ? 600 : 500,
                      fontFamily: "inherit",
                      textAlign: "left",
                      color: active ? "var(--brand)" : "var(--text-2)",
                      background: active ? "var(--brand-subtle)" : "transparent",
                      userSelect: "none",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {active && (
                      <span
                        style={{
                          position: "absolute",
                          left: -10,
                          top: 8,
                          bottom: 8,
                          width: 3,
                          borderRadius: 3,
                          background: "var(--brand)"
                        }}
                      />
                    )}
                    <span style={{ position: "relative", zIndex: 1 }}>{t(item.label)}</span>
                    {item.badge && (
                      <span
                        style={{
                          position: "relative",
                          zIndex: 1,
                          marginLeft: "auto",
                          fontFamily: "var(--mono)",
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "1px 7px",
                          borderRadius: 20,
                          color: TONE_TOKENS[item.badge.tone].fg,
                          background: TONE_TOKENS[item.badge.tone].bg
                        }}
                      >
                        {item.badge.text}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div
          style={{
            flex: "none",
            borderTop: "1px solid var(--border)",
            padding: "11px 14px",
            display: "flex",
            alignItems: "center",
            gap: 10
          }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: "50%",
              background: "linear-gradient(135deg,#5b76e8,#8a5be8)",
              color: "#fff",
              fontSize: 12,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: "none"
            }}
          >
            陈
          </div>
          <div style={{ minWidth: 0, lineHeight: 1.25 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text)" }}>陈牧之</div>
            <div style={{ fontSize: 11, color: "var(--text-3)" }}>{t("shell.userRole")}</div>
          </div>
        </div>
      </aside>

      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <header
          style={{
            height: HEADER_H,
            flex: "none",
            background: "var(--surface)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "0 22px",
            position: "sticky",
            top: 0,
            zIndex: 20
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "4px 11px",
              border: "1px solid var(--border)",
              borderRadius: 7,
              background: "var(--surface-2)"
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: "var(--success)",
                boxShadow: "0 0 0 3px var(--success-subtle)"
              }}
            />
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)" }}>
              {props.dataMode === "live" ? t("top.liveApi") : t("top.envProd")}
            </span>
            <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
              {props.dataMode === "live" ? "live" : "prod-cn"}
            </span>
          </div>

          <div style={{ flex: 1, maxWidth: 420, position: "relative" }}>
            <span style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)", display: "inline-flex" }}>
              <IconSearch size={15} />
            </span>
            <input
              aria-label={t("top.search")}
              placeholder={t("top.search")}
              className="le-input"
              style={{
                width: "100%",
                height: 34,
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--bg-subtle)",
                padding: "0 12px 0 32px",
                fontSize: 13,
                color: "var(--text)",
                outline: "none",
                fontFamily: "inherit"
              }}
            />
          </div>

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <select
              value={props.tenantScope}
              aria-label={t("top.tenantScope")}
              onChange={(event) => handleTenantScopeChange(event.target.value)}
              style={selectStyle}
            >
              <option value="all">{t("top.allTenants")}</option>
              {props.tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>

            <button
              type="button"
              aria-label={t("shell.themeToggle")}
              onClick={toggleTheme}
              className="le-hover-soft"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                height: 32,
                padding: "0 11px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--surface)",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 500,
                color: "var(--text-2)",
                fontFamily: "inherit",
                userSelect: "none"
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--brand)" }} />
              {theme === "dark" ? t("top.themeDark") : t("top.themeLight")}
            </button>

            <div
              aria-label={t("shell.language")}
              role="group"
              style={{
                display: "flex",
                alignItems: "center",
                height: 32,
                border: "1px solid var(--border)",
                borderRadius: 8,
                overflow: "hidden"
              }}
            >
              {(["zh", "en"] as Language[]).map((lang) => {
                const active = props.language === lang;
                return (
                  <button
                    key={lang}
                    type="button"
                    aria-pressed={active}
                    onClick={() => props.onLanguageChange(lang)}
                    style={{
                      height: "100%",
                      padding: "0 10px",
                      border: "none",
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: 600,
                      fontFamily: "inherit",
                      background: active ? "var(--brand-subtle)" : "var(--surface)",
                      color: active ? "var(--brand)" : "var(--text-3)"
                    }}
                  >
                    {lang === "zh" ? "中文" : "EN"}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        <main style={{ flex: 1, overflowY: "auto", padding: "26px 28px 60px" }}>{props.children}</main>
      </div>
    </div>
  );
}

const selectStyle: CSSProperties = {
  height: 32,
  padding: "0 10px",
  border: "1px solid var(--border)",
  borderRadius: 8,
  background: "var(--surface)",
  color: "var(--text-2)",
  fontSize: 12.5,
  fontWeight: 500,
  fontFamily: "inherit",
  outline: "none",
  cursor: "pointer"
};
