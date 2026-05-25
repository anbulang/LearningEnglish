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
});
