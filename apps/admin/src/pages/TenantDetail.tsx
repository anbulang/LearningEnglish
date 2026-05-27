import { useState } from "react";
import { MetricCard, StatusChip } from "../components/ui";
import { getEffectiveProviderPolicy } from "../domain/selectors";
import type {
  AdminMaterial,
  Language,
  MaterialStatus,
  MediaStatus,
  ModuleKey,
  ProviderPolicy,
  Tenant,
  TenantModuleSetting,
  TenantStatus
} from "../domain/types";

export interface TenantModuleToggleInput {
  tenantId: string;
  moduleKey: ModuleKey;
  enabled: boolean;
  reason: string;
}

interface TenantDetailProps {
  language: Language;
  tenantId: string;
  tenants: Tenant[];
  materials: AdminMaterial[];
  policies: ProviderPolicy[];
  moduleSettings: TenantModuleSetting[];
  isAllTenantPreview?: boolean;
  dataMode?: "mock" | "live";
  onToggleTenantModule?: (input: TenantModuleToggleInput) => Promise<void>;
}

export function TenantDetail({
  language,
  tenantId,
  tenants,
  materials,
  policies,
  moduleSettings,
  isAllTenantPreview = false,
  dataMode = "mock",
  onToggleTenantModule
}: TenantDetailProps) {
  const tenant = tenants.find((item) => item.id === tenantId);
  const copy = language === "zh" ? zhCopy : enCopy;
  const [moduleReason, setModuleReason] = useState("");
  const [moduleMessage, setModuleMessage] = useState("");
  const [savingModuleKey, setSavingModuleKey] = useState<ModuleKey | "">("");

  if (!tenant) {
    return (
      <section className="surface empty-phase">
        <h1>{copy.emptyTitle}</h1>
        <p>
          {copy.emptyDetail}: <strong>{tenantId}</strong>
        </p>
      </section>
    );
  }

  const selectedTenant = tenant;
  const tenantMaterials = materials.filter((material) => material.tenantId === selectedTenant.id);
  const policy = getEffectiveProviderPolicy(policies, selectedTenant.id, selectedTenant.tier);
  const failedJobs = tenantMaterials.filter((item) => item.jobStatus === "failed" || item.materialStatus === "failed").length;
  const processingMedia = tenantMaterials.filter((item) => item.mediaStatus === "pending" || item.mediaStatus === "processing").length;
  const moduleRows = buildModules(policy, failedJobs, selectedTenant, moduleSettings, language);

  async function handleModuleToggle(module: ModuleRow) {
    if (!onToggleTenantModule || !moduleReason.trim()) {
      return;
    }
    setSavingModuleKey(module.moduleKey);
    setModuleMessage("");
    try {
      await onToggleTenantModule({
        tenantId: selectedTenant.id,
        moduleKey: module.moduleKey,
        enabled: !module.enabled,
        reason: moduleReason.trim()
      });
      setModuleReason("");
      setModuleMessage(copy.moduleUpdated);
    } catch {
      setModuleMessage(copy.moduleFailed);
    } finally {
      setSavingModuleKey("");
    }
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Tenants / {selectedTenant.name}</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
        {isAllTenantPreview && (
          <p className="scope-note">
            {copy.allTenantPreview}: <strong>{selectedTenant.name}</strong>
          </p>
        )}
      </section>

      <section className="surface span-5">
        <div className="tenant-profile">
          <div className="tenant-badge" aria-hidden="true">
            {getTenantInitials(selectedTenant.name)}
          </div>
          <div>
            <h2>{selectedTenant.name}</h2>
            <StatusChip tone={getTenantStatusTone(selectedTenant.status)}>{selectedTenant.status}</StatusChip>
          </div>
        </div>
        <dl className="detail-list">
          <dt>Tenant ID</dt>
          <dd>{selectedTenant.id}</dd>
          <dt>{copy.type}</dt>
          <dd>{selectedTenant.tenantType}</dd>
          <dt>{copy.region}</dt>
          <dd>{selectedTenant.region}</dd>
          <dt>{copy.owner}</dt>
          <dd>{selectedTenant.ownerContact}</dd>
          <dt>{copy.tier}</dt>
          <dd>{selectedTenant.tier}</dd>
          <dt>{copy.created}</dt>
          <dd>{selectedTenant.createdAt}</dd>
        </dl>
      </section>

      <section className="metric-row span-7" aria-label={copy.metrics}>
        <MetricCard label={copy.parents} value={selectedTenant.activeParents.toLocaleString()} detail={copy.parentsDetail} />
        <MetricCard label={copy.children} value={selectedTenant.children.toLocaleString()} detail={copy.childrenDetail} />
        <MetricCard label={copy.materialsMetric} value={tenantMaterials.length} detail={copy.materialsDetail} />
        <MetricCard label={copy.failedJobs} value={failedJobs} detail={copy.failedJobsDetail} />
      </section>

      <section className="surface span-5">
        <div className="section-title">
          <h2>{copy.policy}</h2>
          <StatusChip tone={policy.source === "tenant_override" ? "warning" : "neutral"}>{policy.source}</StatusChip>
        </div>
        <dl className="detail-list">
          <dt>AI_PROVIDER</dt>
          <dd>{policy.aiProvider}</dd>
          <dt>MEDIA_PROVIDER</dt>
          <dd>{policy.mediaProvider}</dd>
          <dt>{copy.fallback}</dt>
          <dd>{policy.fallbackMode}</dd>
          <dt>{copy.guardrail}</dt>
          <dd>{policy.monthlyGuardrail.toLocaleString()}</dd>
          <dt>{copy.policySource}</dt>
          <dd>{policy.source}</dd>
        </dl>
      </section>

      <section className="surface span-7">
        <div className="section-title">
          <div>
            <h2>{copy.modules}</h2>
            <p>{copy.modulesDetail}</p>
          </div>
          <StatusChip tone={processingMedia > 0 ? "warning" : "success"}>
            {processingMedia > 0 ? copy.mediaProcessing : copy.allClear}
          </StatusChip>
        </div>
        <div className="module-reason">
          <label>
            <span>{copy.moduleReason}</span>
            <textarea
              aria-label={copy.moduleReason}
              maxLength={240}
              placeholder={dataMode === "live" ? copy.moduleReasonPlaceholderLive : copy.moduleReasonPlaceholder}
              value={moduleReason}
              onChange={(event) => setModuleReason(event.target.value)}
            />
          </label>
        </div>
        <div className="module-grid">
          {moduleRows.map((module) => (
            <div key={module.moduleKey} className="module-row">
              <div>
                <span>{module.name}</span>
                <small>{module.detail}</small>
              </div>
              <div className="module-actions">
                <StatusChip tone={module.enabled ? "success" : "danger"}>{module.enabled ? copy.enabled : copy.disabled}</StatusChip>
                <StatusChip tone={module.source === "tenant_override" ? "warning" : "neutral"}>
                  {module.source === "tenant_override" ? copy.tenantOverride : copy.globalDefault}
                </StatusChip>
                <button
                  type="button"
                  className="ghost-button compact-action"
                  disabled={
                    dataMode !== "live" ||
                    !onToggleTenantModule ||
                    !moduleReason.trim() ||
                    savingModuleKey === module.moduleKey
                  }
                  onClick={() => void handleModuleToggle(module)}
                >
                  {module.enabled ? copy.disableModule(module.name) : copy.enableModule(module.name)}
                </button>
              </div>
            </div>
          ))}
        </div>
        {moduleMessage && <p className="action-message">{moduleMessage}</p>}
      </section>

      <section className="surface wide table-panel">
        <div className="section-title">
          <h2>{copy.materials}</h2>
          <StatusChip tone={tenantMaterials.length > 0 ? "success" : "neutral"}>{tenantMaterials.length}</StatusChip>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{copy.material}</th>
                <th>{copy.child}</th>
                <th>{copy.parent}</th>
                <th>{copy.materialStatus}</th>
                <th>{copy.jobStatus}</th>
                <th>{copy.media}</th>
                <th>{copy.updated}</th>
              </tr>
            </thead>
            <tbody>
              {tenantMaterials.map((material) => (
                <tr key={material.id}>
                  <td>
                    <strong className="table-title">{material.title}</strong>
                    <small>
                      {material.pageCount} pages / {material.learningAssets} assets
                    </small>
                  </td>
                  <td>
                    {material.childName}
                    <small>
                      {material.childAge} {copy.yearsOld}
                    </small>
                  </td>
                  <td>{material.parentName}</td>
                  <td>
                    <StatusChip tone={getMaterialStatusTone(material.materialStatus)}>{material.materialStatus}</StatusChip>
                  </td>
                  <td>
                    <StatusChip tone={getMaterialStatusTone(material.jobStatus)}>{material.jobStatus}</StatusChip>
                  </td>
                  <td>
                    <StatusChip tone={getMediaStatusTone(material.mediaStatus)}>{material.mediaStatus}</StatusChip>
                  </td>
                  <td>{material.updatedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

type ModuleRow = {
  moduleKey: ModuleKey;
  name: string;
  detail: string;
  enabled: boolean;
  source: TenantModuleSetting["source"];
  tone: "success" | "warning" | "danger" | "neutral";
};

function buildModules(
  policy: ProviderPolicy,
  failedJobs: number,
  tenant: Tenant,
  moduleSettings: TenantModuleSetting[],
  language: Language
): ModuleRow[] {
  const isPilotTier = tenant.tier.toLowerCase().includes("pilot");
  const rows: Array<Omit<ModuleRow, "enabled" | "source">> = [
    { moduleKey: "worksheet_import", name: moduleLabel("worksheet_import", language), detail: `${tenant.tier} ready`, tone: "success" },
    {
      moduleKey: "ai_review",
      name: moduleLabel("ai_review", language),
      detail: policy.aiProvider === "stub" ? "Prototype stub" : `Provider ${policy.aiProvider}`,
      tone: policy.aiProvider === "stub" ? "neutral" : "success"
    },
    {
      moduleKey: "media_pipeline",
      name: moduleLabel("media_pipeline", language),
      detail: policy.mediaProvider === "real" ? "Real media preview" : "Mock media preview",
      tone: policy.mediaProvider === "real" ? "success" : "warning"
    },
    {
      moduleKey: "speaking_score",
      name: moduleLabel("speaking_score", language),
      detail: isPilotTier ? "Pilot-tier ready" : "Tier review",
      tone: isPilotTier ? "success" : "warning"
    },
    {
      moduleKey: "weekly_reports",
      name: moduleLabel("weekly_reports", language),
      detail: failedJobs > 0 ? "Watch failed jobs" : "Readiness OK",
      tone: failedJobs > 0 ? "warning" : "success"
    }
  ];
  return rows.map((row) => {
    const setting = moduleSettings.find((item) => item.tenantId === tenant.id && item.moduleKey === row.moduleKey);
    return {
      ...row,
      enabled: setting?.enabled ?? true,
      source: setting?.source ?? "global_default"
    };
  });
}

function moduleLabel(moduleKey: ModuleKey, language: Language): string {
  const labels: Record<ModuleKey, { zh: string; en: string }> = {
    worksheet_import: { zh: "讲义导入", en: "Worksheet import" },
    ai_review: { zh: "AI 解析", en: "AI review" },
    media_pipeline: { zh: "媒体流水线", en: "Media pipeline" },
    speaking_score: { zh: "口语评分", en: "Speaking score" },
    weekly_reports: { zh: "周报", en: "Weekly reports" }
  };
  return labels[moduleKey][language];
}

function getTenantInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getTenantStatusTone(status: TenantStatus): "success" | "warning" | "danger" {
  if (status === "active") {
    return "success";
  }
  if (status === "suspended") {
    return "danger";
  }
  return "warning";
}

function getMaterialStatusTone(status: MaterialStatus | AdminMaterial["jobStatus"]): "success" | "warning" | "danger" | "neutral" {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "processing" || status === "needs_review" || status === "queued") {
    return "warning";
  }
  return "neutral";
}

function getMediaStatusTone(status: MediaStatus): "success" | "warning" | "danger" {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  return "warning";
}

const zhCopy = {
  title: "租户详情",
  subtitle: "查看租户身份、配额使用、模块访问、Provider 策略和内容材料状态。",
  emptyTitle: "未找到租户",
  emptyDetail: "当前 mock 数据中不存在请求的 tenantId",
  allTenantPreview: "All tenants selected; showing first tenant preview",
  type: "类型",
  region: "区域",
  owner: "负责人",
  tier: "套餐",
  created: "创建时间",
  metrics: "租户指标",
  parents: "家长账号",
  parentsDetail: "active parent accounts",
  children: "孩子档案",
  childrenDetail: "child profiles",
  materialsMetric: "材料",
  materialsDetail: "current tenant scope",
  failedJobs: "失败任务",
  failedJobsDetail: "requires attention",
  policy: "Effective provider policy",
  fallback: "Fallback",
  guardrail: "Monthly guardrail",
  policySource: "Policy source",
  modules: "租户模块访问",
  modulesDetail: "已审计的模块开关控制租户级功能访问。",
  moduleReason: "模块变更原因",
  moduleReasonPlaceholder: "填写启用或禁用模块的原因。Mock mode 不会提交真实 mutation。",
  moduleReasonPlaceholderLive: "填写启用或禁用模块的原因；live mode 会写入模块设置和审计。",
  moduleUpdated: "模块设置已更新。",
  moduleFailed: "模块设置更新失败，请稍后重试。",
  enabled: "enabled",
  disabled: "disabled",
  tenantOverride: "租户 override",
  globalDefault: "全局默认",
  enableModule: (name: string) => `启用 ${name}`,
  disableModule: (name: string) => `禁用 ${name}`,
  mediaProcessing: "Media processing",
  allClear: "All clear",
  materials: "Tenant materials",
  material: "Material",
  child: "Child",
  parent: "Parent",
  materialStatus: "Material status",
  jobStatus: "Job status",
  media: "Media",
  updated: "Updated",
  yearsOld: "years old"
};

const enCopy = {
  title: "Tenant Detail",
  subtitle: "Tenant identity, quota usage, module access, provider policy, and tenant content health.",
  emptyTitle: "Tenant not found",
  emptyDetail: "Requested tenantId is not present in the current mock dataset",
  allTenantPreview: "All tenants selected; showing first tenant preview",
  type: "Type",
  region: "Region",
  owner: "Owner",
  tier: "Tier",
  created: "Created",
  metrics: "Tenant metrics",
  parents: "Parents",
  parentsDetail: "active parent accounts",
  children: "Children",
  childrenDetail: "child profiles",
  materialsMetric: "Materials",
  materialsDetail: "current tenant scope",
  failedJobs: "Failed jobs",
  failedJobsDetail: "requires attention",
  policy: "Effective provider policy",
  fallback: "Fallback",
  guardrail: "Monthly guardrail",
  policySource: "Policy source",
  modules: "Tenant module access",
  modulesDetail: "Audited module switches control tenant-level feature access.",
  moduleReason: "Module change reason",
  moduleReasonPlaceholder: "Enter a reason before enabling or disabling a module. Mock mode will not call a real mutation.",
  moduleReasonPlaceholderLive: "Enter a reason before enabling or disabling a module; live mode writes module settings and audit.",
  moduleUpdated: "Module setting updated.",
  moduleFailed: "Module setting update failed. Try again later.",
  enabled: "enabled",
  disabled: "disabled",
  tenantOverride: "Tenant override",
  globalDefault: "Global default",
  enableModule: (name: string) => `Enable ${name}`,
  disableModule: (name: string) => `Disable ${name}`,
  mediaProcessing: "Media processing",
  allClear: "All clear",
  materials: "Tenant materials",
  material: "Material",
  child: "Child",
  parent: "Parent",
  materialStatus: "Material status",
  jobStatus: "Job status",
  media: "Media",
  updated: "Updated",
  yearsOld: "years old"
};
