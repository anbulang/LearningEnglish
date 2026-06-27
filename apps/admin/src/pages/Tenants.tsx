import { useEffect, useRef, useState } from "react";
import {
  TENANT_PLAN_KEYS,
  TENANT_PLAN_LABEL,
  TENANT_STATUS_META,
  consoleTenants,
  type ConsoleTenant,
  type TenantPlanKey
} from "../domain/consoleData";
import { tenantsToConsole } from "../domain/liveMappers";
import { CloseButton, Drawer, StatusBadge, Switch, accentBarStyle } from "../components/ui";
import { IconTrash } from "../components/icons";
import { useConfirm, useToast } from "../components/providers";
import { createTranslator, localize, translateMessage } from "../i18n/i18n";
import { GhostButton, PageHeader, PageRoot, PrimaryButton, PrototypeBadge, SectionCard } from "./shared";
import type { AdminTenantDetailData, ModuleKey, TenantModuleSetting } from "../domain/types";
import type { TenantsProps } from "./contracts";

/** The 5 toggleable modules, in display order. */
const MODULE_KEYS: readonly ModuleKey[] = [
  "worksheet_import",
  "ai_review",
  "media_pipeline",
  "speaking_score",
  "weekly_reports"
];

const copy = {
  zh: {
    eyebrow: "主控 / 租户管理",
    title: "租户管理",
    subtitle: "各接入机构的自然拼读内容生产与活跃概况 · 支持新增、编辑套餐、停用与删除",
    addAction: "+ 新增租户",
    formAdd: "新增租户",
    formEdit: "编辑租户",
    cancel: "取消",
    fieldName: "机构名称 *",
    fieldNamePlaceholder: "如 明德外国语小学",
    fieldPlan: "套餐",
    fieldKids: "活跃孩子数",
    save: "保存",
    listTitle: "租户清单",
    colOrg: "机构",
    colPlan: "套餐",
    colKids: "孩子数",
    colDecks: "本周讲义",
    colRate: "识别成功率",
    colStatus: "状态",
    colActions: "操作",
    activeKids: "活跃孩子",
    edit: "编辑",
    suspend: "停用",
    resume: "恢复",
    deleteTitle: "删除租户？",
    deleteLabel: "删除",
    newSeed: "新接入 · 待生产",
    detail: (decks: number, rate: string) => `本周 ${decks} 份 · ${rate}`,
    deleteBody: (name: string) => `将移除 “${name}” 的接入配置，其家庭与内容数据将被归档。此操作不可撤销。`,
    addedToast: (name: string) => `已新增租户 “${name}”`,
    savedToast: (name: string) => `已保存 “${name}”`,
    suspendedToast: (name: string) => `已停用 “${name}”`,
    resumedToast: (name: string) => `已恢复 “${name}”`,
    deletedToast: (name: string) => `已删除 “${name}”`,
    details: "详情",
    drawerEyebrow: "租户详情",
    drawerLoading: "加载中…",
    drawerOverview: "概览",
    fieldRegion: "区域",
    fieldTier: "套餐档位",
    fieldOwner: "负责人",
    fieldPhone: "联系电话",
    fieldStatus: "状态",
    fieldActiveParents: "活跃家长",
    fieldChildren: "孩子数",
    fieldCreated: "创建于",
    childrenTitle: "孩子",
    childrenEmpty: "暂无孩子档案",
    materialsTitle: "讲义",
    materialsCount: (n: number) => `共 ${n} 份讲义`,
    providerTitle: "Provider 策略",
    providerAi: "AI Provider",
    providerMedia: "媒体 Provider",
    providerFallback: "降级模式",
    providerGuardrail: "月度护栏",
    modulesTitle: "模块开关",
    moduleInherited: "全局默认",
    moduleOverride: "租户覆盖",
    moduleReason: "管理后台手动切换",
    moduleToggleError: "切换失败，请重试",
    weeklyTitle: "周报",
    speakingTitle: "口语",
    riskTitle: "风险",
    close: "关闭"
  },
  en: {
    eyebrow: "Console / Tenants",
    title: "Tenants",
    subtitle:
      "Phonics content production and activity overview per onboarded institution · add, change plan, suspend & delete",
    addAction: "+ New tenant",
    formAdd: "New tenant",
    formEdit: "Edit tenant",
    cancel: "Cancel",
    fieldName: "Institution name *",
    fieldNamePlaceholder: "e.g. Mingde Foreign Language School",
    fieldPlan: "Plan",
    fieldKids: "Active kids",
    save: "Save",
    listTitle: "Tenant list",
    colOrg: "Institution",
    colPlan: "Plan",
    colKids: "Kids",
    colDecks: "Decks this week",
    colRate: "Recognition rate",
    colStatus: "Status",
    colActions: "Actions",
    activeKids: "Active kids",
    edit: "Edit",
    suspend: "Suspend",
    resume: "Resume",
    deleteTitle: "Delete tenant?",
    deleteLabel: "Delete",
    newSeed: "Newly onboarded · pending production",
    detail: (decks: number, rate: string) => `${decks} this week · ${rate}`,
    deleteBody: (name: string) =>
      `This removes the onboarding config for “${name}”; its families and content data will be archived. This cannot be undone.`,
    addedToast: (name: string) => `Added tenant “${name}”`,
    savedToast: (name: string) => `Saved “${name}”`,
    suspendedToast: (name: string) => `Suspended “${name}”`,
    resumedToast: (name: string) => `Resumed “${name}”`,
    deletedToast: (name: string) => `Deleted “${name}”`,
    details: "Details",
    drawerEyebrow: "Tenant detail",
    drawerLoading: "Loading…",
    drawerOverview: "Overview",
    fieldRegion: "Region",
    fieldTier: "Tier",
    fieldOwner: "Owner",
    fieldPhone: "Phone",
    fieldStatus: "Status",
    fieldActiveParents: "Active parents",
    fieldChildren: "Children",
    fieldCreated: "Created",
    childrenTitle: "Children",
    childrenEmpty: "No child profiles yet",
    materialsTitle: "Materials",
    materialsCount: (n: number) => `${n} materials total`,
    providerTitle: "Provider policy",
    providerAi: "AI provider",
    providerMedia: "Media provider",
    providerFallback: "Fallback mode",
    providerGuardrail: "Monthly guardrail",
    modulesTitle: "Module toggles",
    moduleInherited: "Global default",
    moduleOverride: "Tenant override",
    moduleReason: "Manual toggle from admin console",
    moduleToggleError: "Toggle failed, please retry",
    weeklyTitle: "Weekly reports",
    speakingTitle: "Speaking",
    riskTitle: "Risk",
    close: "Close"
  }
};

interface Draft {
  mode: "add" | "edit";
  id: string | null;
  name: string;
  plan: TenantPlanKey;
  kids: string;
}

const inputStyle: React.CSSProperties = {
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
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-2)",
  marginBottom: 6
};

const thBase: React.CSSProperties = { fontWeight: 600, fontSize: 11, padding: "9px 8px" };

/** A GhostButton rendered as a disabled prototype affordance (live mode). */
const disabledGhostStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: "not-allowed",
  color: "var(--text-3)"
};

/** Read a numeric metric defensively from an untyped JSON blob. */
function readNumber(blob: Record<string, unknown> | undefined, ...keys: string[]): number | null {
  if (!blob) return null;
  for (const key of keys) {
    const value = blob[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }
  return null;
}

export function Tenants({
  language,
  tenantScope,
  dataMode,
  liveTenants,
  materials,
  moduleSettings,
  onToggleModule,
  onLoadTenantDetail
}: TenantsProps) {
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();
  const confirm = useConfirm();
  const idCounter = useRef(0);

  // In live mode the create/edit/suspend/delete flows have no backend and the
  // re-seed effect below would wipe any local edits — so they are read-only and
  // flagged as prototype. Module toggles + the detail drawer are the real ops.
  const live = dataMode === "live";
  const moduleControls = live && onToggleModule;

  const seed = (): ConsoleTenant[] =>
    dataMode === "live" && liveTenants ? tenantsToConsole(liveTenants, materials) : consoleTenants();

  const [list, setList] = useState<ConsoleTenant[]>(seed);
  const [formOpen, setFormOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>({ mode: "add", id: null, name: "", plan: "standard", kids: "0" });

  // Live tenant deep-dive drawer state.
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminTenantDetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  // Locally-applied module overrides keyed by `${tenantId}::${moduleKey}`, so a
  // toggle reflects immediately even before the drawer payload is reloaded.
  const [moduleOverrides, setModuleOverrides] = useState<Record<string, boolean>>({});

  // Re-seed when the data source changes (mock ⇄ live, or live payload updates).
  useEffect(() => {
    setList(seed());
    setModuleOverrides({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataMode, liveTenants, materials]);

  // The module settings that drive a tenant's switches: prefer the loaded
  // drawer payload, fall back to the live dashboard prop.
  function settingsFor(tenantId: string): TenantModuleSetting[] {
    const source =
      detail && detail.tenant.id === tenantId ? detail.moduleSettings : moduleSettings;
    return source.filter((m) => m.tenantId === tenantId);
  }

  function moduleState(tenantId: string, key: ModuleKey): { enabled: boolean; inherited: boolean } {
    const localKey = `${tenantId}::${key}`;
    if (localKey in moduleOverrides) {
      return { enabled: moduleOverrides[localKey], inherited: false };
    }
    const row = settingsFor(tenantId).find((m) => m.moduleKey === key);
    // Default to enabled (inherited from the global default) when no row exists.
    return { enabled: row ? row.enabled : true, inherited: row ? row.source === "global_default" : true };
  }

  async function toggleModule(tenantId: string, key: ModuleKey, current: boolean) {
    if (!onToggleModule) return;
    const next = !current;
    const localKey = `${tenantId}::${key}`;
    setModuleOverrides((prev) => ({ ...prev, [localKey]: next }));
    try {
      await onToggleModule(tenantId, key, next, c.moduleReason);
      toast(`${translateMessage(language, `module.${key}`)} · ${next ? c.resume : c.suspend}`);
    } catch {
      // Roll back the optimistic flip.
      setModuleOverrides((prev) => {
        const rest = { ...prev };
        delete rest[localKey];
        return rest;
      });
      toast(c.moduleToggleError);
    }
  }

  async function openDetail(tenantId: string) {
    if (!onLoadTenantDetail) return;
    setSelectedTenantId(tenantId);
    setDetail(null);
    setDetailLoading(true);
    try {
      const data = await onLoadTenantDetail(tenantId);
      setDetail(data);
    } catch {
      toast(c.moduleToggleError);
      setSelectedTenantId(null);
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDetail() {
    setSelectedTenantId(null);
    setDetail(null);
  }

  function openAdd() {
    setDraft({ mode: "add", id: null, name: "", plan: "standard", kids: "0" });
    setFormOpen(true);
  }

  function openEdit(tenant: ConsoleTenant) {
    setDraft({ mode: "edit", id: tenant.id, name: tenant.name, plan: tenant.plan, kids: String(tenant.kids) });
    setFormOpen(true);
  }

  function save() {
    const name = draft.name.trim();
    if (!name) return;
    const kids = parseInt(draft.kids, 10) || 0;
    if (draft.mode === "edit") {
      setList((prev) =>
        prev.map((row) => (row.id === draft.id ? { ...row, name, plan: draft.plan, kids } : row))
      );
      toast(c.savedToast(name));
    } else {
      const id = `tenant-${++idCounter.current}-${name}`;
      setList((prev) => [
        ...prev,
        { id, name, plan: draft.plan, kids, decks: 0, rate: "—", status: "normal", enabled: true }
      ]);
      toast(c.addedToast(name));
    }
    setFormOpen(false);
  }

  function toggle(tenant: ConsoleTenant) {
    setList((prev) => prev.map((row) => (row.id === tenant.id ? { ...row, enabled: !row.enabled } : row)));
    toast(tenant.enabled ? c.suspendedToast(tenant.name) : c.resumedToast(tenant.name));
  }

  function askDelete(tenant: ConsoleTenant) {
    confirm({
      title: c.deleteTitle,
      body: c.deleteBody(tenant.name),
      confirmLabel: t("common.confirmDelete"),
      cancelLabel: t("common.cancel"),
      onConfirm: () => {
        setList((prev) => prev.filter((row) => row.id !== tenant.id));
        toast(c.deletedToast(tenant.name));
      }
    });
  }

  const nameBlank = !draft.name.trim();

  return (
    <PageRoot screen="tenants">
      <PageHeader
        eyebrow={c.eyebrow}
        title={c.title}
        subtitle={c.subtitle}
        language={language}
        tenantScope={tenantScope}
        action={
          live ? (
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <PrototypeBadge language={language} />
              <PrimaryButton onClick={openAdd} disabled>
                {c.addAction}
              </PrimaryButton>
            </div>
          ) : (
            <PrimaryButton onClick={openAdd}>{c.addAction}</PrimaryButton>
          )
        }
      />

      {!live && formOpen && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--brand)",
            borderRadius: 10,
            boxShadow: "var(--shadow-sm)",
            padding: 18,
            marginBottom: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 14 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{draft.mode === "edit" ? c.formEdit : c.formAdd}</div>
            <GhostButton onClick={() => setFormOpen(false)} style={{ marginLeft: "auto" }}>
              {c.cancel}
            </GhostButton>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 14 }}>
            <div>
              <label style={labelStyle} htmlFor="tenant-name">
                {c.fieldName}
              </label>
              <input
                id="tenant-name"
                className="le-input"
                aria-label={c.fieldName}
                value={draft.name}
                placeholder={c.fieldNamePlaceholder}
                onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle} htmlFor="tenant-plan">
                {c.fieldPlan}
              </label>
              <select
                id="tenant-plan"
                className="le-input"
                aria-label={c.fieldPlan}
                value={draft.plan}
                onChange={(e) => setDraft((d) => ({ ...d, plan: e.target.value as TenantPlanKey }))}
                style={{ ...inputStyle, padding: "0 10px", cursor: "pointer" }}
              >
                {TENANT_PLAN_KEYS.map((k) => (
                  <option key={k} value={k}>
                    {t(TENANT_PLAN_LABEL[k])}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle} htmlFor="tenant-kids">
                {c.fieldKids}
              </label>
              <input
                id="tenant-kids"
                className="le-input"
                aria-label={c.fieldKids}
                value={draft.kids}
                placeholder="0"
                onChange={(e) => setDraft((d) => ({ ...d, kids: e.target.value }))}
                style={{ ...inputStyle, fontFamily: "var(--mono)" }}
              />
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <PrimaryButton onClick={save} disabled={nameBlank} style={{ height: 38, padding: "0 18px" }}>
              {c.save}
            </PrimaryButton>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 16 }}>
        {list.map((tenant) => {
          const accentColor = !tenant.enabled
            ? "var(--neutral)"
            : tenant.status === "quotaWarning"
              ? "var(--warning)"
              : "var(--brand)";
          return (
            <div
              key={tenant.id}
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
              <div style={accentBarStyle(accentColor)} />
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)" }}>{tenant.name}</div>
              <div
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 27,
                  fontWeight: 600,
                  color: "var(--text)",
                  lineHeight: 1,
                  marginTop: 12
                }}
              >
                {tenant.kids.toLocaleString()}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 4 }}>{c.activeKids}</div>
              <div
                style={{
                  fontSize: 11.5,
                  color: "var(--text-3)",
                  marginTop: 10,
                  borderTop: "1px solid var(--border)",
                  paddingTop: 9
                }}
              >
                {tenant.decks === 0 && tenant.rate === "—" ? c.newSeed : c.detail(tenant.decks, tenant.rate)}
              </div>
            </div>
          );
        })}
      </div>

      <SectionCard>
        <div style={{ padding: "15px 18px 13px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{c.listTitle}</div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={{ ...thBase, textAlign: "left", padding: "9px 18px" }}>{c.colOrg}</th>
              <th style={{ ...thBase, textAlign: "left" }}>{c.colPlan}</th>
              <th style={{ ...thBase, textAlign: "right" }}>{c.colKids}</th>
              <th style={{ ...thBase, textAlign: "right" }}>{c.colDecks}</th>
              <th style={{ ...thBase, textAlign: "right" }}>{c.colRate}</th>
              <th style={{ ...thBase, textAlign: "right" }}>{c.colStatus}</th>
              <th style={{ ...thBase, textAlign: "right", padding: "9px 18px" }}>{c.colActions}</th>
            </tr>
          </thead>
          <tbody>
            {list.map((tenant) => {
              const meta = TENANT_STATUS_META[tenant.status];
              return (
                <tr key={tenant.id} className="le-hover-soft" style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "11px 18px" }}>
                    <div style={{ fontWeight: 600, color: "var(--text)" }}>{tenant.name}</div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>
                      {tenant.id}
                    </div>
                  </td>
                  <td style={{ padding: "11px 8px", color: "var(--text-2)" }}>{t(TENANT_PLAN_LABEL[tenant.plan])}</td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", color: "var(--text-2)" }}>
                    {tenant.kids.toLocaleString()}
                  </td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", color: "var(--text-2)" }}>
                    {tenant.decks}
                  </td>
                  <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: "var(--mono)", color: "var(--text-2)" }}>
                    {tenant.rate}
                  </td>
                  <td style={{ padding: "11px 8px", textAlign: "right" }}>
                    {!tenant.enabled ? (
                      <StatusBadge tone="neutral">{t("status.tenant.suspended")}</StatusBadge>
                    ) : (
                      <StatusBadge tone={meta.tone}>{t(meta.labelKey)}</StatusBadge>
                    )}
                  </td>
                  <td style={{ padding: "11px 18px" }}>
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", alignItems: "center" }}>
                      {live && onLoadTenantDetail && (
                        <GhostButton onClick={() => openDetail(tenant.id)}>{c.details}</GhostButton>
                      )}
                      {live && <PrototypeBadge language={language} />}
                      <GhostButton
                        onClick={live ? undefined : () => openEdit(tenant)}
                        style={live ? disabledGhostStyle : undefined}
                      >
                        {c.edit}
                      </GhostButton>
                      <GhostButton
                        onClick={live ? undefined : () => toggle(tenant)}
                        style={live ? disabledGhostStyle : undefined}
                      >
                        {tenant.enabled ? c.suspend : c.resume}
                      </GhostButton>
                      <button
                        type="button"
                        className={live ? undefined : "le-hover-danger"}
                        aria-label={c.deleteLabel}
                        title={c.deleteLabel}
                        disabled={live}
                        onClick={live ? undefined : () => askDelete(tenant)}
                        style={{
                          width: 28,
                          height: 28,
                          border: "1px solid var(--border)",
                          borderRadius: 7,
                          background: "var(--surface)",
                          color: live ? "var(--text-3)" : "var(--danger)",
                          cursor: live ? "not-allowed" : "pointer",
                          opacity: live ? 0.5 : 1,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        <IconTrash size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </SectionCard>

      {live && onLoadTenantDetail && (
        <Drawer
          open={selectedTenantId !== null}
          onClose={closeDetail}
          width={500}
          closeLabel={c.close}
          ariaLabel={selectedTenantId ?? c.drawerEyebrow}
        >
          <div
            style={{
              flex: "none",
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "16px 20px",
              borderBottom: "1px solid var(--border)"
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{c.drawerEyebrow}</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", marginTop: 1 }}>
                {detail?.tenant.displayName || detail?.tenant.name || selectedTenantId}
              </div>
            </div>
            <span style={{ marginLeft: "auto" }}>
              <CloseButton onClick={closeDetail} label={c.close} />
            </span>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px" }}>
            {detailLoading && (
              <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>{c.drawerLoading}</div>
            )}
            {!detailLoading && detail && (
              <TenantDetailBody
                detail={detail}
                c={c}
                language={language}
                moduleControls={moduleControls ? true : false}
                moduleState={moduleState}
                toggleModule={toggleModule}
              />
            )}
          </div>
        </Drawer>
      )}
    </PageRoot>
  );
}

/* ── Drawer body: overview + children + materials + provider + modules ─ */

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 12.5,
  fontWeight: 600,
  color: "var(--text)",
  margin: "18px 0 9px"
};

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === "") return null;
  return (
    <div style={{ display: "flex", gap: 10, fontSize: 12.5, lineHeight: 1.9 }}>
      <span style={{ color: "var(--text-3)", flex: "none", minWidth: 84 }}>{label}</span>
      <span style={{ color: "var(--text)", fontWeight: 500, wordBreak: "break-word" }}>{value}</span>
    </div>
  );
}

function TenantDetailBody({
  detail,
  c,
  language,
  moduleControls,
  moduleState,
  toggleModule
}: {
  detail: AdminTenantDetailData;
  c: (typeof copy)["zh"];
  language: TenantsProps["language"];
  moduleControls: boolean;
  moduleState: (tenantId: string, key: ModuleKey) => { enabled: boolean; inherited: boolean };
  toggleModule: (tenantId: string, key: ModuleKey, current: boolean) => void;
}) {
  const tenant = detail.tenant;
  const policy = detail.providerPolicy;
  const weekly = readNumber(detail.weeklyReports, "total", "count");
  const speaking = readNumber(detail.speakingAttempts, "total", "count");
  const risk = readNumber(detail.riskSummary, "blockedJobs", "blocked", "failures", "total");

  return (
    <>
      <div style={{ ...sectionTitleStyle, marginTop: 0 }}>{c.drawerOverview}</div>
      <DetailRow label={c.fieldRegion} value={tenant.region} />
      <DetailRow label={c.fieldTier} value={tenant.tier} />
      <DetailRow label={c.fieldOwner} value={tenant.ownerContact} />
      <DetailRow label={c.fieldPhone} value={tenant.phoneNumber} />
      <DetailRow label={c.fieldStatus} value={tenant.status} />
      <DetailRow label={c.fieldActiveParents} value={tenant.activeParents.toLocaleString()} />
      <DetailRow label={c.fieldChildren} value={tenant.children.toLocaleString()} />
      <DetailRow label={c.fieldCreated} value={tenant.createdAt} />

      <div style={sectionTitleStyle}>
        {c.childrenTitle}{" "}
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)", fontWeight: 400 }}>
          {detail.children.length}
        </span>
      </div>
      {detail.children.length === 0 ? (
        <div style={{ fontSize: 12, color: "var(--text-3)" }}>{c.childrenEmpty}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {detail.children.map((child) => (
            <div
              key={child.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12.5,
                padding: "7px 10px",
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "var(--bg-subtle)"
              }}
            >
              <span style={{ fontWeight: 600, color: "var(--text)" }}>{child.name}</span>
              <span style={{ color: "var(--text-3)" }}>· {child.age} · {child.level}</span>
            </div>
          ))}
        </div>
      )}

      <div style={sectionTitleStyle}>{c.materialsTitle}</div>
      <div style={{ fontSize: 12.5, color: "var(--text-2)" }}>{c.materialsCount(detail.materials.length)}</div>

      {policy && (
        <>
          <div style={sectionTitleStyle}>{c.providerTitle}</div>
          <DetailRow label={c.providerAi} value={policy.aiProvider} />
          <DetailRow label={c.providerMedia} value={policy.mediaProvider} />
          <DetailRow label={c.providerFallback} value={policy.fallbackMode} />
          <DetailRow label={c.providerGuardrail} value={policy.monthlyGuardrail?.toLocaleString?.()} />
        </>
      )}

      {(weekly != null || speaking != null || risk != null) && (
        <div style={{ display: "flex", gap: 18, marginTop: 16, flexWrap: "wrap" }}>
          {weekly != null && <MiniStat label={c.weeklyTitle} value={weekly} />}
          {speaking != null && <MiniStat label={c.speakingTitle} value={speaking} />}
          {risk != null && <MiniStat label={c.riskTitle} value={risk} />}
        </div>
      )}

      {moduleControls && (
        <>
          <div style={sectionTitleStyle}>{c.modulesTitle}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {MODULE_KEYS.map((key) => {
              const state = moduleState(tenant.id, key);
              return (
                <div
                  key={key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "9px 11px",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    background: "var(--surface)"
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--text)" }}>
                      {translateMessage(language, `module.${key}`)}
                    </div>
                    <div style={{ fontSize: 10.5, color: "var(--text-3)", marginTop: 1 }}>
                      {state.inherited ? c.moduleInherited : c.moduleOverride}
                    </div>
                  </div>
                  <span style={{ marginLeft: "auto" }}>
                    <Switch
                      on={state.enabled}
                      onToggle={() => toggleModule(tenant.id, key, state.enabled)}
                      ariaLabel={translateMessage(language, `module.${key}`)}
                    />
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 19, fontWeight: 600, color: "var(--text)", lineHeight: 1 }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>{label}</div>
    </div>
  );
}
