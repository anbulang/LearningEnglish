import { useState } from "react";
import {
  PROVIDER_STATUS_META,
  READY_TREND_SERIES,
  TONE_TOKENS,
  commandKpis,
  consoleAnomalies,
  consoleJobs,
  consoleProviders,
  phaseStats,
  type ConsoleAnomaly,
  type PhaseStat,
  type Tone
} from "../domain/consoleData";
import { operationsToKpis, operationsToPhaseStats, providerConfigToProviders } from "../domain/liveMappers";
import { EmptyState, Modal, Sparkline, MetricCard, bigDotStyle } from "../components/ui";
import { useToast } from "../components/providers";
import { createTranslator, localize } from "../i18n/i18n";
import { PageHeader, PageRoot, PrototypeBadge } from "./shared";
import type { AdminOperationsIssue } from "../domain/types";
import type { CommandCenterProps } from "./contracts";

const copy = {
  zh: {
    eyebrow: "主控 / 指挥中心",
    title: "平台指挥中心",
    subtitle: "多租户自然拼读内容生产、AI 处理与学习结果统一总览",
    pipelineTitle: "拼读处理流水线健康度",
    pipelineSub: "各阶段在处理任务量 · 实时快照",
    systemOk: "系统正常",
    trendTitle: "已就绪任务趋势",
    trendRange: "过去 14 小时",
    providerTitle: "Provider 运维状态",
    providerDetails: "详情",
    anomaliesTitle: "最近异常事件",
    pendingPill: "待关注",
    modalTitle: "执行处置动作",
    reasonLabel: "处置原因（必填）",
    reasonPlaceholder: "请填写本次处置的原因，将记入审计日志",
    submit: "提交",
    cancel: "取消",
    placeholderToast: "原型演示：已记录处置意向",
    reasonRequired: "请先填写处置原因",
    actionFailed: "处置失败，请重试",
    liveNoData: "实时运营数据加载中或暂不可用（不展示示例数据）"
  },
  en: {
    eyebrow: "Console / Command Center",
    title: "Platform Command Center",
    subtitle: "Unified view of multi-tenant phonics content production, AI processing and learning outcomes",
    pipelineTitle: "Phonics processing pipeline health",
    pipelineSub: "In-flight task volume per phase · realtime snapshot",
    systemOk: "System healthy",
    trendTitle: "Ready-task trend",
    trendRange: "Past 14 hours",
    providerTitle: "Provider operations status",
    providerDetails: "Details",
    anomaliesTitle: "Recent anomalies",
    pendingPill: "to review",
    modalTitle: "Run remediation action",
    reasonLabel: "Reason (required)",
    reasonPlaceholder: "Describe why you are taking this action — recorded in the audit log",
    submit: "Submit",
    cancel: "Cancel",
    placeholderToast: "Prototype: remediation intent recorded",
    reasonRequired: "Please enter a reason first",
    actionFailed: "Action failed, please retry",
    liveNoData: "Live operations data is loading or unavailable (no sample data shown)"
  }
};

const PROVIDER_PREFIX = "DashScope · ";

const SEVERITY_TONE: Record<string, Tone> = {
  critical: "danger",
  warning: "warning",
  info: "info",
  ok: "neutral"
};

function hhmm(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso || "");
  return match ? match[1] : "—";
}

export function CommandCenter(props: CommandCenterProps) {
  const { language, tenantScope, dataMode, operations, permissions, onIssueAction, onNavigate } = props;
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();

  const live = dataMode === "live" && operations ? operations : null;

  const kpis = live ? operationsToKpis(live) : commandKpis();
  // Mock funnel is scope-aware: when a tenant is selected, recompute the five
  // phase counts from that tenant's jobs (the design folds parsing into OCR).
  const mockPhases = (): PhaseStat[] => {
    const base = phaseStats();
    if (tenantScope === "all") {
      return base;
    }
    const scoped = consoleJobs().filter((job) => job.tenant === tenantScope);
    return base.map((phase) => ({
      ...phase,
      count: scoped.filter((job) => job.status === phase.statusKey || (phase.statusKey === "ocr" && job.status === "parsing")).length
    }));
  };
  const phases: PhaseStat[] = live ? operationsToPhaseStats(live) : mockPhases();
  const maxCount = Math.max(1, ...phases.map((p) => p.count));
  const anomalies: ConsoleAnomaly[] = live ? [] : consoleAnomalies();
  const issues: AdminOperationsIssue[] = live ? live.issues : [];
  const providers = live
    ? providerConfigToProviders(live)
    : consoleProviders()
        .filter((p) => p.enabled)
        .slice(0, 4);

  const generatedAt = live && typeof live.summary.generated_at === "string" ? hhmm(String(live.summary.generated_at)) : "—";

  const [activeIssue, setActiveIssue] = useState<AdminOperationsIssue | null>(null);
  const [reason, setReason] = useState("");

  // In live mode, never fall back to fabricated mock seeds when the operations
  // snapshot is missing (loading, or a failed fetch). Show an honest placeholder
  // instead of inventing KPIs/providers/anomalies under the "live" badge.
  if (dataMode === "live" && !operations) {
    return (
      <PageRoot screen="command">
        <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />
        <EmptyState>{c.liveNoData}</EmptyState>
      </PageRoot>
    );
  }

  const issueActionEnabled = (issue: AdminOperationsIssue): boolean =>
    !!onIssueAction && (!issue.requiredPermission || permissions.includes(issue.requiredPermission));

  const openIssueModal = (issue: AdminOperationsIssue) => {
    setReason("");
    setActiveIssue(issue);
  };

  const closeIssueModal = () => {
    setActiveIssue(null);
    setReason("");
  };

  const submitIssueAction = async () => {
    if (!activeIssue || !onIssueAction) {
      return;
    }
    const trimmed = reason.trim();
    if (!trimmed) {
      toast(c.reasonRequired);
      return;
    }
    const issue = activeIssue;
    closeIssueModal();
    try {
      await onIssueAction(issue, trimmed);
    } catch {
      toast(c.actionFailed);
    }
  };

  const totalPending = live ? issues.length : anomalies.length;

  return (
    <PageRoot screen="command">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      {/* KPI grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(158px,1fr))", gap: 13, marginBottom: 16 }}>
        {kpis.map((kpi) => (
          <MetricCard
            key={kpi.labelKey}
            label={t(kpi.labelKey)}
            value={kpi.value}
            delta={kpi.delta}
            positive={kpi.positive}
            sub={t(kpi.subKey)}
            barTone={kpi.barTone}
          />
        ))}
      </div>

      {/* Pipeline + provider two-col */}
      <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 16, alignItems: "stretch", marginBottom: 16 }}>
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 18px" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{c.pipelineTitle}</div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{c.pipelineSub}</div>
            </div>
            <div
              style={{
                marginLeft: "auto",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11.5,
                color: "var(--success)",
                background: "var(--success-subtle)",
                padding: "3px 10px",
                borderRadius: 20,
                fontWeight: 600
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} />
              {c.systemOk}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 18 }}>
            {phases.map((phase) => {
              const tone = TONE_TOKENS[phase.tone];
              return (
                <div key={phase.statusKey} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "11px 12px", background: "var(--surface-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 3, flex: "none", background: tone.c }} />
                    <span style={{ fontSize: 11.5, color: "var(--text-2)" }}>{t(phase.labelKey)}</span>
                  </div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 19, fontWeight: 600, lineHeight: 1 }}>{phase.count.toLocaleString()}</div>
                  <div style={{ height: 4, borderRadius: 3, background: "var(--bg-subtle)", marginTop: 8, overflow: "hidden" }}>
                    <div style={{ height: 4, borderRadius: 3, background: tone.c, width: `${Math.max(4, (phase.count / maxCount) * 100)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: "var(--text-2)", fontWeight: 500 }}>{c.trendTitle}</span>
              {live && <PrototypeBadge language={language} />}
              <span style={{ marginLeft: "auto", fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)" }}>{c.trendRange}</span>
            </div>
            <Sparkline series={READY_TREND_SERIES} />
          </div>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 18px" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.providerTitle}</div>
            <button
              type="button"
              onClick={() => onNavigate("providers")}
              style={{
                marginLeft: "auto",
                border: "none",
                background: "none",
                padding: 0,
                fontSize: 11.5,
                color: "var(--brand)",
                cursor: "pointer",
                fontWeight: 500,
                fontFamily: "inherit"
              }}
            >
              {c.providerDetails}
            </button>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {providers.map((provider) => {
              const tone = TONE_TOKENS[PROVIDER_STATUS_META[provider.status].tone];
              return (
                <div key={provider.id} style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={bigDotStyle(tone.c, tone.bg)} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {provider.name.replace(PROVIDER_PREFIX, "")}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>{provider.use}</div>
                  </div>
                  <div style={{ textAlign: "right", flex: "none" }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, fontWeight: 600, color: "var(--text)" }}>
                      {provider.success ? `${provider.success.toFixed(1)}%` : "—"}
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-3)" }}>
                      {provider.latency ? `${provider.latency.toLocaleString()} ms` : "—"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Anomalies */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", padding: "15px 18px 13px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{c.anomaliesTitle}</div>
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--danger)", marginLeft: 9, background: "var(--danger-subtle)", padding: "1px 7px", borderRadius: 20 }}>
            {totalPending} {c.pendingPill}
          </span>
        </div>
        <div>
          {live
            ? issues.map((issue) => {
                const tone = TONE_TOKENS[SEVERITY_TONE[issue.severity] ?? "neutral"];
                const enabled = issueActionEnabled(issue);
                return (
                  <AnomalyRow
                    key={issue.id}
                    barColor={tone.c}
                    title={issue.statusLabel}
                    meta={issue.reason}
                    time={generatedAt}
                    actionLabel={issue.recommendedAction}
                    actionDisabled={!enabled}
                    onAction={enabled ? () => openIssueModal(issue) : undefined}
                  />
                );
              })
            : anomalies.map((anomaly, index) => {
                const tone = TONE_TOKENS[anomaly.tone];
                return (
                  <AnomalyRow
                    key={`${anomaly.title}-${index}`}
                    barColor={tone.c}
                    title={anomaly.title}
                    meta={anomaly.meta}
                    time={anomaly.time}
                    actionLabel={anomaly.action}
                    onAction={() => toast(c.placeholderToast)}
                  />
                );
              })}
        </div>
      </div>

      <Modal open={activeIssue !== null} onClose={closeIssueModal} width={440} ariaLabel={c.modalTitle}>
        {activeIssue && (
          <>
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>{c.modalTitle}</div>
            <div style={{ fontSize: 13, color: "var(--text-2)", marginTop: 8, lineHeight: 1.6 }}>{activeIssue.statusLabel}</div>
            <label htmlFor="cc-issue-reason" style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-2)", margin: "16px 0 6px" }}>
              {c.reasonLabel}
            </label>
            <textarea
              id="cc-issue-reason"
              aria-label={c.reasonLabel}
              className="le-input"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder={c.reasonPlaceholder}
              rows={3}
              style={{
                width: "100%",
                resize: "vertical",
                minHeight: 72,
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--bg-subtle)",
                padding: "9px 12px",
                fontSize: 13,
                color: "var(--text)",
                outline: "none",
                fontFamily: "inherit",
                boxSizing: "border-box"
              }}
            />
            <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
              <button
                type="button"
                onClick={closeIssueModal}
                className="le-hover-soft"
                style={{
                  flex: 1,
                  height: 38,
                  border: "1px solid var(--border-strong)",
                  borderRadius: 8,
                  background: "var(--surface)",
                  color: "var(--text)",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "inherit"
                }}
              >
                {c.cancel}
              </button>
              <button
                type="button"
                onClick={submitIssueAction}
                disabled={!reason.trim()}
                style={{
                  flex: 1,
                  height: 38,
                  border: "none",
                  borderRadius: 8,
                  background: reason.trim() ? "var(--brand)" : "var(--border-strong)",
                  color: reason.trim() ? "var(--brand-fg)" : "var(--text-3)",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: reason.trim() ? "pointer" : "not-allowed",
                  fontFamily: "inherit"
                }}
              >
                {c.submit}
              </button>
            </div>
          </>
        )}
      </Modal>
    </PageRoot>
  );
}

function AnomalyRow({
  barColor,
  title,
  meta,
  time,
  actionLabel,
  actionDisabled = false,
  onAction
}: {
  barColor: string;
  title: string;
  meta: string;
  time: string;
  actionLabel: string;
  actionDisabled?: boolean;
  onAction?: () => void;
}) {
  const disabled = actionDisabled || !onAction;
  return (
    <div className="le-hover-soft" style={{ display: "flex", alignItems: "stretch", gap: 13, padding: "13px 18px", borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 3, alignSelf: "stretch", borderRadius: 3, flex: "none", background: barColor }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{title}</div>
        <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 3 }}>{meta}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, flex: "none" }}>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}>{time}</span>
        <button
          type="button"
          onClick={onAction}
          disabled={disabled}
          className={disabled ? undefined : "le-hover-soft"}
          style={{
            height: 28,
            padding: "0 12px",
            border: "1px solid var(--border-strong)",
            borderRadius: 7,
            background: "var(--surface)",
            color: disabled ? "var(--text-3)" : "var(--text-2)",
            fontSize: 12,
            fontWeight: 500,
            cursor: disabled ? "not-allowed" : "pointer",
            fontFamily: "inherit",
            whiteSpace: "nowrap"
          }}
        >
          {actionLabel}
        </button>
      </div>
    </div>
  );
}
