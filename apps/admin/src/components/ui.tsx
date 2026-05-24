import type { ReactNode } from "react";

type StatusTone = "success" | "warning" | "danger" | "neutral";

export function StatusChip({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  return <span className={`status-chip ${tone}`}>{children}</span>;
}

export function MetricCard({ label, value, detail }: { label: string; value: ReactNode; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

export function EmptyPhase({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="surface empty-phase">
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}
