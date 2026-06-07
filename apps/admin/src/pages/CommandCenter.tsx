import { useState } from "react";
import { ActionDrawer } from "../components/ActionDrawer";
import { MetricCard, StatusChip } from "../components/ui";
import { getLifecycleCounts, getMaterialsForScope, getTenantHealthRows, isBlockedMaterial } from "../domain/selectors";
import type { AdminMaterial, AdminOperationsData, AdminOperationsIssue, Language, LifecycleCounts, Tenant, TenantScope } from "../domain/types";

interface CommandCenterProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
  operationsData?: AdminOperationsData;
  adminPermissions?: string[];
  onSubmitIssueAction?: (issue: AdminOperationsIssue, reason: string) => void | Promise<void>;
}

type FunnelItem = {
  key: keyof LifecycleCounts;
  label: string;
};

export function CommandCenter({
  language,
  tenantScope,
  tenants,
  materials,
  operationsData,
  adminPermissions = [],
  onSubmitIssueAction
}: CommandCenterProps) {
  const [selectedIssue, setSelectedIssue] = useState<AdminOperationsIssue | null>(null);
  const [isSubmittingIssue, setIsSubmittingIssue] = useState(false);
  const [issueActionError, setIssueActionError] = useState("");
  const scopedMaterials = getMaterialsForScope(materials, tenantScope);
  const scopedTenants = tenantScope === "all" ? tenants : tenants.filter((tenant) => tenant.id === tenantScope);
  const counts = getLifecycleCounts(scopedMaterials);
  const tenantRows = getTenantHealthRows(scopedTenants, scopedMaterials).slice(0, 4);
  const riskRows = scopedMaterials.filter(isBlockedMaterial);
  const operationsDataMatchesScope = operationsData?.tenantScope === tenantScope;
  const operationIssues = (operationsData?.issues ?? []).filter(
    (issue) => tenantScope === "all" || issue.relatedResource.tenantId === tenantScope
  );
  const usesOperationIssues = operationIssues.length > 0;
  const providerIncidents = scopedMaterials.filter(hasProviderIncident).length;
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
        <MetricCard
          label={copy.blockedJobs}
          value={usesOperationIssues ? operationIssues.length : riskRows.length}
          detail={copy.blockedJobsDetail}
        />
        <MetricCard
          label={copy.mediaFailures}
          value={
            usesOperationIssues && operationsDataMatchesScope
              ? numberFromRecord(operationsData?.summary, "media_failures")
              : scopedMaterials.filter((material) => material.mediaStatus === "failed").length
          }
          detail={copy.mediaFailuresDetail}
        />
        <MetricCard label={copy.providerIncidents} value={providerIncidents} detail={copy.providerIncidentDetail} />
      </div>

      <section className="surface table-panel span-7">
        <div className="section-title">
          <h2>{copy.inbox}</h2>
          <StatusChip tone={(usesOperationIssues ? operationIssues.length : riskRows.length) > 0 ? "warning" : "success"}>
            {usesOperationIssues ? operationIssues.length : riskRows.length} SLA
          </StatusChip>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              {usesOperationIssues ? (
                <tr>
                  <th>{copy.tenant}</th>
                  <th>{copy.issue}</th>
                  <th>{copy.scope}</th>
                  <th>{copy.status}</th>
                  <th>{copy.action}</th>
                </tr>
              ) : (
                <tr>
                  <th>{copy.tenant}</th>
                  <th>{copy.issue}</th>
                  <th>{copy.scope}</th>
                  <th>{copy.status}</th>
                  <th>SLA</th>
                </tr>
              )}
            </thead>
            <tbody>
              {usesOperationIssues
                ? operationIssues.map((issue) => (
                    <tr key={issue.id}>
                      <td>{tenantName(tenants, issue.relatedResource.tenantId)}</td>
                      <td>
                        <strong className="table-title">{issue.statusLabel}</strong>
                        <small>{issue.reason}</small>
                      </td>
                      <td>{issue.relatedResource.type}</td>
                      <td>
                        <StatusChip tone={severityTone(issue.severity)}>{issue.severity}</StatusChip>
                      </td>
                      <td>{renderIssueAction(issue)}</td>
                    </tr>
                  ))
                : riskRows.map((material) => (
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
      {selectedIssue && (
        <ActionDrawer
          language={language}
          issue={selectedIssue}
          isOpen={true}
          isSubmitting={isSubmittingIssue}
          submitError={issueActionError}
          onClose={() => {
            setIssueActionError("");
            setSelectedIssue(null);
          }}
          onSubmit={(reason) => void handleSubmitIssueAction(selectedIssue, reason)}
        />
      )}
    </div>
  );

  async function handleSubmitIssueAction(issue: AdminOperationsIssue, reason: string) {
    if (!onSubmitIssueAction) {
      setSelectedIssue(null);
      return;
    }
    setIsSubmittingIssue(true);
    setIssueActionError("");
    try {
      await onSubmitIssueAction(issue, reason);
      setSelectedIssue(null);
    } catch (error) {
      setIssueActionError(error instanceof Error && error.message ? error.message : copy.actionFailed);
    } finally {
      setIsSubmittingIssue(false);
    }
  }

  function renderIssueAction(issue: AdminOperationsIssue) {
    const canSubmit =
      Boolean(onSubmitIssueAction) && isSupportedIssueAction(issue) && hasRequiredPermission(adminPermissions, issue.requiredPermission);
    if (!canSubmit) {
      return (
        <span className="table-muted-action" aria-label={`${copy.actionUnavailableFor} ${issue.statusLabel}`}>
          {issue.recommendedAction}
        </span>
      );
    }
    return (
      <button
        type="button"
        className="table-link-button"
        onClick={() => {
          setIssueActionError("");
          setSelectedIssue(issue);
        }}
        aria-label={`${copy.openActionFor} ${issue.statusLabel}`}
      >
        {issue.recommendedAction}
      </button>
    );
  }
}

function hasProviderIncident(material: AdminMaterial): boolean {
  return material.provider !== "stub" && (isBlockedMaterial(material) || material.mediaStatus === "failed" || material.warnings.length > 0);
}

function severityTone(severity: AdminOperationsIssue["severity"]): "success" | "warning" | "danger" | "neutral" {
  if (severity === "critical") {
    return "danger";
  }
  if (severity === "warning") {
    return "warning";
  }
  if (severity === "ok") {
    return "success";
  }
  return "neutral";
}

function tenantName(tenants: Tenant[], tenantId: string | undefined): string {
  if (!tenantId) {
    return "";
  }
  return tenants.find((tenant) => tenant.id === tenantId)?.name ?? tenantId;
}

function numberFromRecord(record: Record<string, unknown> | undefined, key: string): number {
  const value = record?.[key];
  return typeof value === "number" ? value : 0;
}

function hasRequiredPermission(adminPermissions: string[], requiredPermission: string | undefined): boolean {
  return !requiredPermission || adminPermissions.includes("*") || adminPermissions.includes(requiredPermission);
}

function isSupportedIssueAction(issue: AdminOperationsIssue): boolean {
  if (issue.recommendedAction === "retry_material_job") {
    return issue.relatedResource.type === "material_parse_job";
  }
  if (issue.recommendedAction === "archive_material") {
    return Boolean(issue.relatedResource.materialId || issue.relatedResource.id);
  }
  return false;
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
  providerIncidentDetail: "当前范围内 provider 告警材料",
  inbox: "今日待处理",
  tenant: "租户",
  issue: "问题",
  scope: "影响范围",
  status: "状态",
  action: "操作",
  openActionFor: "打开操作",
  actionUnavailableFor: "不可执行的操作",
  actionFailed: "操作提交失败，请检查权限或稍后重试。",
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
  providerIncidentDetail: "Provider-warning materials in scope",
  inbox: "Action inbox",
  tenant: "Tenant",
  issue: "Issue",
  scope: "Scope",
  status: "Status",
  action: "Action",
  openActionFor: "Open action for",
  actionUnavailableFor: "Unavailable action for",
  actionFailed: "Action failed. Check permissions or try again later.",
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
