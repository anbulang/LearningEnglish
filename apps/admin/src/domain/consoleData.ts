/*
 * Prototype seed data for the 运维控制台 screens, ported from the
 * "LE 运维控制台" Claude Design system.
 *
 * Convention: UI *chrome* (labels, statuses, headers, captions) is referenced
 * through typed i18n keys (`MessageKey`) and translated per-language at render
 * time. Proper-noun / operator-entered *data* (tenant names, family names,
 * provider configs, ids, sample words, numeric metrics) is kept verbatim — it
 * is data, not chrome, and would not be translated in a real deployment.
 *
 * In mock mode these seeds drive every screen 1:1 with the design. In live mode
 * (`VITE_ADMIN_API_BASE_URL` set) the App overlays real `/v1/admin` data on the
 * screens that have a backend (see domain/selectors live-mappers).
 */
import type { MessageKey } from "../i18n/messages";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "brand";

export interface ToneMeta {
  /** Foreground / text color token. */
  fg: string;
  /** Subtle background token. */
  bg: string;
  /** Solid color token (dots, bars). */
  c: string;
}

export const TONE_TOKENS: Record<Tone, ToneMeta> = {
  success: { fg: "var(--success)", bg: "var(--success-subtle)", c: "var(--success)" },
  warning: { fg: "var(--warning)", bg: "var(--warning-subtle)", c: "var(--warning)" },
  danger: { fg: "var(--danger)", bg: "var(--danger-subtle)", c: "var(--danger)" },
  info: { fg: "var(--info)", bg: "var(--info-subtle)", c: "var(--info)" },
  neutral: { fg: "var(--neutral)", bg: "var(--neutral-subtle)", c: "var(--neutral)" },
  brand: { fg: "var(--brand)", bg: "var(--brand-subtle)", c: "var(--brand)" }
};

/* ───────────────────────── Content pipeline ───────────────────────── */

export type JobStatusKey = "queued" | "ocr" | "parsing" | "review" | "done" | "failed";

export interface ConsoleJob {
  id: string;
  family: string;
  child: string;
  type: string;
  status: JobStatusKey;
  ms: number;
  time: string;
  provider: string;
  tenant: string;
}

export const JOB_STATUS_META: Record<JobStatusKey, { tone: Tone; labelKey: MessageKey }> = {
  queued: { tone: "neutral", labelKey: "status.job.queued" },
  ocr: { tone: "info", labelKey: "status.job.ocr" },
  parsing: { tone: "brand", labelKey: "status.job.parsing" },
  review: { tone: "warning", labelKey: "status.job.review" },
  done: { tone: "success", labelKey: "status.job.done" },
  failed: { tone: "danger", labelKey: "status.job.failed" }
};

export const JOB_STATUS_ORDER: JobStatusKey[] = ["queued", "ocr", "parsing", "review", "done", "failed"];

export function consoleJobs(): ConsoleJob[] {
  return [
    { id: "LE-24817", family: "林家·朵朵", child: "二年级 · 字母组合", type: "字母组合", status: "done", ms: 3100, time: "09:48", provider: "Qwen-VL", tenant: "光明小学" },
    { id: "LE-24816", family: "王家·阳阳", child: "三年级 · 长元音", type: "长元音", status: "ocr", ms: 0, time: "09:47", provider: "Qwen-VL", tenant: "未来双语学堂" },
    { id: "LE-24815", family: "赵家·糖糖", child: "一年级 · CVC 拼读", type: "CVC 拼读", status: "review", ms: 5400, time: "09:45", provider: "Qwen-Max", tenant: "光明小学" },
    { id: "LE-24814", family: "孙家·乐乐", child: "三年级 · 高频词", type: "高频词卡", status: "done", ms: 2200, time: "09:43", provider: "Qwen-VL", tenant: "晨星教育" },
    { id: "LE-24813", family: "周家·安安", child: "K · 字母音卡", type: "字母音卡", status: "failed", ms: 0, time: "09:41", provider: "Qwen-VL", tenant: "海淀拼读中心" },
    { id: "LE-24812", family: "吴家·诺诺", child: "二年级 · 字母组合", type: "字母组合", status: "parsing", ms: 0, time: "09:38", provider: "Qwen-Max", tenant: "未来双语学堂" },
    { id: "LE-24811", family: "郑家·苗苗", child: "K · 字母音卡", type: "字母音卡", status: "queued", ms: 0, time: "09:36", provider: "—", tenant: "晨星教育" },
    { id: "LE-24810", family: "冯家·豆豆", child: "二年级 · CVC 拼读", type: "CVC 拼读", status: "done", ms: 3900, time: "09:33", provider: "Qwen-Max", tenant: "光明小学" },
    { id: "LE-24809", family: "陈家·星星", child: "三年级 · 长元音", type: "长元音", status: "review", ms: 7100, time: "09:30", provider: "Qwen-Max", tenant: "海淀拼读中心" },
    { id: "LE-24808", family: "褚家·萌萌", child: "一年级 · 高频词", type: "高频词卡", status: "done", ms: 1800, time: "09:27", provider: "Qwen-VL", tenant: "未来双语学堂" },
    { id: "LE-24807", family: "卫家·航航", child: "二年级 · CVC 拼读", type: "CVC 拼读", status: "ocr", ms: 0, time: "09:25", provider: "Qwen-VL", tenant: "光明小学" },
    { id: "LE-24805", family: "沈家·壮壮", child: "三年级 · 拼读故事", type: "可解码读物", status: "failed", ms: 0, time: "09:19", provider: "Qwen-VL", tenant: "晨星教育" }
  ];
}

/* ───────────────────────── Tenants ───────────────────────── */

export type TenantPlanKey = "flagship" | "standard" | "trial";
export type TenantStatusKey = "normal" | "quotaWarning";

export const TENANT_PLAN_KEYS: TenantPlanKey[] = ["flagship", "standard", "trial"];
export const TENANT_PLAN_LABEL: Record<TenantPlanKey, MessageKey> = {
  flagship: "plan.flagship",
  standard: "plan.standard",
  trial: "plan.trial"
};
export const TENANT_STATUS_META: Record<TenantStatusKey, { tone: Tone; labelKey: MessageKey }> = {
  normal: { tone: "success", labelKey: "status.tenant.normal" },
  quotaWarning: { tone: "warning", labelKey: "status.tenant.quotaWarning" }
};

export interface ConsoleTenant {
  id: string;
  name: string;
  plan: TenantPlanKey;
  kids: number;
  decks: number;
  /** Recognition success rate, e.g. "97.2%" or "—" for new tenants. */
  rate: string;
  status: TenantStatusKey;
  enabled: boolean;
}

export function consoleTenants(): ConsoleTenant[] {
  return [
    { id: "光明小学", name: "光明小学", plan: "flagship", kids: 312, decks: 461, rate: "97.2%", status: "normal", enabled: true },
    { id: "未来双语学堂", name: "未来双语学堂", plan: "standard", kids: 208, decks: 318, rate: "96.1%", status: "normal", enabled: true },
    { id: "晨星教育", name: "晨星教育", plan: "standard", kids: 164, decks: 205, rate: "95.4%", status: "quotaWarning", enabled: true },
    { id: "海淀拼读中心", name: "海淀拼读中心", plan: "trial", kids: 97, decks: 142, rate: "94.0%", status: "normal", enabled: true }
  ];
}

/* ───────────────────────── Providers ───────────────────────── */

export type ProviderStatusKey = "ok" | "degraded" | "down" | "idle" | "disabled";

export const PROVIDER_STATUS_META: Record<ProviderStatusKey, { tone: Tone; labelKey: MessageKey }> = {
  ok: { tone: "success", labelKey: "status.provider.ok" },
  degraded: { tone: "warning", labelKey: "status.provider.degraded" },
  down: { tone: "danger", labelKey: "status.provider.down" },
  idle: { tone: "neutral", labelKey: "status.provider.idle" },
  disabled: { tone: "neutral", labelKey: "status.provider.disabled" }
};

export interface ConsoleProvider {
  id: string;
  name: string;
  use: string;
  endpoint: string;
  model: string;
  status: ProviderStatusKey;
  success: number;
  latency: number;
  quota: number;
  enabled: boolean;
}

export function consoleProviders(): ConsoleProvider[] {
  return [
    { id: "pv0", name: "DashScope · Qwen-VL", use: "拼读讲义 OCR 识别", endpoint: "https://dashscope.aliyuncs.com", model: "qwen-vl-ocr", status: "ok", success: 99.2, latency: 1840, quota: 72, enabled: true },
    { id: "pv1", name: "DashScope · Qwen-Max", use: "拼读结构化解析", endpoint: "https://dashscope.aliyuncs.com", model: "qwen-max", status: "ok", success: 98.6, latency: 2360, quota: 65, enabled: true },
    { id: "pv2", name: "DashScope · CosyVoice", use: "字母音 / 拼读词 TTS", endpoint: "https://dashscope.aliyuncs.com", model: "cosyvoice-v1", status: "degraded", success: 94.1, latency: 3120, quota: 88, enabled: true },
    { id: "pv3", name: "DashScope · SenseVoice", use: "拼读发音评分", endpoint: "https://dashscope.aliyuncs.com", model: "sensevoice-v1", status: "ok", success: 97.8, latency: 1290, quota: 54, enabled: true },
    { id: "pv4", name: "Doubao（备用）", use: "OCR / 解析 故障转移", endpoint: "https://ark.cn-beijing.volces.com", model: "doubao-pro", status: "idle", success: 0, latency: 0, quota: 0, enabled: false }
  ];
}

/* ───────────────────────── Users & families ───────────────────────── */

export type FamilyStatusKey = "active" | "dormant" | "disabled";

export const FAMILY_STATUS_META: Record<FamilyStatusKey, { tone: Tone; labelKey: MessageKey }> = {
  active: { tone: "success", labelKey: "status.family.active" },
  dormant: { tone: "warning", labelKey: "status.family.dormant" },
  disabled: { tone: "danger", labelKey: "status.family.disabled" }
};

export interface ConsoleChild {
  name: string;
  grade: string;
  progress: number;
  last: string;
  /** Live-mode only: material count, localized with a unit at render time. */
  lastMaterials?: number;
}

export interface ConsoleFamily {
  id: string;
  /** Real parent-account id (impersonation target). Equals `id` for mock seeds. */
  parentId: string;
  name: string;
  phone: string;
  tenant: string;
  reg: string;
  status: FamilyStatusKey;
  children: ConsoleChild[];
  /** "knowledgePacks / reviews / pronunciation" usage triple. */
  usage: string;
}

export function consoleFamilies(): ConsoleFamily[] {
  return [
    { id: "F-1024", parentId: "F-1024", name: "林家", phone: "138****6621", tenant: "光明小学", reg: "2025-09-12", status: "active", usage: "42 / 318 / 96", children: [{ name: "朵朵", grade: "二年级", progress: 78, last: "10 分钟前" }, { name: "然然", grade: "K", progress: 45, last: "2 小时前" }] },
    { id: "F-0987", parentId: "F-0987", name: "赵家", phone: "137****7758", tenant: "光明小学", reg: "2025-08-18", status: "active", usage: "55 / 421 / 133", children: [{ name: "糖糖", grade: "一年级", progress: 83, last: "1 小时前" }, { name: "豆豆", grade: "二年级", progress: 52, last: "昨天" }, { name: "果果", grade: "K", progress: 30, last: "3 天前" }] },
    { id: "F-0931", parentId: "F-0931", name: "周家", phone: "136****8830", tenant: "海淀拼读中心", reg: "2025-07-11", status: "active", usage: "61 / 498 / 172", children: [{ name: "安安", grade: "二年级", progress: 90, last: "刚刚" }, { name: "宁宁", grade: "一年级", progress: 67, last: "30 分钟前" }] },
    { id: "F-0952", parentId: "F-0952", name: "孙家", phone: "135****2210", tenant: "晨星教育", reg: "2025-07-26", status: "dormant", usage: "9 / 46 / 8", children: [{ name: "乐乐", grade: "三年级", progress: 40, last: "12 天前" }] },
    { id: "F-0890", parentId: "F-0890", name: "吴家", phone: "150****4417", tenant: "未来双语学堂", reg: "2025-06-29", status: "disabled", usage: "18 / 120 / 33", children: [{ name: "诺诺", grade: "三年级", progress: 55, last: "已停用" }] }
  ];
}

/* ───────────────────────── Infrastructure ───────────────────────── */

export interface InfraNode {
  name: string;
  metric: string;
  sub: string;
  tone: Tone;
  statusKey: MessageKey;
}

export function consoleInfraNodes(): InfraNode[] {
  return [
    { name: "PostgreSQL 主库", metric: "连接 142 / 200", sub: "复制延迟 0.3s · 14d 无重启", tone: "success", statusKey: "status.infra.normal" },
    { name: "PostgreSQL 只读副本", metric: "连接 38 / 100", sub: "复制延迟 0.8s", tone: "success", statusKey: "status.infra.normal" },
    { name: "Redis 缓存", metric: "内存 3.2 / 8 GB", sub: "命中率 98.7% · evict 0", tone: "success", statusKey: "status.infra.normal" },
    { name: "对象存储 MinIO", metric: "已用 1.4 / 5 TB", sub: "桶 7 · 对象 2.1M", tone: "success", statusKey: "status.infra.normal" },
    { name: "Celery Worker", metric: "在线 12 / 12", sub: "并发 96 · 失败任务 3", tone: "success", statusKey: "status.infra.normal" },
    { name: "任务队列深度", metric: "排队 37", sub: "识别 21 · 媒体补齐 16", tone: "warning", statusKey: "status.infra.attention" }
  ];
}

/* ───────────────────────── Audit & access ───────────────────────── */

export type AuditResultKey = "success" | "intercepted" | "alert";

export const AUDIT_RESULT_META: Record<AuditResultKey, { tone: Tone; labelKey: MessageKey }> = {
  success: { tone: "success", labelKey: "status.audit.success" },
  intercepted: { tone: "danger", labelKey: "status.audit.intercepted" },
  alert: { tone: "warning", labelKey: "status.audit.alert" }
};

export interface ConsoleAuditRow {
  time: string;
  actor: string;
  role: string;
  action: string;
  target: string;
  result: AuditResultKey;
  sensitive: boolean;
}

export function consoleAuditLog(): ConsoleAuditRow[] {
  return [
    { time: "09:46:02", actor: "陈牧之", role: "运维 SRE", action: "重试任务", target: "LE-24813", result: "success", sensitive: false },
    { time: "09:31:55", actor: "李审核", role: "内容审核", action: "代登录", target: "F-1024 · 林家", result: "success", sensitive: true },
    { time: "09:18:40", actor: "王越", role: "只读分析", action: "导出数据", target: "家庭活跃报表", result: "intercepted", sensitive: true },
    { time: "08:55:10", actor: "陈牧之", role: "运维 SRE", action: "切换 Provider", target: "TTS → Doubao", result: "success", sensitive: false },
    { time: "08:40:22", actor: "系统", role: "自动", action: "故障转移", target: "CosyVoice 限流", result: "alert", sensitive: false },
    { time: "08:12:03", actor: "李审核", role: "内容审核", action: "数据导出", target: "周报样本 ×20", result: "success", sensitive: true },
    { time: "07:50:44", actor: "赵管理", role: "超级管理员", action: "修改权限", target: "王越 → 只读", result: "success", sensitive: true }
  ];
}

export interface ConsolePermMatrix {
  /** Permission column labels (i18n keys). */
  permKeys: MessageKey[];
  roles: { name: string; scope: string; grants: number[] }[];
}

export function consolePermMatrix(): ConsolePermMatrix {
  return {
    permKeys: ["perm.viewMonitor", "perm.retryJob", "perm.impersonate", "perm.exportData", "perm.manageProvider"],
    roles: [
      { name: "超级管理员", scope: "全部模块", grants: [1, 1, 1, 1, 1] },
      { name: "运维 SRE", scope: "监控 / 管道 / Provider", grants: [1, 1, 0, 0, 1] },
      { name: "内容审核", scope: "管道 / 资产 / 用户", grants: [1, 1, 1, 1, 0] },
      { name: "只读分析", scope: "监控 / 结果", grants: [1, 0, 0, 0, 0] }
    ]
  };
}

export type MemberStatusKey = "active" | "restricted" | "disabled" | "pending";

export const MEMBER_STATUS_META: Record<MemberStatusKey, { tone: Tone; labelKey: MessageKey }> = {
  active: { tone: "success", labelKey: "status.member.active" },
  restricted: { tone: "warning", labelKey: "status.member.restricted" },
  disabled: { tone: "neutral", labelKey: "status.member.disabled" },
  pending: { tone: "info", labelKey: "status.member.pending" }
};

export interface ConsoleMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: MemberStatusKey;
  last: string;
}

export function consoleMembers(): ConsoleMember[] {
  return [
    { id: "u1", name: "陈牧之", email: "chen@le.cn", role: "运维 SRE", status: "active", last: "刚刚" },
    { id: "u2", name: "李审核", email: "li@le.cn", role: "内容审核", status: "active", last: "12 分钟前" },
    { id: "u3", name: "王越", email: "wang@le.cn", role: "只读分析", status: "restricted", last: "1 小时前" },
    { id: "u4", name: "赵管理", email: "zhao@le.cn", role: "超级管理员", status: "active", last: "昨天" }
  ];
}

/* ───────────────────────── Learning assets (phonics curriculum) ───────────────────────── */

export type StageKey = "letter" | "cvc" | "blend" | "vowel" | "sight" | "reader";

export const STAGE_ORDER: StageKey[] = ["letter", "cvc", "blend", "vowel", "sight", "reader"];

export interface StageMeta {
  key: StageKey;
  nameKey: MessageKey;
  en: string;
  color: string;
}

export const STAGE_META: Record<StageKey, StageMeta> = {
  letter: { key: "letter", nameKey: "stage.letter", en: "Letter Sounds", color: "var(--brand)" },
  cvc: { key: "cvc", nameKey: "stage.cvc", en: "CVC Blending", color: "#3f78c4" },
  blend: { key: "blend", nameKey: "stage.blend", en: "Digraphs & Blends", color: "#b0760a" },
  vowel: { key: "vowel", nameKey: "stage.vowel", en: "Long Vowels", color: "var(--success)" },
  sight: { key: "sight", nameKey: "stage.sight", en: "Sight Words", color: "#7c5cd6" },
  reader: { key: "reader", nameKey: "stage.reader", en: "Decodable Readers", color: "#c2683a" }
};

export type AssetMediaState = "ready" | "pending" | "failed" | "—";

export interface PhonicsAsset {
  stage: StageKey;
  grapheme: string;
  phoneme: string;
  example?: string;
  decodability?: number;
  media: { en: AssetMediaState; us: AssetMediaState; img: AssetMediaState };
}

/**
 * Deterministic media-status generator (index-based, no randomness) so the
 * asset grid is stable across renders and tests — ported from the design.
 */
export function consoleAssets(): PhonicsAsset[] {
  const out: PhonicsAsset[] = [];
  let i = 0;
  const ms = (st: StageKey): PhonicsAsset["media"] => {
    i++;
    const en: AssetMediaState = i % 13 === 0 ? "pending" : i % 17 === 0 ? "failed" : "ready";
    let us: AssetMediaState = i % 11 === 0 ? "pending" : i % 23 === 0 ? "failed" : "ready";
    let img: AssetMediaState = i % 7 === 0 ? "pending" : i % 19 === 0 ? "failed" : "ready";
    if (st === "sight") img = "—";
    if (st === "reader") us = "—";
    return { en, us, img };
  };
  const letters: [string, string, string][] = [
    ["Ss", "/s/", "sun"], ["Aa", "/æ/", "apple"], ["Tt", "/t/", "top"], ["Pp", "/p/", "pen"], ["Ii", "/ɪ/", "ink"],
    ["Nn", "/n/", "net"], ["Mm", "/m/", "mat"], ["Dd", "/d/", "dog"], ["Gg", "/g/", "gas"], ["Oo", "/ɒ/", "ox"],
    ["Cc", "/k/", "cat"], ["Kk", "/k/", "kit"], ["Ee", "/e/", "egg"], ["Uu", "/ʌ/", "up"], ["Rr", "/r/", "run"],
    ["Hh", "/h/", "hat"], ["Bb", "/b/", "bus"], ["Ff", "/f/", "fan"], ["Ll", "/l/", "log"], ["Jj", "/dʒ/", "jam"],
    ["Vv", "/v/", "van"], ["Ww", "/w/", "web"], ["Xx", "/ks/", "box"], ["Yy", "/j/", "yes"], ["Zz", "/z/", "zip"], ["Qu", "/kw/", "queen"]
  ];
  letters.forEach(([g, p, ex]) => out.push({ stage: "letter", grapheme: g, phoneme: p, example: ex, media: ms("letter") }));

  const cvc: [string, string][] = [
    ["cat", "短 a"], ["mat", "短 a"], ["pan", "短 a"], ["bag", "短 a"], ["pen", "短 e"], ["bed", "短 e"], ["net", "短 e"], ["leg", "短 e"],
    ["pig", "短 i"], ["sit", "短 i"], ["lip", "短 i"], ["fin", "短 i"], ["dog", "短 o"], ["hot", "短 o"], ["box", "短 o"], ["mop", "短 o"],
    ["sun", "短 u"], ["cup", "短 u"], ["bug", "短 u"], ["mud", "短 u"]
  ];
  cvc.forEach(([w, v]) => out.push({ stage: "cvc", grapheme: w, phoneme: v, media: ms("cvc") }));

  const blend: [string, string, string][] = [
    ["sh", "/ʃ/", "ship"], ["ch", "/tʃ/", "chip"], ["th", "/θ/", "thin"], ["wh", "/w/", "whip"], ["ph", "/f/", "phone"], ["ck", "/k/", "duck"],
    ["ng", "/ŋ/", "ring"], ["bl", "/bl/", "black"], ["cl", "/kl/", "clap"], ["fl", "/fl/", "flag"], ["gl", "/gl/", "glad"], ["pl", "/pl/", "plan"],
    ["sl", "/sl/", "slip"], ["br", "/br/", "brick"], ["cr", "/kr/", "crab"], ["dr", "/dr/", "drum"], ["fr", "/fr/", "frog"], ["gr", "/gr/", "grin"],
    ["tr", "/tr/", "truck"], ["st", "/st/", "stop"], ["sp", "/sp/", "spin"], ["sn", "/sn/", "snap"], ["sw", "/sw/", "swim"], ["sm", "/sm/", "smell"]
  ];
  blend.forEach(([g, p, ex]) => out.push({ stage: "blend", grapheme: g, phoneme: p, example: ex, media: ms("blend") }));

  const vowel: [string, string, string][] = [
    ["a_e", "/eɪ/", "cake"], ["i_e", "/aɪ/", "bike"], ["o_e", "/oʊ/", "home"], ["u_e", "/juː/", "cube"], ["ai", "/eɪ/", "rain"], ["ay", "/eɪ/", "play"],
    ["ee", "/iː/", "tree"], ["ea", "/iː/", "sea"], ["oa", "/oʊ/", "boat"], ["ow", "/oʊ/", "snow"], ["igh", "/aɪ/", "night"], ["oo", "/uː/", "moon"],
    ["ar", "/ɑːr/", "car"], ["or", "/ɔːr/", "fork"], ["er", "/ɜːr/", "her"], ["ir", "/ɜːr/", "bird"], ["ur", "/ɜːr/", "turn"], ["ou", "/aʊ/", "out"],
    ["oi", "/ɔɪ/", "coin"], ["oy", "/ɔɪ/", "toy"], ["aw", "/ɔː/", "saw"]
  ];
  vowel.forEach(([g, p, ex]) => out.push({ stage: "vowel", grapheme: g, phoneme: p, example: ex, media: ms("vowel") }));

  ["the", "a", "I", "said", "was", "you", "they", "are", "have", "of", "to", "do", "my", "for", "he", "she", "we", "me", "be", "is", "her", "his", "put", "one"].forEach((w) =>
    out.push({ stage: "sight", grapheme: w, phoneme: "整词记忆", media: ms("sight") })
  );

  const readers: [string, string, number][] = [
    ["The Fat Cat", "CVC 短 a", 96], ["Sam and the Ham", "CVC 短 a", 94], ["Tim's Big Win", "CVC 短 i", 91], ["Fun in the Sun", "CVC 短 u", 97],
    ["A Big Red Dog", "CVC + sh", 88], ["The Shop on the Hill", "sh / ll", 85], ["Cake for Jake", "a_e", 82], ["The Green Tree", "ee 长元音", 79],
    ["Night on the Boat", "igh / oa", 74], ["Play in the Rain", "ai / ay", 90]
  ];
  readers.forEach(([t, tg, d]) => out.push({ stage: "reader", grapheme: t, phoneme: tg, decodability: d, media: ms("reader") }));

  return out;
}

/* ───────────────────────── Command Center KPIs / anomalies ───────────────────────── */

export interface ConsoleKpi {
  labelKey: MessageKey;
  value: string;
  delta: string;
  positive: boolean;
  subKey: MessageKey;
  barTone: Tone;
}

export function commandKpis(): ConsoleKpi[] {
  return [
    { labelKey: "kpi.activeFamilies", value: "8,642", delta: "▲ 3.1%", positive: true, subKey: "kpi.vsYesterday", barTone: "brand" },
    { labelKey: "kpi.uploads", value: "1,284", delta: "▲ 12.4%", positive: true, subKey: "kpi.today", barTone: "brand" },
    { labelKey: "kpi.pendingOcr", value: "37", delta: "▲ 9", positive: false, subKey: "kpi.inQueue", barTone: "warning" },
    { labelKey: "kpi.recognitionRate", value: "96.8%", delta: "▲ 0.6pt", positive: true, subKey: "kpi.last24h", barTone: "success" },
    { labelKey: "kpi.pronunciationRuns", value: "5,920", delta: "▲ 7.8%", positive: true, subKey: "kpi.today", barTone: "info" },
    { labelKey: "kpi.weeklyReports", value: "8,512", delta: "▲ 2.4%", positive: true, subKey: "kpi.delivered", barTone: "success" }
  ];
}

/** Phase funnel counts for the command center (all-tenant snapshot). */
export interface PhaseStat {
  labelKey: MessageKey;
  statusKey: JobStatusKey;
  tone: Tone;
  count: number;
}
export function phaseStats(): PhaseStat[] {
  return [
    { labelKey: "phase.queued", statusKey: "queued", tone: "neutral", count: 37 },
    { labelKey: "phase.ocr", statusKey: "ocr", tone: "info", count: 128 },
    { labelKey: "phase.review", statusKey: "review", tone: "warning", count: 54 },
    { labelKey: "phase.done", statusKey: "done", tone: "success", count: 1042 },
    { labelKey: "phase.failed", statusKey: "failed", tone: "danger", count: 9 }
  ];
}
export const READY_TREND_SERIES = [42, 38, 46, 58, 72, 86, 92, 80, 74, 88, 96, 84, 70, 62];

export interface ConsoleAnomaly {
  tone: Tone;
  title: string;
  meta: string;
  time: string;
  action: string;
}
export function consoleAnomalies(): ConsoleAnomaly[] {
  return [
    { tone: "danger", title: "讲义 LE-24805 解析卡住 >6min", meta: "Qwen-Max · 已重试 2 次", time: "09:24", action: "查看" },
    { tone: "warning", title: "CosyVoice TTS 触发限流 429", meta: "近 10 分钟失败率 5.9%", time: "09:19", action: "查看 Provider" },
    { tone: "warning", title: "媒体补齐队列积压 16", meta: "字母音配图生成延迟升高", time: "09:05", action: "查看" },
    { tone: "danger", title: "讲义 LE-24813 OCR 失败", meta: "图像过曝 · 置信度低", time: "08:58", action: "重试" },
    { tone: "neutral", title: "Doubao 备用配额预警 80%", meta: "本月用量接近上限", time: "08:30", action: "查看配额" }
  ];
}

/* ───────────────────────── Learning outcomes ───────────────────────── */

export function outcomeKpis(): ConsoleKpi[] {
  return [
    { labelKey: "okpi.practicingKids", value: "6,120", delta: "▲ 4.2%", positive: true, subKey: "okpi.vsLastWeek", barTone: "brand" },
    { labelKey: "okpi.passRate", value: "88.4%", delta: "▲ 1.1pt", positive: true, subKey: "okpi.last7d", barTone: "success" },
    { labelKey: "okpi.letterStage", value: "73%", delta: "▲ 5pt", positive: true, subKey: "okpi.k1kids", barTone: "info" },
    { labelKey: "okpi.decodable", value: "2,341", delta: "▲ 6.0%", positive: true, subKey: "okpi.thisWeekDone", barTone: "brand" }
  ];
}

export interface StageMasteryRow {
  label: string;
  value: number;
  color: string;
}
export function stageMastery(): StageMasteryRow[] {
  return [
    { label: "字母音 Letter Sounds", value: 94, color: "var(--success)" },
    { label: "CVC 拼读 Blending", value: 89, color: "var(--success)" },
    { label: "字母组合 Digraphs", value: 82, color: "var(--warning)" },
    { label: "长元音 Long Vowels", value: 76, color: "var(--warning)" },
    { label: "高频词 Sight Words", value: 85, color: "var(--success)" },
    { label: "可解码读物 Readers", value: 71, color: "var(--danger)" }
  ];
}

/* ───────────────────────── Cost & token optimization ───────────────────────── */

export interface CostLever {
  key: string;
  nameKey: MessageKey;
  descKey: MessageKey;
  save: number;
  tagKey?: MessageKey;
}
export function costLevers(): CostLever[] {
  return [
    { key: "tier", nameKey: "lever.tier.name", descKey: "lever.tier.desc", save: 28400, tagKey: "lever.tag.biggest" },
    { key: "reuse", nameKey: "lever.reuse.name", descKey: "lever.reuse.desc", save: 14200, tagKey: "lever.tag.scale" },
    { key: "cache", nameKey: "lever.cache.name", descKey: "lever.cache.desc", save: 9800 },
    { key: "batch", nameKey: "lever.batch.name", descKey: "lever.batch.desc", save: 3600 },
    { key: "output", nameKey: "lever.output.name", descKey: "lever.output.desc", save: 1400 }
  ];
}
export const COST_BASE = 96200;
export const COST_KIDS = 18400;
export const COST_FIXED = 14200;

export type TierKey = "small" | "mid" | "flag" | "vis" | "spec";
export const TIER_LABEL: Record<TierKey, MessageKey> = {
  small: "tier.small",
  mid: "tier.mid",
  flag: "tier.flag",
  vis: "tier.vis",
  spec: "tier.spec"
};
export const TIER_TONE: Record<TierKey, Tone> = {
  small: "success",
  mid: "brand",
  flag: "warning",
  vis: "info",
  spec: "info"
};
export const TIER_MULT: Partial<Record<TierKey, number>> = { small: 1, mid: 2.8, flag: 6.5 };

export interface RouteRule {
  key: string;
  task: string;
  base: number;
  calls: string;
  allow: TierKey[];
  rec: TierKey;
  def: TierKey;
  model: Partial<Record<TierKey, string>>;
}
export function routeDefs(): RouteRule[] {
  return [
    { key: "card", task: "拼读卡片文案", base: 126, calls: "182k", allow: ["small", "mid", "flag"], rec: "small", def: "small", model: { small: "qwen-turbo", mid: "qwen-plus", flag: "qwen-max" } },
    { key: "sent", task: "例句 / 高频词造句", base: 68, calls: "96k", allow: ["small", "mid", "flag"], rec: "small", def: "small", model: { small: "qwen-turbo", mid: "qwen-plus", flag: "qwen-max" } },
    { key: "score", task: "发音评分判定", base: 41, calls: "5.9k", allow: ["spec"], rec: "spec", def: "spec", model: { spec: "sensevoice-v1" } },
    { key: "ocr", task: "讲义 OCR 识别", base: 320, calls: "1.28k", allow: ["vis"], rec: "vis", def: "vis", model: { vis: "qwen-vl-ocr" } },
    { key: "parse", task: "拼读结构化解析", base: 66, calls: "1.28k", allow: ["small", "mid", "flag"], rec: "mid", def: "mid", model: { small: "qwen-turbo", mid: "qwen-plus", flag: "qwen-max" } },
    { key: "report", task: "学习周报总结", base: 56, calls: "8.5k", allow: ["small", "mid", "flag"], rec: "mid", def: "mid", model: { small: "qwen-turbo", mid: "qwen-plus", flag: "qwen-max" } },
    { key: "path", task: "个性化路径诊断", base: 38, calls: "2.1k", allow: ["small", "mid", "flag"], rec: "flag", def: "flag", model: { small: "qwen-turbo", mid: "qwen-plus", flag: "qwen-max" } }
  ];
}

export interface CacheCard {
  labelKey: MessageKey;
  value: string;
  pct: number;
  color: string;
  descKey: MessageKey;
}
export function cacheCards(): CacheCard[] {
  return [
    { labelKey: "cache.prompt", value: "87.4%", pct: 87.4, color: "var(--brand)", descKey: "cache.prompt.desc" },
    { labelKey: "cache.reuse", value: "91.7%", pct: 91.7, color: "var(--success)", descKey: "cache.reuse.desc" },
    { labelKey: "cache.dedup", value: "63.2%", pct: 63.2, color: "var(--info)", descKey: "cache.dedup.desc" }
  ];
}

export const GEN_STAGES: StageKey[] = ["letter", "cvc", "blend", "vowel", "sight", "reader"];

/* ───────────────────────── Pure view helpers ───────────────────────── */

/** Build a sparkline polyline + filled area path from a numeric series. */
export function sparkline(
  series: number[],
  width = 300,
  height = 78,
  pad = 6
): { linePoints: string; areaPath: string } {
  const n = series.length;
  const pts = series.map((v, i) => ({
    x: Number(((i / (n - 1)) * width).toFixed(1)),
    y: Number((height - pad - (v / 100) * (height - 2 * pad)).toFixed(1))
  }));
  const linePoints = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const areaPath = `M${pts[0].x},${height} ${pts.map((p) => `L${p.x},${p.y}`).join(" ")} L${pts[n - 1].x},${height} Z`;
  return { linePoints, areaPath };
}

/** Reduce an asset's three media states to a single status. */
export function rollupMedia(media: PhonicsAsset["media"]): "ready" | "pending" | "failed" {
  const values = [media.en, media.us, media.img].filter((x) => x && x !== "—");
  if (values.includes("failed")) return "failed";
  if (values.includes("pending")) return "pending";
  return "ready";
}
