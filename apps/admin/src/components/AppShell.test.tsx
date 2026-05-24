import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { mockTenants } from "../domain/mockData";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("shows tenant scope and switches language", async () => {
    render(<App />);
    expect(screen.getByRole("combobox", { name: "租户范围" })).toHaveValue("all");
    expect(screen.getByText("指挥台")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "中文" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByRole("combobox", { name: "Tenant scope" })).toHaveValue("all");
    expect(screen.getByText("Command Center")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "中文" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  });

  it("moves semantic current state when navigation changes", async () => {
    render(<App />);

    const command = screen.getByRole("button", { name: "指挥台" });
    const tenants = screen.getByRole("button", { name: "租户管理" });
    expect(command).toHaveAttribute("aria-current", "page");
    expect(tenants).not.toHaveAttribute("aria-current");

    await userEvent.click(tenants);

    expect(command).not.toHaveAttribute("aria-current");
    expect(tenants).toHaveAttribute("aria-current", "page");
  });

  it("switches tenant scope through the named combobox", async () => {
    render(<App />);

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "租户范围" }), "tenant_sunny_kids");

    expect(screen.getByRole("combobox", { name: "租户范围" })).toHaveValue("tenant_sunny_kids");
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("ignores unknown tenant scope values", async () => {
    const onTenantScopeChange = vi.fn();
    render(
      <AppShell
        activePage="command"
        language="en"
        tenantScope="all"
        tenants={mockTenants}
        onLanguageChange={vi.fn()}
        onTenantScopeChange={onTenantScopeChange}
        onPageChange={vi.fn()}
      >
        <div>content</div>
      </AppShell>
    );

    const select = screen.getByRole("combobox", { name: "Tenant scope" });
    select.append(new Option("Unknown tenant", "tenant_unknown"));

    await userEvent.selectOptions(select, "tenant_unknown");

    expect(onTenantScopeChange).not.toHaveBeenCalled();
  });
});
