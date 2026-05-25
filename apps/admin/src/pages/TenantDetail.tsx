import { MetricCard, StatusChip } from "../components/ui";
import { getEffectiveProviderPolicy } from "../domain/selectors";
import type { AdminMaterial, Language, MaterialStatus, MediaStatus, ProviderPolicy, Tenant, TenantStatus } from "../domain/types";

interface TenantDetailProps {
  language: Language;
  tenantId: string;
  tenants: Tenant[];
  materials: AdminMaterial[];
  policies: ProviderPolicy[];
  isAllTenantPreview?: boolean;
}

export function TenantDetail({ language, tenantId, tenants, materials, policies, isAllTenantPreview = false }: TenantDetailProps) {
  const tenant = tenants.find((item) => item.id === tenantId);
  const copy = language === "zh" ? zhCopy : enCopy;

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

  const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
  const policy = getEffectiveProviderPolicy(policies, tenant.id);
  const failedJobs = tenantMaterials.filter((item) => item.jobStatus === "failed" || item.materialStatus === "failed").length;
  const processingMedia = tenantMaterials.filter((item) => item.mediaStatus === "pending" || item.mediaStatus === "processing").length;

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Tenants / {tenant.name}</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
        {isAllTenantPreview && (
          <p className="scope-note">
            {copy.allTenantPreview}: <strong>{tenant.name}</strong>
          </p>
        )}
      </section>

      <section className="surface span-5">
        <div className="tenant-profile">
          <div className="tenant-badge" aria-hidden="true">
            {getTenantInitials(tenant.name)}
          </div>
          <div>
            <h2>{tenant.name}</h2>
            <StatusChip tone={getTenantStatusTone(tenant.status)}>{tenant.status}</StatusChip>
          </div>
        </div>
        <dl className="detail-list">
          <dt>Tenant ID</dt>
          <dd>{tenant.id}</dd>
          <dt>{copy.type}</dt>
          <dd>{tenant.tenantType}</dd>
          <dt>{copy.region}</dt>
          <dd>{tenant.region}</dd>
          <dt>{copy.owner}</dt>
          <dd>{tenant.ownerContact}</dd>
          <dt>{copy.tier}</dt>
          <dd>{tenant.tier}</dd>
          <dt>{copy.created}</dt>
          <dd>{tenant.createdAt}</dd>
        </dl>
      </section>

      <section className="metric-row span-7" aria-label={copy.metrics}>
        <MetricCard label={copy.parents} value={tenant.activeParents.toLocaleString()} detail={copy.parentsDetail} />
        <MetricCard label={copy.children} value={tenant.children.toLocaleString()} detail={copy.childrenDetail} />
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
        <div className="module-grid">
          {buildModules(policy, failedJobs, tenant).map((module) => (
            <div key={module.name} className="module-row">
              <span>{module.name}</span>
              <StatusChip tone={module.tone}>{module.status}</StatusChip>
            </div>
          ))}
        </div>
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
  name: string;
  status: string;
  tone: "success" | "warning" | "danger" | "neutral";
};

function buildModules(policy: ProviderPolicy, failedJobs: number, tenant: Tenant): ModuleRow[] {
  const isPilotTier = tenant.tier.toLowerCase().includes("pilot");

  return [
    { name: "Worksheet import", status: `${tenant.tier} ready`, tone: "success" },
    {
      name: "AI review",
      status: policy.aiProvider === "stub" ? "Prototype stub" : `Provider ${policy.aiProvider}`,
      tone: policy.aiProvider === "stub" ? "neutral" : "success"
    },
    {
      name: "Media pipeline",
      status: policy.mediaProvider === "real" ? "Real media preview" : "Mock media preview",
      tone: policy.mediaProvider === "real" ? "success" : "warning"
    },
    { name: "Speaking score", status: isPilotTier ? "Pilot-tier ready" : "Tier review", tone: isPilotTier ? "success" : "warning" },
    { name: "Weekly reports", status: failedJobs > 0 ? "Watch failed jobs" : "Readiness OK", tone: failedJobs > 0 ? "warning" : "success" }
  ];
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
  subtitle: "查看租户身份、配额使用、Prototype readiness、Provider 策略和内容材料状态。",
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
  modules: "Prototype operational readiness",
  modulesDetail: "Phase 1 readiness view derived from tenant tier and provider policy; not authoritative module access.",
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
  subtitle: "Tenant identity, quota usage, prototype readiness, provider policy, and tenant content health.",
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
  modules: "Prototype operational readiness",
  modulesDetail: "Phase 1 readiness view derived from tenant tier and provider policy; not authoritative module access.",
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
