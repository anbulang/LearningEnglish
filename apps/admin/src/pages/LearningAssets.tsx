import { useMemo, useState } from "react";
import { StatusChip } from "../components/ui";
import type { AdminLearningAsset, Language, MediaStatus, Tenant, TenantScope } from "../domain/types";

interface LearningAssetsProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  assets: AdminLearningAsset[];
  dataMode?: "mock" | "live";
}

type MediaFilter = "all" | MediaStatus;

const mediaFilterOptions: MediaFilter[] = ["all", "pending", "processing", "ready", "failed"];

export function LearningAssets({ language, tenantScope, tenants, assets, dataMode = "mock" }: LearningAssetsProps) {
  const [mediaFilter, setMediaFilter] = useState<MediaFilter>("all");
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const copy = language === "zh" ? zhCopy : enCopy;
  const tenantNameById = useMemo(() => new Map(tenants.map((tenant) => [tenant.id, tenant.name])), [tenants]);
  const scopedAssets = useMemo(
    () => (tenantScope === "all" ? assets : assets.filter((asset) => asset.tenantId === tenantScope)),
    [assets, tenantScope]
  );
  const filteredAssets = useMemo(
    () => (mediaFilter === "all" ? scopedAssets : scopedAssets.filter((asset) => asset.mediaStatus === mediaFilter)),
    [scopedAssets, mediaFilter]
  );
  const selectedAsset = filteredAssets.find((asset) => asset.id === selectedAssetId) ?? filteredAssets[0] ?? null;

  function handleMediaFilterChange(value: string) {
    if (isMediaFilter(value)) {
      setMediaFilter(value);
      setSelectedAssetId(null);
    }
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">CourseMaterial / LearningAsset</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface wide filter-bar" aria-label={copy.filters}>
        <label>
          <span>{copy.media}</span>
          <select aria-label={copy.mediaFilter} value={mediaFilter} onChange={(event) => handleMediaFilterChange(event.target.value)}>
            {mediaFilterOptions.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? copy.all : option}
              </option>
            ))}
          </select>
        </label>
        <span className="filter-summary">
          {dataMode === "live" ? copy.liveHint : copy.mockHint}
        </span>
      </section>

      <section className="surface table-panel span-8">
        <div className="section-title">
          <div>
            <h2>{copy.library}</h2>
            <p>
              {filteredAssets.length} / {scopedAssets.length} {copy.assetsInScope}
            </p>
          </div>
          <StatusChip tone={filteredAssets.some((asset) => asset.mediaStatus === "failed") ? "danger" : "neutral"}>
            {mediaFilter === "all" ? copy.all : mediaFilter}
          </StatusChip>
        </div>
        {filteredAssets.length > 0 ? (
          <div className="table-scroll">
            <table className="pipeline-table">
              <thead>
                <tr>
                  <th>{copy.tenant}</th>
                  <th>{copy.child}</th>
                  <th>{copy.material}</th>
                  <th>{copy.asset}</th>
                  <th>{copy.kind}</th>
                  <th>{copy.media}</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.map((asset) => (
                  <tr key={`${asset.materialId}:${asset.id}`} className={selectedAsset?.id === asset.id ? "selected-row" : ""}>
                    <td>{tenantNameById.get(asset.tenantId) ?? asset.tenantId}</td>
                    <td>
                      {asset.childName}
                      <small>{asset.parentName}</small>
                    </td>
                    <td>
                      {asset.materialTitle}
                      <small>{asset.materialId}</small>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="table-link-button"
                        aria-label={`${copy.inspect} ${asset.text}`}
                        onClick={() => setSelectedAssetId(asset.id)}
                      >
                        {asset.text}
                      </button>
                      <small>{asset.translation}</small>
                    </td>
                    <td>{asset.kind}</td>
                    <td>
                      <StatusChip tone={toneForMediaStatus(asset.mediaStatus)}>{asset.mediaStatus}</StatusChip>
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
            <p>{selectedAsset ? copy.selectedHint : copy.noSelection}</p>
          </div>
        </div>
        {selectedAsset ? (
          <AssetInspector asset={selectedAsset} tenantName={tenantNameById.get(selectedAsset.tenantId)} copy={copy} />
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

function AssetInspector({
  asset,
  tenantName,
  copy
}: {
  asset: AdminLearningAsset;
  tenantName: string | undefined;
  copy: typeof zhCopy;
}) {
  const mediaRows = [
    `${copy.image}: ${asset.generatedImageStatus}`,
    `${copy.ttsUs}: ${asset.ttsUsStatus}`,
    `${copy.ttsUk}: ${asset.ttsUkStatus}`
  ];

  return (
    <>
      <h3>{copy.inspectorDetail}</h3>
      <dl className="detail-list compact">
        <dt>{copy.asset}</dt>
        <dd>{asset.text}</dd>
        <dt>{copy.translation}</dt>
        <dd>{asset.translation || copy.none}</dd>
        <dt>{copy.kind}</dt>
        <dd>{asset.kind}</dd>
        <dt>{copy.accent}</dt>
        <dd>{asset.primaryAccent || copy.none}</dd>
        <dt>{copy.material}</dt>
        <dd>
          {asset.materialTitle}
          <small>
            {asset.materialId} · {asset.materialStatus}
          </small>
        </dd>
        <dt>{copy.tenant}</dt>
        <dd>{tenantName ?? asset.tenantId}</dd>
        <dt>{copy.parentChild}</dt>
        <dd>
          {asset.parentName} / {asset.childName}
        </dd>
        <dt>{copy.media}</dt>
        <dd>
          <StatusChip tone={toneForMediaStatus(asset.mediaStatus)}>{asset.mediaStatus}</StatusChip>
        </dd>
        <dt>{copy.updated}</dt>
        <dd>{asset.updatedAt}</dd>
      </dl>

      <div className="timeline" aria-label={copy.mediaAria}>
        <h4>{copy.mediaBreakdown}</h4>
        {mediaRows.map((item) => (
          <div className="timeline-row" key={item}>
            <span aria-hidden="true" />
            <p>{item}</p>
          </div>
        ))}
      </div>
    </>
  );
}

function isMediaFilter(value: string): value is MediaFilter {
  return mediaFilterOptions.includes(value as MediaFilter);
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
  title: "学习资产",
  subtitle: "按租户浏览各讲义生成的核心词与句子资产，以及配图、英美音的生成状态。",
  filters: "学习资产筛选",
  media: "媒体状态",
  mediaFilter: "媒体状态筛选",
  all: "全部",
  liveHint: "live 数据：来自 /v1/admin/learning-assets。",
  mockHint: "mock 数据：未连接 live admin API。",
  library: "资产库",
  assetsInScope: "条资产",
  tenant: "租户",
  child: "孩子",
  material: "讲义",
  asset: "资产",
  kind: "类型",
  inspect: "查看",
  inspector: "当前选中",
  inspectorDetail: "资产详情",
  inspectorAria: "选中资产详情",
  selectedHint: "查看下方资产与媒体明细",
  noSelection: "未选择资产",
  parentChild: "家长 / 孩子",
  translation: "释义",
  accent: "主发音",
  none: "无",
  updated: "更新时间",
  image: "配图",
  ttsUs: "美音 TTS",
  ttsUk: "英音 TTS",
  mediaBreakdown: "媒体生成明细",
  mediaAria: "媒体生成明细",
  emptyFiltered: "没有符合当前筛选的学习资产。",
  emptyFilteredDetail: "切换媒体状态或租户范围查看其他资产。",
  emptyInspector: "当前筛选没有可检查资产。",
  emptyInspectorDetail: "Inspector 会在有结果时显示资产文本、释义和媒体状态。"
};

const enCopy: typeof zhCopy = {
  title: "Learning Assets",
  subtitle: "Browse tenant-scoped vocabulary and sentence assets generated from worksheets, with image and US/UK audio status.",
  filters: "Learning asset filters",
  media: "Media status",
  mediaFilter: "Media status filter",
  all: "All",
  liveHint: "Live data from /v1/admin/learning-assets.",
  mockHint: "Mock data: live admin API not connected.",
  library: "Asset library",
  assetsInScope: "assets in scope",
  tenant: "Tenant",
  child: "Child",
  material: "Worksheet",
  asset: "Asset",
  kind: "Kind",
  inspect: "Inspect",
  inspector: "Selected asset",
  inspectorDetail: "Asset detail",
  inspectorAria: "Selected asset inspector",
  selectedHint: "See asset and media detail below",
  noSelection: "No asset selected",
  parentChild: "Parent / child",
  translation: "Translation",
  accent: "Primary accent",
  none: "None",
  updated: "Updated",
  image: "Image",
  ttsUs: "US TTS",
  ttsUk: "UK TTS",
  mediaBreakdown: "Media generation breakdown",
  mediaAria: "Media generation breakdown",
  emptyFiltered: "No learning assets match this filter.",
  emptyFilteredDetail: "Change media status or tenant scope to inspect other assets.",
  emptyInspector: "No asset is available for inspection.",
  emptyInspectorDetail: "The inspector shows asset text, translation, and media status when the filter has results."
};
