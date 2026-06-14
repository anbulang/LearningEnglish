import { useMemo } from "react";
import { StatusChip } from "../components/ui";
import type { AdminOperationsData, AdminSeverity, Language, TenantScope } from "../domain/types";

interface InfrastructureProps {
  language: Language;
  tenantScope: TenantScope;
  operationsData: AdminOperationsData | null;
  dataMode?: "mock" | "live";
}

const READINESS_KEYS = [
  "ai_provider_ready",
  "media_image_provider_ready",
  "media_tts_provider_ready",
  "speech_provider_ready",
  "speech_assessment_provider_ready"
] as const;

export function Infrastructure({ language, tenantScope, operationsData, dataMode = "mock" }: InfrastructureProps) {
  const copy = language === "zh" ? zhCopy : enCopy;

  const derived = useMemo(() => {
    if (!operationsData) {
      return null;
    }
    const summary = rec(operationsData.summary);
    const jobs = rec(operationsData.materialParseJobs);
    const speaking = rec(operationsData.speakingAttempts);
    const media = rec(operationsData.mediaGeneration);
    const failureSignals = rec(media.failure_signals);
    const provider = rec(operationsData.providerConfiguration);
    const runtime = rec(provider.runtime);
    const readiness = rec(runtime.readiness);
    const moduleCoverage = rec(operationsData.moduleToggleCoverage);
    return { summary, jobs, speaking, failureSignals, runtime, readiness, moduleCoverage };
  }, [operationsData]);

  if (!operationsData || !derived) {
    return (
      <div className="page-grid">
        <section className="page-header wide">
          <p className="eyebrow">Operations / Database snapshot</p>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </section>
        <section className="surface wide pipeline-empty">
          <strong>{copy.emptyTitle}</strong>
          <p>{copy.emptyDetail}</p>
        </section>
      </div>
    );
  }

  const { summary, jobs, speaking, failureSignals, runtime, readiness, moduleCoverage } = derived;
  const severity = (str(summary.severity) || "ok") as AdminSeverity;
  const issues = operationsData.issues ?? [];

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Operations / Database snapshot</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface wide filter-bar" aria-label={copy.filters}>
        <StatusChip tone={toneForSeverity(severity)}>{copy.severity}: {severity}</StatusChip>
        <span className="filter-summary">{dataMode === "live" ? copy.liveHint : copy.mockHint}</span>
      </section>

      <section className="surface wide" aria-label={copy.summary}>
        <div className="section-title">
          <div>
            <h2>{copy.summary}</h2>
            <p>{copy.snapshotNote}</p>
          </div>
        </div>
        <dl className="detail-list compact">
          <dt>{copy.tenants}</dt>
          <dd>{num(summary.tenant_count)}</dd>
          <dt>{copy.materials}</dt>
          <dd>{num(summary.materials)}</dd>
          <dt>{copy.parseJobs}</dt>
          <dd>{num(summary.material_parse_jobs)}</dd>
          <dt>{copy.mediaFailures}</dt>
          <dd>{num(summary.media_failures)}</dd>
          <dt>{copy.speakingAttempts}</dt>
          <dd>{num(summary.speaking_attempts)}</dd>
          <dt>{copy.issues}</dt>
          <dd>{num(summary.issue_count)}</dd>
        </dl>
      </section>

      <section className="surface span-8" aria-label={copy.health}>
        <div className="section-title">
          <div>
            <h2>{copy.health}</h2>
            <p>{copy.healthDetail}</p>
          </div>
        </div>
        <table className="pipeline-table">
          <thead>
            <tr>
              <th>{copy.pipeline}</th>
              <th>{copy.total}</th>
              <th>{copy.failed}</th>
              <th>{copy.runningPending}</th>
              <th>{copy.stale}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{copy.parseJobs}</td>
              <td>{num(jobs.total)}</td>
              <td>
                <StatusChip tone={num(jobs.failed) > 0 ? "danger" : "neutral"}>{num(jobs.failed)}</StatusChip>
              </td>
              <td>{num(jobs.running)}</td>
              <td>
                <StatusChip tone={num(jobs.stale_processing) > 0 ? "warning" : "neutral"}>{num(jobs.stale_processing)}</StatusChip>
              </td>
            </tr>
            <tr>
              <td>{copy.speakingAttempts}</td>
              <td>{num(speaking.total)}</td>
              <td>
                <StatusChip tone={num(speaking.failed) > 0 ? "danger" : "neutral"}>{num(speaking.failed)}</StatusChip>
              </td>
              <td>{num(speaking.pending)}</td>
              <td>
                <StatusChip tone={num(speaking.stale_pending) > 0 ? "warning" : "neutral"}>{num(speaking.stale_pending)}</StatusChip>
              </td>
            </tr>
          </tbody>
        </table>
        <div className="timeline" aria-label={copy.mediaFailures}>
          <h4>{copy.mediaFailures}</h4>
          <div className="timeline-row">
            <span aria-hidden="true" />
            <p>
              {copy.image}: {num(failureSignals.generated_image_status)} · {copy.ttsUs}: {num(failureSignals.tts_us_status)} ·{" "}
              {copy.ttsUk}: {num(failureSignals.tts_uk_status)} · {copy.total}: {num(failureSignals.total)}
            </p>
          </div>
        </div>
      </section>

      <aside className="surface span-4" aria-label={copy.providers}>
        <div className="section-title">
          <div>
            <h2>{copy.providers}</h2>
            <p>
              {str(runtime.ai_provider) || "—"} / {str(runtime.media_provider) || "—"}
            </p>
          </div>
        </div>
        <dl className="detail-list compact">
          {READINESS_KEYS.map((key) => (
            <div key={key} style={{ display: "contents" }}>
              <dt>{copy.readiness[key]}</dt>
              <dd>
                <StatusChip tone={bool(readiness[key]) ? "success" : "danger"}>
                  {bool(readiness[key]) ? copy.ready : copy.notReady}
                </StatusChip>
              </dd>
            </div>
          ))}
        </dl>
        <div className="timeline" aria-label={copy.moduleCoverage}>
          <h4>{copy.moduleCoverage}</h4>
          <div className="timeline-row">
            <span aria-hidden="true" />
            <p>
              {copy.enabled}: {num(moduleCoverage.enabled)} · {copy.disabled}: {num(moduleCoverage.disabled)} ·{" "}
              {copy.overrides}: {num(moduleCoverage.overrides)}
            </p>
          </div>
        </div>
      </aside>

      <section className="surface wide table-panel" aria-label={copy.issues}>
        <div className="section-title">
          <div>
            <h2>{copy.issues}</h2>
            <p>
              {issues.length} {copy.issuesDetail}
            </p>
          </div>
        </div>
        {issues.length > 0 ? (
          <div className="table-scroll">
            <table className="pipeline-table">
              <thead>
                <tr>
                  <th>{copy.severity}</th>
                  <th>{copy.statusLabel}</th>
                  <th>{copy.reason}</th>
                  <th>{copy.resource}</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue) => (
                  <tr key={issue.id}>
                    <td>
                      <StatusChip tone={toneForSeverity(issue.severity)}>{issue.severity}</StatusChip>
                    </td>
                    <td>{issue.statusLabel}</td>
                    <td>{issue.reason}</td>
                    <td>
                      {issue.relatedResource.type}
                      <small>{issue.relatedResource.id}</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pipeline-empty">
            <strong>{copy.noIssues}</strong>
            <p>{copy.noIssuesDetail}</p>
          </div>
        )}
      </section>
    </div>
  );
}

function toneForSeverity(severity: AdminSeverity): "success" | "warning" | "danger" | "neutral" {
  if (severity === "critical") {
    return "danger";
  }
  if (severity === "warning") {
    return "warning";
  }
  if (severity === "ok") {
    return "success";
  }
  return "neutral";
}

function rec(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function num(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function bool(value: unknown): boolean {
  return value === true;
}

const zhCopy = {
  title: "基础设施",
  subtitle: "基于数据库快照的系统健康概览:解析任务、口语评分、媒体生成、provider 就绪与模块覆盖。",
  filters: "基础设施概览",
  severity: "严重度",
  liveHint: "live 数据:来自 /v1/admin/operations。",
  mockHint: "mock 数据:未连接 live admin API。",
  summary: "概览",
  snapshotNote: "注:为数据库快照,不代表实时 broker / worker 心跳。",
  tenants: "租户数",
  materials: "讲义数",
  parseJobs: "解析任务",
  mediaFailures: "媒体失败",
  speakingAttempts: "口语评分",
  issues: "问题",
  health: "处理健康度",
  healthDetail: "解析任务与口语评分的失败/积压情况。",
  pipeline: "链路",
  total: "总计",
  failed: "失败",
  runningPending: "进行中/待处理",
  stale: "超时积压",
  image: "配图",
  ttsUs: "美音",
  ttsUk: "英音",
  providers: "Provider 就绪",
  ready: "就绪",
  notReady: "未就绪",
  readiness: {
    ai_provider_ready: "AI 识别",
    media_image_provider_ready: "配图生成",
    media_tts_provider_ready: "TTS 生成",
    speech_provider_ready: "语音",
    speech_assessment_provider_ready: "口语评分"
  } as Record<(typeof READINESS_KEYS)[number], string>,
  moduleCoverage: "模块覆盖",
  enabled: "启用",
  disabled: "禁用",
  overrides: "租户覆盖",
  statusLabel: "状态",
  reason: "原因",
  resource: "关联资源",
  issuesDetail: "个待处理问题(按严重度排序)",
  noIssues: "当前没有待处理问题。",
  noIssuesDetail: "解析、口语和媒体链路均无失败或超时积压。",
  emptyTitle: "暂无运营快照数据。",
  emptyDetail: "live 模式下切换租户范围会加载 operations 快照;未连接 API 时显示 mock。"
};

const enCopy: typeof zhCopy = {
  title: "Infrastructure",
  subtitle: "Database-snapshot system health: parse jobs, speaking assessment, media generation, provider readiness, and module coverage.",
  filters: "Infrastructure overview",
  severity: "Severity",
  liveHint: "Live data from /v1/admin/operations.",
  mockHint: "Mock data: live admin API not connected.",
  summary: "Summary",
  snapshotNote: "Note: database snapshot — not real-time broker/worker heartbeats.",
  tenants: "Tenants",
  materials: "Materials",
  parseJobs: "Parse jobs",
  mediaFailures: "Media failures",
  speakingAttempts: "Speaking attempts",
  issues: "Issues",
  health: "Processing health",
  healthDetail: "Failure and backlog signals for parse jobs and speaking assessment.",
  pipeline: "Pipeline",
  total: "Total",
  failed: "Failed",
  runningPending: "Running/Pending",
  stale: "Stale backlog",
  image: "Image",
  ttsUs: "US",
  ttsUk: "UK",
  providers: "Provider readiness",
  ready: "Ready",
  notReady: "Not ready",
  readiness: {
    ai_provider_ready: "AI recognition",
    media_image_provider_ready: "Image generation",
    media_tts_provider_ready: "TTS generation",
    speech_provider_ready: "Speech",
    speech_assessment_provider_ready: "Speaking score"
  } as Record<(typeof READINESS_KEYS)[number], string>,
  moduleCoverage: "Module coverage",
  enabled: "Enabled",
  disabled: "Disabled",
  overrides: "Tenant overrides",
  statusLabel: "Status",
  reason: "Reason",
  resource: "Related resource",
  issuesDetail: "open issues (sorted by severity)",
  noIssues: "No open issues.",
  noIssuesDetail: "Parse, speaking, and media pipelines have no failures or stale backlog.",
  emptyTitle: "No operations snapshot data.",
  emptyDetail: "In live mode, changing tenant scope loads the operations snapshot; mock data shows when the API is not connected."
};
