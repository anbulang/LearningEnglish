import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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
    expect(screen.getByRole("button", { name: "导出失败清单 mock/no-op" })).toBeDisabled();
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

  it("submits a live archive mutation with the selected material and audit reason", async () => {
    const onArchiveMaterial = vi.fn().mockResolvedValue(undefined);
    render(
      <ContentPipeline
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        dataMode="live"
        onArchiveMaterial={onArchiveMaterial}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /Inspect Weekend Reading Worksheet/ }));
    await userEvent.type(screen.getByLabelText("Audit reason"), "Duplicate worksheet uploaded by parent.");
    await userEvent.click(screen.getByRole("button", { name: "Archive material" }));

    expect(onArchiveMaterial).toHaveBeenCalledWith("mat_weekend", "Duplicate worksheet uploaded by parent.");
    expect(await screen.findByText("Archive request recorded.")).toBeInTheDocument();
  });

  it("submits a live retry mutation with the selected job and audit reason", async () => {
    const onRetryMaterialJob = vi.fn().mockResolvedValue(undefined);
    render(
      <ContentPipeline
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        dataMode="live"
        onRetryMaterialJob={onRetryMaterialJob}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText("Status filter"), "failed");
    await userEvent.click(screen.getByRole("button", { name: /Inspect Animal Sounds Practice/ }));
    await userEvent.type(screen.getByLabelText("Audit reason"), "OCR provider recovered.");
    await userEvent.click(screen.getByRole("button", { name: "Retry job" }));

    expect(onRetryMaterialJob).toHaveBeenCalledWith("job_animals_parse", "OCR provider recovered.");
    expect(await screen.findByText("Retry request recorded.")).toBeInTheDocument();
  });
});
