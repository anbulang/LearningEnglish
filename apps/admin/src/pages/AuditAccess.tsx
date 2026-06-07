import { useEffect, useState } from "react";
import { StatusChip } from "../components/ui";
import type { AdminAccessData } from "../domain/adminApi";
import type {
  AdminAuditEvent,
  AdminAuditEventsData,
  AdminImpersonationSessionsData,
  EndAdminImpersonationSessionResult,
  Language,
  Tenant
} from "../domain/types";

export interface StartImpersonationInput {
  tenantId: string;
  targetParentId: string;
  reason: string;
}

export interface AuditEventFilters {
  tenantScope: string;
  action?: string;
  resourceType?: string;
  resourceId?: string;
  riskLevel?: string;
  result?: string;
  actorId?: string;
  cursor?: string;
}

interface AuditAccessProps {
  language: Language;
  accessData: AdminAccessData | null;
  dataMode: "mock" | "live";
  tenants: Tenant[];
  tenantScope?: string;
  auditEventsPage?: AdminAuditEventsData | null;
  impersonationSessions?: AdminImpersonationSessionsData | null;
  onLoadAuditEvents?: (filters: AuditEventFilters) => Promise<AdminAuditEventsData | void>;
  onStartImpersonation?: (input: StartImpersonationInput) => Promise<void>;
  onEndImpersonationSession?: (sessionId: string, reason: string) => Promise<EndAdminImpersonationSessionResult | void>;
}

export function AuditAccess({
  language,
  accessData,
  dataMode,
  tenants,
  tenantScope = "all",
  auditEventsPage,
  impersonationSessions,
  onLoadAuditEvents,
  onStartImpersonation,
  onEndImpersonationSession
}: AuditAccessProps) {
  const copy = language === "zh" ? zhCopy : enCopy;
  const [selectedTenantId, setSelectedTenantId] = useState(tenants[0]?.id ?? "");
  const [auditFilters, setAuditFilters] = useState({
    tenantScope,
    actorId: "",
    action: "",
    resourceType: "",
    resourceId: "",
    riskLevel: "",
    result: ""
  });
  const [impersonationReason, setImpersonationReason] = useState("");
  const [impersonationMessage, setImpersonationMessage] = useState("");
  const [isStartingImpersonation, setIsStartingImpersonation] = useState(false);
  const [endSessionReason, setEndSessionReason] = useState("");
  const [endSessionError, setEndSessionError] = useState("");
  const [endSessionMessage, setEndSessionMessage] = useState("");
  const [endingSessionId, setEndingSessionId] = useState("");
  const hasImpersonationPermission = hasPermission(accessData?.permissions, "admin.impersonation.start");
  const hasEndImpersonationPermission = hasPermission(accessData?.permissions, "admin.impersonation.end");
  const effectiveTenantId = tenants.some((tenant) => tenant.id === selectedTenantId) ? selectedTenantId : tenants[0]?.id ?? "";
  const auditEvents = auditEventsPage?.items ?? accessData?.auditEvents ?? [];
  const nextCursor = auditEventsPage?.nextCursor ?? "";

  useEffect(() => {
    setAuditFilters((current) => ({ ...current, tenantScope }));
  }, [tenantScope]);

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

  async function handleLoadAuditEvents(cursor?: string) {
    if (!onLoadAuditEvents) {
      return;
    }
    await onLoadAuditEvents(toAuditEventFilters(auditFilters, cursor));
  }

  async function handleEndImpersonationSession(sessionId: string) {
    if (!onEndImpersonationSession || !endSessionReason.trim()) {
      setEndSessionError(copy.endReasonRequired);
      return;
    }
    setEndingSessionId(sessionId);
    setEndSessionError("");
    setEndSessionMessage("");
    try {
      const result = await onEndImpersonationSession(sessionId, endSessionReason.trim());
      if (result?.actionResult) {
        setEndSessionMessage(`${result.actionResult.status}: ${result.actionResult.message}`);
      } else {
        setEndSessionMessage(copy.sessionEnded);
      }
      setEndSessionReason("");
    } catch {
      setEndSessionMessage(copy.sessionEndFailed);
    } finally {
      setEndingSessionId("");
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
                <h2>{copy.sessions}</h2>
                <p>{copy.sessionsDetail}</p>
              </div>
              <StatusChip tone="neutral">{impersonationSessions?.items.length ?? 0}</StatusChip>
            </div>
            <div className="provider-form">
              <label>
                <span>{copy.endSessionReason}</span>
                <textarea
                  aria-label={copy.endSessionReason}
                  maxLength={240}
                  placeholder={copy.endSessionPlaceholder}
                  value={endSessionReason}
                  onChange={(event) => setEndSessionReason(event.target.value)}
                />
              </label>
              {endSessionError && <p className="form-error">{endSessionError}</p>}
              {endSessionMessage && <p className="action-message">{endSessionMessage}</p>}
            </div>
            <div className="table-scroll">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>{copy.session}</th>
                    <th>{copy.tenant}</th>
                    <th>{copy.target}</th>
                    <th>{copy.status}</th>
                    <th>{copy.created}</th>
                    <th>{copy.ended}</th>
                    <th>{copy.reason}</th>
                    <th>{copy.action}</th>
                  </tr>
                </thead>
                <tbody>
                  {(impersonationSessions?.items ?? []).map((session) => (
                    <tr key={session.id}>
                      <td data-label={copy.session}>
                        <strong className="table-title">{session.id}</strong>
                        <small>{session.actorId}</small>
                      </td>
                      <td data-label={copy.tenant}>
                        {session.tenantDisplayName || session.tenantId}
                        <small>{session.tenantId}</small>
                      </td>
                      <td data-label={copy.target}>
                        {session.targetParentDisplayName || session.targetParentId}
                        <small>{session.targetParentId}</small>
                      </td>
                      <td data-label={copy.status}>
                        <StatusChip tone={sessionStatusTone(session.status)}>{session.status}</StatusChip>
                      </td>
                      <td data-label={copy.created}>{session.createdAt}</td>
                      <td data-label={copy.ended}>{session.endedAt || copy.noReason}</td>
                      <td data-label={copy.reason}>{session.reason || copy.noReason}</td>
                      <td data-label={copy.action}>
                        <button
                          type="button"
                          className="ghost-button compact-action"
                          disabled={
                            dataMode !== "live" ||
                            !hasEndImpersonationPermission ||
                            !onEndImpersonationSession ||
                            endingSessionId === session.id
                          }
                          onClick={() => void handleEndImpersonationSession(session.id)}
                        >
                          {copy.endSession(session.id)}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
            <div className="filter-bar audit-filter-bar">
              <label>
                <span>{copy.tenantFilter}</span>
                <select
                  aria-label={copy.tenantFilter}
                  value={auditFilters.tenantScope}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, tenantScope: event.target.value }))}
                >
                  <option value="all">{copy.allTenants}</option>
                  {tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>
                      {tenant.name} / {tenant.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{copy.actorFilter}</span>
                <input
                  aria-label={copy.actorFilter}
                  value={auditFilters.actorId}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, actorId: event.target.value }))}
                />
              </label>
              <label>
                <span>{copy.actionFilter}</span>
                <input
                  aria-label={copy.actionFilter}
                  value={auditFilters.action}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, action: event.target.value }))}
                />
              </label>
              <label>
                <span>{copy.resourceTypeFilter}</span>
                <input
                  aria-label={copy.resourceTypeFilter}
                  value={auditFilters.resourceType}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, resourceType: event.target.value }))}
                />
              </label>
              <label>
                <span>{copy.resourceIdFilter}</span>
                <input
                  aria-label={copy.resourceIdFilter}
                  value={auditFilters.resourceId}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, resourceId: event.target.value }))}
                />
              </label>
              <label>
                <span>{copy.riskFilter}</span>
                <select
                  aria-label={copy.riskFilter}
                  value={auditFilters.riskLevel}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, riskLevel: event.target.value }))}
                >
                  <option value="">{copy.any}</option>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </label>
              <label>
                <span>{copy.resultFilter}</span>
                <select
                  aria-label={copy.resultFilter}
                  value={auditFilters.result}
                  onChange={(event) => setAuditFilters((current) => ({ ...current, result: event.target.value }))}
                >
                  <option value="">{copy.any}</option>
                  <option value="success">success</option>
                  <option value="failed">failed</option>
                  <option value="noop">noop</option>
                </select>
              </label>
              <button type="button" className="primary-button" onClick={() => void handleLoadAuditEvents()}>
                {copy.applyFilters}
              </button>
              {nextCursor && (
                <button type="button" className="ghost-button" onClick={() => void handleLoadAuditEvents(nextCursor)}>
                  {copy.loadNextPage}
                </button>
              )}
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
                    <th>{copy.risk}</th>
                    <th>{copy.result}</th>
                    <th>{copy.reason}</th>
                    <th>{copy.trace}</th>
                  </tr>
                </thead>
                <tbody>
                  {auditEvents.map((event) => (
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
                      <td data-label={copy.risk}>
                        <StatusChip tone={riskTone(event.riskLevel)}>{event.riskLevel}</StatusChip>
                      </td>
                      <td data-label={copy.result}>
                        <StatusChip tone={resultTone(event.result)}>{event.result}</StatusChip>
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

function toAuditEventFilters(filters: AuditEventFilters, cursor?: string): AuditEventFilters {
  const normalized: AuditEventFilters = {
    tenantScope: filters.tenantScope || "all"
  };
  addOptionalFilter(normalized, "actorId", filters.actorId);
  addOptionalFilter(normalized, "action", filters.action);
  addOptionalFilter(normalized, "resourceType", filters.resourceType);
  addOptionalFilter(normalized, "resourceId", filters.resourceId);
  addOptionalFilter(normalized, "riskLevel", filters.riskLevel);
  addOptionalFilter(normalized, "result", filters.result);
  if (cursor) {
    normalized.cursor = cursor;
  }
  return normalized;
}

function addOptionalFilter(filters: AuditEventFilters, key: keyof AuditEventFilters, value: string | undefined) {
  const trimmed = value?.trim();
  if (trimmed) {
    filters[key] = trimmed;
  }
}

function hasPermission(permissions: string[] | undefined, permission: string): boolean {
  return Boolean(permissions?.includes("*") || permissions?.includes(permission));
}

function riskTone(riskLevel: AdminAuditEvent["riskLevel"]): "success" | "warning" | "danger" | "neutral" {
  if (riskLevel === "high") {
    return "danger";
  }
  if (riskLevel === "medium") {
    return "warning";
  }
  if (riskLevel === "low") {
    return "success";
  }
  return "neutral";
}

function resultTone(result: AdminAuditEvent["result"]): "success" | "warning" | "danger" | "neutral" {
  if (result === "success") {
    return "success";
  }
  if (result === "noop") {
    return "warning";
  }
  if (result === "failed") {
    return "danger";
  }
  return "neutral";
}

function sessionStatusTone(status: AdminImpersonationSessionsData["items"][number]["status"]): "success" | "warning" | "danger" {
  if (status === "active") {
    return "success";
  }
  if (status === "expired") {
    return "danger";
  }
  return "warning";
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
  sessions: "代管会话",
  sessionsDetail: "查看 active、ended 和 expired 会话，并以审计原因结束会话。",
  session: "会话",
  target: "目标",
  created: "创建时间",
  ended: "结束时间",
  endSessionReason: "结束会话原因",
  endSessionPlaceholder: "说明为什么结束或复核该代管会话。",
  endReasonRequired: "必须填写结束原因。",
  endSession: (id: string) => `结束会话 ${id}`,
  sessionEnded: "代管会话已结束。",
  sessionEndFailed: "代管会话结束失败，请稍后重试。",
  auditLog: "审计日志",
  auditLogDetail: "后台读取、重试、归档和高风险操作会写入不可变审计记录。",
  immutable: "不可删除",
  tenantFilter: "租户过滤",
  actorFilter: "Actor 过滤",
  actionFilter: "动作过滤",
  resourceTypeFilter: "资源类型过滤",
  resourceIdFilter: "资源 ID 过滤",
  riskFilter: "风险过滤",
  resultFilter: "结果过滤",
  allTenants: "所有租户",
  any: "不限",
  applyFilters: "应用过滤",
  loadNextPage: "加载下一页",
  time: "时间",
  actor: "Actor",
  tenant: "租户",
  action: "动作",
  resource: "资源",
  risk: "风险",
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
  sessions: "Impersonation sessions",
  sessionsDetail: "Review active, ended, and expired sessions and close sessions with an audited reason.",
  session: "Session",
  target: "Target",
  created: "Created",
  ended: "Ended",
  endSessionReason: "End session reason",
  endSessionPlaceholder: "Explain why this support session is being closed or reviewed.",
  endReasonRequired: "End reason is required.",
  endSession: (id: string) => `End session ${id}`,
  sessionEnded: "Impersonation session ended.",
  sessionEndFailed: "Impersonation session end failed. Try again later.",
  auditLog: "Audit log",
  auditLogDetail: "Admin reads, retries, archives, and high-risk actions write immutable audit records.",
  immutable: "Immutable",
  tenantFilter: "Tenant filter",
  actorFilter: "Actor filter",
  actionFilter: "Action filter",
  resourceTypeFilter: "Resource type filter",
  resourceIdFilter: "Resource ID filter",
  riskFilter: "Risk filter",
  resultFilter: "Result filter",
  allTenants: "All tenants",
  any: "Any",
  applyFilters: "Apply filters",
  loadNextPage: "Load next page",
  time: "Time",
  actor: "Actor",
  tenant: "Tenant",
  action: "Action",
  resource: "Resource",
  risk: "Risk",
  result: "Result",
  reason: "Reason",
  noReason: "-",
  trace: "Trace"
};
