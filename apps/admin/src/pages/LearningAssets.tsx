import { useEffect, useMemo, useRef, useState } from "react";
import {
  STAGE_META,
  STAGE_ORDER,
  consoleAssets,
  rollupMedia,
  type AssetMediaState,
  type PhonicsAsset,
  type StageKey
} from "../domain/consoleData";
import { createTranslator, localize } from "../i18n/i18n";
import { FilterChip, Modal } from "../components/ui";
import { IconChevronRight, IconTrash } from "../components/icons";
import { useConfirm, useToast } from "../components/providers";
import { PageHeader, PageRoot, PrototypeBadge } from "./shared";
import { liveAssetsToConsole } from "../domain/liveMappers";
import type { LearningAssetsProps } from "./contracts";

/*
 * NOTE on mock vs live: the phonics curriculum (《自然拼读教学宝典》K–3 scope &
 * sequence) has NO backend equivalent. In MOCK mode we render the full mock
 * curriculum (`consoleAssets()`) with the scope-and-sequence band, per-stage
 * chips, and working optimistic mutations. In LIVE mode the backend exposes a
 * FLAT list of per-material derived media (no phonics stage / IPA / curriculum):
 * `liveAssetsToConsole` buckets every item into one stage, so we hide the
 * scope-and-sequence band + per-stage chips and render a flat grid. The
 * regen / edit / remove actions have NO backend, so in live mode they are
 * disabled and flagged with <PrototypeBadge />.
 */

const copy = {
  zh: {
    eyebrow: "内容 / 学习资产",
    title: "学习资产",
    subtitleA: "按《自然拼读教学宝典》K–3 完整教学序列组织 · 共 ",
    subtitleB: " 项学习资产",
    subtitleLiveA: "讲义衍生媒体（音频 / 配图）· 共 ",
    subtitleLiveB: " 项资产",
    seqTitle: "教学序列 · Scope & Sequence",
    readyPrefix: "就绪 ",
    all: "全部",
    regen: "重生成媒体",
    regening: "生成中…",
    edit: "编辑",
    removeTitle: "下架",
    metaCvc: "音素分段",
    metaSight: "整词记忆",
    metaReaderA: "可解码率 ",
    metaReaderB: "%",
    metaExample: "示例 · ",
    pillBackfill: " 补齐",
    pillRetry: " 重试",
    enLabel: "英",
    usLabel: "美",
    imgLabel: "图",
    editTitle: "编辑资产 · ",
    fieldPhoneme: "音标 / 分类",
    fieldExample: "示例词",
    examplePh: "如 sun",
    cancel: "取消",
    save: "保存",
    regenToast: "已重新生成媒体",
    saveToast: "资产已更新",
    removeToast: "资产已下架",
    removeBodyA: "确认下架学习资产「",
    removeBodyB: "」？孩子端将不再展示该项。",
    removeConfirm: "下架",
    regenPending: "生成中…"
  },
  en: {
    eyebrow: "Content / Learning Assets",
    title: "Learning Assets",
    subtitleA: "Organized by the full K–3 phonics scope & sequence · ",
    subtitleB: " learning assets",
    subtitleLiveA: "Per-material derived media (audio / images) · ",
    subtitleLiveB: " assets",
    seqTitle: "Scope & Sequence",
    readyPrefix: "",
    all: "All",
    regen: "Regenerate",
    regening: "Generating…",
    edit: "Edit",
    removeTitle: "Remove",
    metaCvc: "Phoneme segmenting",
    metaSight: "Whole-word",
    metaReaderA: "",
    metaReaderB: "% decodable",
    metaExample: "e.g. ",
    pillBackfill: " backfill",
    pillRetry: " retry",
    enLabel: "EN",
    usLabel: "US",
    imgLabel: "IMG",
    editTitle: "Edit asset · ",
    fieldPhoneme: "Phoneme / category",
    fieldExample: "Example word",
    examplePh: "e.g. sun",
    cancel: "Cancel",
    save: "Save",
    regenToast: "Media regenerated",
    saveToast: "Asset updated",
    removeToast: "Asset removed",
    removeBodyA: "Remove learning asset “",
    removeBodyB: "”? It will no longer appear for children.",
    removeConfirm: "Remove",
    regenPending: "Generating…"
  }
};

interface Override {
  phoneme?: string;
  example?: string;
  media?: { en: AssetMediaState; us: AssetMediaState; img: AssetMediaState };
}

interface EditDraft {
  key: string;
  stage: StageKey;
  grapheme: string;
  phoneme: string;
  example: string;
}

const assetKey = (a: { stage: StageKey; grapheme: string }) => `${a.stage}:${a.grapheme}`;

/** Apply an override's media onto the base asset media (keeping "—" channels). */
function mergeMedia(base: PhonicsAsset["media"], ov?: Override["media"]): PhonicsAsset["media"] {
  if (!ov) return base;
  return {
    en: base.en === "—" ? "—" : ov.en,
    us: base.us === "—" ? "—" : ov.us,
    img: base.img === "—" ? "—" : ov.img
  };
}

export function LearningAssets(_props: LearningAssetsProps) {
  const { language, dataMode, liveAssets } = _props;
  // Live data is a flat list with no phonics curriculum: hide the scope-and-
  // sequence band + per-stage chips, render a flat grid, and disable the
  // (backend-less) regen / edit / remove actions.
  const live = dataMode === "live" && liveAssets !== null;
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();
  const confirm = useConfirm();
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // Cancel any in-flight regen timers if the screen unmounts (it is routed).
  useEffect(() => {
    const pending = timers.current;
    return () => {
      Object.values(pending).forEach((id) => clearTimeout(id));
    };
  }, []);

  const seed = useMemo(
    () => (live && liveAssets ? liveAssetsToConsole(liveAssets) : consoleAssets()),
    [live, liveAssets]
  );
  const [removed, setRemoved] = useState<Record<string, true>>({});
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [stageFilter, setStageFilter] = useState<StageKey | "all">("all");
  const [draft, setDraft] = useState<EditDraft | null>(null);

  const all = useMemo(() => seed.filter((a) => !removed[assetKey(a)]), [seed, removed]);

  /** Resolve an asset's effective media (override merged over base). */
  const mediaOf = (a: PhonicsAsset) => mergeMedia(a.media, overrides[assetKey(a)]?.media);

  /* Scope & sequence rollup per stage. */
  const stageSeq = STAGE_ORDER.map((key, idx) => {
    const items = all.filter((a) => a.stage === key);
    const ready = items.filter((a) => rollupMedia(mediaOf(a)) === "ready").length;
    const cov = items.length ? Math.round((ready / items.length) * 100) : 0;
    return { key, idx, meta: STAGE_META[key], count: items.length, cov };
  });

  const counts: Record<string, number> = { all: all.length };
  STAGE_ORDER.forEach((k) => {
    counts[k] = all.filter((a) => a.stage === k).length;
  });

  // Live data is flat (single bucketed stage) — ignore the per-stage filter.
  const visible = live || stageFilter === "all" ? all : all.filter((a) => a.stage === stageFilter);

  /* Simulated async media regeneration: pending → ready after ~1600ms. */
  const regenAsset = (a: PhonicsAsset) => {
    const key = assetKey(a);
    const base = a.media;
    const pending: PhonicsAsset["media"] = {
      en: base.en === "—" ? "—" : "pending",
      us: base.us === "—" ? "—" : "pending",
      img: base.img === "—" ? "—" : "pending"
    };
    const ready: PhonicsAsset["media"] = {
      en: base.en === "—" ? "—" : "ready",
      us: base.us === "—" ? "—" : "ready",
      img: base.img === "—" ? "—" : "ready"
    };
    setOverrides((prev) => ({ ...prev, [key]: { ...prev[key], media: pending } }));
    if (timers.current[key]) clearTimeout(timers.current[key]);
    timers.current[key] = setTimeout(() => {
      setOverrides((prev) => ({ ...prev, [key]: { ...prev[key], media: ready } }));
      toast(c.regenToast);
    }, 1600);
  };

  const openEdit = (a: PhonicsAsset) => {
    const ov = overrides[assetKey(a)] ?? {};
    setDraft({
      key: assetKey(a),
      stage: a.stage,
      grapheme: a.grapheme,
      phoneme: ov.phoneme ?? a.phoneme,
      example: ov.example ?? a.example ?? ""
    });
  };

  const saveEdit = () => {
    if (!draft) return;
    setOverrides((prev) => ({
      ...prev,
      [draft.key]: { ...prev[draft.key], phoneme: draft.phoneme, example: draft.example }
    }));
    setDraft(null);
    toast(c.saveToast);
  };

  const removeAsset = (a: PhonicsAsset) => {
    confirm({
      title: c.removeTitle,
      body: (
        <>
          {c.removeBodyA}
          {a.grapheme}
          {c.removeBodyB}
        </>
      ),
      confirmLabel: c.removeConfirm,
      cancelLabel: c.cancel,
      onConfirm: () => {
        setRemoved((prev) => ({ ...prev, [assetKey(a)]: true }));
        toast(c.removeToast);
      }
    });
  };

  const metaText = (a: PhonicsAsset, example: string) => {
    if (a.stage === "cvc") return c.metaCvc;
    if (a.stage === "sight") return c.metaSight;
    if (a.stage === "reader") return `${c.metaReaderA}${a.decodability ?? 0}${c.metaReaderB}`;
    return `${c.metaExample}${example}`;
  };

  const mediaLabels: Record<"en" | "us" | "img", string> = { en: c.enLabel, us: c.usLabel, img: c.imgLabel };

  const draftStageName = draft ? t(STAGE_META[draft.stage].nameKey) : "";

  return (
    <PageRoot screen="assets">
      <PageHeader
        eyebrow={c.eyebrow}
        title={c.title}
        subtitle={
          live ? `${c.subtitleLiveA}${all.length}${c.subtitleLiveB}` : `${c.subtitleA}${all.length}${c.subtitleB}`
        }
        language={language}
        tenantScope={_props.tenantScope}
      />

      {/* Scope & Sequence — mock-only (live data carries no phonics curriculum). */}
      {!live && (
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          boxShadow: "var(--shadow-sm)",
          padding: "16px 18px",
          marginBottom: 18
        }}
      >
        <div style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 14 }}>{c.seqTitle}</div>
        <div style={{ display: "flex", alignItems: "stretch" }}>
          {stageSeq.map((g) => (
            <div key={g.key} style={{ display: "contents" }}>
              <div style={{ flex: 1, minWidth: 0, paddingRight: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: 6,
                      flex: "none",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: "var(--mono)",
                      fontSize: 11,
                      fontWeight: 600,
                      color: "#fff",
                      background: g.meta.color
                    }}
                  >
                    {String(g.idx + 1).padStart(2, "0")}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text)", whiteSpace: "nowrap" }}>
                      {t(g.meta.nameKey)}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "var(--text-3)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis"
                      }}
                    >
                      {g.meta.en}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 5, marginTop: 10 }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 17, fontWeight: 600, color: "var(--text)" }}>
                    {g.count}
                  </span>
                  <span style={{ fontSize: 10.5, color: "var(--text-3)" }}>
                    {c.readyPrefix}
                    {g.cov}%{language === "en" ? " ready" : ""}
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    borderRadius: 3,
                    background: "var(--bg-subtle)",
                    overflow: "hidden",
                    marginTop: 8
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.max(4, g.cov)}%`,
                      background: g.meta.color,
                      borderRadius: 3
                    }}
                  />
                </div>
              </div>
              {g.idx < STAGE_ORDER.length - 1 && (
                <div
                  style={{
                    flex: "none",
                    display: "flex",
                    alignItems: "center",
                    color: "var(--text-3)",
                    paddingRight: 8
                  }}
                >
                  <IconChevronRight size={14} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      )}

      {/* Filter chips — mock-only (flat live data has no per-stage buckets). */}
      {!live && (
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <FilterChip
          active={stageFilter === "all"}
          label={c.all}
          count={counts.all}
          onClick={() => setStageFilter("all")}
        />
        {STAGE_ORDER.map((k) => (
          <FilterChip
            key={k}
            active={stageFilter === k}
            label={t(STAGE_META[k].nameKey)}
            count={counts[k]}
            onClick={() => setStageFilter(k)}
          />
        ))}
      </div>
      )}

      {/* Asset cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(168px,1fr))", gap: 12 }}>
        {visible.map((a, idx) => {
          // Live items are flat (often duplicate stage+grapheme) — disambiguate
          // the React key with the array index. Mock keys stay the stable assetKey.
          const itemKey = live ? `${assetKey(a)}#${idx}` : assetKey(a);
          const ov = overrides[assetKey(a)] ?? {};
          const phoneme = ov.phoneme ?? a.phoneme;
          const example = ov.example ?? a.example ?? "";
          const media = mediaOf(a);
          const rollup = rollupMedia(media);
          const regening = (["en", "us", "img"] as const).some((k) => media[k] === "pending");
          const color = STAGE_META[a.stage].color;
          const gl = a.grapheme.length;
          const gSize = gl <= 3 ? 28 : gl <= 8 ? 18 : 14;
          const glyphMono = !(a.stage === "reader" || a.stage === "sight");

          const badgeTone = regening
            ? { fg: "var(--warning)", bg: "var(--warning-subtle)" }
            : rollup === "ready"
              ? { fg: "var(--success)", bg: "var(--success-subtle)" }
              : rollup === "pending"
                ? { fg: "var(--info)", bg: "var(--info-subtle)" }
                : { fg: "var(--danger)", bg: "var(--danger-subtle)" };
          const rollupKey = (
            { ready: "asset.media.ready", pending: "asset.media.pending", failed: "asset.media.failed" } as const
          )[rollup];
          const badgeLabel = regening ? c.regenPending : t(rollupKey);

          const pills = (["en", "us", "img"] as const)
            .filter((k) => media[k] && media[k] !== "—")
            .map((k) => {
              const st = media[k];
              const col = st === "ready" ? "var(--success)" : st === "pending" ? "var(--warning)" : "var(--danger)";
              const bg =
                st === "ready" ? "var(--success-subtle)" : st === "pending" ? "var(--warning-subtle)" : "var(--danger-subtle)";
              const lbl =
                st === "failed"
                  ? `${mediaLabels[k]}${c.pillRetry}`
                  : st === "pending"
                    ? `${mediaLabels[k]}${c.pillBackfill}`
                    : mediaLabels[k];
              return { k, label: lbl, col, bg };
            });

          const actionBtn = {
            height: 27,
            padding: "0 9px",
            border: "1px solid var(--border)",
            borderRadius: 6,
            background: "var(--surface)",
            color: "var(--text-2)",
            fontSize: 11.5,
            fontWeight: 500,
            cursor: "pointer",
            fontFamily: "inherit",
            whiteSpace: "nowrap" as const
          };

          return (
            <div
              key={itemKey}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                boxShadow: "var(--shadow-sm)",
                overflow: "hidden"
              }}
            >
              <div
                style={{
                  position: "relative",
                  height: 96,
                  borderBottom: "1px solid var(--border)",
                  background: `color-mix(in srgb, ${color} 8%, var(--surface))`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    top: 8,
                    left: 9,
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#fff",
                    background: color,
                    padding: "2px 7px",
                    borderRadius: 5
                  }}
                >
                  {t(STAGE_META[a.stage].nameKey)}
                </span>
                <span
                  style={{
                    position: "absolute",
                    top: 9,
                    right: 10,
                    fontFamily: "var(--mono)",
                    fontSize: 11.5,
                    fontWeight: 700,
                    color: "var(--text-3)"
                  }}
                >
                  {phoneme}
                </span>
                <span
                  style={{
                    fontFamily: glyphMono ? "var(--mono)" : "inherit",
                    fontSize: gSize,
                    fontWeight: 700,
                    color,
                    textAlign: "center",
                    padding: "0 12px",
                    lineHeight: 1.15
                  }}
                >
                  {a.grapheme}
                </span>
              </div>

              <div style={{ padding: "11px 12px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 8,
                    marginBottom: 8
                  }}
                >
                  <span style={{ fontSize: 11.5, color: "var(--text-2)" }}>{metaText(a, example)}</span>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      fontSize: 11.5,
                      fontWeight: 600,
                      padding: "2px 9px",
                      borderRadius: 20,
                      whiteSpace: "nowrap",
                      color: badgeTone.fg,
                      background: badgeTone.bg
                    }}
                  >
                    {badgeLabel}
                  </span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {pills.map((p) => (
                    <span
                      key={p.k}
                      style={{
                        display: "inline-flex",
                        fontSize: 11,
                        fontWeight: 600,
                        padding: "3px 8px",
                        borderRadius: 6,
                        color: p.col,
                        background: p.bg
                      }}
                    >
                      {p.label}
                    </span>
                  ))}
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    marginTop: 11,
                    paddingTop: 10,
                    borderTop: "1px solid var(--border)"
                  }}
                >
                  <button
                    type="button"
                    onClick={() => !live && !regening && regenAsset(a)}
                    disabled={live || regening}
                    className={live || regening ? undefined : "le-hover-soft"}
                    style={{ ...actionBtn, ...(live || regening ? { opacity: 0.55, cursor: "default" } : null) }}
                  >
                    {regening ? c.regening : c.regen}
                  </button>
                  {live ? (
                    /* No backend for edit/remove — flag as prototype and disable. */
                    <PrototypeBadge language={language} style={{ marginLeft: "auto" }} />
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => openEdit(a)}
                        className="le-hover-soft"
                        style={actionBtn}
                      >
                        {c.edit}
                      </button>
                      <button
                        type="button"
                        onClick={() => removeAsset(a)}
                        title={c.removeTitle}
                        aria-label={c.removeTitle}
                        className="le-hover-danger"
                        style={{
                          marginLeft: "auto",
                          width: 27,
                          height: 27,
                          flex: "none",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                          background: "var(--surface)",
                          color: "var(--danger)",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        <IconTrash size={13} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit modal */}
      <Modal open={draft !== null} onClose={() => setDraft(null)} width={420}>
        {draft && (
          <>
            <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 2 }}>
              {c.editTitle}
              {draftStageName}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text)", marginBottom: 18 }}>{draft.grapheme}</div>

            <div style={{ marginBottom: 14 }}>
              <label
                style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-2)", marginBottom: 6 }}
              >
                {c.fieldPhoneme}
              </label>
              <input
                className="le-input"
                aria-label={c.fieldPhoneme}
                value={draft.phoneme}
                onChange={(e) => setDraft({ ...draft, phoneme: e.target.value })}
                style={{
                  width: "100%",
                  height: 38,
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  background: "var(--bg-subtle)",
                  padding: "0 12px",
                  fontSize: 13,
                  color: "var(--text)",
                  outline: "none",
                  fontFamily: "var(--mono)",
                  boxSizing: "border-box"
                }}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label
                style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-2)", marginBottom: 6 }}
              >
                {c.fieldExample}
              </label>
              <input
                className="le-input"
                aria-label={c.fieldExample}
                value={draft.example}
                placeholder={c.examplePh}
                onChange={(e) => setDraft({ ...draft, example: e.target.value })}
                style={{
                  width: "100%",
                  height: 38,
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  background: "var(--bg-subtle)",
                  padding: "0 12px",
                  fontSize: 13,
                  color: "var(--text)",
                  outline: "none",
                  fontFamily: "inherit",
                  boxSizing: "border-box"
                }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                type="button"
                onClick={() => setDraft(null)}
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
                onClick={saveEdit}
                style={{
                  flex: 1,
                  height: 38,
                  border: "none",
                  borderRadius: 8,
                  background: "var(--brand)",
                  color: "var(--brand-fg)",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  fontFamily: "inherit"
                }}
              >
                {c.save}
              </button>
            </div>
          </>
        )}
      </Modal>
    </PageRoot>
  );
}
