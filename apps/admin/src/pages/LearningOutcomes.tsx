import { outcomeKpis, stageMastery } from "../domain/consoleData";
import { createTranslator, localize } from "../i18n/i18n";
import { MetricCard } from "../components/ui";
import { PageHeader, PageRoot, PrototypeBanner, SectionCard } from "./shared";
import type { LearningOutcomesProps } from "./contracts";

const copy = {
  zh: {
    eyebrow: "内容 / 学习结果",
    title: "学习结果",
    subtitle: "孩子在各拼读阶段的练习量与发音掌握度",
    masteryTitle: "各拼读阶段掌握度",
    masterySub: "孩子在该阶段练习的平均发音评分通过率"
  },
  en: {
    eyebrow: "Content / Learning Outcomes",
    title: "Learning Outcomes",
    subtitle: "Practice volume and pronunciation mastery across each phonics stage",
    masteryTitle: "Mastery by phonics stage",
    masterySub: "Average pronunciation pass rate for practice in each stage"
  }
};

export function LearningOutcomes({ language, tenantScope, dataMode }: LearningOutcomesProps) {
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
