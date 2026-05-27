import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockMaterials, mockTenants } from "../domain/mockData";
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
});
