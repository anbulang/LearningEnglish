import { describe, expect, it } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./mockData";
import {
  BLOCKED_SLA_MINUTES,
  getEffectiveProviderPolicy,
  getLifecycleCounts,
  getMaterialsForScope,
  getTenantHealthRows,
  isBlockedMaterial
} from "./selectors";
import type { ProviderPolicy } from "./types";

describe("admin domain selectors", () => {
  it("filters materials by all tenants or a selected tenant", () => {
    expect(getMaterialsForScope(mockMaterials, "all")).toHaveLength(mockMaterials.length);
    expect(
      getMaterialsForScope(mockMaterials, "tenant_bright_future").every((item) => item.tenantId === "tenant_bright_future")
    ).toBe(true);
  });

  it("counts lifecycle stages from material, job, and media status", () => {
    const counts = getLifecycleCounts(mockMaterials);
    expect(counts).toEqual({
      upload: 5,
      parse: 1,
      parentReview: 1,
      knowledgePack: 1,
      media: 1,
      ready: 0,
      failed: 1
    });
  });

  it("applies provider policy precedence with tenant override above global default", () => {
    const effective = getEffectiveProviderPolicy(mockProviderPolicies, "tenant_bright_future");
    expect(effective.aiProvider).toBe("doubao");
    expect(effective.mediaProvider).toBe("real");
    expect(effective.source).toBe("tenant_override");

    const fallback = getEffectiveProviderPolicy(mockProviderPolicies, "tenant_unknown");
    expect(fallback.source).toBe("global_default");
    expect(fallback.aiProvider).toBe("stub");
  });

  it("applies emergency provider policy above tenant overrides", () => {
    const policies: ProviderPolicy[] = [
      ...mockProviderPolicies,
      {
        tenantId: "global",
        aiProvider: "stub",
        mediaProvider: "mock",
        fallbackMode: "global_stub",
        monthlyGuardrail: 0,
        source: "emergency_global"
      }
    ];

    const effective = getEffectiveProviderPolicy(policies, "tenant_bright_future", "Pilot Plus");

    expect(effective.source).toBe("emergency_global");
    expect(effective.aiProvider).toBe("stub");
    expect(effective.mediaProvider).toBe("mock");
  });

  it("applies tier defaults between tenant overrides and global defaults", () => {
    const policies: ProviderPolicy[] = [
      {
        tenantId: "global",
        aiProvider: "stub",
        mediaProvider: "mock",
        fallbackMode: "global_stub",
        monthlyGuardrail: 100,
        source: "global_default"
      },
      {
        tenantId: "tier_standard",
        tier: "Standard",
        aiProvider: "doubao",
        mediaProvider: "mock",
        fallbackMode: "auto_to_mock",
        monthlyGuardrail: 300,
        source: "tier_default"
      }
    ];

    const tierDefault = getEffectiveProviderPolicy(policies, "tenant_sunny_kids", "Standard");
    const globalDefault = getEffectiveProviderPolicy(policies, "tenant_little_star", "Family Pilot");

    expect(tierDefault.source).toBe("tier_default");
    expect(tierDefault.aiProvider).toBe("doubao");
    expect(globalDefault.source).toBe("global_default");
    expect(globalDefault.aiProvider).toBe("stub");
  });

  it("sorts tenant health rows by risk before healthy tenants", () => {
    const rows = getTenantHealthRows(mockTenants, mockMaterials);
    expect(rows[0].tenant.id).toBe("tenant_sunny_kids");
    expect(rows[rows.length - 1].blockedJobs).toBe(0);
    expect(rows[rows.length - 1].healthScore).toBeGreaterThanOrEqual(rows[0].healthScore);
  });

  it("uses one blocked SLA boundary across inbox and tenant health", () => {
    const atBoundary = {
      ...mockMaterials[0],
      id: "mat_at_boundary",
      materialStatus: "processing" as const,
      jobStatus: "ready" as const,
      mediaStatus: "pending" as const,
      slaMinutes: BLOCKED_SLA_MINUTES
    };
    const overBoundary = { ...atBoundary, id: "mat_over_boundary", slaMinutes: BLOCKED_SLA_MINUTES + 1 };

    expect(isBlockedMaterial(atBoundary)).toBe(false);
    expect(isBlockedMaterial(overBoundary)).toBe(true);

    const rows = getTenantHealthRows(mockTenants, [atBoundary, overBoundary]);
    expect(rows.find((row) => row.tenant.id === atBoundary.tenantId)?.blockedJobs).toBe(1);
  });
});
