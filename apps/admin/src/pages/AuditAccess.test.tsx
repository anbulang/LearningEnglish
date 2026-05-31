import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AdminAccessData } from "../domain/adminApi";
import { mockAuditEventsPage, mockImpersonationSessions, mockTenants } from "../domain/mockData";
import { AuditAccess } from "./AuditAccess";

const accessData: AdminAccessData = {
  currentAdmin: {
    id: "admin_local",
    displayName: "Local Platform Admin",
    email: "admin@learningenglish.local",
    role: "Platform Owner",
    status: "active"
  },
  permissions: ["admin.dashboard.read", "admin.audit.read"],
  auditEvents: [
    {
      id: "audit_1",
      actorId: "admin_local",
      actorRole: "Platform Owner",
      tenantScope: "all",
      action: "admin.dashboard.read",
      resourceType: "admin_dashboard",
      resourceId: "dashboard",
      riskLevel: "low",
      result: "success",
      reason: "Duplicate worksheet uploaded by parent.",
      traceId: "req_12345678",
      createdAt: "2026-05-25T10:06:00+00:00"
    }
  ]
};

describe("AuditAccess", () => {
  it("shows live admin identity permissions and audit events in Chinese", () => {
    render(<AuditAccess language="zh" accessData={accessData} dataMode="live" tenants={mockTenants} />);

    expect(screen.getByText("审计与权限")).toBeInTheDocument();
    expect(screen.getByText("Local Platform Admin")).toBeInTheDocument();
    expect(screen.getAllByText("Platform Owner").length).toBeGreaterThan(0);
    expect(screen.getAllByText("admin.dashboard.read").length).toBeGreaterThan(0);
    expect(screen.getByText("admin.audit.read")).toBeInTheDocument();
    expect(screen.getByText("Duplicate worksheet uploaded by parent.")).toBeInTheDocument();
    expect(screen.getByText("req_12345678")).toBeInTheDocument();
  });

  it("keeps the target-state copy when live access data has not loaded", () => {
    render(<AuditAccess language="en" accessData={null} dataMode="mock" tenants={mockTenants} />);

    expect(screen.getByText("Audit & Access")).toBeInTheDocument();
    expect(screen.getByText("Mock mode")).toBeInTheDocument();
    expect(screen.getByText("Admin access data will load from the live read API when configured.")).toBeInTheDocument();
  });

  it("submits a supervised impersonation session in live mode", async () => {
    const onStartImpersonation = vi.fn().mockResolvedValue(undefined);
    render(
      <AuditAccess
        language="en"
        accessData={{ ...accessData, permissions: [...accessData.permissions, "admin.impersonation.start"] }}
        dataMode="live"
        tenants={mockTenants}
        onStartImpersonation={onStartImpersonation}
      />
    );

    await userEvent.type(
      screen.getByLabelText("Impersonation reason"),
      "Support is reproducing parent-reported upload issue."
    );
    await userEvent.click(screen.getByRole("button", { name: "Start supervised session" }));

    expect(onStartImpersonation).toHaveBeenCalledWith({
      tenantId: "tenant_bright_future",
      targetParentId: "tenant_bright_future",
      reason: "Support is reproducing parent-reported upload issue."
    });
    expect(await screen.findByText("Supervised session started.")).toBeInTheDocument();
  });

  it("loads audit events with filters and cursor pagination", async () => {
    const onLoadAuditEvents = vi.fn().mockResolvedValue(mockAuditEventsPage);
    render(
      <AuditAccess
        language="en"
        accessData={accessData}
        dataMode="live"
        tenants={mockTenants}
        auditEventsPage={mockAuditEventsPage}
        onLoadAuditEvents={onLoadAuditEvents}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText("Tenant filter"), "tenant_sunny_kids");
    await userEvent.type(screen.getByLabelText("Actor filter"), "admin_001");
    await userEvent.type(screen.getByLabelText("Action filter"), "admin.material_job.retry");
    await userEvent.type(screen.getByLabelText("Resource type filter"), "material_parse_job");
    await userEvent.type(screen.getByLabelText("Resource ID filter"), "job_animals_parse");
    await userEvent.selectOptions(screen.getByLabelText("Risk filter"), "high");
    await userEvent.selectOptions(screen.getByLabelText("Result filter"), "success");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    expect(onLoadAuditEvents).toHaveBeenCalledWith({
      tenantScope: "tenant_sunny_kids",
      actorId: "admin_001",
      action: "admin.material_job.retry",
      resourceType: "material_parse_job",
      resourceId: "job_animals_parse",
      riskLevel: "high",
      result: "success"
    });

    await userEvent.click(screen.getByRole("button", { name: "Load next page" }));

    expect(onLoadAuditEvents).toHaveBeenLastCalledWith({
      tenantScope: "tenant_sunny_kids",
      actorId: "admin_001",
      action: "admin.material_job.retry",
      resourceType: "material_parse_job",
      resourceId: "job_animals_parse",
      riskLevel: "high",
      result: "success",
      cursor: mockAuditEventsPage.nextCursor
    });
  });

  it("lists impersonation sessions and requires a reason before ending one", async () => {
    const onEndImpersonationSession = vi.fn().mockResolvedValue({
      requiredPermission: "admin.impersonation.end",
      impersonationSession: mockImpersonationSessions.items[1],
      actionResult: {
        action: "end_impersonation_session",
        status: "noop",
        resourceType: "admin_impersonation_session",
        resourceId: "imp_mock_ended",
        tenantId: "tenant_maple_pilot",
        message: "Session was already ended."
      },
      auditEvent: mockAuditEventsPage.items[0]
    });
    render(
      <AuditAccess
        language="en"
        accessData={{
          ...accessData,
          permissions: [...accessData.permissions, "admin.impersonation.start", "admin.impersonation.end"]
        }}
        dataMode="live"
        tenants={mockTenants}
        impersonationSessions={mockImpersonationSessions}
        onEndImpersonationSession={onEndImpersonationSession}
      />
    );

    expect(screen.getByText("imp_mock_active")).toBeInTheDocument();
    expect(screen.getByText("imp_mock_ended")).toBeInTheDocument();
    expect(screen.getByText("2026-05-24T09:18:00+00:00")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "End session imp_mock_ended" }));
    expect(screen.getByText("End reason is required.")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("End session reason"), "Support handoff complete.");
    await userEvent.click(screen.getByRole("button", { name: "End session imp_mock_ended" }));

    expect(onEndImpersonationSession).toHaveBeenCalledWith("imp_mock_ended", "Support handoff complete.");
    expect(await screen.findByText("noop: Session was already ended.")).toBeInTheDocument();
    expect(screen.getByText("2026-05-24T09:18:00+00:00")).toBeInTheDocument();
  });
});
