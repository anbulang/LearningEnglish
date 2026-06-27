import { useState } from "react";
import {
  JOB_STATUS_META,
  JOB_STATUS_ORDER,
  TONE_TOKENS,
  consoleJobs,
  type ConsoleJob,
  type JobStatusKey
} from "../domain/consoleData";
import { materialsToJobs } from "../domain/liveMappers";
import { CloseButton, Drawer, EmptyState, FilterChip, StatusBadge, badgeStyle, dotStyle } from "../components/ui";
import { createTranslator, localize } from "../i18n/i18n";
import { useToast } from "../components/providers";
import { PageHeader, PageRoot } from "./shared";
import type { ContentPipelineProps } from "./contracts";

type ChipKey = "all" | JobStatusKey;

const copy = {
  zh: {
    eyebrow: "主控 / 内容管道",
    title: "内容管道",
    subtitle: "监控家长上传自然拼读讲义的 AI 处理流水线 · 快速定位卡住或失败的任务",
    chip: { all: "全部", queued: "排队", ocr: "OCR", parsing: "解析", review: "待校对", done: "已就绪", failed: "失败" } as Record<ChipKey, string>,
    colJob: "任务 ID",
    colFamily: "家庭 / 孩子",
    colType: "类型",
    colStatus: "状态",
    colDur: "耗时",
    colProvider: "Provider",
    colTime: "上传",
    empty: "该筛选下暂无任务",
    tableFoot: "点击任意一行查看处理时间线、阶段日志与失败重试",
    drawerEyebrow: "任务详情",
    detFamily: "家庭 / 孩子 ·",
    detType: "类型 ·",
    detTenant: "租户",
    detProvider: "Provider ·",
    detUploaded: "上传时间 ·",
    detToday: "今日",
    timeline: "处理时间线",
    stageLog: "阶段日志",
    failTitle: "失败原因",
    failReason: "图像过曝且倾斜，OCR 置信度 0.42 低于阈值 0.65，解析阶段无法提取拼读结构化字段。",
    retry: "重新处理",
    stageName: { queued: "进入队列", ocr: "OCR 识别", parsing: "结构化解析", review: "人工校对", done: "生成知识包" } as Record<string, string>,
    stateLabel: { done: "完成", active: "进行中", failed: "失败", pending: "等待" } as Record<string, string>,
    timeUsed: (s: string) => `· 用时 ${s}s`,
    close: "关闭",
    retryReason: "运维台手动重试",
    retryDone: (id: string) => `已重新提交任务 ${id}`,
    retryFail: "重试失败，请稍后再试"
  },
  en: {
    eyebrow: "Console / Content Pipeline",
    title: "Content Pipeline",
    subtitle: "Monitor the AI processing pipeline for parent-uploaded phonics worksheets · quickly spot stuck or failed jobs",
    chip: { all: "All", queued: "Queued", ocr: "OCR", parsing: "Parsing", review: "Review", done: "Ready", failed: "Failed" } as Record<ChipKey, string>,
    colJob: "Job ID",
    colFamily: "Family / Child",
    colType: "Type",
    colStatus: "Status",
    colDur: "Duration",
    colProvider: "Provider",
    colTime: "Uploaded",
    empty: "No jobs under this filter",
    tableFoot: "Click any row to view the timeline, stage log and failure retry",
    drawerEyebrow: "Job detail",
    detFamily: "Family / Child ·",
    detType: "Type ·",
    detTenant: "tenant",
    detProvider: "Provider ·",
    detUploaded: "Uploaded ·",
    detToday: "Today",
    timeline: "Processing timeline",
    stageLog: "Stage log",
    failTitle: "Failure reason",
    failReason: "Image is overexposed and skewed; OCR confidence 0.42 is below the 0.65 threshold, so the parse stage cannot extract structured phonics fields.",
    retry: "Retry",
    stageName: { queued: "Enqueued", ocr: "OCR recognition", parsing: "Structured parse", review: "Manual review", done: "Build knowledge pack" } as Record<string, string>,
    stateLabel: { done: "Done", active: "In progress", failed: "Failed", pending: "Pending" } as Record<string, string>,
    timeUsed: (s: string) => `· took ${s}s`,
    close: "Close",
    retryReason: "manual retry from console",
    retryDone: (id: string) => `Resubmitted job ${id}`,
    retryFail: "Retry failed, please try again later"
  }
};

const STAGE_ORDER: JobStatusKey[] = ["queued", "ocr", "parsing", "review", "done"];

type StageState = "done" | "active" | "failed" | "pending";

function stageStateOf(jobStatus: JobStatusKey, index: number): StageState {
  if (jobStatus === "failed") {
    return index < 2 ? "done" : index === 2 ? "failed" : "pending";
  }
  if (jobStatus === "done") {
    return "done";
  }
  const idx = STAGE_ORDER.indexOf(jobStatus);
  if (index < idx) return "done";
  if (index === idx) return "active";
  return "pending";
}

function stageColor(state: StageState): string {
  if (state === "done") return "var(--success)";
  if (state === "active") return "var(--info)";
  if (state === "failed") return "var(--danger)";
  return "var(--text-3)";
}

export function ContentPipeline({ language, tenantScope, dataMode, materials, onRetryJob }: ContentPipelineProps) {
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();

  const [filter, setFilter] = useState<ChipKey>("all");
  const [drawerId, setDrawerId] = useState<string | null>(null);

  const jobs: ConsoleJob[] = dataMode === "live" ? materialsToJobs(materials) : consoleJobs();
  const counts: Record<ChipKey, number> = { all: jobs.length } as Record<ChipKey, number>;
  for (const status of JOB_STATUS_ORDER) {
    counts[status] = jobs.filter((job) => job.status === status).length;
  }
  const rows = filter === "all" ? jobs : jobs.filter((job) => job.status === filter);
  const chipKeys: ChipKey[] = ["all", ...JOB_STATUS_ORDER];

  const drawerJob = drawerId ? jobs.find((job) => job.id === drawerId) ?? null : null;

  const handleRetry = async (job: ConsoleJob) => {
    if (onRetryJob) {
      try {
        await onRetryJob(job.id, c.retryReason);
        toast(c.retryDone(job.id));
        setDrawerId(null);
      } catch {
        toast(c.retryFail);
      }
      return;
    }
    toast(c.retryDone(job.id));
    setDrawerId(null);
  };

  const th: React.CSSProperties = { textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 8px" };
  const thR: React.CSSProperties = { ...th, textAlign: "right" };

  return (
    <PageRoot screen="pipeline">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        {chipKeys.map((key) => (
          <FilterChip
            key={key}
            active={filter === key}
            label={c.chip[key]}
            count={counts[key] ?? 0}
            onClick={() => setFilter(key)}
          />
        ))}
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={{ ...th, padding: "9px 18px" }}>{c.colJob}</th>
              <th style={th}>{c.colFamily}</th>
              <th style={th}>{c.colType}</th>
              <th style={th}>{c.colStatus}</th>
              <th style={thR}>{c.colDur}</th>
              <th style={th}>{c.colProvider}</th>
              <th style={{ ...thR, padding: "9px 18px" }}>{c.colTime}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((job) => {
              const meta = JOB_STATUS_META[job.status];
              const tone = TONE_TOKENS[meta.tone];
              const processing = job.status === "ocr" || job.status === "parsing";
              return (
                <tr
                  key={job.id}
                  className="le-hover-soft"
                  role="button"
                  tabIndex={0}
                  aria-label={job.id}
                  onClick={() => setDrawerId(job.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setDrawerId(job.id);
                    }
                  }}
                  style={{ borderTop: "1px solid var(--border)", cursor: "pointer" }}
                >
                  <td style={{ padding: "11px 18px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--brand)", fontWeight: 500 }}>{job.id}</td>
                  <td style={{ padding: "11px 8px" }}>
                    <div style={{ fontWeight: 500, color: "var(--text)" }}>{job.family}</div>
                    <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>{job.child}</div>
                  </td>
                  <td style={{ padding: "11px 8px", color: "var(--text-2)" }}>{job.type}</td>
                  <td style={{ padding: "11px 8px" }}>
                    <span style={badgeStyle(meta.tone)}>
                      {processing ? (
                        <span
                          className="le-spin"
                          style={{
                            width: 9,
                            height: 9,
                            border: `1.6px solid ${tone.c}`,
                            borderTopColor: "transparent",
                            borderRadius: "50%",
                            display: "inline-block"
                          }}
                        />
                      ) : (
                        <span style={dotStyle(tone.c)} />
                      )}
                      {t(meta.labelKey)}
                    </span>
                  </td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-2)" }}>
                    {job.ms ? `${(job.ms / 1000).toFixed(1)}s` : "—"}
                  </td>
                  <td style={{ padding: "11px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-2)" }}>{job.provider}</td>
                  <td style={{ padding: "11px 18px", textAlign: "right", fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-2)" }}>{job.time}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <EmptyState>{c.empty}</EmptyState>}
        <div style={{ padding: "11px 18px", borderTop: "1px solid var(--border)", fontSize: 11.5, color: "var(--text-3)" }}>{c.tableFoot}</div>
      </div>

      <Drawer open={drawerJob !== null} onClose={() => setDrawerId(null)} width={468} closeLabel={c.close} ariaLabel={drawerJob?.id}>
        {drawerJob && (
          <PipelineDrawer
            job={drawerJob}
            c={c}
            statusLabel={t(JOB_STATUS_META[drawerJob.status].labelKey)}
            onClose={() => setDrawerId(null)}
            onRetry={() => handleRetry(drawerJob)}
          />
        )}
      </Drawer>
    </PageRoot>
  );
}

function PipelineDrawer({
  job,
  c,
  statusLabel,
  onClose,
  onRetry
}: {
  job: ConsoleJob;
  c: (typeof copy)["zh"];
  statusLabel: string;
  onClose: () => void;
  onRetry: () => void;
}) {
  const meta = JOB_STATUS_META[job.status];
  const failed = job.status === "failed";
  const logs = failed
    ? [
        { t: "09:41:02", m: "task accepted" },
        { t: "09:41:03", m: "OCR start (Qwen-VL)" },
        { t: "09:41:07", m: "OCR done conf=0.42" },
        { t: "09:41:07", m: "parse start" },
        { t: "09:41:12", m: "ERROR low_confidence" }
      ]
    : [
        { t: `${job.time}:02`, m: "task accepted" },
        { t: `${job.time}:03`, m: "OCR start" },
        { t: `${job.time}:06`, m: "OCR done conf=0.94" },
        { t: `${job.time}:06`, m: "parse start" },
        { t: `${job.time}:09`, m: job.status === "done" ? "pack generated" : "parsing…" }
      ];

  return (
    <>
      <div style={{ flex: "none", display: "flex", alignItems: "center", gap: 12, padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{c.drawerEyebrow}</div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 600, color: "var(--text)", marginTop: 1 }}>{job.id}</div>
        </div>
        <span style={{ marginLeft: 6 }}>
          <StatusBadge tone={meta.tone}>{statusLabel}</StatusBadge>
        </span>
        <span style={{ marginLeft: "auto" }}>
          <CloseButton onClick={onClose} label={c.close} />
        </span>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px" }}>
        <div style={{ fontSize: 12.5, lineHeight: 1.9, color: "var(--text-2)", marginBottom: 20 }}>
          <div>
            <span style={{ color: "var(--text-3)" }}>{c.detFamily}</span>{" "}
            <span style={{ color: "var(--text)", fontWeight: 500 }}>{job.family} · {job.child}</span>
          </div>
          <div>
            <span style={{ color: "var(--text-3)" }}>{c.detType}</span> {job.type} ·{" "}
            <span style={{ color: "var(--text-3)" }}>{c.detTenant}</span> {job.tenant}
          </div>
          <div>
            <span style={{ color: "var(--text-3)" }}>{c.detProvider}</span>{" "}
            <span style={{ fontFamily: "var(--mono)" }}>{job.provider}</span>
          </div>
          <div>
            <span style={{ color: "var(--text-3)" }}>{c.detUploaded}</span>{" "}
            <span style={{ fontFamily: "var(--mono)" }}>{c.detToday} {job.time}</span>
          </div>
        </div>

        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text)", marginBottom: 10 }}>{c.timeline}</div>
        <div style={{ position: "relative", paddingLeft: 2, marginBottom: 24 }}>
          <div style={{ position: "absolute", left: 7, top: 10, bottom: 10, width: 2, background: "var(--border)" }} />
          {STAGE_ORDER.map((key, index) => {
            const state = stageStateOf(job.status, index);
            const color = stageColor(state);
            return (
              <div key={key} style={{ display: "flex", gap: 13, padding: "6px 0", position: "relative" }}>
                <span
                  style={{
                    width: 13,
                    height: 13,
                    borderRadius: "50%",
                    flex: "none",
                    background: state === "pending" ? "var(--surface)" : color,
                    border: `2px solid ${color}`,
                    position: "relative",
                    zIndex: 1,
                    boxShadow: state === "active" ? "0 0 0 4px var(--info-subtle)" : undefined
                  }}
                />
                <div style={{ paddingTop: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: state === "pending" ? "var(--text-3)" : "var(--text)" }}>
                    {c.stageName[key]}{" "}
                    {state === "done" && (
                      <span style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--text-3)", fontWeight: 400 }}>
                        {c.timeUsed((0.8 + index * 0.9).toFixed(1))}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>{c.stateLabel[state]}</div>
                </div>
              </div>
            );
          })}
        </div>

        {failed && (
          <div style={{ border: "1px solid var(--danger-subtle)", background: "var(--danger-subtle)", borderRadius: 9, padding: "13px 14px", marginBottom: 22 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--danger)", marginBottom: 6 }}>{c.failTitle}</div>
            <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.6 }}>{c.failReason}</div>
            <button
              type="button"
              onClick={onRetry}
              style={{
                marginTop: 11,
                height: 32,
                padding: "0 16px",
                border: "none",
                borderRadius: 7,
                background: "var(--danger)",
                color: "#fff",
                fontSize: 12.5,
                fontWeight: 600,
                cursor: "pointer",
                fontFamily: "inherit"
              }}
            >
              {c.retry}
            </button>
          </div>
        )}

        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text)", marginBottom: 10 }}>{c.stageLog}</div>
        <div style={{ border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-2)", padding: "11px 13px", fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.9 }}>
          {logs.map((log, index) => (
            <div key={index} style={{ display: "flex", gap: 10 }}>
              <span style={{ color: "var(--text-3)", flex: "none" }}>{log.t}</span>
              <span style={{ color: "var(--text-2)" }}>{log.m}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
