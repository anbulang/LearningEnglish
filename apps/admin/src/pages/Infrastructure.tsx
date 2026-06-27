import { TONE_TOKENS, consoleInfraNodes, type InfraNode } from "../domain/consoleData";
import { operationsToInfraNodes } from "../domain/liveMappers";
import { EmptyState, accentBarStyle, bigDotStyle } from "../components/ui";
import { IconInfo } from "../components/icons";
import { createTranslator, localize } from "../i18n/i18n";
import { PageHeader, PageRoot } from "./shared";
import type { InfrastructureProps } from "./contracts";

const copy = {
  zh: {
    eyebrow: "运维 / 基础设施",
    title: "基础设施",
    subtitle: "系统核心组件健康度快照",
    bannerLead: "以下为",
    bannerStrong: "配置与数据库快照",
    bannerMid: "，每 5 分钟刷新 · ",
    bannerTail: "非实时 telemetry",
    liveNoData: "实时运营数据加载中或暂不可用（不展示示例数据）"
  },
  en: {
    eyebrow: "Operations / Infrastructure",
    title: "Infrastructure",
    subtitle: "Health snapshot of core system components",
    bannerLead: "Below is a ",
    bannerStrong: "configuration & database snapshot",
    bannerMid: ", refreshed every 5 min · ",
    bannerTail: "not realtime telemetry",
    liveNoData: "Live operations data is loading or unavailable (no sample data shown)"
  }
};

export function Infrastructure({ language, tenantScope, dataMode, operations }: InfrastructureProps) {
  const t = createTranslator(language);
  const c = localize(language, copy);

  // In live mode never substitute mock component cards when the operations
  // snapshot is missing (loading / failed fetch) — show an honest placeholder.
  if (dataMode === "live" && !operations) {
    return (
      <PageRoot screen="infrastructure">
        <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />
        <EmptyState>{c.liveNoData}</EmptyState>
      </PageRoot>
    );
  }

  const nodes: InfraNode[] = dataMode === "live" && operations ? operationsToInfraNodes(operations) : consoleInfraNodes();

  return (
    <PageRoot screen="infrastructure">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "var(--info-subtle)",
          border: "1px solid color-mix(in srgb,var(--info) 22%, transparent)",
          borderRadius: 9,
          padding: "11px 15px",
          marginBottom: 18,
          color: "var(--info)"
        }}
      >
        <IconInfo size={17} style={{ flex: "none" }} />
        <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>
          {c.bannerLead}
          <span style={{ fontWeight: 600, color: "var(--text)" }}>{c.bannerStrong}</span>
          {c.bannerMid}
          <span style={{ color: "var(--text-3)" }}>{c.bannerTail}</span>
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
        {nodes.map((node, index) => {
          const tone = TONE_TOKENS[node.tone];
          return (
            <div
              key={`${node.name}-${index}`}
              style={{
                position: "relative",
                overflow: "hidden",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                boxShadow: "var(--shadow-sm)",
                padding: "16px 17px 16px 19px"
              }}
            >
              <div style={accentBarStyle(tone.c)} />
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 14 }}>
                <span style={bigDotStyle(tone.c, tone.bg)} />
                <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)", flex: 1 }}>{node.name}</span>
                <span style={{ fontSize: 11, color: "var(--text-3)" }}>{t(node.statusKey)}</span>
              </div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 18, fontWeight: 600, color: "var(--text)", lineHeight: 1 }}>
                {node.metric}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 8 }}>{node.sub}</div>
            </div>
          );
        })}
      </div>
    </PageRoot>
  );
}
