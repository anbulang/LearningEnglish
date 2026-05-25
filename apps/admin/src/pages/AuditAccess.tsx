import { StatusChip } from "../components/ui";
import type { AdminAccessData } from "../domain/adminApi";
import type { Language } from "../domain/types";

interface AuditAccessProps {
  language: Language;
  accessData: AdminAccessData | null;
  dataMode: "mock" | "live";
}

export function AuditAccess({ language, accessData, dataMode }: AuditAccessProps) {
  const copy = language === "zh" ? zhCopy : enCopy;

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
