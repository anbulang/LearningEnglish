import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { App } from "./App";

const SCREENS: { nav: string; h1: string }[] = [
  { nav: "指挥中心", h1: "平台指挥中心" },
  { nav: "租户管理", h1: "租户管理" },
  { nav: "内容管道", h1: "内容管道" },
  { nav: "学习资产", h1: "学习资产" },
  { nav: "学习结果", h1: "学习结果" },
  { nav: "用户与家庭", h1: "用户与家庭" },
  { nav: "Provider 运维", h1: "Provider 运维" },
  { nav: "成本与 Token", h1: "成本与 Token 优化" },
  { nav: "基础设施", h1: "基础设施" },
  { nav: "审计与权限", h1: "审计与权限" }
];

beforeEach(() => {
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  cleanup();
});

describe("AppShell + navigation", () => {
  it("renders the command center by default", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "平台指挥中心" })).toBeInTheDocument();
  });

  it("navigates across every console screen", () => {
    render(<App />);
    for (const route of SCREENS) {
      // Some nav items carry a badge ("37", "↓60%") in their accessible name, so match by prefix.
      fireEvent.click(screen.getByRole("button", { name: new RegExp(route.nav) }));
      expect(screen.getByRole("heading", { level: 1, name: route.h1 })).toBeInTheDocument();
    }
  });

  it("marks the active nav item with aria-current", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: "指挥中心" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: "审计与权限" }));
    expect(screen.getByRole("button", { name: "审计与权限" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "指挥中心" })).not.toHaveAttribute("aria-current");
  });

  it("shows the Mock-data env chip by default", () => {
    render(<App />);
    expect(screen.getByText("生产环境")).toBeInTheDocument();
  });
});

describe("theme + language toggles", () => {
  it("toggles light/dark theme on the document root", () => {
    render(<App />);
    const toggle = screen.getByRole("button", { name: "切换深浅色" });
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    fireEvent.click(toggle);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    fireEvent.click(toggle);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("switches the whole UI to English", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.getByRole("heading", { level: 1, name: "Platform Command Center" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Command Center" })).toBeInTheDocument();
  });
});

describe("tenant scope", () => {
  it("exposes the tenant scope selector with the all-tenants option", () => {
    render(<App />);
    const select = screen.getByRole("combobox", { name: "租户范围" });
    expect(within(select).getByRole("option", { name: "所有租户" })).toBeInTheDocument();
  });
});

describe("interactions", () => {
  it("filters the content pipeline and opens the job drawer", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /内容管道/ }));
    // A ready job is visible under the default (all) filter.
    expect(screen.getByText("LE-24817")).toBeInTheDocument();

    // Filtering to 失败 hides the ready job and keeps a failed one.
    fireEvent.click(screen.getByRole("button", { name: /失败/ }));
    expect(screen.queryByText("LE-24817")).not.toBeInTheDocument();
    expect(screen.getByText("LE-24813")).toBeInTheDocument();

    // Clicking a row opens the detail drawer with the timeline.
    fireEvent.click(screen.getByText("LE-24813"));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("处理时间线")).toBeInTheDocument();
  });

  it("opens the tenant add form", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "租户管理" }));
    fireEvent.click(screen.getByRole("button", { name: "+ 新增租户" }));
    expect(screen.getByLabelText("机构名称 *")).toBeInTheDocument();
  });

  it("recomputes projected cost when a lever is toggled off", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /成本与 Token/ }));
    // All five levers on → projected 96,200 − 57,400 = 38,800.
    expect(screen.getAllByText("¥38,800").length).toBeGreaterThan(0);
    // Toggle the first lever (tier, ¥28,400) off → projected 67,200.
    fireEvent.click(screen.getAllByRole("switch")[0]);
    expect(screen.getAllByText("¥67,200").length).toBeGreaterThan(0);
  });

  it("renders mastery rows on the outcomes screen", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "学习结果" }));
    expect(screen.getByText("字母音 Letter Sounds")).toBeInTheDocument();
  });

  it("promotes an idle provider to healthy when enabled (no stale idle badge)", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Provider 运维/ }));
    // The backup Doubao provider seeds disabled.
    expect(screen.getByText("已停用")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "启用" }));
    // After enabling, it promotes to healthy — never stuck on the "idle" label.
    expect(screen.queryByText("未启用")).not.toBeInTheDocument();
    expect(screen.queryByText("已停用")).not.toBeInTheDocument();
  });

  it("filters the family list by search query", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "用户与家庭" }));
    expect(screen.getByText("赵家")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("搜索家庭"), { target: { value: "zzz" } });
    expect(screen.queryByText("赵家")).not.toBeInTheDocument();
  });
});
