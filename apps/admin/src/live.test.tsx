import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const ISO = "2026-06-27T09:48:00+00:00";

function dashboardPayload() {
  return {
    tenants: [
      {
        id: "t1",
        name: "Sunny Kids",
        tenant_type: "pilot_family",
        status: "active",
        region: "local",
        owner_contact: "ops@sunny",
        tier: "pilot",
        created_at: ISO,
        active_parents: 5,
        children: 8
      }
    ],
    materials: [
      {
        id: "m1",
        tenant_id: "t1",
        parent_name: "Lin",
        child_name: "Duo",
        child_age: 7,
        title: "Worksheet A",
        page_count: 1,
        job_id: "job-1",
        confidence_summary: "low",
        ocr_confidence: 0.42,
        source_pages: [],
        material_status: "failed",
        job_status: "failed",
        provider: "qwen",
        learning_assets: 0,
        media_status: "pending",
        sla_minutes: 200,
        updated_at: ISO,
        warnings: []
      }
    ],
    provider_policies: [
      { tenant_id: "global", ai_provider: "stub", media_provider: "mock", fallback_mode: "global_stub", monthly_guardrail: 0, source: "global_default" }
    ],
    module_settings: []
  };
}

function accessPayload() {
  return {
    current_admin: { id: "admin_local", display_name: "Local Admin", email: "a@le.cn", role: "Platform Owner", status: "active" },
    permissions: ["admin.material.retry", "admin.material.archive", "admin.operations.read"],
    audit_events: []
  };
}

function auditEvent() {
  return {
    id: "ae-1",
    actor_id: "admin_local",
    actor_role: "Platform Owner",
    tenant_scope: "all",
    action: "retry_material_job",
    resource_type: "material_parse_job",
    resource_id: "job-1",
    risk_level: "low",
    result: "success",
    reason: "console retry",
    trace_id: "tr-1",
    created_at: "2026-06-27T09:51:00+00:00"
  };
}

function operationsPayload() {
  return {
    required_permission: "admin.operations.read",
    tenant_scope: "all",
    summary: { generated_at: "2026-06-27T09:50:00+00:00", tenant_count: 1, severity: "warning", issue_count: 1 },
    material_parse_jobs: { total: 1, by_status: { queued: 0, processing: 0, needs_review: 0, ready: 0, failed: 1 }, failed: 1, running: 0, stale_processing: 0 },
    media_generation: { failure_signals: { total: 0 } },
    speaking_attempts: { total: 0, failed: 0, pending: 0 },
    provider_configuration: { runtime: { readiness: { ai_provider_ready: true } } },
    module_toggle_coverage: {},
    issues: [
      {
        id: "iss-1",
        severity: "warning",
        status_label: "Parse failed",
        reason: "low confidence",
        recommended_action: "retry_material_job",
        required_permission: "admin.material.retry",
        related_resource: { type: "material_parse_job", id: "job-1", tenant_id: "t1", material_id: "m1" },
        source: "database_snapshot"
      }
    ],
    audit_event: auditEvent(),
    access_context: { current_admin: { id: "admin_local", display_name: "Local Admin", email: "a@le.cn", role: "Platform Owner", status: "active" }, recent_audit_events: [] }
  };
}

function retryPayload() {
  return {
    required_permission: "admin.material.retry",
    material: { ...dashboardPayload().materials[0], material_status: "processing", job_status: "processing" },
    action_result: { action: "retry_material_job", status: "success", resource_type: "material_parse_job", resource_id: "job-1", tenant_id: "t1", message: "queued" },
    audit_event: auditEvent()
  };
}

function usersPayload() {
  return {
    required_permission: "admin.tenant.read",
    tenant_scope: "all",
    items: [
      {
        child_id: "c1",
        child_name: "Duo",
        age: 7,
        level: "K",
        learning_goal: "",
        preferred_review_duration_minutes: 10,
        parent_notes: "",
        tenant_id: "t1",
        parent_name: "Lin",
        materials_count: 3,
        speaking_attempts: 2,
        latest_weekly_report_id: "",
        created_at: ISO
      }
    ],
    total: 1,
    audit_event: auditEvent()
  };
}

function impersonationStartPayload() {
  return {
    required_permission: "admin.impersonation.start",
    impersonation_session: {
      id: "imp-1",
      tenant_id: "t1",
      target_parent_id: "t1",
      actor_id: "admin_local",
      status: "active",
      reason: "console read-only triage",
      created_at: ISO,
      expires_at: ISO,
      ended_at: "",
      updated_at: ISO,
      tenant_display_name: "Sunny Kids",
      target_parent_display_name: "Lin"
    },
    audit_event: auditEvent()
  };
}

function activeSession() {
  return {
    id: "imp-1",
    tenant_id: "t1",
    target_parent_id: "t1",
    actor_id: "admin_local",
    status: "active",
    reason: "console read-only triage",
    created_at: ISO,
    expires_at: ISO,
    ended_at: "",
    updated_at: ISO,
    tenant_display_name: "Sunny Kids",
    target_parent_display_name: "Lin"
  };
}

function impersonationSessionsListPayload() {
  return {
    required_permission: "admin.impersonation.read",
    tenant_scope: "all",
    status: "all",
    items: [activeSession()],
    audit_event: auditEvent()
  };
}

function endSessionPayload() {
  return {
    required_permission: "admin.impersonation.end",
    impersonation_session: { ...activeSession(), status: "ended", ended_at: ISO },
    action_result: {
      action: "end_impersonation_session",
      status: "success",
      resource_type: "impersonation_session",
      resource_id: "imp-1",
      tenant_id: "t1",
      message: "ended"
    },
    audit_event: auditEvent()
  };
}

function auditEventsListPayload() {
  return { items: [auditEvent()], next_cursor: "" };
}

function tenantDetailPayload() {
  return {
    required_permission: "admin.tenant.read",
    tenant: {
      id: "t1",
      name: "Sunny Kids",
      tenant_type: "pilot_family",
      status: "active",
      region: "local",
      owner_contact: "ops@sunny",
      tier: "pilot",
      created_at: ISO,
      active_parents: 5,
      children: 8,
      display_name: "Sunny Kids",
      avatar_url: "",
      phone_number: "13800000000",
      phone_verified_at: ISO,
      wechat_union_id: "",
      wechat_open_id: "",
      updated_at: ISO
    },
    summary: {},
    children: [
      {
        id: "c1",
        name: "Duo",
        age: 7,
        level: "K",
        learning_goal: "",
        preferred_review_duration_minutes: 10,
        parent_notes: "",
        latest_weekly_report_id: "",
        speaking_attempts: 2
      }
    ],
    materials: [],
    provider_policy: {
      tenant_id: "t1",
      ai_provider: "qwen",
      media_provider: "real",
      fallback_mode: "per_tenant",
      monthly_guardrail: 1000,
      source: "tenant_override"
    },
    module_settings: [{ tenant_id: "t1", module_key: "ai_review", enabled: true, source: "tenant_override" }],
    weekly_reports: { total: 3 },
    speaking_attempts: { total: 2 },
    risk_summary: { blocked_jobs: 0 },
    audit_event: auditEvent()
  };
}

function moduleTogglePayload() {
  return {
    required_permission: "admin.tenant.module.toggle",
    module_setting: { tenant_id: "t1", module_key: "worksheet_import", enabled: false, source: "tenant_override" },
    action_result: {
      action: "toggle_tenant_module",
      status: "success",
      resource_type: "tenant_module",
      resource_id: "worksheet_import",
      tenant_id: "t1",
      message: "ok"
    },
    audit_event: auditEvent()
  };
}

function providerPolicyPayload(tenantId = "global") {
  return {
    required_permission: "admin.provider.override",
    provider_policy: {
      tenant_id: tenantId,
      ai_provider: "doubao",
      media_provider: "real",
      fallback_mode: "per_tenant",
      monthly_guardrail: 5000,
      source: "tenant_override"
    },
    action_result: {
      action: "override_provider_policy",
      status: "success",
      resource_type: "provider_policy",
      resource_id: "global",
      tenant_id: "global",
      message: "ok"
    },
    audit_event: auditEvent()
  };
}

function learningAssetsPayload() {
  return {
    tenant_scope: "all",
    items: [
      {
        id: "asset-1",
        material_id: "m1",
        material_title: "Worksheet A",
        material_status: "ready",
        tenant_id: "t1",
        parent_name: "Lin",
        child_name: "Duo",
        text: "queen",
        kind: "word",
        translation: "女王",
        primary_accent: "us",
        media_status: "ready",
        generated_image_status: "ready",
        generated_image_url: "",
        tts_us_status: "ready",
        tts_us_url: "",
        tts_uk_status: "pending",
        tts_uk_url: "",
        updated_at: ISO
      }
    ],
    total: 1
  };
}

function jsonResponse(payload: unknown) {
  return { ok: true, status: 200, json: async () => payload } as unknown as Response;
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.stubEnv("VITE_ADMIN_API_BASE_URL", "https://api.test");
  vi.stubEnv("VITE_ADMIN_API_TOKEN", "test-token");
  fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    // ── POST mutations (most specific first) ──
    if (url.includes("/material-jobs/") && url.includes("/retry") && method === "POST") {
      return Promise.resolve(jsonResponse(retryPayload()));
    }
    if (url.includes("/modules/") && method === "POST") {
      return Promise.resolve(jsonResponse(moduleTogglePayload()));
    }
    if (url.includes("/providers/policies") && method === "POST") {
      const body = JSON.parse(String(init?.body ?? "{}"));
      return Promise.resolve(jsonResponse(providerPolicyPayload(body.tenant_id)));
    }
    if (url.includes("/impersonation-sessions/") && url.includes("/end") && method === "POST") {
      return Promise.resolve(jsonResponse(endSessionPayload()));
    }
    if (url.includes("/impersonation-sessions") && method === "POST") {
      return Promise.resolve(jsonResponse(impersonationStartPayload()));
    }
    // ── GET reads ──
    if (url.includes("/audit-events")) return Promise.resolve(jsonResponse(auditEventsListPayload()));
    if (url.includes("/impersonation-sessions")) return Promise.resolve(jsonResponse(impersonationSessionsListPayload()));
    if (url.includes("/learning-assets")) return Promise.resolve(jsonResponse(learningAssetsPayload()));
    if (url.includes("/tenants/")) return Promise.resolve(jsonResponse(tenantDetailPayload()));
    if (url.includes("/dashboard")) return Promise.resolve(jsonResponse(dashboardPayload()));
    if (url.includes("/access")) return Promise.resolve(jsonResponse(accessPayload()));
    if (url.includes("/operations")) return Promise.resolve(jsonResponse(operationsPayload()));
    if (url.includes("/users")) return Promise.resolve(jsonResponse(usersPayload()));
    return Promise.resolve(jsonResponse({}));
  });
  vi.stubGlobal("fetch", fetchMock);
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
  document.documentElement.removeAttribute("data-theme");
});

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("live mode", () => {
  it("flips to live API and shows live tenant + operations data", async () => {
    render(<App />);
    expect(await screen.findByText("真实 API")).toBeInTheDocument();
    const scope = screen.getByRole("combobox", { name: "租户范围" });
    expect(await within(scope).findByRole("option", { name: "Sunny Kids" })).toBeInTheDocument();
    // Operations issue surfaces as a command-center anomaly.
    expect(await screen.findByText("Parse failed")).toBeInTheDocument();
  });

  it("runs a live retry mutation from a command-center issue", async () => {
    render(<App />);
    // Wait for the live operations issue + its action button.
    const actionButton = await screen.findByRole("button", { name: "retry_material_job" });
    fireEvent.click(actionButton);

    const dialog = screen.getByRole("dialog");
    const reason = within(dialog).getByLabelText("处置原因（必填）");
    fireEvent.change(reason, { target: { value: "manual console retry" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "提交" }));

    await waitFor(() => {
      const calledRetry = fetchMock.mock.calls.some(
        ([input, init]) => String(input).includes("/material-jobs/job-1/retry") && (init?.method ?? "").toUpperCase() === "POST"
      );
      expect(calledRetry).toBe(true);
    });
  });

  it("impersonates with the real parent id, not the composite list key", async () => {
    render(<App />);
    // Wait for live mode, then open the users screen (loads /users live).
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "用户与家庭" }));
    await screen.findAllByText("Lin");

    fireEvent.click(screen.getByRole("button", { name: "发起代登录" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "确认并记录" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([input, init]) => String(input).includes("/impersonation-sessions") && (init?.method ?? "").toUpperCase() === "POST"
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(String((call![1] as RequestInit).body));
      // The real parent-account id ("t1"), never the "t1::Lin" composite key.
      expect(body.target_parent_id).toBe("t1");
      expect(body.tenant_id).toBe("t1");
    });
  });
});

describe("live wiring (newly connected endpoints)", () => {
  it("opens a live tenant detail drawer (GET /tenants/{id})", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "租户管理" }));
    fireEvent.click(await screen.findByRole("button", { name: "详情" }));
    // The drawer renders the live tenant's child profile from the detail payload.
    expect(await screen.findByText("Duo")).toBeInTheDocument();
    await waitFor(() => {
      const called = fetchMock.mock.calls.some(
        ([input, init]) => String(input).includes("/tenants/t1") && (init?.method ?? "GET").toUpperCase() === "GET"
      );
      expect(called).toBe(true);
    });
  });

  it("toggles a tenant module live (POST /tenants/{id}/modules/{key})", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "租户管理" }));
    fireEvent.click(await screen.findByRole("button", { name: "详情" }));
    // worksheet_import has no override row → defaults enabled; toggling sends enabled:false.
    const toggle = await screen.findByRole("switch", { name: "讲义导入" });
    fireEvent.click(toggle);
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).includes("/tenants/t1/modules/worksheet_import") && (init?.method ?? "").toUpperCase() === "POST"
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(String((call![1] as RequestInit).body));
      expect(body.enabled).toBe(false);
      expect(typeof body.reason).toBe("string");
    });
  });

  it("saves a provider policy override live (POST /providers/policies)", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: /Provider 运维/ }));
    // The global policy row (from dashboard.provider_policies) is editable.
    const reason = await screen.findByLabelText("原因 * global");
    fireEvent.change(reason, { target: { value: "switch to doubao" } });
    fireEvent.click(screen.getByRole("button", { name: "保存策略" }));
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([input, init]) => String(input).includes("/providers/policies") && (init?.method ?? "").toUpperCase() === "POST"
      );
      expect(call).toBeTruthy();
      const body = JSON.parse(String((call![1] as RequestInit).body));
      expect(body.tenant_id).toBe("global");
      expect(body.reason).toBe("switch to doubao");
    });
  });

  it("ends an impersonation session live (POST /impersonation-sessions/{id}/end)", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "审计与权限" }));
    // The live sessions table renders the active session; end it.
    fireEvent.click(await screen.findByRole("button", { name: "结束会话" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "确认" }));
    await waitFor(() => {
      const called = fetchMock.mock.calls.some(
        ([input, init]) =>
          String(input).includes("/impersonation-sessions/imp-1/end") && (init?.method ?? "").toUpperCase() === "POST"
      );
      expect(called).toBe(true);
    });
  });

  it("applies an audit filter live (GET /audit-events with filter params)", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "审计与权限" }));
    const actorInput = await screen.findByLabelText("操作者 ID");
    fireEvent.change(actorInput, { target: { value: "admin_local" } });
    fireEvent.click(screen.getByRole("button", { name: "筛选" }));
    await waitFor(() => {
      const called = fetchMock.mock.calls.some(
        ([input]) => String(input).includes("/audit-events") && String(input).includes("actor_id=admin_local")
      );
      expect(called).toBe(true);
    });
  });

  it("renders live learning assets and flags no-backend controls as prototype", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: "学习资产" }));
    // The live asset's grapheme (from `text`) renders in the flat grid.
    expect(await screen.findByText("queen")).toBeInTheDocument();
    // Asset regen/edit/remove have no backend → flagged as prototype in live mode.
    expect(screen.getAllByText("原型").length).toBeGreaterThan(0);
  });

  it("does not fall back to fabricated KPIs when live operations is unavailable", async () => {
    // Operations fetch fails → CommandCenter shows an honest placeholder, not mock seeds.
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/operations")) {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({}) } as unknown as Response);
      }
      if (url.includes("/dashboard")) return Promise.resolve(jsonResponse(dashboardPayload()));
      if (url.includes("/access")) return Promise.resolve(jsonResponse(accessPayload()));
      return Promise.resolve(jsonResponse({}));
    });
    render(<App />);
    await screen.findByText("真实 API");
    // The honest placeholder renders; the fabricated mock KPI ("8,642") never shows under the live badge.
    expect(await screen.findByText(/实时运营数据加载中或暂不可用/)).toBeInTheDocument();
    expect(screen.queryByText("8,642")).not.toBeInTheDocument();
  });

  it("does not duplicate a policy row after saving a new tenant override", async () => {
    render(<App />);
    await screen.findByText("真实 API");
    fireEvent.click(screen.getByRole("button", { name: /Provider 运维/ }));
    // Pick the (uncovered) tenant t1 to create a draft override row.
    const picker = await screen.findByLabelText("为租户新增覆盖");
    fireEvent.change(picker, { target: { value: "t1" } });
    const reason = await screen.findByLabelText("原因 * t1");
    fireEvent.change(reason, { target: { value: "tenant override" } });
    // Save the t1 draft (rows render as [global, t1-draft] → last "保存策略").
    const saves = screen.getAllByRole("button", { name: "保存策略" });
    fireEvent.click(saves[saves.length - 1]);
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).includes("/providers/policies") &&
          (init?.method ?? "").toUpperCase() === "POST" &&
          JSON.parse(String((init as RequestInit).body)).tenant_id === "t1"
      );
      expect(call).toBeTruthy();
    });
    // After save, exactly ONE t1 row exists — no phantom duplicate / duplicate React key.
    await waitFor(() => {
      expect(screen.getAllByLabelText("原因 * t1").length).toBe(1);
    });
  });
});
