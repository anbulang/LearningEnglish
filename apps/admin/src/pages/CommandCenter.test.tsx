import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
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
  });
});
