import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockLearningAssets, mockTenants } from "../domain/mockData";
import { LearningAssets } from "./LearningAssets";

describe("LearningAssets", () => {
  it("shows the asset library table with seeded assets", () => {
    render(<LearningAssets language="zh" tenantScope="all" tenants={mockTenants} assets={mockLearningAssets} />);

    expect(screen.getByText("学习资产")).toBeInTheDocument();
    expect(screen.getByText("资产库")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看 queen" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看 rabbit" })).toBeInTheDocument();
  });

  it("filters by media status", async () => {
    render(<LearningAssets language="en" tenantScope="all" tenants={mockTenants} assets={mockLearningAssets} />);

    await userEvent.selectOptions(screen.getByLabelText("Media status filter"), "failed");

    expect(screen.getByRole("button", { name: "Inspect rabbit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inspect queen" })).not.toBeInTheDocument();
  });

  it("updates the inspector when an asset is selected", async () => {
    render(<LearningAssets language="en" tenantScope="all" tenants={mockTenants} assets={mockLearningAssets} />);

    await userEvent.click(screen.getByRole("button", { name: "Inspect rabbit" }));

    const inspector = screen.getByRole("complementary", { name: "Selected asset inspector" });
    expect(within(inspector).getByText("兔子")).toBeInTheDocument();
    expect(within(inspector).getByText("Maple Pilot Rr Worksheet")).toBeInTheDocument();
    expect(within(inspector).getByText(/UK TTS: ready/)).toBeInTheDocument();
  });

  it("scopes assets to the selected tenant", () => {
    render(
      <LearningAssets language="en" tenantScope="tenant_maple_pilot" tenants={mockTenants} assets={mockLearningAssets} />
    );

    expect(screen.getByRole("button", { name: "Inspect rabbit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inspect queen" })).not.toBeInTheDocument();
  });

  it("shows an empty state when no asset matches the filter", async () => {
    render(
      <LearningAssets language="en" tenantScope="tenant_little_star" tenants={mockTenants} assets={mockLearningAssets} />
    );

    await userEvent.selectOptions(screen.getByLabelText("Media status filter"), "ready");

    expect(screen.getByText("No learning assets match this filter.")).toBeInTheDocument();
  });
});
