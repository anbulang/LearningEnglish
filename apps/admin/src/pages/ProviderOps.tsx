import { useEffect, useMemo, useState } from "react";
import { StatusChip } from "../components/ui";
import { getEffectiveProviderPolicy, getMaterialsForScope, isBlockedMaterial } from "../domain/selectors";
import type { AdminMaterial, Language, ProviderPolicy, Tenant, TenantScope } from "../domain/types";

export interface ProviderPolicyOverrideInput {
  tenantId: string;
  aiProvider: ProviderPolicy["aiProvider"];
  mediaProvider: ProviderPolicy["mediaProvider"];
  fallbackMode: ProviderPolicy["fallbackMode"];
  monthlyGuardrail: number;
  reason: string;
}

interface ProviderOpsProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
  policies: ProviderPolicy[];
  dataMode: "mock" | "live";
  onOverrideProviderPolicy?: (input: ProviderPolicyOverrideInput) => Promise<void>;
}

const aiProviderOptions: ProviderPolicy["aiProvider"][] = ["stub", "doubao", "qwen", "dashscope", "bailian", "aliyun"];
const mediaProviderOptions: ProviderPolicy["mediaProvider"][] = ["mock", "real"];
const fallbackModeOptions: ProviderPolicy["fallbackMode"][] = ["global_stub", "auto_to_mock", "per_tenant"];

export function ProviderOps({
  language,
  tenantScope,
  tenants,
  materials,
  policies,
  dataMode,
  onOverrideProviderPolicy
}: ProviderOpsProps) {
  const copy = language === "zh" ? zhCopy : enCopy;
  const scopedTenants = useMemo(
    () => (tenantScope === "all" ? tenants : tenants.filter((tenant) => tenant.id === tenantScope)),
    [tenantScope, tenants]
  );
  const scopedMaterials = useMemo(() => getMaterialsForScope(materials, tenantScope), [materials, tenantScope]);
  const providerWarnings = scopedMaterials.filter(hasProviderWarning).length;
  const [selectedTenantId, setSelectedTenantId] = useState(scopedTenants[0]?.id ?? "");
  const selectedTenant = scopedTenants.find((tenant) => tenant.id === selectedTenantId) ?? scopedTenants[0] ?? null;
  const effectivePolicy = selectedTenant ? getEffectiveProviderPolicy(policies, selectedTenant.id, selectedTenant.tier) : null;
  const [aiProvider, setAiProvider] = useState<ProviderPolicy["aiProvider"]>(effectivePolicy?.aiProvider ?? "stub");
  const [mediaProvider, setMediaProvider] = useState<ProviderPolicy["mediaProvider"]>(effectivePolicy?.mediaProvider ?? "mock");
  const [fallbackMode, setFallbackMode] = useState<ProviderPolicy["fallbackMode"]>(effectivePolicy?.fallbackMode ?? "global_stub");
  const [monthlyGuardrail, setMonthlyGuardrail] = useState(effectivePolicy?.monthlyGuardrail ?? 0);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const nextTenant = scopedTenants.find((tenant) => tenant.id === selectedTenantId) ?? scopedTenants[0] ?? null;
    if (!nextTenant) {
      setSelectedTenantId("");
      setAiProvider("stub");
      setMediaProvider("mock");
      setFallbackMode("global_stub");
      setMonthlyGuardrail(0);
      setReason("");
      setMessage("");
      return;
    }

    const tenantChanged = nextTenant.id !== selectedTenantId;
    if (tenantChanged) {
      setSelectedTenantId(nextTenant.id);
      setReason("");
      setMessage("");
    }
    const policy = getEffectiveProviderPolicy(policies, nextTenant.id, nextTenant.tier);
    setAiProvider(policy.aiProvider);
    setMediaProvider(policy.mediaProvider);
    setFallbackMode(policy.fallbackMode);
    setMonthlyGuardrail(policy.monthlyGuardrail);
  }, [policies, scopedTenants, selectedTenantId]);

  const policyRows = scopedTenants.map((tenant) => ({
    tenant,
    policy: getEffectiveProviderPolicy(policies, tenant.id, tenant.tier),
    warnings: materials.filter((material) => material.tenantId === tenant.id && hasProviderWarning(material)).length
  }));

  function handleTenantChange(tenantId: string) {
    const tenant = scopedTenants.find((item) => item.id === tenantId);
    if (!tenant) {
      return;
    }
    setSelectedTenantId(tenant.id);
    setReason("");
    setMessage("");
  }

  async function handleSubmit() {
    if (!selectedTenant || !onOverrideProviderPolicy || !reason.trim()) {
      return;
    }
    setIsSaving(true);
    setMessage("");
    try {
      await onOverrideProviderPolicy({
        tenantId: selectedTenant.id,
        aiProvider,
        mediaProvider,
        fallbackMode,
        monthlyGuardrail,
        reason: reason.trim()
      });
      setReason("");
      setMessage(copy.overrideRecorded);
    } catch {
      setMessage(copy.overrideFailed);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">TenantProviderPolicy / ProviderIncident / AuditEvent</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="metric-row wide">
        <div className="metric-card">
          <span>{copy.providerWarningMaterials}</span>
          <strong>{providerWarnings}</strong>
          <p>{copy.providerWarningDetail}</p>
        </div>
        <div className="metric-card">
          <span>{copy.tenantOverrides}</span>
          <strong>{policies.filter((policy) => policy.source === "tenant_override").length}</strong>
          <p>{copy.tenantOverrideDetail}</p>
        </div>
        <div className="metric-card">
          <span>{copy.secretPolicy}</span>
          <strong>{copy.secretsMasked}</strong>
          <p>{copy.secretPolicyDetail}</p>
        </div>
      </section>

      <section className="surface table-panel span-8 provider-policy-panel">
        <div className="section-title">
          <div>
            <h2>{copy.policyTable}</h2>
            <p>{copy.policyTableDetail}</p>
          </div>
          <StatusChip tone="neutral">{policyRows.length}</StatusChip>
        </div>
        <div className="table-scroll">
          <table className="provider-policy-table">
            <thead>
              <tr>
                <th>{copy.tenant}</th>
                <th>AI</th>
                <th>Media</th>
                <th>{copy.fallback}</th>
                <th>{copy.controls}</th>
              </tr>
            </thead>
            <tbody>
              {policyRows.map(({ tenant, policy, warnings }) => (
                <tr key={tenant.id}>
                  <td data-label={copy.tenant}>
                    <strong className="table-title">{tenant.name}</strong>
                    <small>{tenant.tier}</small>
                  </td>
                  <td data-label="AI">
                    <StatusChip tone={toneForAiProvider(policy.aiProvider)}>{policy.aiProvider}</StatusChip>
                  </td>
                  <td data-label="Media">
                    <StatusChip tone={toneForMediaProvider(policy.mediaProvider)}>{policy.mediaProvider}</StatusChip>
                  </td>
                  <td data-label={copy.fallback}>
                    <StatusChip tone={toneForFallbackMode(policy.fallbackMode)}>{policy.fallbackMode}</StatusChip>
                  </td>
                  <td className="provider-control-cell" data-label={copy.controls}>
                    <div className="provider-control-stack">
                      <strong>{policy.monthlyGuardrail}</strong>
                      <span>
                        <StatusChip tone={toneForPolicySource(policy.source)}>{labelForPolicySource(policy.source, language)}</StatusChip>
                        <small className={warnings > 0 ? "sla-risk" : ""}>
                          {warnings} {copy.warnings}
                        </small>
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="surface span-4 inspector" role="complementary" aria-label={copy.overridePanel}>
        <div className="section-title">
          <div>
            <h2>{copy.overridePanel}</h2>
            <p>{copy.overrideDetail}</p>
          </div>
        </div>
        {selectedTenant ? (
          <div className="provider-form">
            <label>
              <span>{copy.tenant}</span>
              <select aria-label={copy.tenant} value={selectedTenant.id} onChange={(event) => handleTenantChange(event.target.value)}>
                {scopedTenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.aiProvider}</span>
              <select
                aria-label={copy.aiProvider}
                value={aiProvider}
                onChange={(event) => setAiProvider(event.target.value as ProviderPolicy["aiProvider"])}
              >
                {aiProviderOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.mediaProvider}</span>
              <select
                aria-label={copy.mediaProvider}
                value={mediaProvider}
                onChange={(event) => setMediaProvider(event.target.value as ProviderPolicy["mediaProvider"])}
              >
                {mediaProviderOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.fallbackMode}</span>
              <select
                aria-label={copy.fallbackMode}
                value={fallbackMode}
                onChange={(event) => setFallbackMode(event.target.value as ProviderPolicy["fallbackMode"])}
              >
                {fallbackModeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{copy.monthlyGuardrail}</span>
              <input
                aria-label={copy.monthlyGuardrail}
                min={0}
                type="number"
                value={monthlyGuardrail}
                onChange={(event) => setMonthlyGuardrail(Number(event.target.value))}
              />
            </label>
            <label>
              <span>{copy.auditReason}</span>
              <textarea
                aria-label={copy.auditReason}
                maxLength={240}
                placeholder={dataMode === "live" ? copy.auditPlaceholderLive : copy.auditPlaceholder}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <button
              type="button"
              className="primary-button"
              disabled={dataMode !== "live" || !onOverrideProviderPolicy || !reason.trim() || isSaving}
              onClick={() => void handleSubmit()}
            >
              {dataMode === "live" ? copy.overridePolicy : copy.mockOverride}
            </button>
            {message && <p className="action-message">{message}</p>}
          </div>
        ) : (
          <div className="pipeline-empty inspector-empty">
            <strong>{copy.emptyTitle}</strong>
            <p>{copy.emptyDetail}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function hasProviderWarning(material: AdminMaterial): boolean {
  return material.provider !== "stub" && (isBlockedMaterial(material) || material.mediaStatus === "failed" || material.warnings.length > 0);
}

function toneForAiProvider(provider: ProviderPolicy["aiProvider"]) {
  return provider === "stub" ? "neutral" : "success";
}

function toneForMediaProvider(provider: ProviderPolicy["mediaProvider"]) {
  return provider === "real" ? "success" : "neutral";
}

function toneForFallbackMode(mode: ProviderPolicy["fallbackMode"]) {
  if (mode === "per_tenant") {
    return "success";
  }
  if (mode === "auto_to_mock") {
    return "warning";
  }
  return "neutral";
}

function toneForPolicySource(source: ProviderPolicy["source"]) {
  if (source === "tenant_override") {
    return "warning";
  }
  if (source === "emergency_global") {
    return "danger";
  }
  if (source === "tier_default") {
    return "success";
  }
  return "neutral";
}

function labelForPolicySource(source: ProviderPolicy["source"], language: Language): string {
  const labels: Record<ProviderPolicy["source"], { zh: string; en: string }> = {
    global_default: { zh: "全局默认", en: "Global" },
    tenant_override: { zh: "租户 override", en: "Tenant" },
    tier_default: { zh: "层级默认", en: "Tier" },
    emergency_global: { zh: "紧急全局", en: "Incident" }
  };
  return labels[source][language];
}

const zhCopy = {
  title: "Provider 运维",
  subtitle: "跨租户管理 AI、media provider、降级策略和审计化 override。",
  providerWarningMaterials: "Provider 告警材料",
  providerWarningDetail: "当前租户范围内非 stub 且有失败、超时或 warning 的材料。",
  tenantOverrides: "租户 override",
  tenantOverrideDetail: "当前 dashboard 中启用的 tenant-level provider policy。",
  secretPolicy: "Secret 策略",
  secretsMasked: "已隐藏",
  secretPolicyDetail: "后台只展示 provider key，不返回任何 secret 明文。",
  policyTable: "Provider policy",
  policyTableDetail: "按租户扫描有效 AI/media provider、fallback 和 guardrail。",
  tenant: "租户",
  fallback: "Fallback",
  controls: "控制",
  warnings: "告警",
  overridePanel: "Override policy",
  overrideDetail: "高风险变更必须填写审计原因。",
  aiProvider: "AI provider",
  mediaProvider: "Media provider",
  fallbackMode: "Fallback mode",
  monthlyGuardrail: "Monthly guardrail",
  auditReason: "审计原因",
  auditPlaceholder: "填写 override 原因。Mock mode 不会提交真实 mutation。",
  auditPlaceholderLive: "填写 override 原因；live mode 会写入 provider policy 和审计。",
  overridePolicy: "写入 override",
  mockOverride: "模拟 override（no-op）",
  overrideRecorded: "Provider policy override 已记录。",
  overrideFailed: "Provider policy override 失败，请稍后重试。",
  emptyTitle: "没有可配置租户",
  emptyDetail: "切换租户范围后再配置 provider policy。"
};

const enCopy = {
  title: "Provider Ops",
  subtitle: "Manage tenant-scoped AI/media providers, fallback strategy, and audited overrides.",
  providerWarningMaterials: "Provider-warning materials",
  providerWarningDetail: "Non-stub materials with failures, SLA pressure, or warnings in the current scope.",
  tenantOverrides: "Tenant overrides",
  tenantOverrideDetail: "Tenant-level provider policies currently visible in the dashboard.",
  secretPolicy: "Secret policy",
  secretsMasked: "Secrets are masked",
  secretPolicyDetail: "The admin API returns provider keys only, never plaintext secrets.",
  policyTable: "Provider policy",
  policyTableDetail: "Scan effective AI/media provider, fallback, and guardrail by tenant.",
  tenant: "Tenant",
  fallback: "Fallback",
  controls: "Controls",
  warnings: "Warnings",
  overridePanel: "Override policy",
  overrideDetail: "High-risk provider changes require an audit reason.",
  aiProvider: "AI provider",
  mediaProvider: "Media provider",
  fallbackMode: "Fallback mode",
  monthlyGuardrail: "Monthly guardrail",
  auditReason: "Audit reason",
  auditPlaceholder: "Enter an override reason. Mock mode will not call a real mutation.",
  auditPlaceholderLive: "Enter an override reason; live mode writes provider policy and audit event.",
  overridePolicy: "Override policy",
  mockOverride: "Mock override only (no-op)",
  overrideRecorded: "Provider policy override recorded.",
  overrideFailed: "Provider policy override failed. Try again later.",
  emptyTitle: "No tenant is configurable",
  emptyDetail: "Change tenant scope before configuring provider policy."
};
