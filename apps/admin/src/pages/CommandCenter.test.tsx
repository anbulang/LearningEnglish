import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { mockMaterials, mockOperationsData, mockTenants } from "../domain/mockData";
import { CommandCenter } from "./CommandCenter";

describe("CommandCenter", () => {
  it("shows risk inbox and lifecycle funnel", () => {
    render(<CommandCenter language="zh" tenantScope="all" tenants={mockTenants} materials={mockMaterials} />);

    expect(screen.getByText("平台指挥台")).toBeInTheDocument();
    expect(screen.getByText("今日待处理")).toBeInTheDocument();
    expect(screen.getByText("内容生产生命周期")).toBeInTheDocument();
    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
  });

  it("filters risk inbox by selected tenant", () => {
    render(<CommandCenter language="en" tenantScope="tenant_sunny_kids" tenants={mockTenants} materials={mockMaterials} />);

    expect(screen.getByText("Platform Command Center")).toBeInTheDocument();
    expect(screen.getByText("Animal Sounds Practice")).toBeInTheDocument();
    expect(screen.queryByText("Queen / Quilt Review Pack")).not.toBeInTheDocument();

    const activeTenantsCard = screen.getByText("Active tenants").closest(".metric-card");
    expect(activeTenantsCard).not.toBeNull();
    expect(within(activeTenantsCard as HTMLElement).getByText("1")).toBeInTheDocument();

    const blockedJobsCard = screen.getByText("Blocked jobs").closest(".metric-card");
    expect(blockedJobsCard).not.toBeNull();
    expect(within(blockedJobsCard as HTMLElement).getByText("1")).toBeInTheDocument();

    const mediaFailuresCard = screen.getByText("Media failures").closest(".metric-card");
    expect(mediaFailuresCard).not.toBeNull();
    expect(within(mediaFailuresCard as HTMLElement).getByText("1")).toBeInTheDocument();

    const providerIncidentsCard = screen.getByText("Provider incidents").closest(".metric-card");
    expect(providerIncidentsCard).not.toBeNull();
    expect(within(providerIncidentsCard as HTMLElement).getByText("1")).toBeInTheDocument();

    expect(screen.getAllByText("Sunny Kids English")).toHaveLength(2);
    expect(screen.queryByText("Bright Future School")).not.toBeInTheDocument();
    expect(screen.queryByText("Maple Pilot Group")).not.toBeInTheDocument();
  });

  it("uses the shared blocked SLA boundary for risk inbox rows", () => {
    const boundaryMaterials = [
      {
        ...mockMaterials[0],
        id: "mat_boundary_180",
        tenantId: "tenant_sunny_kids",
        title: "SLA Boundary 180",
        materialStatus: "processing" as const,
        jobStatus: "ready" as const,
        mediaStatus: "pending" as const,
        warnings: [],
        slaMinutes: 180
      },
      {
        ...mockMaterials[0],
        id: "mat_boundary_181",
        tenantId: "tenant_sunny_kids",
        title: "SLA Boundary 181",
        materialStatus: "processing" as const,
        jobStatus: "ready" as const,
        mediaStatus: "pending" as const,
        warnings: [],
        slaMinutes: 181
      }
    ];

    render(<CommandCenter language="en" tenantScope="tenant_sunny_kids" tenants={mockTenants} materials={boundaryMaterials} />);

    expect(screen.queryByText("SLA Boundary 180")).not.toBeInTheDocument();
    expect(screen.getByText("SLA Boundary 181")).toBeInTheDocument();
  });

  it("renders backend operations issues and opens the action drawer", async () => {
    render(
      <CommandCenter
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        operationsData={mockOperationsData}
        adminPermissions={["admin.material.retry"]}
        onSubmitIssueAction={vi.fn().mockResolvedValue(undefined)}
      />
    );

    expect(screen.getByText("Parse failed")).toBeInTheDocument();
    expect(screen.getByText("OCR request failed before draft assets were generated.")).toBeInTheDocument();
    expect(screen.getByText("retry_material_job")).toBeInTheDocument();

    const issueRow = screen.getByText("Parse failed").closest("tr");
    expect(issueRow).not.toBeNull();
    expect(within(issueRow as HTMLElement).getByText("critical")).toHaveClass("danger");

    await userEvent.click(screen.getByRole("button", { name: "Open action for Parse failed" }));

    const dialog = screen.getByRole("dialog", { name: "Action review" });
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText("material_parse_job")).toBeInTheDocument();
  });

  it("submits a backend operations issue action with the audit reason", async () => {
    const onSubmitIssueAction = vi.fn().mockResolvedValue(undefined);
    render(
      <CommandCenter
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        operationsData={mockOperationsData}
        adminPermissions={["admin.material.retry"]}
        onSubmitIssueAction={onSubmitIssueAction}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Open action for Parse failed" }));
    await userEvent.type(screen.getByLabelText("Audit reason"), "OCR provider recovered.");
    await userEvent.click(screen.getByRole("button", { name: "Submit action" }));

    expect(onSubmitIssueAction).toHaveBeenCalledWith(mockOperationsData.issues[0], "OCR provider recovered.");
  });

  it("keeps the action drawer open and surfaces failed backend action results", async () => {
    const onSubmitIssueAction = vi.fn().mockRejectedValue(new Error("Material retry enqueue failed."));
    render(
      <CommandCenter
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        operationsData={mockOperationsData}
        adminPermissions={["admin.material.retry"]}
        onSubmitIssueAction={onSubmitIssueAction}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Open action for Parse failed" }));
    await userEvent.type(screen.getByLabelText("Audit reason"), "Queue broker is recovering.");
    await userEvent.click(screen.getByRole("button", { name: "Submit action" }));

    expect(await screen.findByText("Material retry enqueue failed.")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Action review" })).toBeInTheDocument();
  });

  it("does not open unsupported backend operations issue actions", () => {
    const onSubmitIssueAction = vi.fn().mockResolvedValue(undefined);
    render(
      <CommandCenter
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        operationsData={mockOperationsData}
        adminPermissions={["admin.operations.read", "admin.material.retry"]}
        onSubmitIssueAction={onSubmitIssueAction}
      />
    );

    expect(screen.getByLabelText("Unavailable action for Parse processing stale")).toHaveTextContent(
      "inspect_material_job"
    );
    expect(screen.queryByRole("button", { name: "Open action for Parse processing stale" })).not.toBeInTheDocument();
  });

  it("does not open backend operations issue actions without the required permission", () => {
    const onSubmitIssueAction = vi.fn().mockResolvedValue(undefined);
    render(
      <CommandCenter
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        materials={mockMaterials}
        operationsData={mockOperationsData}
        adminPermissions={["admin.operations.read"]}
        onSubmitIssueAction={onSubmitIssueAction}
      />
    );

    expect(screen.getByLabelText("Unavailable action for Parse failed")).toHaveTextContent("retry_material_job");
    expect(screen.queryByRole("button", { name: "Open action for Parse failed" })).not.toBeInTheDocument();
  });
});
