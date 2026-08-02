import { outcomeKpis, stageMastery } from "../domain/consoleData";
import { createTranslator, localize } from "../i18n/i18n";
import { MetricCard } from "../components/ui";
import { PageHeader, PageRoot, PrototypeBanner, SectionCard } from "./shared";
import type { LearningOutcomesProps } from "./contracts";
import type { AdminLearningOutcomePoint, AdminLearningOutcomesData } from "../domain/types";

const copy = {
  zh: {
    eyebrow: "内容 / 学习结果",
    title: "学习结果",
    subtitle: "孩子在各拼读阶段的练习量与发音掌握度",
    masteryTitle: "各拼读阶段掌握度",
    masterySub: "孩子在该阶段练习的平均发音评分通过率",
    // live
    liveSubtitle: "近 8 周的复习完成量、单词量与口语练习趋势",
    kpiActiveChildren: "本周活跃孩子",
    kpiActiveChildrenSub: "范围内孩子",
    kpiSessions: "复习完成次数",
    kpiSessionsSub: "近 8 周合计",
    kpiWords: "复习单词量",
    kpiWordsSub: "近 8 周合计",
    kpiSpeaking: "口语练习次数",
    kpiSpeakingSub: "近 8 周合计",
    trendTitle: "每周复习完成趋势",
    trendSub: "每根柱为一个自然周的复习完成次数（由旧到新）",
    emptyTrend: "本周暂无足够趋势数据",
    weakItemsTitle: "近期薄弱项",
    weakItemsEmpty: "近期没有标记的薄弱项",
    weekAxisNote: "周起始（月/日）"
  },
  en: {
    eyebrow: "Content / Learning Outcomes",
    title: "Learning Outcomes",
    subtitle: "Practice volume and pronunciation mastery across each phonics stage",
    masteryTitle: "Mastery by phonics stage",
    masterySub: "Average pronunciation pass rate for practice in each stage",
    // live
    liveSubtitle: "Review completion, vocabulary and speaking trends over the last 8 weeks",
    kpiActiveChildren: "Active children this week",
    kpiActiveChildrenSub: "of children in scope",
    kpiSessions: "Review sessions",
    kpiSessionsSub: "last 8 weeks total",
    kpiWords: "Words reviewed",
    kpiWordsSub: "last 8 weeks total",
    kpiSpeaking: "Speaking attempts",
    kpiSpeakingSub: "last 8 weeks total",
    trendTitle: "Weekly review completion trend",
    trendSub: "Each bar is one calendar week of completed reviews (oldest to newest)",
    emptyTrend: "Not enough trend data yet",
    weakItemsTitle: "Recent weak items",
    weakItemsEmpty: "No weak items flagged recently",
    weekAxisNote: "Week start (M/D)"
  }
};

function formatWeekLabel(weekStart: string): string {
  const parts = weekStart.split("-");
  if (parts.length === 3) {
    return `${Number(parts[1])}/${Number(parts[2])}`;
  }
  return weekStart;
}

function TrendChart({
  points,
  emptyLabel,
  axisNote
}: {
  points: AdminLearningOutcomePoint[];
  emptyLabel: string;
  axisNote: string;
}) {
  const maxValue = points.reduce((max, point) => Math.max(max, point.completedSessions), 0);

  if (points.length < 2 || maxValue === 0) {
    return (
      <div
        style={{
          padding: "26px 0",
          textAlign: "center",
          fontSize: 12.5,
          color: "var(--text-3)"
        }}
      >
        {emptyLabel}
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 10,
          height: 168,
          padding: "8px 2px 0"
        }}
      >
        {points.map((point) => {
          const value = point.completedSessions;
          const heightPct = maxValue > 0 ? Math.max(value > 0 ? 4 : 0, (value / maxValue) * 100) : 0;
          return (
            <div
              key={point.weekStart}
              style={{
                flex: 1,
                minWidth: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "flex-end",
                height: "100%"
              }}
              title={`${point.weekStart} → ${point.weekEnd}: ${value}`}
            >
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 11,
                  fontWeight: 600,
                  color: value > 0 ? "var(--text)" : "var(--text-3)",
                  marginBottom: 5
                }}
              >
                {value}
              </span>
              <span
                style={{
                  display: "block",
                  width: "100%",
                  maxWidth: 40,
                  height: `${heightPct}%`,
                  minHeight: value > 0 ? 4 : 0,
                  borderRadius: "5px 5px 0 0",
                  background: "var(--brand)"
                }}
              />
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 10, padding: "8px 2px 0", borderTop: "1px solid var(--border)" }}>
        {points.map((point) => (
          <span
            key={point.weekStart}
            style={{
              flex: 1,
              minWidth: 0,
              textAlign: "center",
              fontFamily: "var(--mono)",
              fontSize: 10.5,
              color: "var(--text-3)"
            }}
          >
            {formatWeekLabel(point.weekStart)}
          </span>
        ))}
      </div>
      <div style={{ marginTop: 6, fontSize: 10.5, color: "var(--text-3)" }}>{axisNote}</div>
    </div>
  );
}

function LiveOutcomes({
  language,
  tenantScope,
  data
}: {
  language: LearningOutcomesProps["language"];
  tenantScope: LearningOutcomesProps["tenantScope"];
  data: AdminLearningOutcomesData;
}) {
  const c = localize(language, copy);
  const { summary, points } = data;

  return (
    <PageRoot screen="outcomes">
      <PageHeader
        eyebrow={c.eyebrow}
        title={c.title}
        subtitle={c.liveSubtitle}
        language={language}
        tenantScope={tenantScope}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 13, marginBottom: 16 }}>
        <MetricCard
          label={c.kpiActiveChildren}
          value={`${summary.activeChildrenLatest} / ${summary.childrenInScope}`}
          sub={c.kpiActiveChildrenSub}
          barTone="brand"
        />
        <MetricCard
          label={c.kpiSessions}
          value={summary.completedSessions.toLocaleString()}
          sub={c.kpiSessionsSub}
          barTone="success"
        />
        <MetricCard
          label={c.kpiWords}
          value={summary.reviewedWords.toLocaleString()}
          sub={c.kpiWordsSub}
          barTone="info"
        />
        <MetricCard
          label={c.kpiSpeaking}
          value={summary.speakingAttempts.toLocaleString()}
          sub={c.kpiSpeakingSub}
          barTone="brand"
        />
      </div>

      <SectionCard style={{ marginBottom: 16 }}>
        <div style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 3 }}>{c.trendTitle}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 16 }}>{c.trendSub}</div>
          <TrendChart points={points} emptyLabel={c.emptyTrend} axisNote={c.weekAxisNote} />
        </div>
      </SectionCard>

      <SectionCard>
        <div style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{c.weakItemsTitle}</div>
          {summary.weakItems.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>{c.weakItemsEmpty}</div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {summary.weakItems.map((item) => (
                <span
                  key={item}
                  style={{
                    fontSize: 12.5,
                    fontWeight: 500,
                    padding: "5px 11px",
                    borderRadius: 7,
                    color: "var(--warning)",
                    background: "var(--warning-subtle)",
                    border: "1px solid var(--warning)"
                  }}
                >
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      </SectionCard>
    </PageRoot>
  );
}

export function LearningOutcomes({ language, tenantScope, dataMode, data }: LearningOutcomesProps) {
  if (data) {
    return <LiveOutcomes language={language} tenantScope={tenantScope} data={data} />;
  }

  const t = createTranslator(language);
  const c = localize(language, copy);
  const kpis = outcomeKpis();
  const mastery = stageMastery();

  return (
    <PageRoot screen="outcomes">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      {dataMode === "live" && <PrototypeBanner language={language} />}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 13, marginBottom: 16 }}>
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

      <SectionCard>
        <div style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 3 }}>{c.masteryTitle}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 16 }}>{c.masterySub}</div>
          <div style={{ display: "grid", gap: 11 }}>
            {mastery.map((row) => (
              <div key={row.label} style={{ display: "grid", gridTemplateColumns: "210px 1fr 46px", gap: 12, alignItems: "center" }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{row.label}</span>
                <span style={{ height: 8, borderRadius: 5, background: "var(--bg-subtle)", overflow: "hidden", display: "block" }}>
                  <span style={{ display: "block", height: "100%", width: `${row.value}%`, background: row.color, borderRadius: 5 }} />
                </span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12.5, fontWeight: 600, color: "var(--text)", textAlign: "right" }}>
                  {row.value}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </SectionCard>
    </PageRoot>
  );
}
