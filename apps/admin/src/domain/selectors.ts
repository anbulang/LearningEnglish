import type { AdminMaterial, LifecycleCounts, ProviderPolicy, Tenant, TenantHealthRow, TenantScope } from "./types";

export const BLOCKED_SLA_MINUTES = 180;

export function isBlockedMaterial(material: AdminMaterial): boolean {
  return material.materialStatus === "failed" || material.jobStatus === "failed" || material.slaMinutes > BLOCKED_SLA_MINUTES;
}

export function getMaterialsForScope(materials: AdminMaterial[], scope: TenantScope): AdminMaterial[] {
  if (scope === "all") {
    return materials;
  }
  return materials.filter((material) => material.tenantId === scope);
}

export function getLifecycleCounts(materials: AdminMaterial[]): LifecycleCounts {
  return materials.reduce<LifecycleCounts>(
    (counts, material) => {
      const isArchived = material.materialStatus === "archived";
      const isFailed = material.materialStatus === "failed" || material.jobStatus === "failed" || material.mediaStatus === "failed";
      const isFullyReady = material.materialStatus === "ready" && material.mediaStatus === "ready";
      const hasKnowledgePack = material.jobStatus === "ready" || material.materialStatus === "ready";

      counts.upload += 1;
      if (!isArchived && (material.jobStatus === "queued" || material.jobStatus === "processing")) {
        counts.parse += 1;
      }
      if (!isArchived && (material.jobStatus === "needs_review" || material.materialStatus === "needs_review")) {
        counts.parentReview += 1;
      }
      if (!isArchived && !isFailed && hasKnowledgePack && !isFullyReady) {
        counts.knowledgePack += 1;
      }
      if (!isArchived && !isFailed && hasKnowledgePack && (material.mediaStatus === "pending" || material.mediaStatus === "processing")) {
        counts.media += 1;
      }
      if (!isArchived && !isFailed && isFullyReady) {
        counts.ready += 1;
      }
      if (isFailed) {
        counts.failed += 1;
      }
      return counts;
    },
    { upload: 0, parse: 0, parentReview: 0, knowledgePack: 0, media: 0, ready: 0, failed: 0 }
  );
}

export function getEffectiveProviderPolicy(policies: ProviderPolicy[], tenantId: string, tenantTier?: string): ProviderPolicy {
  const emergencyPolicy = policies.find((policy) => policy.source === "emergency_global");
  const globalPolicy = policies.find((policy) => policy.tenantId === "global" && policy.source === "global_default");
  const tenantPolicy = policies.find((policy) => policy.tenantId === tenantId && policy.source === "tenant_override");
  const tierPolicy = policies.find(
    (policy) => policy.source === "tier_default" && policy.tier !== undefined && normalizeTier(policy.tier) === normalizeTier(tenantTier)
  );
  if (emergencyPolicy) {
    return emergencyPolicy;
  }
  if (tenantPolicy) {
    return tenantPolicy;
  }
  if (tierPolicy) {
    return tierPolicy;
  }
  if (globalPolicy) {
    return globalPolicy;
  }
  return {
    tenantId: "global",
    aiProvider: "stub",
    mediaProvider: "mock",
    fallbackMode: "global_stub",
    monthlyGuardrail: 0,
    source: "global_default"
  };
}

function normalizeTier(tier: string | undefined): string {
  return tier?.trim().toLowerCase() ?? "";
}

export function getTenantHealthRows(tenants: Tenant[], materials: AdminMaterial[]): TenantHealthRow[] {
  return tenants
    .map((tenant) => {
      const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
      const blockedJobs = tenantMaterials.filter(isBlockedMaterial).length;
      const mediaFailures = tenantMaterials.filter((material) => material.mediaStatus === "failed").length;
      const healthScore = Math.max(0, 100 - blockedJobs * 12 - mediaFailures * 8);
      return { tenant, blockedJobs, mediaFailures, healthScore };
    })
    .sort((a, b) => b.blockedJobs - a.blockedJobs || a.healthScore - b.healthScore);
}
