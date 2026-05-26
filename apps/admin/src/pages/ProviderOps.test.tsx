import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { mockMaterials, mockProviderPolicies, mockTenants } from "../domain/mockData";
import { ProviderOps } from "./ProviderOps";

describe("ProviderOps", () => {
  it("shows provider policy density and tenant risk context", () => {
    render(
      <ProviderOps
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        dataMode="mock"
      />
    );

    expect(screen.getByText("Provider Ops")).toBeInTheDocument();
    expect(screen.getAllByText("Bright Future School").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tenant").length).toBeGreaterThan(0);
    expect(screen.getByText("Provider-warning materials")).toBeInTheDocument();
    expect(screen.getByText("Secrets are masked")).toBeInTheDocument();
  });

  it("submits a live tenant provider override with an audit reason", async () => {
    const onOverrideProviderPolicy = vi.fn().mockResolvedValue(undefined);
    render(
      <ProviderOps
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        dataMode="live"
        onOverrideProviderPolicy={onOverrideProviderPolicy}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText("Tenant"), "tenant_sunny_kids");
    await userEvent.selectOptions(screen.getByLabelText("AI provider"), "doubao");
    await userEvent.selectOptions(screen.getByLabelText("Media provider"), "real");
    await userEvent.selectOptions(screen.getByLabelText("Fallback mode"), "per_tenant");
    await userEvent.clear(screen.getByLabelText("Monthly guardrail"));
    await userEvent.type(screen.getByLabelText("Monthly guardrail"), "750");
    await userEvent.type(screen.getByLabelText("Audit reason"), "Pilot tenant approved for real media provider.");
    await userEvent.click(screen.getByRole("button", { name: "Override policy" }));

    expect(onOverrideProviderPolicy).toHaveBeenCalledWith({
      tenantId: "tenant_sunny_kids",
      aiProvider: "doubao",
      mediaProvider: "real",
      fallbackMode: "per_tenant",
      monthlyGuardrail: 750,
      reason: "Pilot tenant approved for real media provider."
    });
    expect(await screen.findByText("Provider policy override recorded.")).toBeInTheDocument();
  });

  it("resets the override form to the scoped tenant policy when tenant scope changes", async () => {
    const { rerender } = render(
      <ProviderOps
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        dataMode="live"
        onOverrideProviderPolicy={vi.fn()}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText("Tenant"), "tenant_bright_future");
    expect(screen.getByLabelText("AI provider")).toHaveValue("doubao");
    expect(screen.getByLabelText("Media provider")).toHaveValue("real");
    expect(screen.getByLabelText("Fallback mode")).toHaveValue("per_tenant");
    expect(screen.getByLabelText("Monthly guardrail")).toHaveValue(1000);

    await userEvent.selectOptions(screen.getByLabelText("AI provider"), "stub");
    await userEvent.selectOptions(screen.getByLabelText("Media provider"), "real");
    await userEvent.selectOptions(screen.getByLabelText("Fallback mode"), "per_tenant");
    await userEvent.clear(screen.getByLabelText("Monthly guardrail"));
    await userEvent.type(screen.getByLabelText("Monthly guardrail"), "750");
    await userEvent.type(screen.getByLabelText("Audit reason"), "Draft change that should not leak.");

    rerender(
      <ProviderOps
        language="en"
        tenantScope="tenant_maple_pilot"
        tenants={mockTenants}
        materials={mockMaterials}
        policies={mockProviderPolicies}
        dataMode="live"
        onOverrideProviderPolicy={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Tenant")).toHaveValue("tenant_maple_pilot");
    expect(screen.getByLabelText("AI provider")).toHaveValue("doubao");
    expect(screen.getByLabelText("Media provider")).toHaveValue("mock");
    expect(screen.getByLabelText("Fallback mode")).toHaveValue("auto_to_mock");
    expect(screen.getByLabelText("Monthly guardrail")).toHaveValue(500);
    expect(screen.getByLabelText("Audit reason")).toHaveValue("");
  });
});
