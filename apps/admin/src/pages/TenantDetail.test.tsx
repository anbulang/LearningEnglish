import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "../domain/mockData";
import { TenantDetail } from "./TenantDetail";

describe("TenantDetail", () => {
  it("shows tenant identity, quota, modules, policy source, and materials", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_bright_future"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
      />
    );

    expect(screen.getByText("Bright Future School")).toBeInTheDocument();
    expect(screen.getAllByText("tenant_override").length).toBeGreaterThan(0);
    expect(screen.getByText("Worksheet import")).toBeInTheDocument();
    expect(screen.getByText("Tenant materials")).toBeInTheDocument();
  });

  it("falls back to the first tenant for an unknown tenant id", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_missing"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
      />
    );

    expect(screen.getByText("Bright Future School")).toBeInTheDocument();
    expect(screen.getByText("HN-014 Phonics Worksheet")).toBeInTheDocument();
  });
});
