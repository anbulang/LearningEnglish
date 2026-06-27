import { useEffect, useRef, useState } from "react";
import {
  COST_BASE,
  COST_FIXED,
  COST_KIDS,
  GEN_STAGES,
  STAGE_META,
  TIER_LABEL,
  TIER_MULT,
  TIER_TONE,
  TONE_TOKENS,
  cacheCards,
  costLevers,
  routeDefs,
  type StageKey,
  type TierKey
} from "../domain/consoleData";
import { MetricCard, StatusBadge, Switch, badgeStyle } from "../components/ui";
import { useToast } from "../components/providers";
import { createTranslator, localize } from "../i18n/i18n";
import { PageHeader, PageRoot, PrimaryButton, PrototypeBadge, PrototypeBanner, scopeNote } from "./shared";
import type { CostTokenProps } from "./contracts";

const copy = {
  zh: {
    eyebrow: "运维 / 成本与 Token",
    title: "成本与 Token 优化",
    subtitle: "按任务分层调度模型、缓存固定前缀、预生成内容复用 —— 把 AI 边际成本压到最低",
    leverTitle: "优化杠杆",
    leverCaption: "开关任一项即时模拟月度成本",
    leverEnabledA: "已启用 ",
    leverEnabledB: " 项 · 预计每月节省 ",
    perMonth: "/ 月",
    structTitle: "成本结构",
    structSub: "当前开关下的月度预测",
    structProjectedLabel: "预计本月 AI 成本",
    baselineLabel: "未优化基线 ¥",
    savedPrefix: "省 ",
    perKidLabel: "单活跃孩子 / 月",
    marginalLabel: "边际成本占比",
    routeTitle: "模型分层路由",
    routeSub: "调用网关按任务类型自动路由到对应层级模型 · 约 80% 调用下沉到小模型",
    colTask: "任务类型",
    colTier: "层级",
    colModel: "模型",
    colCalls: "日调用",
    colCost: "日成本",
    colStatus: "优化状态",
    routeFootA: "应用后日成本合计 ",
    routeFootB: " · 月度约 ",
    routeRecSuffix: " 项可继续下沉",
    applyRoute: "应用路由规则",
    applyToast: "路由规则已下发到调用网关 ✓",
    statusSink: "建议下沉至",
    statusFixed: "必要调用",
    statusMatch: "符合建议",
    statusOptimized: "已优化",
    genTitle: "预生成与内容复用",
    genCaption: "一次生成入库 · 后续命中复用，新增学员零增量调用",
    genSub: "选择拼读阶段，批量预生成其全部资产媒体并写入复用库",
    genBusyText: "批量预生成中 · 写入复用库…",
    genBtn: "批量预生成",
    genBtnBusy: "预生成中…",
    genLibA: "库内已生成 ",
    genLibB: " · 待生成 ",
    genDoneA: "已预生成 ",
    genDoneB: " 项「",
    genDoneC: "」资产并写入复用库，本批复用率 +",
    genDoneD: "pt",
    genToast: "批量预生成完成 · 已写入复用库 ✓",
    protoNote: "本屏成本与 Token 数字均为示例数据，暂无后端数据源；应用路由规则、批量预生成均为前端模拟，不会下发到任何服务。"
  },
  en: {
    eyebrow: "Operations / Cost & Token",
    title: "Cost & Token Optimization",
    subtitle: "Tier models per task, cache fixed prefixes, and reuse pre-generated content — drive AI marginal cost to the floor",
    leverTitle: "Optimization levers",
    leverCaption: "Toggle any lever to simulate monthly cost instantly",
    leverEnabledA: "Enabled ",
    leverEnabledB: " · est. monthly savings ",
    perMonth: "/ mo",
    structTitle: "Cost structure",
    structSub: "Monthly projection under current toggles",
    structProjectedLabel: "Projected AI cost this month",
    baselineLabel: "Unoptimized baseline ¥",
    savedPrefix: "−",
    perKidLabel: "Per active child / mo",
    marginalLabel: "Marginal cost share",
    routeTitle: "Tiered model routing",
    routeSub: "The call gateway auto-routes by task type to the matching model tier · ~80% of calls drop to small models",
    colTask: "Task type",
    colTier: "Tier",
    colModel: "Model",
    colCalls: "Daily calls",
    colCost: "Daily cost",
    colStatus: "Optimization",
    routeFootA: "Applied daily cost total ",
    routeFootB: " · ~monthly ",
    routeRecSuffix: " can still drop further",
    applyRoute: "Apply routing rules",
    applyToast: "Routing rules pushed to the call gateway ✓",
    statusSink: "Drop to ",
    statusFixed: "Required call",
    statusMatch: "Matches recommendation",
    statusOptimized: "Optimized",
    genTitle: "Pre-generation & content reuse",
    genCaption: "Generate once into the library · later requests hit reuse, new students add zero incremental calls",
    genSub: "Pick a phonics stage to batch pre-generate all of its asset media into the reuse library",
    genBusyText: "Batch pre-generating · writing to reuse library…",
    genBtn: "Batch pre-generate",
    genBtnBusy: "Generating…",
    genLibA: "Generated in library ",
    genLibB: " · pending ",
    genDoneA: "Pre-generated ",
    genDoneB: " “",
    genDoneC: "” assets into the reuse library; batch reuse rate +",
    genDoneD: "pt",
    genToast: "Batch pre-generation done · written to reuse library ✓",
    protoNote: "All cost & token numbers on this screen are sample data with no backend source; Apply routing rules and Batch pre-generate are front-end simulations that reach no service."
  }
};

const yen = (n: number) => "¥" + n.toLocaleString();

export function CostToken({ language, tenantScope, dataMode }: CostTokenProps) {
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();
  const live = dataMode === "live";

  const [costOff, setCostOff] = useState<Record<string, boolean>>({});
  const [routeTier, setRouteTier] = useState<Record<string, TierKey>>({});
  const [genStage, setGenStage] = useState<StageKey>("letter");
  const [genBusy, setGenBusy] = useState(false);
  const [genResult, setGenResult] = useState<{ stage: StageKey; n: number } | null>(null);
  const genTimer = useRef<ReturnType<typeof setTimeout>>();

  // Cancel the in-flight batch pre-generation timer if the screen unmounts.
  useEffect(() => {
    return () => {
      if (genTimer.current) {
        clearTimeout(genTimer.current);
      }
    };
  }, []);

  const levers = costLevers();
  const routes = routeDefs();
  const caches = cacheCards();

  /* ── Cost-structure formulas (ported verbatim from the design) ── */
  const savedTotal = levers.filter((l) => !costOff[l.key]).reduce((a, l) => a + l.save, 0);
  const projected = COST_BASE - savedTotal;
  const savedPct = Math.round((savedTotal / COST_BASE) * 100);
  const perKid = projected / COST_KIDS;
  const marginalPct = Math.round(((projected - COST_FIXED) / projected) * 100);
  const projectedPct = Math.round((projected / COST_BASE) * 100);
  const leversOn = levers.filter((l) => !costOff[l.key]).length;

  /* ── Routing formulas ── */
  const tierOf = (r: ReturnType<typeof routeDefs>[number]) => routeTier[r.key] ?? r.def;
  const costOfRoute = (r: ReturnType<typeof routeDefs>[number]) => {
    const tier = tierOf(r);
    const mult = TIER_MULT[tier];
    return mult != null ? Math.round(r.base * mult) : r.base;
  };
  const aboveRec = (r: ReturnType<typeof routeDefs>[number]) => {
    const tier = tierOf(r);
    const m = TIER_MULT[tier];
    const rm = TIER_MULT[r.rec];
    return m != null && rm != null && m > rm;
  };
  const routeDailyTotal = routes.reduce((a, r) => a + costOfRoute(r), 0);
  const routeMonthly = routeDailyTotal * 30;
  const routeRecCount = routes.filter(aboveRec).length;

  const toggleLever = (key: string) => setCostOff((prev) => ({ ...prev, [key]: !prev[key] }));

  const batchPregen = () => {
    if (genBusy) return;
    const stage = genStage;
    const n = 40 + GEN_STAGES.indexOf(stage) * 20;
    setGenBusy(true);
    setGenResult(null);
    if (genTimer.current) clearTimeout(genTimer.current);
    genTimer.current = setTimeout(() => {
      setGenBusy(false);
      setGenResult({ stage, n });
      toast(c.genToast);
    }, 1700);
  };

  const costKpis = [
    { label: language === "zh" ? "今日 Token 消耗" : "Token usage today", value: language === "zh" ? "4.82 亿" : "482M", delta: "▲ 6.2%", positive: true, sub: language === "zh" ? "输入 78% · 输出 22%" : "input 78% · output 22%", barTone: "brand" as const },
    { label: language === "zh" ? "今日 AI 成本" : "AI cost today", value: yen(Math.round(projected / 30)), delta: "▼ " + savedPct + "%", positive: true, sub: language === "zh" ? "按当前优化" : "under current optimization", barTone: "success" as const },
    { label: language === "zh" ? "本月预计成本" : "Projected cost this month", value: yen(projected), delta: "▼ " + yen(savedTotal), positive: true, sub: (language === "zh" ? "未优化 " : "unoptimized ") + yen(COST_BASE), barTone: "brand" as const },
    { label: language === "zh" ? "累计已省" : "Saved to date", value: yen(savedTotal), delta: (language === "zh" ? "省 " : "−") + savedPct + "%", positive: true, sub: language === "zh" ? "相对基线" : "vs baseline", barTone: "success" as const },
    { label: language === "zh" ? "单活跃孩子/月" : "Per active child / mo", value: "¥" + perKid.toFixed(2), delta: "▼ 0.9%", positive: true, sub: language === "zh" ? "AI 边际成本" : "AI marginal cost", barTone: "info" as const },
    { label: language === "zh" ? "内容复用率" : "Content reuse rate", value: "91.7%", delta: "▲ 2.3pt", positive: true, sub: language === "zh" ? "命中已生成库" : "hits generated library", barTone: "success" as const }
  ];

  const genResultText = genResult
    ? c.genDoneA + genResult.n + c.genDoneB + t(STAGE_META[genResult.stage].nameKey) + c.genDoneC + (2 + Math.round(genResult.n / 40)) + c.genDoneD
    : "";

  return (
    <PageRoot screen="cost">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      {live && <PrototypeBanner language={language} note={c.protoNote} />}

      {/* ── KPI grid ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(158px,1fr))", gap: 13, marginBottom: 16 }}>
        {costKpis.map((k) => (
          <MetricCard key={k.label} label={k.label} value={k.value} delta={k.delta} positive={k.positive} sub={k.sub} barTone={k.barTone} />
        ))}
      </div>

      {/* ── Levers + cost structure ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 16, alignItems: "stretch", marginBottom: 16 }}>
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 18px" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 5 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.leverTitle}</div>
            <span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--text-3)" }}>{c.leverCaption}</span>
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 2 }}>
            {c.leverEnabledA}
            <span style={{ fontFamily: "var(--mono)", color: "var(--text)", fontWeight: 600 }}>{leversOn} / {levers.length}</span>
            {c.leverEnabledB}
            <span style={{ fontFamily: "var(--mono)", color: "var(--success)", fontWeight: 600 }}>{yen(savedTotal)}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {levers.map((l) => {
              const on = !costOff[l.key];
              return (
                <div key={l.key} style={{ display: "flex", alignItems: "flex-start", gap: 13, padding: "13px 0", borderTop: "1px solid var(--border)" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: on ? "var(--text)" : "var(--text-3)" }}>{t(l.nameKey)}</span>
                      {l.tagKey && (
                        <span style={{ fontSize: 10, fontWeight: 600, color: "var(--brand)", background: "var(--brand-subtle)", padding: "1px 7px", borderRadius: 5 }}>
                          {t(l.tagKey)}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 3, lineHeight: 1.5 }}>{t(l.descKey)}</div>
                  </div>
                  <div style={{ textAlign: "right", flex: "none" }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 600, color: on ? "var(--success)" : "var(--text-3)" }}>{yen(l.save)}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-3)", marginTop: 1 }}>{c.perMonth}</div>
                  </div>
                  <Switch on={on} onToggle={() => toggleLever(l.key)} ariaLabel={t(l.nameKey)} />
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 18px", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 3 }}>{c.structTitle}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 16 }}>{c.structSub}</div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 30, fontWeight: 700, letterSpacing: "-1px", color: "var(--text)", lineHeight: 1 }}>{yen(projected)}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 6 }}>{c.structProjectedLabel}</div>
          <div style={{ marginTop: 18 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>
              <span>{c.baselineLabel}{COST_BASE.toLocaleString()}</span>
              <span style={{ color: "var(--success)", fontWeight: 600 }}>{c.savedPrefix}{savedPct}%</span>
            </div>
            <div style={{ height: 10, borderRadius: 6, background: "var(--bg-subtle)", overflow: "hidden", display: "flex" }}>
              <div style={{ height: "100%", width: `${projectedPct}%`, background: "var(--brand)" }} />
              <div style={{ height: "100%", flex: 1, background: "repeating-linear-gradient(45deg,var(--success-subtle),var(--success-subtle) 5px,transparent 5px,transparent 10px)" }} />
            </div>
          </div>
          <div style={{ marginTop: "auto", paddingTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: "var(--border)", border: "1px solid var(--border)", borderRadius: 9, overflow: "hidden" }}>
            <div style={{ background: "var(--surface)", padding: "11px 13px" }}>
              <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.perKidLabel}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 600, color: "var(--text)", marginTop: 3 }}>¥{perKid.toFixed(2)}</div>
            </div>
            <div style={{ background: "var(--surface)", padding: "11px 13px" }}>
              <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.marginalLabel}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 600, color: "var(--text)", marginTop: 3 }}>{marginalPct}%</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tiered routing table ── */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", overflow: "hidden", marginBottom: 16 }}>
        <div style={{ padding: "15px 18px 13px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{c.routeTitle}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{c.routeSub}</div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={{ textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 18px" }}>{c.colTask}</th>
              <th style={{ textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 8px" }}>{c.colTier}</th>
              <th style={{ textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 8px" }}>{c.colModel}</th>
              <th style={{ textAlign: "right", fontWeight: 600, fontSize: 11, padding: "9px 8px" }}>{c.colCalls}</th>
              <th style={{ textAlign: "right", fontWeight: 600, fontSize: 11, padding: "9px 8px" }}>{c.colCost}</th>
              <th style={{ textAlign: "right", fontWeight: 600, fontSize: 11, padding: "9px 18px" }}>{c.colStatus}</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((r) => {
              const tier = tierOf(r);
              const above = aboveRec(r);
              const fixed = r.allow.length <= 1;
              let statusText: string;
              let statusTone: "warning" | "neutral" | "success";
              if (above) {
                statusText = c.statusSink + t(TIER_LABEL[r.rec]);
                statusTone = "warning";
              } else if (fixed) {
                statusText = c.statusFixed;
                statusTone = "neutral";
              } else if (tier === r.rec) {
                statusText = c.statusMatch;
                statusTone = "success";
              } else {
                statusText = c.statusOptimized;
                statusTone = "success";
              }
              return (
                <tr key={r.key} className="le-hover-soft" style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "11px 18px", fontWeight: 500, color: "var(--text)" }}>{r.task}</td>
                  <td style={{ padding: "11px 8px" }}>
                    {fixed ? (
                      <StatusBadge tone={TIER_TONE[tier]}>{t(TIER_LABEL[tier])}</StatusBadge>
                    ) : (
                      <select
                        aria-label={r.task}
                        className="le-input"
                        value={tier}
                        onChange={(e) => setRouteTier((prev) => ({ ...prev, [r.key]: e.target.value as TierKey }))}
                        style={{ height: 28, border: "1px solid var(--border)", borderRadius: 7, background: "var(--surface)", color: "var(--text)", fontSize: 12, fontFamily: "inherit", padding: "0 6px", cursor: "pointer" }}
                      >
                        {r.allow.map((a) => (
                          <option key={a} value={a}>{t(TIER_LABEL[a])}</option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td style={{ padding: "11px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-2)" }}>{r.model[tier] ?? "—"}</td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", color: "var(--text-2)" }}>{r.calls}</td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", color: "var(--text)" }}>{yen(costOfRoute(r))}</td>
                  <td style={{ padding: "11px 18px", textAlign: "right" }}>
                    <span style={badgeStyle(statusTone)}>{statusText}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div style={{ display: "flex", alignItems: "center", gap: 13, padding: "12px 18px", borderTop: "1px solid var(--border)", background: "var(--surface-2)", flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--text-2)" }}>
            {c.routeFootA}
            <span style={{ fontFamily: "var(--mono)", fontWeight: 600, color: "var(--text)" }}>{yen(routeDailyTotal)}</span>
            {c.routeFootB}
            <span style={{ fontFamily: "var(--mono)", fontWeight: 600, color: "var(--text)" }}>{yen(routeMonthly)}</span>
          </span>
          {routeRecCount > 0 && (
            <span style={{ fontSize: 11.5, color: "var(--warning)", fontWeight: 500 }}>· {routeRecCount}{c.routeRecSuffix}</span>
          )}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 9 }}>
            {live && <PrototypeBadge language={language} />}
            <PrimaryButton onClick={() => toast(c.applyToast)} disabled={live} style={{ height: 32 }}>{c.applyRoute}</PrimaryButton>
          </div>
        </div>
      </div>

      {/* ── Pre-generation & reuse ── */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 18px", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 4 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{c.genTitle}</div>
          <span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--text-3)" }}>{c.genCaption}</span>
        </div>
        <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 13 }}>
          {c.genSub}
          {scopeNote(language, tenantScope)}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          {GEN_STAGES.map((s) => {
            const active = genStage === s;
            return (
              <button
                key={s}
                type="button"
                aria-pressed={active}
                onClick={() => setGenStage(s)}
                style={{
                  height: 30,
                  padding: "0 12px",
                  borderRadius: 8,
                  fontSize: 12.5,
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  whiteSpace: "nowrap",
                  border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
                  background: active ? "var(--brand-subtle)" : "var(--surface)",
                  color: active ? "var(--brand)" : "var(--text-2)"
                }}
              >
                {t(STAGE_META[s].nameKey)}
              </button>
            );
          })}
        </div>
        {genBusy && (
          <div style={{ marginBottom: 13 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11.5, color: "var(--text-2)", marginBottom: 6 }}>
              <span style={{ width: 9, height: 9, border: "1.6px solid var(--brand)", borderTopColor: "transparent", borderRadius: "50%", animation: "le-spin .7s linear infinite", display: "inline-block" }} />
              {c.genBusyText}
            </div>
            <div style={{ height: 8, borderRadius: 5, background: "var(--bg-subtle)", overflow: "hidden" }}>
              <div style={{ height: "100%", background: "var(--brand)", borderRadius: 5, animation: "le-fill 1.6s linear forwards" }} />
            </div>
          </div>
        )}
        {genResult && !genBusy && (
          <div style={{ display: "flex", alignItems: "center", gap: 9, background: "var(--success-subtle)", border: "1px solid color-mix(in srgb,var(--success) 22%, transparent)", borderRadius: 9, padding: "11px 14px", marginBottom: 13, fontSize: 12.5, color: "var(--text-2)" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--success)", flex: "none" }} />
            {genResultText}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
          <button
            type="button"
            onClick={batchPregen}
            disabled={genBusy || live}
            style={{
              height: 34,
              padding: "0 16px",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "inherit",
              color: genBusy || live ? "var(--text-3)" : "#fff",
              background: genBusy || live ? "var(--border-strong)" : "var(--brand)",
              cursor: genBusy || live ? "not-allowed" : "pointer"
            }}
          >
            {genBusy ? c.genBtnBusy : c.genBtn}
          </button>
          {live && <PrototypeBadge language={language} />}
          <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
            {c.genLibA}
            <span style={{ fontFamily: "var(--mono)", color: "var(--text-2)", fontWeight: 600 }}>2,418</span>
            {c.genLibB}
            <span style={{ fontFamily: "var(--mono)", color: "var(--text-2)", fontWeight: 600 }}>213</span>
          </span>
        </div>
      </div>

      {/* ── Cache cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
        {caches.map((card) => (
          <div key={card.labelKey} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, boxShadow: "var(--shadow-sm)", padding: "16px 17px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", flex: "none", background: card.color }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{t(card.labelKey)}</span>
              <span style={{ marginLeft: "auto", fontFamily: "var(--mono)", fontSize: 17, fontWeight: 600, color: "var(--text)" }}>{card.value}</span>
            </div>
            <div style={{ height: 6, borderRadius: 4, background: "var(--bg-subtle)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${card.pct}%`, background: card.color, borderRadius: 4 }} />
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 10, lineHeight: 1.5 }}>{t(card.descKey)}</div>
          </div>
        ))}
      </div>
    </PageRoot>
  );
}
