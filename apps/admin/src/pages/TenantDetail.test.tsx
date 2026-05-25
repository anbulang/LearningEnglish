import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { mockMaterials, mockModuleSettings, mockProviderPolicies, mockTenants } from "../domain/mockData";
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
        moduleSettings={mockModuleSettings}
      />
    );

    expect(screen.getByText("Bright Future School")).toBeInTheDocument();
    expect(screen.getAllByText("tenant_override").length).toBeGreaterThan(0);
    expect(screen.getByText("Worksheet import")).toBeInTheDocument();
    expect(screen.getByText("Tenant materials")).toBeInTheDocument();
  });

  it("shows a clear not-found state for an unknown tenant id", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_missing"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        moduleSettings={mockModuleSettings}
      />
    );

    expect(screen.getByText("Tenant not found")).toBeInTheDocument();
    expect(screen.getByText("tenant_missing")).toBeInTheDocument();
    expect(screen.queryByText("Bright Future School")).not.toBeInTheDocument();
    expect(screen.queryByText("HN-014 Phonics Worksheet")).not.toBeInTheDocument();
  });

  it("shows global provider defaults for a tenant without override", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_little_star"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        moduleSettings={mockModuleSettings}
      />
    );

    expect(screen.getAllByText("global_default").length).toBeGreaterThan(0);
    expect(screen.getByText("stub")).toBeInTheDocument();
    expect(screen.getByText("mock")).toBeInTheDocument();
  });

  it("makes the all-tenant preview context visible from App routing", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "租户管理" }));

    expect(screen.getByText(/All tenants selected; showing first tenant preview/)).toBeInTheDocument();
    expect(screen.getAllByText("Bright Future School").length).toBeGreaterThan(0);
  });

  it("labels module states as prototype readiness instead of authoritative access", () => {
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_bright_future"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        moduleSettings={mockModuleSettings}
      />
    );

    expect(screen.getByText("Tenant module access")).toBeInTheDocument();
    expect(screen.getByText("Audited module switches control tenant-level feature access.")).toBeInTheDocument();
    expect(screen.getAllByText("enabled").length).toBeGreaterThan(0);
  });

  it("submits a live audited tenant module toggle", async () => {
    const onToggleTenantModule = vi.fn().mockResolvedValue(undefined);
    render(
      <TenantDetail
        language="en"
        tenantId="tenant_bright_future"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        moduleSettings={mockModuleSettings}
        dataMode="live"
        onToggleTenantModule={onToggleTenantModule}
      />
    );

    await userEvent.type(screen.getByLabelText("Module change reason"), "Pilot asked to pause speaking score.");
    await userEvent.click(screen.getByRole("button", { name: "Disable Speaking score" }));

    expect(onToggleTenantModule).toHaveBeenCalledWith({
      tenantId: "tenant_bright_future",
      moduleKey: "speaking_score",
      enabled: false,
      reason: "Pilot asked to pause speaking score."
    });
    expect(await screen.findByText("Module setting updated.")).toBeInTheDocument();
  });
});
