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
    expect(counts.upload).toBeGreaterThan(0);
    expect(counts.parse).toBeGreaterThan(0);
    expect(counts.parentReview).toBeGreaterThan(0);
    expect(counts.media).toBeGreaterThan(0);
    expect(counts.ready).toBeGreaterThan(0);
    expect(counts.failed).toBeGreaterThan(0);
  });

  it("applies provider policy precedence with tenant override above global default", () => {
    const effective = getEffectiveProviderPolicy(mockProviderPolicies, "tenant_bright_future");
    expect(effective.aiProvider).toBe("doubao");
    expect(effective.mediaProvider).toBe("real");
    expect(effective.source).toBe("tenant_override");
  });

  it("sorts tenant health rows by risk before healthy tenants", () => {
    const rows = getTenantHealthRows(mockTenants, mockMaterials);
    expect(rows[0].blockedJobs).toBeGreaterThanOrEqual(rows[rows.length - 1].blockedJobs);
  });
});
