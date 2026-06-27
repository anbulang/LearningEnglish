/*
 * Stateless UI primitives + inline-style builders for the 运维控制台.
 * The design uses inline styles + CSS variables throughout; these helpers
 * encapsulate the repeated patterns (badges, dots, cards, switches, drawers,
 * modals) so screens stay DRY while remaining faithful to the source design.
 */
import type { CSSProperties, ReactNode } from "react";
import { TONE_TOKENS, sparkline, type Tone } from "../domain/consoleData";
import { IconX } from "./icons";

export function toneTokens(tone: Tone) {
  return TONE_TOKENS[tone];
}

/* ── Style builders ───────────────────────────────────────────── */

export function badgeStyle(tone: Tone): CSSProperties {
  const t = TONE_TOKENS[tone];
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    fontSize: 11.5,
    fontWeight: 600,
    padding: "2px 9px",
    borderRadius: 20,
    whiteSpace: "nowrap",
    color: t.fg,
    background: t.bg
  };
}

export function dotStyle(color: string): CSSProperties {
  return { width: 6, height: 6, borderRadius: "50%", flex: "none", background: color };
}

export function bigDotStyle(color: string, ringBg: string): CSSProperties {
  return { width: 9, height: 9, borderRadius: "50%", flex: "none", background: color, boxShadow: `0 0 0 3px ${ringBg}` };
}

export function accentBarStyle(color: string): CSSProperties {
  return { position: "absolute", left: 0, top: 0, bottom: 0, width: 3, background: color };
}

export function surfaceStyle(extra?: CSSProperties): CSSProperties {
  return {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 10,
    boxShadow: "var(--shadow-sm)",
    ...extra
  };
}

/* ── Badges ───────────────────────────────────────────────────── */

export function StatusBadge({ tone, children, dot = false }: { tone: Tone; children: ReactNode; dot?: boolean }) {
  return (
    <span style={badgeStyle(tone)}>
      {dot && <span style={dotStyle(TONE_TOKENS[tone].c)} />}
      {children}
    </span>
  );
}

/** Back-compat alias used by a few shared call sites. */
export function StatusChip({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <StatusBadge tone={tone}>{children}</StatusBadge>;
}

/* ── Surface card ─────────────────────────────────────────────── */

export function Surface({ children, style, className }: { children: ReactNode; style?: CSSProperties; className?: string }) {
  return (
    <div className={className} style={surfaceStyle(style)}>
      {children}
    </div>
  );
}

/* ── KPI / metric card ────────────────────────────────────────── */

export function MetricCard({
  label,
  value,
  delta,
  positive = true,
  sub,
  barTone = "brand"
}: {
  label: string;
  value: ReactNode;
  delta?: string;
  positive?: boolean;
  sub?: string;
  barTone?: Tone;
}) {
  const deltaColor = positive ? "var(--success)" : "var(--danger)";
  const deltaBg = positive ? "var(--success-subtle)" : "var(--danger-subtle)";
  return (
    <article
      className="metric-card"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "16px 16px 15px",
        boxShadow: "var(--shadow-sm)",
        position: "relative",
        overflow: "hidden"
      }}
    >
      <div style={accentBarStyle(TONE_TOKENS[barTone].c)} />
      <div style={{ fontSize: 12, color: "var(--text-2)", marginBottom: 9 }}>{label}</div>
      <div
        style={{
          fontFamily: "var(--mono)",
          fontSize: 23,
          fontWeight: 600,
          letterSpacing: "-.5px",
          color: "var(--text)",
          lineHeight: 1
        }}
      >
        {value}
      </div>
      {(delta || sub) && (
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 7 }}>
          {delta && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 2,
                fontFamily: "var(--mono)",
                fontSize: 11.5,
                fontWeight: 600,
                padding: "1px 7px",
                borderRadius: 5,
                color: deltaColor,
                background: deltaBg
              }}
            >
              {delta}
            </span>
          )}
          {sub && <span style={{ fontSize: 11, color: "var(--text-3)" }}>{sub}</span>}
        </div>
      )}
    </article>
  );
}

/* ── Toggle switch ────────────────────────────────────────────── */

export function Switch({ on, onToggle, ariaLabel }: { on: boolean; onToggle: () => void; ariaLabel?: string }) {
  return (
    <div
      role="switch"
      aria-checked={on}
      aria-label={ariaLabel}
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onToggle();
        }
      }}
      style={{
        width: 38,
        height: 22,
        borderRadius: 12,
        flex: "none",
        cursor: "pointer",
        position: "relative",
        transition: "background .15s",
        background: on ? "var(--brand)" : "var(--border-strong)"
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 2,
          left: on ? 18 : 2,
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: "#fff",
          transition: "left .15s",
          boxShadow: "0 1px 2px rgba(0,0,0,.3)"
        }}
      />
    </div>
  );
}

/* ── Sparkline ────────────────────────────────────────────────── */

export function Sparkline({ series, height = 84 }: { series: number[]; height?: number }) {
  const { linePoints, areaPath } = sparkline(series);
  return (
    <svg viewBox="0 0 300 78" preserveAspectRatio="none" style={{ width: "100%", height, display: "block", overflow: "visible" }}>
      <path d={areaPath} fill="var(--brand-subtle)" stroke="none" />
      <polyline
        points={linePoints}
        fill="none"
        stroke="var(--brand)"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* ── Progress bar ─────────────────────────────────────────────── */

export function ProgressBar({ pct, color = "var(--brand)", height = 6 }: { pct: number; color?: string; height?: number }) {
  return (
    <div style={{ height, borderRadius: height / 2, background: "var(--bg-subtle)", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, pct))}%`, background: color, borderRadius: height / 2 }} />
    </div>
  );
}

/* ── Filter chip ──────────────────────────────────────────────── */

export function FilterChip({
  active,
  label,
  count,
  onClick
}: {
  active: boolean;
  label: string;
  count?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        height: 30,
        padding: "0 12px",
        borderRadius: 8,
        fontSize: 12.5,
        fontWeight: 500,
        cursor: "pointer",
        whiteSpace: "nowrap",
        userSelect: "none",
        fontFamily: "inherit",
        border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
        background: active ? "var(--brand-subtle)" : "var(--surface)",
        color: active ? "var(--brand)" : "var(--text-2)"
      }}
    >
      {label}
      {count != null && (
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10.5,
            fontWeight: 600,
            padding: "0 5px",
            borderRadius: 10,
            background: active ? "var(--brand-border)" : "var(--bg-subtle)",
            color: active ? "var(--brand)" : "var(--text-3)"
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

/* ── Right-side drawer ────────────────────────────────────────── */

export function Drawer({
  open,
  onClose,
  children,
  width = 468,
  closeLabel = "Close",
  ariaLabel
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  width?: number;
  closeLabel?: string;
  ariaLabel?: string;
}) {
  if (!open) return null;
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(8,11,16,.34)", zIndex: 50 }} />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width,
          maxWidth: "92vw",
          background: "var(--surface)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "var(--shadow-pop)",
          zIndex: 51,
          display: "flex",
          flexDirection: "column"
        }}
      >
        {children}
        <button aria-label={closeLabel} onClick={onClose} style={{ display: "none" }} />
      </aside>
    </>
  );
}

/* ── Centered modal ───────────────────────────────────────────── */

export function Modal({
  open,
  onClose,
  children,
  width = 420,
  zIndex = 60,
  ariaLabel
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  width?: number;
  zIndex?: number;
  ariaLabel?: string;
}) {
  if (!open) return null;
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(8,11,16,.42)", zIndex }} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%,-50%)",
          width,
          maxWidth: "92vw",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          boxShadow: "var(--shadow-pop)",
          zIndex: zIndex + 1,
          padding: 24
        }}
      >
        {children}
      </div>
    </>
  );
}

/* ── Close icon button (drawer/modal headers) ─────────────────── */

export function CloseButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="le-hover-soft"
      style={{
        width: 32,
        height: 32,
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--surface)",
        color: "var(--text-2)",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}
    >
      <IconX size={15} />
    </button>
  );
}

/* ── Empty state ──────────────────────────────────────────────── */

export function EmptyState({ children }: { children: ReactNode }) {
  return <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "var(--text-3)" }}>{children}</div>;
}
