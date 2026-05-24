import { describe, expect, it } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "./mockData";
import {
  getEffectiveProviderPolicy,
  getLifecycleCounts,
  getMaterialsForScope,
  getTenantHealthRows
} from "./selectors";

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
      media: 3,
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

  it("sorts tenant health rows by risk before healthy tenants", () => {
    const rows = getTenantHealthRows(mockTenants, mockMaterials);
    expect(rows[0].tenant.id).toBe("tenant_sunny_kids");
    expect(rows[rows.length - 1].blockedJobs).toBe(0);
    expect(rows[rows.length - 1].healthScore).toBeGreaterThanOrEqual(rows[0].healthScore);
  });
});
