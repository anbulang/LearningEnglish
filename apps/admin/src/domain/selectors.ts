import type { AdminMaterial, LifecycleCounts, ProviderPolicy, Tenant, TenantHealthRow, TenantScope } from "./types";

export function getMaterialsForScope(materials: AdminMaterial[], scope: TenantScope): AdminMaterial[] {
  if (scope === "all") {
    return materials;
  }
  return materials.filter((material) => material.tenantId === scope);
}

export function getLifecycleCounts(materials: AdminMaterial[]): LifecycleCounts {
  return materials.reduce<LifecycleCounts>(
    (counts, material) => {
      counts.upload += 1;
      if (material.jobStatus === "queued" || material.jobStatus === "processing") {
        counts.parse += 1;
      }
      if (material.jobStatus === "needs_review" || material.materialStatus === "needs_review") {
        counts.parentReview += 1;
      }
      if (material.jobStatus === "ready" || material.materialStatus === "ready") {
        counts.knowledgePack += 1;
      }
      if (material.mediaStatus === "pending" || material.mediaStatus === "processing") {
        counts.media += 1;
      }
      if (material.materialStatus === "ready" && material.mediaStatus === "ready") {
        counts.ready += 1;
      }
      if (material.materialStatus === "failed" || material.jobStatus === "failed" || material.mediaStatus === "failed") {
        counts.failed += 1;
      }
      return counts;
    },
    { upload: 0, parse: 0, parentReview: 0, knowledgePack: 0, media: 0, ready: 0, failed: 0 }
  );
}

export function getEffectiveProviderPolicy(policies: ProviderPolicy[], tenantId: string): ProviderPolicy {
  const globalPolicy = policies.find((policy) => policy.tenantId === "global");
  const tenantPolicy = policies.find((policy) => policy.tenantId === tenantId);
  if (tenantPolicy) {
    return tenantPolicy;
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

export function getTenantHealthRows(tenants: Tenant[], materials: AdminMaterial[]): TenantHealthRow[] {
  return tenants
    .map((tenant) => {
      const tenantMaterials = materials.filter((material) => material.tenantId === tenant.id);
      const blockedJobs = tenantMaterials.filter(
        (material) => material.materialStatus === "failed" || material.jobStatus === "failed" || material.slaMinutes > 180
      ).length;
      const mediaFailures = tenantMaterials.filter((material) => material.mediaStatus === "failed").length;
      const healthScore = Math.max(0, 100 - blockedJobs * 12 - mediaFailures * 8);
      return { tenant, blockedJobs, mediaFailures, healthScore };
    })
    .sort((a, b) => b.blockedJobs - a.blockedJobs || a.healthScore - b.healthScore);
}
