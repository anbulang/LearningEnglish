import { useState } from "react";
import { StatusChip } from "../components/ui";
import type { AdminAccessData } from "../domain/adminApi";
import type { Language, Tenant } from "../domain/types";

export interface StartImpersonationInput {
  tenantId: string;
  targetParentId: string;
  reason: string;
}

interface AuditAccessProps {
  language: Language;
  accessData: AdminAccessData | null;
  dataMode: "mock" | "live";
  tenants: Tenant[];
  onStartImpersonation?: (input: StartImpersonationInput) => Promise<void>;
}

export function AuditAccess({ language, accessData, dataMode, tenants, onStartImpersonation }: AuditAccessProps) {
  const copy = language === "zh" ? zhCopy : enCopy;
  const [selectedTenantId, setSelectedTenantId] = useState(tenants[0]?.id ?? "");
  const [impersonationReason, setImpersonationReason] = useState("");
  const [impersonationMessage, setImpersonationMessage] = useState("");
  const [isStartingImpersonation, setIsStartingImpersonation] = useState(false);
  const hasImpersonationPermission = Boolean(accessData?.permissions.includes("admin.impersonation.start"));
  const effectiveTenantId = tenants.some((tenant) => tenant.id === selectedTenantId) ? selectedTenantId : tenants[0]?.id ?? "";

  async function handleStartImpersonation() {
    if (!onStartImpersonation || !effectiveTenantId || !impersonationReason.trim()) {
      return;
    }
    setIsStartingImpersonation(true);
    setImpersonationMessage("");
    try {
      await onStartImpersonation({
        tenantId: effectiveTenantId,
        targetParentId: effectiveTenantId,
        reason: impersonationReason.trim()
      });
      setImpersonationReason("");
      setImpersonationMessage(copy.impersonationStarted);
    } catch {
      setImpersonationMessage(copy.impersonationFailed);
    } finally {
      setIsStartingImpersonation(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">AdminUser / Permission / AuditEvent</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      {!accessData ? (
        <section className="surface empty-phase wide">
          <StatusChip tone="neutral">{dataMode === "live" ? copy.loading : copy.mockMode}</StatusChip>
          <h2>{copy.emptyTitle}</h2>
          <p>{copy.emptyDetail}</p>
        </section>
      ) : (
        <>
          <section className="surface span-4">
            <div className="section-title">
              <h2>{copy.currentAdmin}</h2>
            </div>
            <dl className="detail-list compact">
              <dt>{copy.name}</dt>
              <dd>{accessData.currentAdmin.displayName}</dd>
              <dt>{copy.email}</dt>
              <dd>{accessData.currentAdmin.email}</dd>
              <dt>{copy.role}</dt>
              <dd>{accessData.currentAdmin.role}</dd>
              <dt>{copy.status}</dt>
              <dd>
                <StatusChip tone={accessData.currentAdmin.status === "active" ? "success" : "warning"}>
                  {accessData.currentAdmin.status}
                </StatusChip>
              </dd>
            </dl>
          </section>

          <section className="surface span-8">
            <div className="section-title">
              <h2>{copy.permissions}</h2>
              <StatusChip tone="neutral">{accessData.permissions.length}</StatusChip>
            </div>
            <div className="permission-grid">
              {accessData.permissions.map((permission) => (
                <span className="permission-pill" key={permission}>
                  {permission}
                </span>
              ))}
            </div>
          </section>

          <section className="surface wide">
            <div className="section-title">
              <div>
                <h2>{copy.impersonationTitle}</h2>
                <p>{copy.impersonationDetail}</p>
              </div>
              <StatusChip tone={hasImpersonationPermission ? "warning" : "neutral"}>
                {hasImpersonationPermission ? "admin.impersonation.start" : copy.permissionMissing}
              </StatusChip>
            </div>
            <div className="provider-form">
              <label>
                <span>{copy.targetTenant}</span>
                <select value={effectiveTenantId} onChange={(event) => setSelectedTenantId(event.target.value)}>
                  {tenants.map((tenant) => (
                    <option value={tenant.id} key={tenant.id}>
                      {tenant.name} / {tenant.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{copy.impersonationReason}</span>
                <textarea
                  aria-label={copy.impersonationReason}
                  maxLength={240}
                  placeholder={copy.impersonationPlaceholder}
                  value={impersonationReason}
                  onChange={(event) => setImpersonationReason(event.target.value)}
                />
              </label>
              <div className="audit-actions">
                <button
                  type="button"
                  className="primary-button"
                  disabled={
                    dataMode !== "live" ||
                    !hasImpersonationPermission ||
                    !onStartImpersonation ||
                    !effectiveTenantId ||
                    !impersonationReason.trim() ||
                    isStartingImpersonation
                  }
                  onClick={() => void handleStartImpersonation()}
                >
                  {copy.startImpersonation}
                </button>
                <StatusChip tone="neutral">{copy.noParentToken}</StatusChip>
              </div>
              {impersonationMessage && <p className="action-message">{impersonationMessage}</p>}
            </div>
          </section>

          <section className="surface table-panel wide">
            <div className="section-title">
              <div>
                <h2>{copy.auditLog}</h2>
                <p>{copy.auditLogDetail}</p>
              </div>
              <StatusChip tone="success">{copy.immutable}</StatusChip>
            </div>
            <div className="table-scroll">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>{copy.time}</th>
                    <th>{copy.actor}</th>
                    <th>{copy.tenant}</th>
                    <th>{copy.action}</th>
                    <th>{copy.resource}</th>
                    <th>{copy.result}</th>
                    <th>{copy.reason}</th>
                    <th>{copy.trace}</th>
                  </tr>
                </thead>
                <tbody>
                  {accessData.auditEvents.map((event) => (
                    <tr key={event.id}>
                      <td data-label={copy.time}>{event.createdAt}</td>
                      <td data-label={copy.actor}>
                        <strong className="table-title">{event.actorId}</strong>
                        <small>{event.actorRole}</small>
                      </td>
                      <td data-label={copy.tenant}>{event.tenantScope}</td>
                      <td data-label={copy.action}>{event.action}</td>
                      <td data-label={copy.resource}>
                        {event.resourceType}
                        <small>{event.resourceId}</small>
                      </td>
                      <td data-label={copy.result}>
                        <StatusChip tone={event.result === "success" ? "success" : "danger"}>{event.result}</StatusChip>
                      </td>
                      <td data-label={copy.reason}>{event.reason || copy.noReason}</td>
                      <td data-label={copy.trace}>{event.traceId}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

const zhCopy = {
  title: "审计与权限",
  subtitle: "查看当前后台管理员、权限边界和最近管理操作审计记录",
  loading: "加载中",
  mockMode: "Mock mode",
  emptyTitle: "等待 live admin access 数据",
  emptyDetail: "配置 live read API 后会显示管理员身份、权限和审计事件。",
  currentAdmin: "当前管理员",
  name: "姓名",
  email: "邮箱",
  role: "角色",
  status: "状态",
  permissions: "权限",
  impersonationTitle: "受监督代入",
  impersonationDetail: "创建短期支持会话，用于复现问题；不会签发家长 token。",
  targetTenant: "目标租户 / 家长账号",
  impersonationReason: "代入原因",
  impersonationPlaceholder: "说明支持人员为什么需要进入该租户上下文。",
  startImpersonation: "启动受监督会话",
  noParentToken: "不签发 parent token",
  permissionMissing: "缺少权限",
  impersonationStarted: "受监督会话已启动。",
  impersonationFailed: "受监督会话启动失败，请稍后重试。",
  auditLog: "审计日志",
  auditLogDetail: "后台读取、重试、归档和高风险操作会写入不可变审计记录。",
  immutable: "不可删除",
  time: "时间",
  actor: "Actor",
  tenant: "租户",
  action: "动作",
  resource: "资源",
  result: "结果",
  reason: "原因",
  noReason: "-",
  trace: "Trace"
};

const enCopy = {
  title: "Audit & Access",
  subtitle: "Inspect the current admin identity, permission boundary, and recent management audit events.",
  loading: "Loading",
  mockMode: "Mock mode",
  emptyTitle: "Waiting for live admin access data",
  emptyDetail: "Admin access data will load from the live read API when configured.",
  currentAdmin: "Current admin",
  name: "Name",
  email: "Email",
  role: "Role",
  status: "Status",
  permissions: "Permissions",
  impersonationTitle: "Supervised impersonation",
  impersonationDetail: "Create a short support session to reproduce an issue; no parent token is issued.",
  targetTenant: "Target tenant / parent account",
  impersonationReason: "Impersonation reason",
  impersonationPlaceholder: "Explain why support needs to enter this tenant context.",
  startImpersonation: "Start supervised session",
  noParentToken: "No parent token issued",
  permissionMissing: "Missing permission",
  impersonationStarted: "Supervised session started.",
  impersonationFailed: "Supervised session failed. Try again later.",
  auditLog: "Audit log",
  auditLogDetail: "Admin reads, retries, archives, and high-risk actions write immutable audit records.",
  immutable: "Immutable",
  time: "Time",
  actor: "Actor",
  tenant: "Tenant",
  action: "Action",
  resource: "Resource",
  result: "Result",
  reason: "Reason",
  noReason: "-",
  trace: "Trace"
};
