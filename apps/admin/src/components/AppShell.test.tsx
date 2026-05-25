import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { mockTenants } from "../domain/mockData";
import { AppShell } from "./AppShell";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("AppShell", () => {
  it("shows tenant scope and switches language", async () => {
    render(<App />);
    expect(screen.getByRole("combobox", { name: "租户范围" })).toHaveValue("all");
    expect(screen.getByText("指挥台")).toBeInTheDocument();
    expect(screen.getByText("Mock 数据")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "中文" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByRole("combobox", { name: "Tenant scope" })).toHaveValue("all");
    expect(screen.getByText("Command Center")).toBeInTheDocument();
    expect(screen.getByText("Mock data")).toBeInTheDocument();
    expect(screen.getByText("Prototype OK")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OpenAPI placeholder" })).toBeDisabled();
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

  it("shows live API mode when the admin dashboard endpoint responds", async () => {
    vi.stubEnv("VITE_ADMIN_API_BASE_URL", "http://127.0.0.1:8000");
    vi.stubEnv("VITE_ADMIN_API_TOKEN", "local-admin-token");
    const dashboardPayload = {
      tenants: [
        {
          id: "parent_live",
          name: "微信家长live",
          tenant_type: "pilot_family",
          status: "active",
          region: "local",
          owner_contact: "13800138110",
          tier: "pilot",
          created_at: "2026-05-25T10:00:00+00:00",
          active_parents: 1,
          children: 1
        }
      ],
      materials: [
        {
          id: "material_live",
          tenant_id: "parent_live",
          parent_name: "微信家长live",
          child_name: "Mia Wang",
          child_age: 6,
          title: "Live API Worksheet",
          page_count: 1,
          job_id: "job_live",
          confidence_summary: "上传完成，等待 OCR 与解析。",
          ocr_confidence: 0.72,
          source_pages: [],
          material_status: "processing",
          job_status: "processing",
          provider: "stub",
          learning_assets: 0,
          media_status: "pending",
          sla_minutes: 12,
          updated_at: "2026-05-25T10:05:00+00:00",
          warnings: []
        }
      ],
      provider_policies: [
        {
          tenant_id: "global",
          ai_provider: "stub",
          media_provider: "mock",
          fallback_mode: "global_stub",
          monthly_guardrail: 0,
          source: "global_default"
        }
      ]
    };
    const accessPayload = {
      current_admin: {
        id: "admin_local",
        display_name: "Local Platform Admin",
        email: "admin@learningenglish.local",
        role: "Platform Owner",
        status: "active"
      },
      permissions: ["admin.dashboard.read", "admin.audit.read"],
      audit_events: [
        {
          id: "audit_1",
          actor_id: "admin_local",
          actor_role: "Platform Owner",
          tenant_scope: "all",
          action: "admin.dashboard.read",
          resource_type: "admin_dashboard",
          resource_id: "dashboard",
          risk_level: "low",
          result: "success",
          reason: "",
          trace_id: "req_12345678",
          created_at: "2026-05-25T10:06:00+00:00"
        }
      ]
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: Parameters<typeof fetch>[0]) => ({
        ok: true,
        json: async () => (String(input).includes("/v1/admin/access") ? accessPayload : dashboardPayload)
      }))
    );

    render(<App />);

    expect(await screen.findByText("真实 API")).toBeInTheDocument();
    expect(screen.getAllByText("微信家长live").length).toBeGreaterThan(0);
    expect(screen.getByRole("combobox", { name: "租户范围" })).toHaveDisplayValue("所有租户");
  });

  it("submits live admin archive mutation from the content pipeline", async () => {
    vi.stubEnv("VITE_ADMIN_API_BASE_URL", "http://127.0.0.1:8000");
    vi.stubEnv("VITE_ADMIN_API_TOKEN", "local-admin-token");
    const dashboardPayload = {
      tenants: [
        {
          id: "parent_live",
          name: "微信家长live",
          tenant_type: "pilot_family",
          status: "active",
          region: "local",
          owner_contact: "13800138110",
          tier: "pilot",
          created_at: "2026-05-25T10:00:00+00:00",
          active_parents: 1,
          children: 1
        }
      ],
      materials: [
        {
          id: "material_live",
          tenant_id: "parent_live",
          parent_name: "微信家长live",
          child_name: "Mia Wang",
          child_age: 6,
          title: "Live API Worksheet",
          page_count: 1,
          job_id: "job_live",
          confidence_summary: "上传完成，等待 OCR 与解析。",
          ocr_confidence: 0.72,
          source_pages: [],
          material_status: "processing",
          job_status: "processing",
          provider: "stub",
          learning_assets: 0,
          media_status: "pending",
          sla_minutes: 12,
          updated_at: "2026-05-25T10:05:00+00:00",
          warnings: []
        }
      ],
      provider_policies: [
        {
          tenant_id: "global",
          ai_provider: "stub",
          media_provider: "mock",
          fallback_mode: "global_stub",
          monthly_guardrail: 0,
          source: "global_default"
        }
      ]
    };
    const archivedMaterial = { ...dashboardPayload.materials[0], material_status: "archived" };
    const accessPayload = {
      current_admin: {
        id: "admin_local",
        display_name: "Local Platform Admin",
        email: "admin@learningenglish.local",
        role: "Platform Owner",
        status: "active"
      },
      permissions: ["admin.dashboard.read", "admin.material.archive", "admin.audit.read"],
      audit_events: []
    };
    const archiveEvent = {
      id: "audit_archive",
      actor_id: "admin_local",
      actor_role: "Platform Owner",
      tenant_scope: "parent_live",
      action: "admin.material.archive",
      resource_type: "course_material",
      resource_id: "material_live",
      risk_level: "high",
      result: "success",
      reason: "Duplicate worksheet uploaded by parent.",
      trace_id: "req_archive",
      created_at: "2026-05-25T10:07:00+00:00"
    };
    const fetchImpl = vi.fn(async (input: Parameters<typeof fetch>[0]) => {
      const url = String(input);
      if (url.includes("/v1/admin/materials/material_live/archive")) {
        return {
          ok: true,
          json: async () => ({
            required_permission: "admin.material.archive",
            material: archivedMaterial,
            audit_event: archiveEvent
          })
        };
      }
      return {
        ok: true,
        json: async () => (url.includes("/v1/admin/access") ? accessPayload : dashboardPayload)
      };
    });
    vi.stubGlobal("fetch", fetchImpl);

    render(<App />);

    expect(await screen.findByText("真实 API")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "内容流水线" }));
    await userEvent.click(screen.getByRole("button", { name: "查看 Live API Worksheet" }));
    await userEvent.type(screen.getByLabelText("审计原因"), "Duplicate worksheet uploaded by parent.");
    await userEvent.click(screen.getByRole("button", { name: "归档材料" }));

    expect(await screen.findByText("归档请求已记录。")).toBeInTheDocument();
    expect(screen.getAllByText("archived").length).toBeGreaterThan(0);
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/materials/material_live/archive?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({ reason: "Duplicate worksheet uploaded by parent." })
    });
  });

  it("submits live admin retry mutation and shows the audit reason", async () => {
    vi.stubEnv("VITE_ADMIN_API_BASE_URL", "http://127.0.0.1:8000");
    vi.stubEnv("VITE_ADMIN_API_TOKEN", "local-admin-token");
    const dashboardPayload = {
      tenants: [
        {
          id: "parent_live",
          name: "微信家长live",
          tenant_type: "pilot_family",
          status: "warning",
          region: "local",
          owner_contact: "13800138110",
          tier: "pilot",
          created_at: "2026-05-25T10:00:00+00:00",
          active_parents: 1,
          children: 1
        }
      ],
      materials: [
        {
          id: "material_failed",
          tenant_id: "parent_live",
          parent_name: "微信家长live",
          child_name: "Mia Wang",
          child_age: 6,
          title: "Failed API Worksheet",
          page_count: 1,
          job_id: "job_failed",
          confidence_summary: "OCR request failed.",
          ocr_confidence: 0,
          source_pages: [],
          material_status: "failed",
          job_status: "failed",
          provider: "stub",
          learning_assets: 0,
          media_status: "failed",
          sla_minutes: 44,
          updated_at: "2026-05-25T10:05:00+00:00",
          warnings: ["OCR request failed"]
        }
      ],
      provider_policies: [
        {
          tenant_id: "global",
          ai_provider: "stub",
          media_provider: "mock",
          fallback_mode: "global_stub",
          monthly_guardrail: 0,
          source: "global_default"
        }
      ]
    };
    const retriedMaterial = {
      ...dashboardPayload.materials[0],
      confidence_summary: "任务已重新排队。",
      material_status: "processing",
      job_status: "processing",
      media_status: "pending",
      warnings: []
    };
    const accessPayload = {
      current_admin: {
        id: "admin_local",
        display_name: "Local Platform Admin",
        email: "admin@learningenglish.local",
        role: "Platform Owner",
        status: "active"
      },
      permissions: ["admin.dashboard.read", "admin.material.retry", "admin.audit.read"],
      audit_events: []
    };
    const retryEvent = {
      id: "audit_retry",
      actor_id: "admin_local",
      actor_role: "Platform Owner",
      tenant_scope: "parent_live",
      action: "admin.material_job.retry",
      resource_type: "material_parse_job",
      resource_id: "job_failed",
      risk_level: "high",
      result: "success",
      reason: "OCR provider recovered.",
      trace_id: "req_retry",
      created_at: "2026-05-25T10:08:00+00:00"
    };
    const fetchImpl = vi.fn(async (input: Parameters<typeof fetch>[0]) => {
      const url = String(input);
      if (url.includes("/v1/admin/material-jobs/job_failed/retry")) {
        return {
          ok: true,
          json: async () => ({
            required_permission: "admin.material.retry",
            material: retriedMaterial,
            audit_event: retryEvent
          })
        };
      }
      return {
        ok: true,
        json: async () => (url.includes("/v1/admin/access") ? accessPayload : dashboardPayload)
      };
    });
    vi.stubGlobal("fetch", fetchImpl);

    render(<App />);

    expect(await screen.findByText("真实 API")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "内容流水线" }));
    await userEvent.click(screen.getByRole("button", { name: "查看 Failed API Worksheet" }));
    await userEvent.type(screen.getByLabelText("审计原因"), "OCR provider recovered.");
    await userEvent.click(screen.getByRole("button", { name: "重试任务" }));

    expect(await screen.findByText("重试请求已记录。")).toBeInTheDocument();
    expect(screen.getAllByText("processing").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: "审计与权限" }));
    expect(await screen.findByText("admin.material_job.retry")).toBeInTheDocument();
    expect(screen.getByText("OCR provider recovered.")).toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/admin/material-jobs/job_failed/retry?tenant_scope=all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": "local-admin-token"
      },
      body: JSON.stringify({ reason: "OCR provider recovered." })
    });
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
