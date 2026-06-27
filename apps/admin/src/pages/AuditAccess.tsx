import { useRef, useState } from "react";
import {
  AUDIT_RESULT_META,
  MEMBER_STATUS_META,
  consoleAuditLog,
  consoleMembers,
  consolePermMatrix,
  type ConsoleAuditRow,
  type ConsoleMember,
  type MemberStatusKey
} from "../domain/consoleData";
import { auditEventsToRows, hhmm } from "../domain/liveMappers";
import { EmptyState, StatusBadge } from "../components/ui";
import type { Tone } from "../domain/consoleData";
import { IconTrash } from "../components/icons";
import { createTranslator, localize } from "../i18n/i18n";
import { GhostButton, PageHeader, PageRoot, PrimaryButton, PrototypeBadge, SectionCard } from "./shared";
import { useConfirm, useToast } from "../components/providers";
import type { AuditAccessProps, AuditEventFilters } from "./contracts";
import type { AdminImpersonationSession } from "../domain/types";

const copy = {
  zh: {
    eyebrow: "运维 / 审计与权限",
    title: "审计与权限",
    subtitle: "管理员权限矩阵与完整审计轨迹 · 敏感操作全程留痕",
    matrixTitle: "角色权限矩阵",
    matrixSub: "点击单元格切换该角色的权限",
    addRole: "+ 新增角色",
    roleColHead: "角色 / 范围",
    actionHead: "操作",
    roleAddTitle: "新增角色",
    roleEditTitle: "编辑角色",
    roleName: "角色名称 *",
    roleNamePh: "如 家长支持",
    roleScope: "可访问范围",
    roleScopePh: "如 用户 / 工单",
    unspecifiedScope: "未指定范围",
    membersTitle: "管理员成员",
    membersSub: "后台账号与角色指派 · 停用即时收回访问",
    invite: "+ 邀请管理员",
    memberAddTitle: "邀请管理员",
    memberEditTitle: "编辑管理员",
    memberName: "姓名 *",
    memberNamePh: "如 周敏",
    memberEmail: "邮箱",
    memberEmailPh: "name@le.cn",
    memberRole: "角色",
    colMember: "成员",
    colRole: "角色",
    colStatus: "状态",
    colLast: "最近活跃",
    cancel: "取消",
    save: "保存",
    edit: "编辑",
    disable: "停用",
    restore: "恢复",
    remove: "移除",
    deleteRole: "删除角色",
    bannerTitle: "越权访问已拦截 · 09:18",
    bannerBodyA: "「只读分析」角色 ",
    bannerActor: "王越",
    bannerBodyB: " 尝试导出家庭活跃报表，已被策略阻断并记入审计。",
    auditTitle: "审计事件",
    colTime: "时间",
    colActor: "操作者",
    colAction: "动作",
    colTarget: "对象",
    colResult: "结果",
    sensitive: "敏感",
    confirmDeleteRoleTitle: "删除角色",
    confirmDeleteRoleBody: (name: string) => `确认删除角色「${name}」？指派到该角色的成员将失去访问权限。`,
    confirmRemoveMemberTitle: "移除管理员",
    confirmRemoveMemberBody: (name: string) => `确认移除「${name}」？该账号将立即失去后台访问权限。`,
    toastRoleSaved: (name: string) => `已保存「${name}」`,
    toastRoleAdded: (name: string) => `已新增角色「${name}」`,
    toastRoleDeleted: (name: string) => `已删除角色「${name}」`,
    toastMemberSaved: (name: string) => `已保存「${name}」`,
    toastMemberInvited: (name: string) => `已邀请「${name}」 · 待激活`,
    toastMemberDisabled: (name: string) => `已停用「${name}」`,
    toastMemberRestored: (name: string) => `已恢复「${name}」`,
    toastMemberRemoved: (name: string) => `已移除「${name}」`,
    confirm: "确认",
    cancelLabel: "取消",
    // ── Impersonation sessions ──
    impTitle: "代登录会话",
    impSub: "运维代登录到家长端的活动会话 · 仅实时数据",
    impColTenant: "租户",
    impColParent: "目标家长",
    impColStatus: "状态",
    impColReason: "原因",
    impColCreated: "开始",
    impColExpires: "到期",
    impColEnded: "结束",
    impColAction: "操作",
    impStatusActive: "进行中",
    impStatusEnded: "已结束",
    impStatusExpired: "已过期",
    impEnd: "结束会话",
    impEndReason: "控制台手动结束",
    impEmpty: "暂无代登录会话",
    impConfirmEndTitle: "结束代登录会话",
    impConfirmEndBody: (name: string) => `确认结束对「${name}」的代登录会话？该会话将立即失效。`,
    impToastEnded: "已结束代登录会话",
    impToastNoop: "该会话已结束，无需操作",
    impToastError: "结束会话失败，请重试",
    // ── Audit filters ──
    filterActorId: "操作者 ID",
    filterAction: "动作",
    filterResourceType: "对象类型",
    filterResourceId: "对象 ID",
    filterRiskLevel: "风险等级",
    filterResult: "结果",
    filterApply: "筛选",
    filterLoadMore: "加载更多",
    filterAny: "全部",
    riskLow: "低",
    riskMedium: "中",
    riskHigh: "高",
    resultSuccess: "成功",
    resultFailed: "失败",
    resultNoop: "无变更",
    auditToastError: "加载审计事件失败，请重试",
    auditEmpty: "暂无审计事件",
    // ── Honesty (no backend) ──
    matrixSubLive: "查看各角色的权限分配（原型，不会写入服务器）",
    membersSubLive: "后台账号与角色指派（原型，不会写入服务器）"
  },
  en: {
    eyebrow: "Operations / Audit & Access",
    title: "Audit & Access",
    subtitle: "Admin permission matrix and a full audit trail · every sensitive action is logged",
    matrixTitle: "Role permission matrix",
    matrixSub: "Click a cell to toggle that role's permission",
    addRole: "+ New role",
    roleColHead: "Role / Scope",
    actionHead: "Actions",
    roleAddTitle: "New role",
    roleEditTitle: "Edit role",
    roleName: "Role name *",
    roleNamePh: "e.g. Parent Support",
    roleScope: "Accessible scope",
    roleScopePh: "e.g. Users / Tickets",
    unspecifiedScope: "Unspecified",
    membersTitle: "Admin members",
    membersSub: "Console accounts and role assignment · disabling revokes access instantly",
    invite: "+ Invite admin",
    memberAddTitle: "Invite admin",
    memberEditTitle: "Edit admin",
    memberName: "Name *",
    memberNamePh: "e.g. Min Zhou",
    memberEmail: "Email",
    memberEmailPh: "name@le.cn",
    memberRole: "Role",
    colMember: "Member",
    colRole: "Role",
    colStatus: "Status",
    colLast: "Last active",
    cancel: "Cancel",
    save: "Save",
    edit: "Edit",
    disable: "Disable",
    restore: "Restore",
    remove: "Remove",
    deleteRole: "Delete role",
    bannerTitle: "Unauthorized access blocked · 09:18",
    bannerBodyA: "Read-only Analyst role ",
    bannerActor: "王越",
    bannerBodyB: " tried to export the family activity report; blocked by policy and recorded in the audit log.",
    auditTitle: "Audit events",
    colTime: "Time",
    colActor: "Actor",
    colAction: "Action",
    colTarget: "Target",
    colResult: "Result",
    sensitive: "Sensitive",
    confirmDeleteRoleTitle: "Delete role",
    confirmDeleteRoleBody: (name: string) => `Delete the role "${name}"? Members assigned to it will lose access.`,
    confirmRemoveMemberTitle: "Remove admin",
    confirmRemoveMemberBody: (name: string) => `Remove "${name}"? This account will lose console access immediately.`,
    toastRoleSaved: (name: string) => `Saved "${name}"`,
    toastRoleAdded: (name: string) => `Added role "${name}"`,
    toastRoleDeleted: (name: string) => `Deleted role "${name}"`,
    toastMemberSaved: (name: string) => `Saved "${name}"`,
    toastMemberInvited: (name: string) => `Invited "${name}" · pending`,
    toastMemberDisabled: (name: string) => `Disabled "${name}"`,
    toastMemberRestored: (name: string) => `Restored "${name}"`,
    toastMemberRemoved: (name: string) => `Removed "${name}"`,
    confirm: "Confirm",
    cancelLabel: "Cancel",
    // ── Impersonation sessions ──
    impTitle: "Impersonation sessions",
    impSub: "Active operator impersonation sessions into the parent app · live data only",
    impColTenant: "Tenant",
    impColParent: "Target parent",
    impColStatus: "Status",
    impColReason: "Reason",
    impColCreated: "Started",
    impColExpires: "Expires",
    impColEnded: "Ended",
    impColAction: "Actions",
    impStatusActive: "Active",
    impStatusEnded: "Ended",
    impStatusExpired: "Expired",
    impEnd: "End session",
    impEndReason: "ended from console",
    impEmpty: "No impersonation sessions",
    impConfirmEndTitle: "End impersonation session",
    impConfirmEndBody: (name: string) => `End the impersonation session for "${name}"? It will be invalidated immediately.`,
    impToastEnded: "Impersonation session ended",
    impToastNoop: "Session already ended; nothing to do",
    impToastError: "Failed to end session, please retry",
    // ── Audit filters ──
    filterActorId: "Actor ID",
    filterAction: "Action",
    filterResourceType: "Resource type",
    filterResourceId: "Resource ID",
    filterRiskLevel: "Risk level",
    filterResult: "Result",
    filterApply: "Apply",
    filterLoadMore: "Load more",
    filterAny: "Any",
    riskLow: "Low",
    riskMedium: "Medium",
    riskHigh: "High",
    resultSuccess: "Success",
    resultFailed: "Failed",
    resultNoop: "No change",
    auditToastError: "Failed to load audit events, please retry",
    auditEmpty: "No audit events yet",
    // ── Honesty (no backend) ──
    matrixSubLive: "View each role's permission assignment (prototype — not persisted to the server)",
    membersSubLive: "Console accounts and role assignment (prototype — not persisted to the server)"
  }
};

interface RoleRow {
  id: string;
  name: string;
  scope: string;
  grants: number[];
}

interface MemberRow extends ConsoleMember {
  // mirrors ConsoleMember shape; id/name/email/role/status/last
}

const thLeft: React.CSSProperties = { textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 18px" };
const thLeftTight: React.CSSProperties = { textAlign: "left", fontWeight: 600, fontSize: 11, padding: "9px 8px" };
const thRight: React.CSSProperties = { textAlign: "right", fontWeight: 600, fontSize: 11, padding: "9px 18px" };

const inputStyle: React.CSSProperties = {
  width: "100%",
  height: 36,
  border: "1px solid var(--border)",
  borderRadius: 8,
  background: "var(--surface)",
  padding: "0 12px",
  fontSize: 13,
  color: "var(--text)",
  outline: "none",
  fontFamily: "inherit"
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11.5,
  fontWeight: 600,
  color: "var(--text-2)",
  marginBottom: 5
};

const IMP_STATUS_TONE: Record<AdminImpersonationSession["status"], Tone> = {
  active: "success",
  ended: "neutral",
  expired: "warning"
};

interface AuditFiltersState {
  actorId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  riskLevel: string;
  result: string;
}

const EMPTY_FILTERS: AuditFiltersState = {
  actorId: "",
  action: "",
  resourceType: "",
  resourceId: "",
  riskLevel: "",
  result: ""
};

export function AuditAccess(props: AuditAccessProps) {
  const {
    language,
    tenantScope,
    dataMode,
    accessData,
    auditEventsPage,
    impersonationSessions,
    onLoadAuditEvents,
    onEndImpersonationSession
  } = props;
  const live = dataMode === "live";
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();
  const confirm = useConfirm();

  const matrix = consolePermMatrix();
  const permKeys = matrix.permKeys;

  const idCounter = useRef(0);
  const nextId = (prefix: string) => `${prefix}-${++idCounter.current}`;

  const [roles, setRoles] = useState<RoleRow[]>(() =>
    matrix.roles.map((r) => ({ id: nextId("role"), name: r.name, scope: r.scope, grants: [...r.grants] }))
  );
  const [members, setMembers] = useState<MemberRow[]>(() => consoleMembers());

  // ── Role form ──────────────────────────────────────────────
  const [roleForm, setRoleForm] = useState<{ id: string | null; name: string; scope: string } | null>(null);
  const openRoleAdd = () => setRoleForm({ id: null, name: "", scope: "" });
  const openRoleEdit = (role: RoleRow) => setRoleForm({ id: role.id, name: role.name, scope: role.scope });

  const saveRoleForm = () => {
    if (!roleForm || !roleForm.name.trim()) return;
    const name = roleForm.name.trim();
    const scope = roleForm.scope.trim();
    if (roleForm.id) {
      setRoles((prev) => prev.map((r) => (r.id === roleForm.id ? { ...r, name, scope } : r)));
      toast(c.toastRoleSaved(name));
    } else {
      setRoles((prev) => [
        ...prev,
        { id: nextId("role"), name, scope: scope || c.unspecifiedScope, grants: permKeys.map(() => 0) }
      ]);
      toast(c.toastRoleAdded(name));
    }
    setRoleForm(null);
  };

  const toggleGrant = (roleId: string, col: number) => {
    setRoles((prev) =>
      prev.map((r) =>
        r.id === roleId ? { ...r, grants: r.grants.map((g, i) => (i === col ? (g ? 0 : 1) : g)) } : r
      )
    );
  };

  const askDeleteRole = (role: RoleRow) => {
    confirm({
      title: c.confirmDeleteRoleTitle,
      body: c.confirmDeleteRoleBody(role.name),
      confirmLabel: c.confirm,
      cancelLabel: c.cancelLabel,
      onConfirm: () => {
        setRoles((prev) => prev.filter((r) => r.id !== role.id));
        toast(c.toastRoleDeleted(role.name));
      }
    });
  };

  // ── Member form ────────────────────────────────────────────
  const roleNames = roles.map((r) => r.name);
  const [memberForm, setMemberForm] = useState<{ id: string | null; name: string; email: string; role: string } | null>(
    null
  );
  const openMemberAdd = () =>
    // Default to the least-privileged role (last in the matrix) as a safe default.
    setMemberForm({ id: null, name: "", email: "", role: roleNames[roleNames.length - 1] ?? "" });
  const openMemberEdit = (member: MemberRow) =>
    setMemberForm({ id: member.id, name: member.name, email: member.email, role: member.role });

  const saveMemberForm = () => {
    if (!memberForm || !memberForm.name.trim()) return;
    const name = memberForm.name.trim();
    const email = memberForm.email.trim();
    const role = memberForm.role;
    if (memberForm.id) {
      setMembers((prev) => prev.map((m) => (m.id === memberForm.id ? { ...m, name, email, role } : m)));
      toast(c.toastMemberSaved(name));
    } else {
      setMembers((prev) => [
        ...prev,
        { id: nextId("member"), name, email: email || "—", role, status: "pending" as MemberStatusKey, last: "—" }
      ]);
      toast(c.toastMemberInvited(name));
    }
    setMemberForm(null);
  };

  const toggleMember = (member: MemberRow) => {
    const disabling = member.status !== "disabled";
    setMembers((prev) =>
      prev.map((m) =>
        m.id === member.id ? { ...m, status: (disabling ? "disabled" : "active") as MemberStatusKey } : m
      )
    );
    toast(disabling ? c.toastMemberDisabled(member.name) : c.toastMemberRestored(member.name));
  };

  const askRemoveMember = (member: MemberRow) => {
    confirm({
      title: c.confirmRemoveMemberTitle,
      body: c.confirmRemoveMemberBody(member.name),
      confirmLabel: c.confirm,
      cancelLabel: c.cancelLabel,
      onConfirm: () => {
        setMembers((prev) => prev.filter((m) => m.id !== member.id));
        toast(c.toastMemberRemoved(member.name));
      }
    });
  };

  // ── Impersonation sessions (live-only) ─────────────────────
  const impSessions = impersonationSessions?.items ?? [];
  const [endingId, setEndingId] = useState<string | null>(null);
  const impStatusLabel = (status: AdminImpersonationSession["status"]) =>
    status === "active" ? c.impStatusActive : status === "ended" ? c.impStatusEnded : c.impStatusExpired;

  const askEndSession = (session: AdminImpersonationSession) => {
    if (!onEndImpersonationSession) return;
    confirm({
      title: c.impConfirmEndTitle,
      body: c.impConfirmEndBody(session.targetParentDisplayName),
      confirmLabel: c.confirm,
      cancelLabel: c.cancelLabel,
      onConfirm: () => {
        setEndingId(session.id);
        void (async () => {
          try {
            const result = await onEndImpersonationSession(session.id, c.impEndReason);
            toast(result.actionResult.status === "noop" ? c.impToastNoop : c.impToastEnded);
          } catch {
            toast(c.impToastError);
          } finally {
            setEndingId(null);
          }
        })();
      }
    });
  };

  // ── Audit filters + pagination (live-only) ─────────────────
  const [filters, setFilters] = useState<AuditFiltersState>(EMPTY_FILTERS);
  const [auditLoading, setAuditLoading] = useState(false);

  const buildFilters = (extra?: Partial<AuditEventFilters>): AuditEventFilters => {
    const f: AuditEventFilters = { tenantScope };
    if (filters.actorId.trim()) f.actorId = filters.actorId.trim();
    if (filters.action.trim()) f.action = filters.action.trim();
    if (filters.resourceType.trim()) f.resourceType = filters.resourceType.trim();
    if (filters.resourceId.trim()) f.resourceId = filters.resourceId.trim();
    if (filters.riskLevel) f.riskLevel = filters.riskLevel;
    if (filters.result) f.result = filters.result;
    return { ...f, ...extra };
  };

  const runLoadAudit = (extra?: Partial<AuditEventFilters>) => {
    if (!onLoadAuditEvents) return;
    setAuditLoading(true);
    void (async () => {
      try {
        await onLoadAuditEvents(buildFilters(extra));
      } catch {
        toast(c.auditToastError);
      } finally {
        setAuditLoading(false);
      }
    })();
  };

  const nextCursor = auditEventsPage?.nextCursor;

  // ── Audit rows: live overlay (never fall back to mock under the live badge) ─
  const liveAuditRows = auditEventsPage?.items ?? accessData?.auditEvents ?? [];
  const auditRows: ConsoleAuditRow[] = live ? auditEventsToRows(liveAuditRows) : consoleAuditLog();

  const trashBtnStyle: React.CSSProperties = {
    width: 28,
    height: 28,
    border: "1px solid var(--border)",
    borderRadius: 7,
    background: "var(--surface)",
    color: "var(--danger)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center"
  };

  return (
    <PageRoot screen="audit">
      <PageHeader
        eyebrow={c.eyebrow}
        title={c.title}
        subtitle={c.subtitle}
        language={language}
        tenantScope={tenantScope}
      />

      {/* ── Role permission matrix ────────────────────────────── */}
      <SectionCard style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "14px 18px",
            borderBottom: "1px solid var(--border)"
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{c.matrixTitle}</span>
              {live && <PrototypeBadge language={language} />}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{live ? c.matrixSubLive : c.matrixSub}</div>
          </div>
          {!live && (
            <div style={{ marginLeft: "auto" }}>
              <GhostButton onClick={openRoleAdd} style={{ height: 32 }}>
                {c.addRole}
              </GhostButton>
            </div>
          )}
        </div>

        {roleForm && (
          <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border)", background: "var(--brand-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>
                {roleForm.id ? c.roleEditTitle : c.roleAddTitle}
              </div>
              <GhostButton onClick={() => setRoleForm(null)} style={{ marginLeft: "auto" }}>
                {c.cancel}
              </GhostButton>
            </div>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle} htmlFor="role-name">
                  {c.roleName}
                </label>
                <input
                  id="role-name"
                  className="le-input"
                  aria-label={c.roleName}
                  value={roleForm.name}
                  placeholder={c.roleNamePh}
                  onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
                  style={inputStyle}
                />
              </div>
              <div style={{ flex: 1.4 }}>
                <label style={labelStyle} htmlFor="role-scope">
                  {c.roleScope}
                </label>
                <input
                  id="role-scope"
                  className="le-input"
                  aria-label={c.roleScope}
                  value={roleForm.scope}
                  placeholder={c.roleScopePh}
                  onChange={(e) => setRoleForm({ ...roleForm, scope: e.target.value })}
                  style={inputStyle}
                />
              </div>
              <PrimaryButton onClick={saveRoleForm} disabled={!roleForm.name.trim()} style={{ height: 38 }}>
                {c.save}
              </PrimaryButton>
            </div>
          </div>
        )}

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={{ ...thLeft, padding: "10px 18px" }}>{c.roleColHead}</th>
              {permKeys.map((key) => (
                <th key={key} style={{ textAlign: "center", fontWeight: 600, fontSize: 11, padding: "10px 6px" }}>
                  {t(key)}
                </th>
              ))}
              <th style={{ ...thRight, padding: "10px 18px" }}>{c.actionHead}</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: "11px 18px" }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{role.name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>{role.scope}</div>
                </td>
                {role.grants.map((grant, col) => (
                  <td key={col} style={{ padding: "11px 6px" }}>
                    <button
                      type="button"
                      aria-label={`${role.name} · ${t(permKeys[col])}`}
                      aria-pressed={grant === 1}
                      disabled={live}
                      onClick={() => toggleGrant(role.id, col)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 24,
                        height: 24,
                        borderRadius: 6,
                        border: "none",
                        margin: "0 auto",
                        fontWeight: 700,
                        fontSize: 12,
                        cursor: live ? "default" : "pointer",
                        fontFamily: "inherit",
                        color: grant ? "var(--success)" : "var(--text-3)",
                        background: grant ? "var(--success-subtle)" : "var(--bg-subtle)"
                      }}
                    >
                      {grant ? "✓" : "—"}
                    </button>
                  </td>
                ))}
                <td style={{ padding: "11px 18px" }}>
                  {!live && (
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                      <GhostButton onClick={() => openRoleEdit(role)}>{c.edit}</GhostButton>
                      <button
                        type="button"
                        title={c.deleteRole}
                        aria-label={`${c.deleteRole} · ${role.name}`}
                        onClick={() => askDeleteRole(role)}
                        className="le-hover-danger"
                        style={trashBtnStyle}
                      >
                        <IconTrash size={14} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>

      {/* ── Admin members ─────────────────────────────────────── */}
      <SectionCard style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "14px 18px",
            borderBottom: "1px solid var(--border)"
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{c.membersTitle}</span>
              {live && <PrototypeBadge language={language} />}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{live ? c.membersSubLive : c.membersSub}</div>
          </div>
          {!live && (
            <div style={{ marginLeft: "auto" }}>
              <PrimaryButton onClick={openMemberAdd} style={{ height: 32 }}>
                {c.invite}
              </PrimaryButton>
            </div>
          )}
        </div>

        {memberForm && (
          <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border)", background: "var(--brand-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>
                {memberForm.id ? c.memberEditTitle : c.memberAddTitle}
              </div>
              <GhostButton onClick={() => setMemberForm(null)} style={{ marginLeft: "auto" }}>
                {c.cancel}
              </GhostButton>
            </div>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle} htmlFor="member-name">
                  {c.memberName}
                </label>
                <input
                  id="member-name"
                  className="le-input"
                  aria-label={c.memberName}
                  value={memberForm.name}
                  placeholder={c.memberNamePh}
                  onChange={(e) => setMemberForm({ ...memberForm, name: e.target.value })}
                  style={inputStyle}
                />
              </div>
              <div style={{ flex: 1.3 }}>
                <label style={labelStyle} htmlFor="member-email">
                  {c.memberEmail}
                </label>
                <input
                  id="member-email"
                  className="le-input"
                  aria-label={c.memberEmail}
                  value={memberForm.email}
                  placeholder={c.memberEmailPh}
                  onChange={(e) => setMemberForm({ ...memberForm, email: e.target.value })}
                  style={{ ...inputStyle, fontFamily: "var(--mono)" }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle} htmlFor="member-role">
                  {c.memberRole}
                </label>
                <select
                  id="member-role"
                  className="le-input"
                  aria-label={c.memberRole}
                  value={memberForm.role}
                  onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                  style={{ ...inputStyle, padding: "0 10px", cursor: "pointer" }}
                >
                  {roleNames.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
              <PrimaryButton onClick={saveMemberForm} disabled={!memberForm.name.trim()} style={{ height: 38 }}>
                {c.save}
              </PrimaryButton>
            </div>
          </div>
        )}

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={thLeft}>{c.colMember}</th>
              <th style={thLeftTight}>{c.colRole}</th>
              <th style={thLeftTight}>{c.colStatus}</th>
              <th style={thLeftTight}>{c.colLast}</th>
              <th style={thRight}>{c.actionHead}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => {
              const statusMeta = MEMBER_STATUS_META[member.status];
              return (
                <tr key={member.id} className="le-hover-soft" style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 18px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div
                        style={{
                          width: 30,
                          height: 30,
                          borderRadius: "50%",
                          flex: "none",
                          background: "linear-gradient(135deg,#5b76e8,#8a5be8)",
                          color: "#fff",
                          fontSize: 12,
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        {member.name.slice(0, 1)}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{member.name}</div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>
                          {member.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "10px 8px", color: "var(--text-2)" }}>{member.role}</td>
                  <td style={{ padding: "10px 8px" }}>
                    <StatusBadge tone={statusMeta.tone}>{t(statusMeta.labelKey)}</StatusBadge>
                  </td>
                  <td style={{ padding: "10px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}>
                    {member.last}
                  </td>
                  <td style={{ padding: "10px 18px" }}>
                    {!live && (
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        <GhostButton onClick={() => openMemberEdit(member)}>{c.edit}</GhostButton>
                        <GhostButton onClick={() => toggleMember(member)}>
                          {member.status === "disabled" ? c.restore : c.disable}
                        </GhostButton>
                        <button
                          type="button"
                          title={c.remove}
                          aria-label={`${c.remove} · ${member.name}`}
                          onClick={() => askRemoveMember(member)}
                          className="le-hover-danger"
                          style={trashBtnStyle}
                        >
                          <IconTrash size={14} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </SectionCard>

      {/* ── Intercepted banner (fabricated mock incident — mock mode only) ── */}
      {!live && (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          background: "var(--danger-subtle)",
          border: "1px solid color-mix(in srgb,var(--danger) 22%, transparent)",
          borderRadius: 10,
          padding: "15px 18px",
          marginBottom: 16
        }}
      >
        <div
          style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            flex: "none",
            background: "var(--surface)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <svg width="19" height="19" viewBox="0 0 22 22" fill="none" stroke="var(--danger)" strokeWidth={1.7}>
            <circle cx="11" cy="11" r="8" />
            <path d="M5.5 5.5l11 11" strokeLinecap="round" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{c.bannerTitle}</div>
          <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 2 }}>
            {c.bannerBodyA}
            <span style={{ fontFamily: "var(--mono)" }}>{c.bannerActor}</span>
            {c.bannerBodyB}
          </div>
        </div>
      </div>
      )}

      {/* ── Impersonation sessions (live-only) ────────────────── */}
      {live && (
        <SectionCard style={{ marginBottom: 16 }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.impTitle}</div>
            <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{c.impSub}</div>
          </div>
          {impSessions.length === 0 ? (
            <EmptyState>{c.impEmpty}</EmptyState>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
                  <th style={thLeft}>{c.impColTenant}</th>
                  <th style={thLeftTight}>{c.impColParent}</th>
                  <th style={thLeftTight}>{c.impColStatus}</th>
                  <th style={thLeftTight}>{c.impColReason}</th>
                  <th style={thLeftTight}>{c.impColCreated}</th>
                  <th style={thLeftTight}>{c.impColExpires}</th>
                  <th style={thLeftTight}>{c.impColEnded}</th>
                  <th style={thRight}>{c.impColAction}</th>
                </tr>
              </thead>
              <tbody>
                {impSessions.map((session) => (
                  <tr key={session.id} className="le-hover-soft" style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 18px", color: "var(--text)", fontWeight: 500 }}>
                      {session.tenantDisplayName}
                    </td>
                    <td style={{ padding: "10px 8px", color: "var(--text-2)" }}>{session.targetParentDisplayName}</td>
                    <td style={{ padding: "10px 8px" }}>
                      <StatusBadge tone={IMP_STATUS_TONE[session.status]}>{impStatusLabel(session.status)}</StatusBadge>
                    </td>
                    <td style={{ padding: "10px 8px", color: "var(--text-2)" }}>{session.reason || "—"}</td>
                    <td
                      style={{ padding: "10px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}
                    >
                      {session.createdAt ? hhmm(session.createdAt) : "—"}
                    </td>
                    <td
                      style={{ padding: "10px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}
                    >
                      {session.expiresAt ? hhmm(session.expiresAt) : "—"}
                    </td>
                    <td
                      style={{ padding: "10px 8px", fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}
                    >
                      {session.endedAt ? hhmm(session.endedAt) : "—"}
                    </td>
                    <td style={{ padding: "10px 18px" }}>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        {session.status === "active" && onEndImpersonationSession && (
                          <GhostButton
                            onClick={endingId === session.id ? undefined : () => askEndSession(session)}
                            style={endingId === session.id ? { opacity: 0.5, cursor: "default" } : undefined}
                          >
                            {c.impEnd}
                          </GhostButton>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>
      )}

      {/* ── Audit events ──────────────────────────────────────── */}
      <SectionCard>
        <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.auditTitle}</div>
            {live && onLoadAuditEvents && (
              <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                <GhostButton
                  onClick={auditLoading ? undefined : () => runLoadAudit()}
                  style={{ height: 30, ...(auditLoading ? { opacity: 0.5, cursor: "default" } : null) }}
                >
                  {c.filterApply}
                </GhostButton>
                <GhostButton
                  onClick={auditLoading || !nextCursor ? undefined : () => runLoadAudit({ cursor: nextCursor })}
                  style={{ height: 30, ...(auditLoading || !nextCursor ? { opacity: 0.5, cursor: "default" } : null) }}
                >
                  {c.filterLoadMore}
                </GhostButton>
              </div>
            )}
          </div>
          {live && onLoadAuditEvents && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginTop: 12
              }}
            >
              <input
                className="le-input"
                aria-label={c.filterActorId}
                placeholder={c.filterActorId}
                value={filters.actorId}
                onChange={(e) => setFilters({ ...filters, actorId: e.target.value })}
                style={{ ...inputStyle, width: 150, fontFamily: "var(--mono)" }}
              />
              <input
                className="le-input"
                aria-label={c.filterAction}
                placeholder={c.filterAction}
                value={filters.action}
                onChange={(e) => setFilters({ ...filters, action: e.target.value })}
                style={{ ...inputStyle, width: 150 }}
              />
              <input
                className="le-input"
                aria-label={c.filterResourceType}
                placeholder={c.filterResourceType}
                value={filters.resourceType}
                onChange={(e) => setFilters({ ...filters, resourceType: e.target.value })}
                style={{ ...inputStyle, width: 140 }}
              />
              <input
                className="le-input"
                aria-label={c.filterResourceId}
                placeholder={c.filterResourceId}
                value={filters.resourceId}
                onChange={(e) => setFilters({ ...filters, resourceId: e.target.value })}
                style={{ ...inputStyle, width: 140, fontFamily: "var(--mono)" }}
              />
              <select
                className="le-input"
                aria-label={c.filterRiskLevel}
                value={filters.riskLevel}
                onChange={(e) => setFilters({ ...filters, riskLevel: e.target.value })}
                style={{ ...inputStyle, width: 120, padding: "0 10px", cursor: "pointer" }}
              >
                <option value="">{`${c.filterRiskLevel}: ${c.filterAny}`}</option>
                <option value="low">{c.riskLow}</option>
                <option value="medium">{c.riskMedium}</option>
                <option value="high">{c.riskHigh}</option>
              </select>
              <select
                className="le-input"
                aria-label={c.filterResult}
                value={filters.result}
                onChange={(e) => setFilters({ ...filters, result: e.target.value })}
                style={{ ...inputStyle, width: 120, padding: "0 10px", cursor: "pointer" }}
              >
                <option value="">{`${c.filterResult}: ${c.filterAny}`}</option>
                <option value="success">{c.resultSuccess}</option>
                <option value="failed">{c.resultFailed}</option>
                <option value="noop">{c.resultNoop}</option>
              </select>
            </div>
          )}
        </div>
        {live && auditRows.length === 0 ? (
          <EmptyState>{c.auditEmpty}</EmptyState>
        ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", color: "var(--text-3)" }}>
              <th style={thLeft}>{c.colTime}</th>
              <th style={thLeftTight}>{c.colActor}</th>
              <th style={thLeftTight}>{c.colAction}</th>
              <th style={thLeftTight}>{c.colTarget}</th>
              <th style={thRight}>{c.colResult}</th>
            </tr>
          </thead>
          <tbody>
            {auditRows.map((row, index) => {
              const resultMeta = AUDIT_RESULT_META[row.result];
              return (
                <tr key={`${row.time}-${index}`} className="le-hover-soft" style={{ borderTop: "1px solid var(--border)" }}>
                  <td
                    style={{
                      padding: "10px 18px",
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      color: "var(--text-2)",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {row.time}
                  </td>
                  <td style={{ padding: "10px 8px" }}>
                    <span style={{ color: "var(--text)", fontWeight: 500 }}>{row.actor}</span>{" "}
                    <span style={{ fontSize: 11, color: "var(--text-3)" }}>{row.role}</span>
                  </td>
                  <td style={{ padding: "10px 8px" }}>
                    <span style={{ color: "var(--text-2)" }}>{row.action}</span>
                    {row.sensitive && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: 10,
                          fontWeight: 600,
                          color: "var(--warning)",
                          background: "var(--warning-subtle)",
                          padding: "1px 6px",
                          borderRadius: 5
                        }}
                      >
                        {c.sensitive}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "10px 8px", color: "var(--text-2)" }}>{row.target}</td>
                  <td style={{ padding: "10px 18px", textAlign: "right" }}>
                    <StatusBadge tone={resultMeta.tone}>{t(resultMeta.labelKey)}</StatusBadge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        )}
      </SectionCard>
    </PageRoot>
  );
}
