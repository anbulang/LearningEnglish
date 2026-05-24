import { MetricCard, StatusChip } from "../components/ui";
import { getLifecycleCounts, getMaterialsForScope, getTenantHealthRows } from "../domain/selectors";
import type { AdminMaterial, Language, LifecycleCounts, Tenant, TenantScope } from "../domain/types";

interface CommandCenterProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
}

type FunnelItem = {
  key: keyof LifecycleCounts;
  label: string;
};

export function CommandCenter({ language, tenantScope, tenants, materials }: CommandCenterProps) {
  const scopedMaterials = getMaterialsForScope(materials, tenantScope);
  const scopedTenants = tenantScope === "all" ? tenants : tenants.filter((tenant) => tenant.id === tenantScope);
  const counts = getLifecycleCounts(scopedMaterials);
  const tenantRows = getTenantHealthRows(scopedTenants, scopedMaterials).slice(0, 4);
  const riskRows = scopedMaterials.filter(
    (material) => material.materialStatus === "failed" || material.jobStatus === "failed" || material.slaMinutes > 120
  );
  const copy = language === "zh" ? zhCopy : enCopy;
  const funnelItems: FunnelItem[] = [
    { key: "upload", label: copy.stageUpload },
    { key: "parse", label: copy.stageParse },
    { key: "parentReview", label: copy.stageParentReview },
    { key: "knowledgePack", label: copy.stageKnowledgePack },
    { key: "media", label: copy.stageMedia },
    { key: "ready", label: copy.stageReady },
    { key: "failed", label: copy.stageFailed }
  ];

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">Platform Admin Console</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <div className="metric-row wide">
        <MetricCard label={copy.activeTenants} value={scopedTenants.length} detail={copy.activeTenantsDetail} />
        <MetricCard label={copy.blockedJobs} value={riskRows.length} detail={copy.blockedJobsDetail} />
        <MetricCard
          label={copy.mediaFailures}
          value={scopedMaterials.filter((material) => material.mediaStatus === "failed").length}
          detail={copy.mediaFailuresDetail}
        />
        <MetricCard label={copy.providerIncidents} value={copy.providerIncidentValue} detail={copy.providerIncidentDetail} />
      </div>

      <section className="surface table-panel span-7">
        <div className="section-title">
          <h2>{copy.inbox}</h2>
          <StatusChip tone={riskRows.length > 0 ? "warning" : "success"}>{riskRows.length} SLA</StatusChip>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{copy.tenant}</th>
                <th>{copy.issue}</th>
                <th>{copy.scope}</th>
                <th>{copy.status}</th>
                <th>SLA</th>
              </tr>
            </thead>
            <tbody>
              {riskRows.map((material) => (
                <tr key={material.id}>
                  <td>{tenants.find((tenant) => tenant.id === material.tenantId)?.name ?? material.tenantId}</td>
                  <td>
                    <strong className="table-title">{material.title}</strong>
                    <small>{material.warnings[0] ?? material.confidenceSummary}</small>
                  </td>
                  <td>{material.childName}</td>
                  <td>
                    <StatusChip tone={material.materialStatus === "failed" ? "danger" : "warning"}>{material.materialStatus}</StatusChip>
                  </td>
                  <td>{material.slaMinutes}m</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface span-5">
        <div className="section-title">
          <h2>{copy.lifecycle}</h2>
        </div>
        <div className="funnel-list">
          {funnelItems.map((item) => (
            <div className="funnel-row" key={item.key}>
              <span>{item.label}</span>
              <strong>{counts[item.key]}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="surface wide">
        <div className="section-title">
          <h2>{copy.tenantHealth}</h2>
        </div>
        <div className="tenant-health-grid">
          {tenantRows.map((row) => (
            <article key={row.tenant.id} className="tenant-health-card">
              <strong>{row.tenant.name}</strong>
              <span>{row.tenant.tenantType}</span>
              <b>{row.healthScore}</b>
              <small>
                {row.blockedJobs} {copy.blockedShort} / {row.mediaFailures} {copy.mediaShort}
              </small>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

const zhCopy = {
  title: "平台指挥台",
  subtitle: "多租户学习内容生产、AI 处理和学习结果的统一运营入口",
  activeTenants: "活跃租户",
  activeTenantsDetail: "当前范围内学校、机构与家庭试点",
  blockedJobs: "阻塞任务",
  blockedJobsDetail: "超过 SLA 或失败",
  mediaFailures: "媒体失败",
  mediaFailuresDetail: "配图或 TTS 失败",
  providerIncidents: "Provider 事件",
  providerIncidentValue: "2 active",
  providerIncidentDetail: "Doubao Text / OpenAI Media",
  inbox: "今日待处理",
  tenant: "租户",
  issue: "问题",
  scope: "影响范围",
  status: "状态",
  lifecycle: "内容生产生命周期",
  tenantHealth: "租户健康摘要",
  stageUpload: "上传",
  stageParse: "OCR / 解析",
  stageParentReview: "家长确认",
  stageKnowledgePack: "知识包",
  stageMedia: "媒体 / TTS",
  stageReady: "可学习",
  stageFailed: "失败",
  blockedShort: "阻塞",
  mediaShort: "媒体"
};

const enCopy = {
  title: "Platform Command Center",
  subtitle: "Unified operations for multi-tenant content production, AI processing, and learning outcomes.",
  activeTenants: "Active tenants",
  activeTenantsDetail: "Schools, organizations, and family pilots in scope",
  blockedJobs: "Blocked jobs",
  blockedJobsDetail: "Failed or over SLA",
  mediaFailures: "Media failures",
  mediaFailuresDetail: "Image or TTS failures",
  providerIncidents: "Provider incidents",
  providerIncidentValue: "2 active",
  providerIncidentDetail: "Doubao Text / OpenAI Media",
  inbox: "Action inbox",
  tenant: "Tenant",
  issue: "Issue",
  scope: "Scope",
  status: "Status",
  lifecycle: "Content lifecycle",
  tenantHealth: "Tenant health summary",
  stageUpload: "Upload",
  stageParse: "OCR / Parse",
  stageParentReview: "Parent Review",
  stageKnowledgePack: "Knowledge Pack",
  stageMedia: "Media / TTS",
  stageReady: "Ready",
  stageFailed: "Failed",
  blockedShort: "blocked",
  mediaShort: "media"
};
