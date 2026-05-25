import { useMemo, useState } from "react";
import { StatusChip } from "../components/ui";
import { getMaterialsForScope } from "../domain/selectors";
import type { AdminMaterial, JobStatus, Language, MaterialStatus, MediaStatus, Tenant, TenantScope } from "../domain/types";

interface ContentPipelineProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  materials: AdminMaterial[];
}

type StatusFilter = "all" | MaterialStatus;

const statusFilterOptions: StatusFilter[] = ["all", "uploaded", "processing", "needs_review", "ready", "failed", "archived"];

export function ContentPipeline({ language, tenantScope, tenants, materials }: ContentPipelineProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);
  const copy = language === "zh" ? zhCopy : enCopy;
  const tenantNameById = useMemo(() => new Map(tenants.map((tenant) => [tenant.id, tenant.name])), [tenants]);
  const scopedMaterials = useMemo(() => getMaterialsForScope(materials, tenantScope), [materials, tenantScope]);
  const filteredMaterials = useMemo(
    () => (statusFilter === "all" ? scopedMaterials : scopedMaterials.filter((material) => material.materialStatus === statusFilter)),
    [scopedMaterials, statusFilter]
  );
  const selectedMaterial =
    filteredMaterials.find((material) => material.id === selectedMaterialId) ?? filteredMaterials[0] ?? null;
  const selectedMaterialLabel = selectedMaterial ? copy.selectedHint : copy.noSelection;

  function handleStatusFilterChange(value: string) {
    if (isStatusFilter(value)) {
      setStatusFilter(value);
      setSelectedMaterialId(null);
    }
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">CourseMaterial / MaterialParseJob / LearningAsset</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface wide filter-bar" aria-label={copy.filters}>
        <label>
          <span>{copy.status}</span>
          <select
            aria-label={copy.statusFilter}
            value={statusFilter}
            onChange={(event) => handleStatusFilterChange(event.target.value)}
          >
            {statusFilterOptions.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? copy.all : option}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="primary-button">
          {copy.bulkRetryMock}
        </button>
        <button type="button" className="ghost-button">
          {copy.exportFailures}
        </button>
      </section>

      <section className="surface table-panel span-8">
        <div className="section-title">
          <div>
            <h2>{copy.queue}</h2>
            <p>
              {filteredMaterials.length} / {scopedMaterials.length} {copy.materialsInScope}
            </p>
          </div>
          <StatusChip tone={filteredMaterials.some((material) => material.materialStatus === "failed") ? "danger" : "neutral"}>
            {statusFilter === "all" ? copy.all : statusFilter}
          </StatusChip>
        </div>
        {filteredMaterials.length > 0 ? (
          <div className="table-scroll">
            <table className="pipeline-table">
              <thead>
                <tr>
                  <th>{copy.tenant}</th>
                  <th>{copy.child}</th>
                  <th>{copy.material}</th>
                  <th>{copy.materialStatus}</th>
                  <th>{copy.jobStatus}</th>
                  <th>Provider</th>
                  <th>Assets</th>
                  <th>Media</th>
                  <th>SLA</th>
                </tr>
              </thead>
              <tbody>
                {filteredMaterials.map((material) => (
                  <tr
                    key={material.id}
                    className={selectedMaterial?.id === material.id ? "selected-row" : ""}
                    onClick={() => setSelectedMaterialId(material.id)}
                  >
                    <td>{tenantNameById.get(material.tenantId) ?? material.tenantId}</td>
                    <td>
                      {material.childName}
                      <small>{material.parentName}</small>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="table-link-button"
                        aria-label={`${copy.inspect} ${material.title}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedMaterialId(material.id);
                        }}
                      >
                        {material.title}
                      </button>
                      <small>
                        {material.id} / {material.jobId}
                      </small>
                    </td>
                    <td>
                      <StatusChip tone={toneForMaterialStatus(material.materialStatus)}>{material.materialStatus}</StatusChip>
                    </td>
                    <td>
                      <StatusChip tone={toneForJobStatus(material.jobStatus)}>{material.jobStatus}</StatusChip>
                    </td>
                    <td>{material.provider}</td>
                    <td>{material.learningAssets}</td>
                    <td>
                      <StatusChip tone={toneForMediaStatus(material.mediaStatus)}>{material.mediaStatus}</StatusChip>
                    </td>
                    <td className={material.slaMinutes > 180 || material.materialStatus === "failed" ? "sla-risk" : ""}>
                      {material.slaMinutes}m
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pipeline-empty">
            <strong>{copy.emptyFiltered}</strong>
            <p>{copy.emptyFilteredDetail}</p>
          </div>
        )}
      </section>

      <aside className="surface span-4 inspector" role="complementary" aria-label={copy.inspectorAria}>
        <div className="section-title">
          <div>
            <h2>{copy.inspector}</h2>
            <p>{selectedMaterialLabel}</p>
          </div>
        </div>
        {selectedMaterial ? (
          <MaterialInspector material={selectedMaterial} tenantName={tenantNameById.get(selectedMaterial.tenantId)} copy={copy} />
        ) : (
          <div className="pipeline-empty inspector-empty">
            <strong>{copy.emptyInspector}</strong>
            <p>{copy.emptyInspectorDetail}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function MaterialInspector({
  material,
  tenantName,
  copy
}: {
  material: AdminMaterial;
  tenantName: string | undefined;
  copy: typeof zhCopy;
}) {
  const timelineItems = [
    `${copy.uploaded}: ${material.sourcePages.length} ${copy.sourcePages}`,
    `${copy.parseJob}: ${material.jobStatus}`,
    `${copy.materialStatus}: ${material.materialStatus}`,
    `${copy.media}: ${material.mediaStatus}`,
    `${copy.updated}: ${material.updatedAt}`
  ];

  return (
    <>
      <h3>{copy.inspectorDetail}</h3>
      <dl className="detail-list compact">
        <dt>Material ID</dt>
        <dd>{material.id}</dd>
        <dt>Job ID</dt>
        <dd>{material.jobId}</dd>
        <dt>{copy.tenant}</dt>
        <dd>{tenantName ?? material.tenantId}</dd>
        <dt>{copy.parentChild}</dt>
        <dd>
          {material.parentName} / {material.childName}
        </dd>
        <dt>{copy.pages}</dt>
        <dd>
          {material.pageCount} / {material.sourcePages.map((page) => `#${page.pageIndex} ${page.sourceType}`).join(", ")}
        </dd>
        <dt>OCR</dt>
        <dd>
          {Math.round(material.ocrConfidence * 100)}% · {material.confidenceSummary}
        </dd>
        <dt>{copy.warnings}</dt>
        <dd>{material.warnings.length > 0 ? material.warnings.join("; ") : copy.noWarnings}</dd>
      </dl>

      <div className="timeline" aria-label={copy.timelineAria}>
        <h4>{copy.timeline}</h4>
        {timelineItems.map((item) => (
          <div className="timeline-row" key={item}>
            <span aria-hidden="true" />
            <p>{item}</p>
          </div>
        ))}
      </div>

      <div className="audit-reason">
        <label>
          <span>{copy.auditReason}</span>
          <textarea maxLength={240} placeholder={copy.auditPlaceholder} />
        </label>
        <div className="audit-actions">
          <button type="button" className="primary-button">
            {copy.retryMock}
          </button>
          <button type="button" className="ghost-button">
            {copy.archiveMock}
          </button>
        </div>
      </div>
    </>
  );
}

function isStatusFilter(value: string): value is StatusFilter {
  return statusFilterOptions.includes(value as StatusFilter);
}

function toneForMaterialStatus(status: MaterialStatus): "success" | "warning" | "danger" | "neutral" {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "processing" || status === "needs_review") {
    return "warning";
  }
  return "neutral";
}

function toneForJobStatus(status: JobStatus): "success" | "warning" | "danger" | "neutral" {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "processing" || status === "queued" || status === "needs_review") {
    return "warning";
  }
  return "neutral";
}

function toneForMediaStatus(status: MediaStatus): "success" | "warning" | "danger" {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  return "warning";
}

const zhCopy = {
  title: "内容流水线",
  subtitle: "按租户追踪讲义、解析任务、学习资产和媒体生成的生命周期；Phase 1 仅使用 mock data。",
  filters: "内容流水线筛选",
  status: "状态",
  statusFilter: "状态筛选",
  all: "全部",
  bulkRetryMock: "批量重试 mock/no-op",
  exportFailures: "导出失败清单",
  queue: "生产队列",
  materialsInScope: "条材料",
  tenant: "租户",
  child: "孩子",
  material: "材料",
  materialStatus: "Material status",
  jobStatus: "Job status",
  inspect: "查看",
  inspector: "当前选中",
  inspectorDetail: "材料详情",
  inspectorAria: "选中材料详情",
  selectedHint: "查看下方 material/job detail",
  noSelection: "未选择材料",
  parentChild: "家长 / 孩子",
  pages: "页数 / Source pages",
  warnings: "Warnings",
  noWarnings: "None",
  uploaded: "上传",
  sourcePages: "source pages",
  parseJob: "解析任务",
  media: "媒体",
  updated: "更新时间",
  timeline: "生命周期时间线",
  timelineAria: "生命周期时间线",
  auditReason: "审计原因",
  auditPlaceholder: "填写重试或归档原因。Phase 1 不会提交真实 API 或 mutation。",
  retryMock: "Mock retry only (no-op)",
  archiveMock: "Mock archive only (no-op)",
  emptyFiltered: "没有符合当前筛选的材料。",
  emptyFilteredDetail: "切换状态或租户范围查看其他 mock materials。",
  emptyInspector: "当前筛选没有可检查材料。",
  emptyInspectorDetail: "Inspector 会在有结果时显示 material/job detail、warnings 和 timeline。"
};

const enCopy = {
  title: "Content Pipeline",
  subtitle: "Track tenant-scoped worksheet, parse job, learning asset, and media lifecycle states with mock data only.",
  filters: "Content pipeline filters",
  status: "Status",
  statusFilter: "Status filter",
  all: "All",
  bulkRetryMock: "Bulk retry mock/no-op",
  exportFailures: "Export failures",
  queue: "Production queue",
  materialsInScope: "materials in scope",
  tenant: "Tenant",
  child: "Child",
  material: "Material",
  materialStatus: "Material status",
  jobStatus: "Job status",
  inspect: "Inspect",
  inspector: "Selected material",
  inspectorDetail: "Material detail",
  inspectorAria: "Selected material inspector",
  selectedHint: "See material/job detail below",
  noSelection: "No material selected",
  parentChild: "Parent / child",
  pages: "Pages / source pages",
  warnings: "Warnings",
  noWarnings: "None",
  uploaded: "Uploaded",
  sourcePages: "source pages",
  parseJob: "Parse job",
  media: "Media",
  updated: "Updated",
  timeline: "Lifecycle timeline",
  timelineAria: "Lifecycle timeline",
  auditReason: "Audit reason",
  auditPlaceholder: "Enter retry or archive reason. Phase 1 will not call a real API or mutation.",
  retryMock: "Mock retry only (no-op)",
  archiveMock: "Mock archive only (no-op)",
  emptyFiltered: "No materials match this filter.",
  emptyFilteredDetail: "Change status or tenant scope to inspect other mock materials.",
  emptyInspector: "No material is available for inspection.",
  emptyInspectorDetail: "The inspector shows material/job detail, warnings, and timeline when the filter has results."
};
