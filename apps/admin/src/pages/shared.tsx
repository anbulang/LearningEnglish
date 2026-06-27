/* Shared page chrome used by every console screen (header, root, card). */
import type { CSSProperties, ReactNode } from "react";
import type { Language, TenantScope } from "../domain/types";
import { Surface } from "../components/ui";
import { translateMessage } from "../i18n/i18n";

export function PageRoot({ children, screen }: { children: ReactNode; screen?: string }) {
  return (
    <div data-screen={screen} style={{ maxWidth: 1320, margin: "0 auto" }}>
      {children}
    </div>
  );
}

export function scopeNote(language: Language, tenantScope: TenantScope): string {
  if (tenantScope === "all") {
    return "";
  }
  return language === "zh" ? `　·　范围：${tenantScope}` : ` · scope: ${tenantScope}`;
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  language,
  tenantScope,
  action
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  language: Language;
  tenantScope: TenantScope;
  action?: ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 20 }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 4 }}>{eyebrow}</div>
        <h1 style={{ margin: 0, fontSize: 23, fontWeight: 700, letterSpacing: "-.2px" }}>{title}</h1>
        {subtitle && (
          <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text-2)" }}>
            {subtitle}
            {scopeNote(language, tenantScope)}
          </p>
        )}
      </div>
      {action && <div style={{ marginLeft: "auto", flex: "none" }}>{action}</div>}
    </div>
  );
}

export function SectionCard({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return <Surface style={{ overflow: "hidden", ...style }}>{children}</Surface>;
}

/** Primary (brand) action button — used for "+ 新增/添加" headers and form saves. */
export function PrimaryButton({
  children,
  onClick,
  disabled,
  style
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  style?: CSSProperties;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={disabled ? undefined : "le-hover-brand"}
      style={{
        height: 36,
        padding: "0 16px",
        border: "none",
        borderRadius: 8,
        background: disabled ? "var(--border-strong)" : "var(--brand)",
        color: disabled ? "var(--text-3)" : "var(--brand-fg)",
        fontSize: 13,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "inherit",
        boxShadow: disabled ? "none" : "var(--shadow-sm)",
        whiteSpace: "nowrap",
        ...style
      }}
    >
      {children}
    </button>
  );
}

/**
 * Small "原型/Prototype" badge for controls or screens with NO backend endpoint.
 * Shown (with `title` explaining actions don't persist) so the live console never
 * implies a no-backend control actually wrote to the server.
 */
export function PrototypeBadge({ language, style }: { language: Language; style?: CSSProperties }) {
  return (
    <span
      title={translateMessage(language, "common.prototypeHint")}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 10.5,
        fontWeight: 600,
        lineHeight: 1,
        padding: "3px 7px",
        borderRadius: 6,
        color: "var(--warning)",
        background: "var(--warning-subtle)",
        border: "1px solid var(--warning)",
        whiteSpace: "nowrap",
        ...style
      }}
    >
      {translateMessage(language, "common.prototype")}
    </span>
  );
}

/**
 * Screen-level banner for fully-prototype screens (cost, outcomes) in live mode:
 * the numbers shown are seeded sample data with no backend source.
 */
export function PrototypeBanner({ language, note }: { language: Language; note?: string }) {
  return (
    <div
      role="note"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 9,
        marginBottom: 16,
        padding: "9px 14px",
        borderRadius: 9,
        fontSize: 12.5,
        color: "var(--warning)",
        background: "var(--warning-subtle)",
        border: "1px solid var(--warning)"
      }}
    >
      <PrototypeBadge language={language} />
      <span style={{ color: "var(--text-2)" }}>{note ?? translateMessage(language, "common.prototypeHint")}</span>
    </div>
  );
}

/** Secondary (outline) button — edit / toggle / cancel actions. */
export function GhostButton({
  children,
  onClick,
  title,
  style
}: {
  children: ReactNode;
  onClick?: () => void;
  title?: string;
  style?: CSSProperties;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className="le-hover-soft"
      style={{
        height: 28,
        padding: "0 11px",
        border: "1px solid var(--border)",
        borderRadius: 7,
        background: "var(--surface)",
        color: "var(--text-2)",
        fontSize: 12,
        fontWeight: 500,
        cursor: "pointer",
        fontFamily: "inherit",
        ...style
      }}
    >
      {children}
    </button>
  );
}
