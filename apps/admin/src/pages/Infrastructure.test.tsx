import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockOperationsData } from "../domain/mockData";
import { Infrastructure } from "./Infrastructure";

describe("Infrastructure", () => {
  it("renders the operations snapshot summary and severity", () => {
    render(<Infrastructure language="zh" tenantScope="all" operationsData={mockOperationsData} />);

    expect(screen.getByText("基础设施")).toBeInTheDocument();
    expect(screen.getByText(/严重度: critical/)).toBeInTheDocument();
    expect(screen.getByText("概览")).toBeInTheDocument();
  });

  it("renders the provider readiness matrix", () => {
    render(<Infrastructure language="en" tenantScope="all" operationsData={mockOperationsData} />);

    const providers = screen.getByRole("complementary", { name: "Provider readiness" });
    expect(within(providers).getByText("AI recognition")).toBeInTheDocument();
    // mock has all readiness true -> "Ready" chips present
    expect(within(providers).getAllByText("Ready").length).toBeGreaterThan(0);
  });

  it("lists open issues from the snapshot", () => {
    render(<Infrastructure language="en" tenantScope="all" operationsData={mockOperationsData} />);

    const issuesPanel = screen.getByRole("region", { name: "Issues" });
    expect(within(issuesPanel).getByText("Parse failed")).toBeInTheDocument();
    expect(within(issuesPanel).getByText("Parse processing stale")).toBeInTheDocument();
  });

  it("shows an empty state when no operations data is available", () => {
    render(<Infrastructure language="en" tenantScope="all" operationsData={null} />);

    expect(screen.getByText("No operations snapshot data.")).toBeInTheDocument();
  });
});
