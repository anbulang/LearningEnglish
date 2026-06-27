/*
 * Maps live `/v1/admin` payloads into the design's Console* view models so each
 * screen renders identically whether sourced from mock seeds or the real
 * backend. Mapping is intentionally defensive: backend snapshots are nested
 * Record<string, unknown> blobs (see domain/types AdminOperationsData), and
 * several design concepts (phonics curriculum, cost, provider connectors) have
 * no backend equivalent and therefore stay mock-only.
 */
import {
  type AssetMediaState,
  type ConsoleAnomaly,
  type ConsoleAuditRow,
  type ConsoleFamily,
  type ConsoleJob,
  type ConsoleKpi,
  type ConsoleProvider,
  type ConsoleTenant,
  type InfraNode,
  type JobStatusKey,
  type PhaseStat,
  type PhonicsAsset,
  type StageKey,
  type AuditResultKey,
  type TenantPlanKey,
  type Tone
} from "./consoleData";
import type {
  AdminAuditEvent,
  AdminLearningAsset,
  AdminMaterial,
  AdminOperationsData,
  AdminOperationsIssue,
  AdminUserAccount,
  Tenant
} from "./types";

function num(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function hhmm(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso || "");
  return match ? match[1] : "—";
}

/* ── Materials → pipeline jobs ─────────────────────────────────── */

function jobStatusOf(material: AdminMaterial): JobStatusKey {
  if (material.materialStatus === "failed" || material.jobStatus === "failed") return "failed";
  if (material.materialStatus === "ready" || material.jobStatus === "ready") return "done";
  if (material.materialStatus === "needs_review" || material.jobStatus === "needs_review") return "review";
  if (material.jobStatus === "processing" || material.materialStatus === "processing") return "ocr";
  return "queued";
}

export function materialsToJobs(materials: AdminMaterial[]): ConsoleJob[] {
  return materials
    .filter((material) => material.materialStatus !== "archived")
    .map((material) => ({
      id: material.jobId || material.id,
      family: material.parentName,
      child: `${material.childName} · ${material.title}`,
      type: material.title,
      status: jobStatusOf(material),
      ms: 0,
      time: hhmm(material.updatedAt),
      provider: material.provider,
      tenant: material.tenantId
    }));
}

/* ── Operations snapshot → command-center funnel ───────────────── */

export function operationsToPhaseStats(operations: AdminOperationsData): PhaseStat[] {
  const jobs = record(operations.materialParseJobs);
  const byStatus = record(jobs.by_status);
  const media = record(operations.mediaGeneration);
  const failureSignals = record(media.failure_signals);
  return [
    { labelKey: "phase.queued", statusKey: "queued", tone: "neutral", count: num(byStatus.queued) },
    { labelKey: "phase.ocr", statusKey: "ocr", tone: "info", count: num(byStatus.processing) },
    { labelKey: "phase.review", statusKey: "review", tone: "warning", count: num(byStatus.needs_review) },
    { labelKey: "phase.done", statusKey: "done", tone: "success", count: num(byStatus.ready) },
    { labelKey: "phase.failed", statusKey: "failed", tone: "danger", count: num(byStatus.failed) + num(failureSignals.total) }
  ];
}

/* ── Operations issues → anomalies feed ────────────────────────── */

const SEVERITY_TONE: Record<string, Tone> = {
  critical: "danger",
  warning: "warning",
  info: "info",
  ok: "neutral"
};

export function operationsToAnomalies(operations: AdminOperationsData): ConsoleAnomaly[] {
  return operations.issues.map((issue: AdminOperationsIssue) => ({
    tone: SEVERITY_TONE[issue.severity] ?? "neutral",
    title: issue.statusLabel,
    meta: issue.reason,
    time: hhmm(String(record(operations.summary).generated_at ?? "")),
    action: issue.recommendedAction
  }));
}

/* ── Operations runtime → infrastructure node cards ────────────── */

export function operationsToInfraNodes(operations: AdminOperationsData): InfraNode[] {
  const summary = record(operations.summary);
  const jobs = record(operations.materialParseJobs);
  const speaking = record(operations.speakingAttempts);
  const providerConfig = record(operations.providerConfiguration);
  const runtime = record(providerConfig.runtime);
  const readiness = record(runtime.readiness);
  const allReady = Object.values(readiness).every(Boolean);
  return [
    {
      name: "Material parse jobs",
      metric: `${num(jobs.running)} running / ${num(jobs.total)}`,
      sub: `failed ${num(jobs.failed)} · stale ${num(jobs.stale_processing)}`,
      tone: num(jobs.failed) > 0 ? "warning" : "success",
      statusKey: num(jobs.failed) > 0 ? "status.infra.attention" : "status.infra.normal"
    },
    {
      name: "Speaking attempts",
      metric: `${num(speaking.pending)} pending / ${num(speaking.total)}`,
      sub: `failed ${num(speaking.failed)}`,
      tone: num(speaking.failed) > 0 ? "warning" : "success",
      statusKey: num(speaking.failed) > 0 ? "status.infra.attention" : "status.infra.normal"
    },
    {
      name: "Provider readiness",
      metric: allReady ? "all ready" : "degraded",
      sub: `${Object.values(readiness).filter(Boolean).length}/${Object.keys(readiness).length} ready`,
      tone: allReady ? "success" : "warning",
      statusKey: allReady ? "status.infra.normal" : "status.infra.attention"
    },
    {
      name: "Media generation",
      metric: `failures ${num(record(record(operations.mediaGeneration).failure_signals).total)}`,
      sub: `tenants ${num(summary.tenant_count)}`,
      tone: "info",
      statusKey: "status.infra.normal"
    }
  ];
}

/* ── Audit events → audit rows ─────────────────────────────────── */

const RESULT_MAP: Record<string, AuditResultKey> = {
  success: "success",
  failed: "intercepted",
  noop: "alert"
};

export function auditEventsToRows(events: AdminAuditEvent[]): ConsoleAuditRow[] {
  return events.map((event) => ({
    time: hhmm(event.createdAt),
    actor: event.actorId,
    role: event.actorRole,
    action: event.action,
    target: `${event.resourceType} · ${event.resourceId}`,
    result: RESULT_MAP[event.result] ?? "alert",
    sensitive: event.riskLevel === "high"
  }));
}

/* ── Users → families ──────────────────────────────────────────── */

export function usersToFamilies(users: AdminUserAccount[]): ConsoleFamily[] {
  const byParent = new Map<string, ConsoleFamily>();
  for (const user of users) {
    const key = `${user.tenantId}::${user.parentName}`;
    let family = byParent.get(key);
    if (!family) {
      family = {
        id: key,
        // tenantId is the parent-account id in this admin model; it is the
        // valid impersonation target (backend requires target == tenant id).
        parentId: user.tenantId,
        name: user.parentName,
        phone: "—",
        tenant: user.tenantId,
        reg: (user.createdAt || "").slice(0, 10) || "—",
        status: "active",
        usage: "—",
        children: []
      };
      byParent.set(key, family);
    }
    family.children.push({
      name: user.childName,
      grade: user.level,
      progress: Math.min(100, user.speakingAttempts * 5),
      last: "",
      lastMaterials: user.materialsCount
    });
  }
  return [...byParent.values()];
}

/* ── Tenants → console tenant rows ─────────────────────────────── */

const TIER_PLAN: Record<string, TenantPlanKey> = {
  pilot: "trial",
  standard: "standard",
  flagship: "flagship"
};

export function tenantsToConsole(tenants: Tenant[], materials: AdminMaterial[]): ConsoleTenant[] {
  return tenants.map((tenant) => {
    const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
    const ready = tenantMaterials.filter((material) => material.materialStatus === "ready").length;
    const rate = tenantMaterials.length ? `${Math.round((ready / tenantMaterials.length) * 100)}%` : "—";
    return {
      id: tenant.id,
      name: tenant.name,
      plan: TIER_PLAN[(tenant.tier || "").toLowerCase()] ?? "standard",
      kids: tenant.children,
      decks: tenantMaterials.length,
      rate,
      status: tenant.status === "warning" ? "quotaWarning" : "normal",
      enabled: tenant.status !== "suspended"
    };
  });
}

/* ── Learning assets → phonics asset cards ─────────────────────── */

function toAssetMediaState(status: string): AssetMediaState {
  if (status === "ready") return "ready";
  if (status === "pending" || status === "processing") return "pending";
  if (status === "failed") return "failed";
  return "—";
}

/**
 * Live assets are a FLAT list of per-material derived media — they carry no
 * phonics stage, IPA, or curriculum. We bucket every item into one stage (the
 * asset grid renders a flat list in live mode; the scope-and-sequence band and
 * per-stage chips are design-only and hidden in live). `grapheme` is the sample
 * word; the three media channels map to the real TTS/image statuses.
 */
export function liveAssetsToConsole(assets: AdminLearningAsset[]): PhonicsAsset[] {
  return assets.map((asset) => ({
    stage: "letter" as StageKey,
    grapheme: asset.text || asset.materialTitle || asset.id,
    phoneme: asset.translation || asset.kind,
    example: asset.materialTitle,
    media: {
      en: toAssetMediaState(asset.ttsUkStatus),
      us: toAssetMediaState(asset.ttsUsStatus),
      img: toAssetMediaState(asset.generatedImageStatus)
    }
  }));
}

/* ── Operations snapshot → command-center KPIs ─────────────────── */

/**
 * Live KPIs derivable from the operations snapshot. The snapshot is a single
 * point-in-time with no comparison baseline, so `delta` is intentionally empty
 * (no fabricated "vs yesterday"). `activeFamilies` / `weeklyReports` have no
 * operations source and are omitted — the command center hides those cards live.
 */
export function operationsToKpis(operations: AdminOperationsData): ConsoleKpi[] {
  const jobs = record(operations.materialParseJobs);
  const byStatus = record(jobs.by_status);
  const media = record(operations.mediaGeneration);
  const failureSignals = record(media.failure_signals);
  const speaking = record(operations.speakingAttempts);
  const total = num(jobs.total);
  const ready = num(byStatus.ready);
  const denom = total > 0 ? total : 1;
  const rate = Math.round((ready / denom) * 100);
  return [
    { labelKey: "kpi.uploads", value: total.toLocaleString(), delta: "", positive: true, subKey: "kpi.inQueue", barTone: "brand" },
    { labelKey: "kpi.pendingOcr", value: num(byStatus.queued).toLocaleString(), delta: "", positive: false, subKey: "kpi.inQueue", barTone: "warning" },
    { labelKey: "kpi.recognitionRate", value: `${rate}%`, delta: "", positive: true, subKey: "kpi.last24h", barTone: "success" },
    { labelKey: "kpi.pronunciationRuns", value: num(speaking.total).toLocaleString(), delta: "", positive: true, subKey: "kpi.last24h", barTone: "info" },
    { labelKey: "kpi.failures", value: (num(byStatus.failed) + num(failureSignals.total)).toLocaleString(), delta: "", positive: false, subKey: "kpi.last24h", barTone: "danger" }
  ];
}

/* ── Operations provider readiness → provider status panel ─────── */

/**
 * Only `provider_configuration.runtime.readiness` (a per-provider boolean map)
 * is exposed by the backend. success/latency/quota have no live source, so they
 * stay 0 and the panel renders "—" for them (graceful degradation).
 */
export function providerConfigToProviders(operations: AdminOperationsData): ConsoleProvider[] {
  const providerConfig = record(operations.providerConfiguration);
  const runtime = record(providerConfig.runtime);
  const readiness = record(runtime.readiness);
  return Object.entries(readiness).map(([key, ready], index) => ({
    id: `live-provider-${index}`,
    name: key,
    use: "",
    endpoint: "",
    model: "",
    status: ready ? "ok" : "down",
    success: 0,
    latency: 0,
    quota: 0,
    enabled: Boolean(ready)
  }));
}
