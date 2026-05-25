import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AdminAccessData } from "../domain/adminApi";
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
      reason: "",
      traceId: "req_12345678",
      createdAt: "2026-05-25T10:06:00+00:00"
    }
  ]
};

describe("AuditAccess", () => {
  it("shows live admin identity permissions and audit events in Chinese", () => {
    render(<AuditAccess language="zh" accessData={accessData} dataMode="live" />);

    expect(screen.getByText("审计与权限")).toBeInTheDocument();
    expect(screen.getByText("Local Platform Admin")).toBeInTheDocument();
    expect(screen.getAllByText("Platform Owner").length).toBeGreaterThan(0);
    expect(screen.getAllByText("admin.dashboard.read").length).toBeGreaterThan(0);
    expect(screen.getByText("admin.audit.read")).toBeInTheDocument();
    expect(screen.getByText("req_12345678")).toBeInTheDocument();
  });

  it("keeps the target-state copy when live access data has not loaded", () => {
    render(<AuditAccess language="en" accessData={null} dataMode="mock" />);

    expect(screen.getByText("Audit & Access")).toBeInTheDocument();
    expect(screen.getByText("Mock mode")).toBeInTheDocument();
    expect(screen.getByText("Admin access data will load from the live read API when configured.")).toBeInTheDocument();
  });
});
