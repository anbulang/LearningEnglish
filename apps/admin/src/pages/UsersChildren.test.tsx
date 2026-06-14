import "@testing-library/jest-dom/vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockTenants, mockUsers } from "../domain/mockData";
import { UsersChildren } from "./UsersChildren";

describe("UsersChildren", () => {
  it("shows the children roster with seeded users", () => {
    render(<UsersChildren language="zh" tenantScope="all" tenants={mockTenants} users={mockUsers} />);

    expect(screen.getByText("用户与孩子")).toBeInTheDocument();
    expect(screen.getByText("孩子名册")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看 Tom Zhang" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看 Ivy Lin" })).toBeInTheDocument();
  });

  it("filters by level", async () => {
    render(<UsersChildren language="en" tenantScope="all" tenants={mockTenants} users={mockUsers} />);

    await userEvent.selectOptions(screen.getByLabelText("Level filter"), "mover");

    expect(screen.getByRole("button", { name: "Inspect Ivy Lin" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inspect Tom Zhang" })).not.toBeInTheDocument();
  });

  it("updates the inspector when a child is selected", async () => {
    render(<UsersChildren language="en" tenantScope="all" tenants={mockTenants} users={mockUsers} />);

    await userEvent.click(screen.getByRole("button", { name: "Inspect Tom Zhang" }));

    const inspector = screen.getByRole("complementary", { name: "Selected child inspector" });
    expect(within(inspector).getByText("课后稳定复习")).toBeInTheDocument();
    expect(within(inspector).getByText("child_tom_zhang")).toBeInTheDocument();
  });

  it("scopes children to the selected tenant", () => {
    render(<UsersChildren language="en" tenantScope="tenant_maple_pilot" tenants={mockTenants} users={mockUsers} />);

    expect(screen.getByRole("button", { name: "Inspect Ivy Lin" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inspect Tom Zhang" })).not.toBeInTheDocument();
  });
});
