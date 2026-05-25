import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockTenants } from "../domain/mockData";
import { ContentPipeline } from "./ContentPipeline";

describe("ContentPipeline", () => {
  it("shows lifecycle table and selected material inspector", () => {
    render(<ContentPipeline language="zh" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);

    expect(screen.getByText("内容流水线")).toBeInTheDocument();
    expect(screen.getByText("生产队列")).toBeInTheDocument();
    expect(screen.getByText("HN-014 Phonics Worksheet")).toBeInTheDocument();
    expect(screen.getByText("生命周期时间线")).toBeInTheDocument();
    expect(screen.getByText("job_hn014_parse")).toBeInTheDocument();
    expect(screen.getByText("Media generation still running")).toBeInTheDocument();
  });

  it("filters failed materials", async () => {
    render(<ContentPipeline language="en" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);

    await userEvent.selectOptions(screen.getByLabelText("Status filter"), "failed");

    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
    expect(screen.queryByText("Weekend Reading Worksheet")).not.toBeInTheDocument();
    expect(screen.getByText("job_animals_parse")).toBeInTheDocument();
  });

  it("updates inspector when the material title button is selected", async () => {
    render(<ContentPipeline language="en" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);

    await userEvent.click(screen.getByRole("button", { name: /Inspect Weekend Reading Worksheet/ }));

    const inspector = screen.getByRole("complementary", { name: "Selected material inspector" });
    expect(within(inspector).getByText("mat_weekend")).toBeInTheDocument();
    expect(within(inspector).getByText("job_weekend_parse")).toBeInTheDocument();
    expect(within(inspector).getByText("Grace Li / Leo Li")).toBeInTheDocument();
  });

  it("falls back to in-scope inspector data when tenant scope changes after selection", async () => {
    const { rerender } = render(<ContentPipeline language="en" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);

    await userEvent.click(screen.getByRole("button", { name: /Inspect Animal Sounds Practice/ }));
    expect(screen.getByText("mat_animals")).toBeInTheDocument();

    rerender(<ContentPipeline language="en" tenantScope="tenant_bright_future" tenants={mockTenants} materials={mockMaterials} />);

    const inspector = screen.getByRole("complementary", { name: "Selected material inspector" });
    expect(within(inspector).queryByText("mat_animals")).not.toBeInTheDocument();
    expect(within(inspector).getByText("mat_014")).toBeInTheDocument();
    expect(within(inspector).getByText("job_hn014_parse")).toBeInTheDocument();
  });

  it("shows an empty inspector state when the filtered list has no materials", async () => {
    render(<ContentPipeline language="en" tenantScope="tenant_bright_future" tenants={mockTenants} materials={mockMaterials} />);

    await userEvent.selectOptions(screen.getByLabelText("Status filter"), "failed");

    expect(screen.getByText("No materials match this filter.")).toBeInTheDocument();
    expect(screen.queryByText("HN-014 Phonics Worksheet")).not.toBeInTheDocument();
  });
});
