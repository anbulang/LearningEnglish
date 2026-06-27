import { useMemo, useRef, useState } from "react";
import {
  PROVIDER_STATUS_META,
  TONE_TOKENS,
  consoleProviders,
  type ConsoleProvider
} from "../domain/consoleData";
import { badgeStyle, bigDotStyle, Modal } from "../components/ui";
import { IconTrash } from "../components/icons";
import { createTranslator, localize } from "../i18n/i18n";
import { useToast } from "../components/providers";
import { PageHeader, PageRoot, PrimaryButton, PrototypeBadge } from "./shared";
import type { ProviderOpsProps, ProviderPolicyOverrideInput } from "./contracts";
import type { AIProvider, ProviderPolicy } from "../domain/types";

const copy = {
  zh: {
    eyebrow: "运维 / Provider 运维",
    title: "Provider 运维",
    subtitle: "所有 AI 服务商集成的连通性、配额与接入配置 · 支持增删改与启停",
    selfCheck: "连通性自检",
    selfChecking: "检测中…",
    selfChecked: "已检测 ✓",
    add: "+ 添加 Provider",
    formAdd: "添加 Provider",
    formEdit: "编辑 Provider",
    cancel: "取消",
    name: "名称 *",
    namePh: "如 DashScope · Qwen-VL",
    use: "用途",
    usePh: "如 拼读讲义 OCR 识别",
    endpoint: "接入地址 Endpoint",
    endpointPh: "https://…",
    model: "模型 Model *",
    modelPh: "qwen-vl-ocr",
    apiKey: "API Key",
    apiKeyPh: "sk-••••••",
    save: "保存",
    saveNote: "新添加的 Provider 默认停用，确认无误后再启用。",
    successRate: "成功率",
    latency: "平均延迟",
    quota: "配额",
    enable: "启用",
    disable: "停用",
    edit: "编辑",
    del: "删除",
    deleteTitle: "删除 Provider？",
    deleteLead: "将永久移除 ",
    deleteTail: " 的接入配置。引用它的任务将自动转移到备用通道。此操作不可撤销。",
    confirmDelete: "确认删除",
    selfCheckDone: "连通性自检完成",
    addedToast: "已添加 Provider（默认停用）",
    updatedToast: "已更新 Provider",
    enabledToast: "已启用 Provider",
    disabledToast: "已停用 Provider",
    deletedToast: "已删除 Provider",
    policyTitle: "Provider 策略（真实生效）",
    policySubtitle: "全局默认与各租户覆盖 · 改动会写入 /v1/admin/providers/policies 并审计",
    policyGlobal: "全局默认",
    policyTenant: "租户覆盖",
    policyTenantPrefix: "租户 ",
    policyTier: "档位",
    aiProvider: "AI Provider",
    mediaProvider: "媒体 Provider",
    fallbackMode: "降级模式",
    monthlyGuardrail: "月度护栏（次）",
    reason: "原因 *",
    reasonPh: "如 切换到 Doubao 控制成本",
    sourceGlobalDefault: "全局默认",
    sourceTenantOverride: "租户覆盖",
    sourceTierDefault: "档位默认",
    sourceEmergencyGlobal: "全局紧急",
    fbGlobalStub: "全局 stub",
    fbAutoToMock: "自动转 mock",
    fbPerTenant: "按租户",
    mediaMock: "mock",
    mediaReal: "real",
    savePolicy: "保存策略",
    savingPolicy: "保存中…",
    addOverride: "为租户新增覆盖",
    pickTenant: "选择租户…",
    policySaved: "已保存 Provider 策略",
    reasonRequired: "请填写变更原因",
    noPolicies: "暂无 Provider 策略数据"
  },
  en: {
    eyebrow: "Operations / Provider Ops",
    title: "Provider Ops",
    subtitle: "Connectivity, quota and access config for every AI provider · add / edit / toggle supported",
    selfCheck: "Self-check",
    selfChecking: "Checking…",
    selfChecked: "Checked ✓",
    add: "+ Add provider",
    formAdd: "Add provider",
    formEdit: "Edit provider",
    cancel: "Cancel",
    name: "Name *",
    namePh: "e.g. DashScope · Qwen-VL",
    use: "Use",
    usePh: "e.g. worksheet OCR",
    endpoint: "Endpoint",
    endpointPh: "https://…",
    model: "Model *",
    modelPh: "qwen-vl-ocr",
    apiKey: "API Key",
    apiKeyPh: "sk-••••••",
    save: "Save",
    saveNote: "New providers are disabled by default — enable once verified.",
    successRate: "Success",
    latency: "Avg latency",
    quota: "Quota",
    enable: "Enable",
    disable: "Disable",
    edit: "Edit",
    del: "Delete",
    deleteTitle: "Delete provider?",
    deleteLead: "This permanently removes the access config for ",
    deleteTail: ". Jobs referencing it fail over to the backup channel. This cannot be undone.",
    confirmDelete: "Delete",
    selfCheckDone: "Connectivity self-check complete",
    addedToast: "Provider added (disabled by default)",
    updatedToast: "Provider updated",
    enabledToast: "Provider enabled",
    disabledToast: "Provider disabled",
    deletedToast: "Provider deleted",
    policyTitle: "Provider policy (live)",
    policySubtitle: "Global default and per-tenant overrides · saves to /v1/admin/providers/policies and is audited",
    policyGlobal: "Global default",
    policyTenant: "Tenant override",
    policyTenantPrefix: "Tenant ",
    policyTier: "Tier",
    aiProvider: "AI provider",
    mediaProvider: "Media provider",
    fallbackMode: "Fallback mode",
    monthlyGuardrail: "Monthly guardrail (calls)",
    reason: "Reason *",
    reasonPh: "e.g. switch to Doubao to control cost",
    sourceGlobalDefault: "Global default",
    sourceTenantOverride: "Tenant override",
    sourceTierDefault: "Tier default",
    sourceEmergencyGlobal: "Emergency global",
    fbGlobalStub: "Global stub",
    fbAutoToMock: "Auto to mock",
    fbPerTenant: "Per tenant",
    mediaMock: "mock",
    mediaReal: "real",
    savePolicy: "Save policy",
    savingPolicy: "Saving…",
    addOverride: "Add tenant override",
    pickTenant: "Pick a tenant…",
    policySaved: "Provider policy saved",
    reasonRequired: "A reason is required",
    noPolicies: "No provider policy data yet"
  }
};

interface ProvFormState {
  name: string;
  use: string;
  endpoint: string;
  model: string;
  apiKey: string;
}

const EMPTY_FORM: ProvFormState = { name: "", use: "", endpoint: "", model: "", apiKey: "" };

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-2)",
  marginBottom: 6
};

const inputStyle = (mono = false): React.CSSProperties => ({
  width: "100%",
  height: 38,
  border: "1px solid var(--border)",
  borderRadius: 8,
  background: "var(--bg-subtle)",
  padding: "0 12px",
  fontSize: 13,
  color: "var(--text)",
  outline: "none",
  fontFamily: mono ? "var(--mono)" : "inherit",
  boxSizing: "border-box"
});

const cardBtnStyle: React.CSSProperties = {
  height: 30,
  padding: "0 12px",
  border: "1px solid var(--border)",
  borderRadius: 7,
  background: "var(--surface)",
  color: "var(--text-2)",
  fontSize: 12,
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "inherit"
};

const selectStyle: React.CSSProperties = {
  width: "100%",
  height: 36,
  border: "1px solid var(--border)",
  borderRadius: 8,
  background: "var(--bg-subtle)",
  padding: "0 10px",
  fontSize: 12.5,
  color: "var(--text)",
  outline: "none",
  fontFamily: "inherit",
  boxSizing: "border-box"
};

const AI_PROVIDER_OPTIONS: AIProvider[] = ["stub", "doubao", "qwen", "dashscope", "bailian", "aliyun"];
const MEDIA_PROVIDER_OPTIONS: ProviderPolicy["mediaProvider"][] = ["mock", "real"];
const FALLBACK_OPTIONS: ProviderPolicy["fallbackMode"][] = ["global_stub", "auto_to_mock", "per_tenant"];

type PolicyCopy = ReturnType<typeof localize<(typeof copy)["zh"]>>;

interface PolicyDraft {
  aiProvider: AIProvider;
  mediaProvider: ProviderPolicy["mediaProvider"];
  fallbackMode: ProviderPolicy["fallbackMode"];
  monthlyGuardrail: number;
  reason: string;
}

function sourceLabel(source: ProviderPolicy["source"], c: PolicyCopy): string {
  switch (source) {
    case "tenant_override":
      return c.sourceTenantOverride;
    case "tier_default":
      return c.sourceTierDefault;
    case "emergency_global":
      return c.sourceEmergencyGlobal;
    default:
      return c.sourceGlobalDefault;
  }
}

function fallbackLabel(mode: ProviderPolicy["fallbackMode"], c: PolicyCopy): string {
  switch (mode) {
    case "auto_to_mock":
      return c.fbAutoToMock;
    case "per_tenant":
      return c.fbPerTenant;
    default:
      return c.fbGlobalStub;
  }
}

function PolicyRow({
  policy,
  c,
  onSave
}: {
  policy: ProviderPolicy;
  c: PolicyCopy;
  onSave: (input: ProviderPolicyOverrideInput) => Promise<void>;
}) {
  const isGlobal = policy.tenantId === "global";
  const [draft, setDraft] = useState<PolicyDraft>({
    aiProvider: policy.aiProvider,
    mediaProvider: policy.mediaProvider,
    fallbackMode: policy.fallbackMode,
    monthlyGuardrail: policy.monthlyGuardrail,
    reason: ""
  });
  const [saving, setSaving] = useState(false);

  const canSave = draft.reason.trim() !== "" && !saving;

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      await onSave({
        tenantId: policy.tenantId,
        aiProvider: draft.aiProvider,
        mediaProvider: draft.mediaProvider,
        fallbackMode: draft.fallbackMode,
        monthlyGuardrail: draft.monthlyGuardrail,
        reason: draft.reason.trim()
      });
      setDraft((d) => ({ ...d, reason: "" }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "14px 16px",
        background: "var(--surface)"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 13 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)" }}>
          {isGlobal ? c.policyGlobal : `${c.policyTenantPrefix}${policy.tenantId}`}
        </span>
        {policy.tier && (
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)" }}>
            {c.policyTier}: {policy.tier}
          </span>
        )}
        <span style={{ marginLeft: "auto" }}>
          <span style={badgeStyle("info")}>{sourceLabel(policy.source, c)}</span>
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
        <div>
          <label style={labelStyle} htmlFor={`ai-${policy.tenantId}`}>
            {c.aiProvider}
          </label>
          <select
            id={`ai-${policy.tenantId}`}
            aria-label={`${c.aiProvider} ${policy.tenantId}`}
            value={draft.aiProvider}
            onChange={(e) => setDraft((d) => ({ ...d, aiProvider: e.target.value as AIProvider }))}
            style={selectStyle}
          >
            {AI_PROVIDER_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={labelStyle} htmlFor={`media-${policy.tenantId}`}>
            {c.mediaProvider}
          </label>
          <select
            id={`media-${policy.tenantId}`}
            aria-label={`${c.mediaProvider} ${policy.tenantId}`}
            value={draft.mediaProvider}
            onChange={(e) =>
              setDraft((d) => ({ ...d, mediaProvider: e.target.value as ProviderPolicy["mediaProvider"] }))
            }
            style={selectStyle}
          >
            {MEDIA_PROVIDER_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "mock" ? c.mediaMock : c.mediaReal}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={labelStyle} htmlFor={`fb-${policy.tenantId}`}>
            {c.fallbackMode}
          </label>
          <select
            id={`fb-${policy.tenantId}`}
            aria-label={`${c.fallbackMode} ${policy.tenantId}`}
            value={draft.fallbackMode}
            onChange={(e) =>
              setDraft((d) => ({ ...d, fallbackMode: e.target.value as ProviderPolicy["fallbackMode"] }))
            }
            style={selectStyle}
          >
            {FALLBACK_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {fallbackLabel(opt, c)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={labelStyle} htmlFor={`guard-${policy.tenantId}`}>
            {c.monthlyGuardrail}
          </label>
          <input
            id={`guard-${policy.tenantId}`}
            className="le-input"
            aria-label={`${c.monthlyGuardrail} ${policy.tenantId}`}
            type="number"
            min={0}
            value={draft.monthlyGuardrail}
            onChange={(e) => setDraft((d) => ({ ...d, monthlyGuardrail: Number(e.target.value) || 0 }))}
            style={{ ...inputStyle(true), height: 36 }}
          />
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", gap: 12, marginTop: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <label style={labelStyle} htmlFor={`reason-${policy.tenantId}`}>
            {c.reason}
          </label>
          <input
            id={`reason-${policy.tenantId}`}
            className="le-input"
            aria-label={`${c.reason} ${policy.tenantId}`}
            value={draft.reason}
            onChange={(e) => setDraft((d) => ({ ...d, reason: e.target.value }))}
            placeholder={c.reasonPh}
            style={inputStyle()}
          />
        </div>
        <PrimaryButton onClick={save} disabled={!canSave}>
          {saving ? c.savingPolicy : c.savePolicy}
        </PrimaryButton>
      </div>
    </div>
  );
}

export function ProviderOps(props: ProviderOpsProps) {
  const { language, dataMode, providerPolicies, liveTenants, onOverridePolicy } = props;
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();

  const isLive = dataMode === "live";
  const canEditPolicy = isLive && typeof onOverridePolicy === "function";

  // Live policy save — wrapped so the row component never needs the toast/contract.
  const savePolicy = async (input: ProviderPolicyOverrideInput) => {
    if (!onOverridePolicy) return;
    try {
      await onOverridePolicy(input);
      toast(c.policySaved);
      // Clear the picker after a new-tenant override is saved so the now-covered
      // tenant's stale selection / draft row don't linger.
      setPickedTenant((current) => (current === input.tenantId ? "" : current));
    } catch (error: unknown) {
      toast(error instanceof Error ? error.message : String(error));
      throw error;
    }
  };

  // Tenants without an override row yet, for the "add override" picker.
  const overridableTenants = useMemo(() => {
    if (!liveTenants) return [];
    const covered = new Set(providerPolicies.map((policy) => policy.tenantId));
    return liveTenants.filter((tenant) => !covered.has(tenant.id));
  }, [liveTenants, providerPolicies]);

  const [pickedTenant, setPickedTenant] = useState("");
  const globalPolicy = providerPolicies.find((policy) => policy.tenantId === "global");

  // A draft override row, seeded from the global default for the picked tenant.
  // Self-heals: once the saved override lands in `providerPolicies` (App appends
  // it), drop the draft so we never render a duplicate row / duplicate React key.
  const draftPolicies: ProviderPolicy[] =
    pickedTenant && globalPolicy && !providerPolicies.some((policy) => policy.tenantId === pickedTenant)
      ? [{ ...globalPolicy, tenantId: pickedTenant, tier: undefined, source: "tenant_override" }]
      : [];

  const idRef = useRef(0);
  const [providers, setProviders] = useState<ConsoleProvider[]>(() => consoleProviders());

  const [selfCheckState, setSelfCheckState] = useState<"idle" | "checking" | "done">("idle");

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProvFormState>(EMPTY_FORM);

  const [deleteTarget, setDeleteTarget] = useState<ConsoleProvider | null>(null);

  const selfCheckLabel =
    selfCheckState === "checking" ? c.selfChecking : selfCheckState === "done" ? c.selfChecked : c.selfCheck;

  const runSelfCheck = () => {
    if (selfCheckState === "checking") return;
    setSelfCheckState("checking");
    setTimeout(() => {
      setSelfCheckState("done");
      toast(c.selfCheckDone);
    }, 1400);
  };

  const openAdd = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormOpen(true);
  };

  const openEdit = (p: ConsoleProvider) => {
    setEditingId(p.id);
    setForm({ name: p.name, use: p.use, endpoint: p.endpoint, model: p.model, apiKey: "" });
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const canSave = form.name.trim() !== "" && form.model.trim() !== "";

  const saveForm = () => {
    if (!canSave) return;
    if (editingId) {
      setProviders((list) =>
        list.map((p) =>
          p.id === editingId
            ? { ...p, name: form.name, use: form.use, endpoint: form.endpoint, model: form.model }
            : p
        )
      );
      toast(c.updatedToast);
    } else {
      idRef.current += 1;
      const next: ConsoleProvider = {
        id: `pv-new-${idRef.current}`,
        name: form.name,
        use: form.use,
        endpoint: form.endpoint,
        model: form.model,
        status: "idle",
        success: 0,
        latency: 0,
        quota: 0,
        enabled: false
      };
      setProviders((list) => [...list, next]);
      toast(c.addedToast);
    }
    closeForm();
  };

  const toggleProvider = (p: ConsoleProvider) => {
    const enabled = !p.enabled;
    // Keep the real status across disable (the badge derives "disabled" from
    // `enabled` at render); on enable, promote only a previously-idle provider.
    setProviders((list) =>
      list.map((row) =>
        row.id === p.id ? { ...row, enabled, status: enabled && row.status === "idle" ? "ok" : row.status } : row
      )
    );
    toast(enabled ? c.enabledToast : c.disabledToast);
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setProviders((list) => list.filter((p) => p.id !== id));
    toast(c.deletedToast);
    setDeleteTarget(null);
  };

  return (
    <PageRoot screen="providers">
      <PageHeader
        eyebrow={c.eyebrow}
        title={c.title}
        subtitle={c.subtitle}
        language={language}
        tenantScope={props.tenantScope}
        action={
          isLive ? undefined : (
            <div style={{ display: "flex", gap: 10 }}>
              <button
                type="button"
                onClick={runSelfCheck}
                className="le-hover-soft"
                style={{
                  height: 36,
                  padding: "0 16px",
                  border: "1px solid var(--border-strong)",
                  borderRadius: 8,
                  background: "var(--surface)",
                  color: "var(--text)",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: selfCheckState === "checking" ? "default" : "pointer",
                  fontFamily: "inherit",
                  whiteSpace: "nowrap"
                }}
              >
                {selfCheckLabel}
              </button>
              <PrimaryButton onClick={openAdd}>{c.add}</PrimaryButton>
            </div>
          )
        }
      />

      {canEditPolicy && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            boxShadow: "var(--shadow-sm)",
            padding: 18,
            marginBottom: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.policyTitle}</div>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 16 }}>{c.policySubtitle}</div>

          {providerPolicies.length === 0 && draftPolicies.length === 0 ? (
            <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>{c.noPolicies}</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[...providerPolicies, ...draftPolicies].map((policy) => (
                <PolicyRow key={policy.tenantId} policy={policy} c={c} onSave={savePolicy} />
              ))}
            </div>
          )}

          {overridableTenants.length > 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginTop: 16,
                paddingTop: 14,
                borderTop: "1px solid var(--border)"
              }}
            >
              <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>{c.addOverride}</span>
              <select
                aria-label={c.addOverride}
                value={pickedTenant}
                onChange={(e) => setPickedTenant(e.target.value)}
                style={{ ...selectStyle, width: 240 }}
              >
                <option value="">{c.pickTenant}</option>
                {overridableTenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name} · {tenant.id}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Connector prototype heading — in live mode it has no backend, so label it. */}
      {isLive && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-2)" }}>{c.title}</div>
          <PrototypeBadge language={language} />
        </div>
      )}

      {!isLive && formOpen && (
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
            <div style={{ fontSize: 14, fontWeight: 600 }}>{editingId ? c.formEdit : c.formAdd}</div>
            <button
              type="button"
              onClick={closeForm}
              className="le-hover-soft"
              style={{
                marginLeft: "auto",
                height: 30,
                padding: "0 12px",
                border: "1px solid var(--border)",
                borderRadius: 7,
                background: "var(--surface)",
                color: "var(--text-2)",
                fontSize: 12,
                cursor: "pointer",
                fontFamily: "inherit"
              }}
            >
              {c.cancel}
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle} htmlFor="prov-name">
                {c.name}
              </label>
              <input
                id="prov-name"
                className="le-input"
                aria-label={c.name}
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder={c.namePh}
                style={inputStyle()}
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle} htmlFor="prov-use">
                {c.use}
              </label>
              <input
                id="prov-use"
                className="le-input"
                aria-label={c.use}
                value={form.use}
                onChange={(e) => setForm((f) => ({ ...f, use: e.target.value }))}
                placeholder={c.usePh}
                style={inputStyle()}
              />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle} htmlFor="prov-endpoint">
                {c.endpoint}
              </label>
              <input
                id="prov-endpoint"
                className="le-input"
                aria-label={c.endpoint}
                value={form.endpoint}
                onChange={(e) => setForm((f) => ({ ...f, endpoint: e.target.value }))}
                placeholder={c.endpointPh}
                style={inputStyle(true)}
              />
            </div>
            <div>
              <label style={labelStyle} htmlFor="prov-model">
                {c.model}
              </label>
              <input
                id="prov-model"
                className="le-input"
                aria-label={c.model}
                value={form.model}
                onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                placeholder={c.modelPh}
                style={inputStyle(true)}
              />
            </div>
            <div>
              <label style={labelStyle} htmlFor="prov-key">
                {c.apiKey}
              </label>
              <input
                id="prov-key"
                className="le-input"
                aria-label={c.apiKey}
                type="password"
                value={form.apiKey}
                onChange={(e) => setForm((f) => ({ ...f, apiKey: e.target.value }))}
                placeholder={c.apiKeyPh}
                style={inputStyle(true)}
              />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 14 }}>
            <PrimaryButton onClick={saveForm} disabled={!canSave}>
              {c.save}
            </PrimaryButton>
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>{c.saveNote}</span>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 14 }}>
        {providers.map((p) => {
          const meta = p.enabled ? PROVIDER_STATUS_META[p.status] : PROVIDER_STATUS_META.disabled;
          const tone = TONE_TOKENS[meta.tone];
          const stat = (value: string) => (p.enabled ? value : "—");
          return (
            <div
              key={p.id}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                boxShadow: "var(--shadow-sm)",
                padding: "16px 17px"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 3 }}>
                <span style={bigDotStyle(tone.c, tone.bg)} />
                <span
                  style={{
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: "var(--text)",
                    flex: 1,
                    minWidth: 0,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis"
                  }}
                >
                  {p.name}
                </span>
                <span style={badgeStyle(meta.tone)}>{t(meta.labelKey)}</span>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 14 }}>
                {p.use}
                {p.use ? " · " : ""}
                <span style={{ fontFamily: "var(--mono)" }}>{p.model}</span>
              </div>
              <div style={{ display: "flex", gap: 18, marginBottom: 13 }}>
                <div>
                  <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>{c.successRate}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 16, fontWeight: 600, marginTop: 3 }}>
                    {stat(`${p.success}%`)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>{c.latency}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 16, fontWeight: 600, marginTop: 3 }}>
                    {stat(`${p.latency.toLocaleString()}ms`)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>{c.quota}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 16, fontWeight: 600, marginTop: 3 }}>
                    {stat(`${p.quota}%`)}
                  </div>
                </div>
              </div>
              {!isLive && (
                <div
                  style={{
                    borderTop: "1px solid var(--border)",
                    paddingTop: 11,
                    display: "flex",
                    alignItems: "center",
                    gap: 8
                  }}
                >
                  <button type="button" onClick={() => toggleProvider(p)} className="le-hover-soft" style={cardBtnStyle}>
                    {p.enabled ? c.disable : c.enable}
                  </button>
                  <button type="button" onClick={() => openEdit(p)} className="le-hover-soft" style={cardBtnStyle}>
                    {c.edit}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(p)}
                    title={c.del}
                    aria-label={`${c.del} ${p.name}`}
                    className="le-hover-danger"
                    style={{
                      marginLeft: "auto",
                      width: 30,
                      height: 30,
                      border: "1px solid var(--border)",
                      borderRadius: 7,
                      background: "var(--surface)",
                      color: "var(--danger)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    <IconTrash size={14} />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <Modal open={deleteTarget !== null} onClose={() => setDeleteTarget(null)} width={412} zIndex={60}>
        <div
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            background: "var(--danger-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 15,
            color: "var(--danger)"
          }}
        >
          <IconTrash size={22} />
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>{c.deleteTitle}</div>
        <div style={{ fontSize: 13, color: "var(--text-2)", marginTop: 9, lineHeight: 1.65 }}>
          {c.deleteLead}
          <span style={{ fontWeight: 600, color: "var(--text)" }}>{deleteTarget?.name}</span>
          {c.deleteTail}
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
          <button
            type="button"
            onClick={() => setDeleteTarget(null)}
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
            onClick={confirmDelete}
            style={{
              flex: 1,
              height: 38,
              border: "none",
              borderRadius: 8,
              background: "var(--danger)",
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit"
            }}
          >
            {c.confirmDelete}
          </button>
        </div>
      </Modal>
    </PageRoot>
  );
}
