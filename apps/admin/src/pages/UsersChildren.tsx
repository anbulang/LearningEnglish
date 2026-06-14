import { useMemo, useState } from "react";
import { StatusChip } from "../components/ui";
import type { AdminUserAccount, Language, Tenant, TenantScope } from "../domain/types";

interface UsersChildrenProps {
  language: Language;
  tenantScope: TenantScope;
  tenants: Tenant[];
  users: AdminUserAccount[];
  dataMode?: "mock" | "live";
}

export function UsersChildren({ language, tenantScope, tenants, users, dataMode = "mock" }: UsersChildrenProps) {
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null);
  const copy = language === "zh" ? zhCopy : enCopy;
  const tenantNameById = useMemo(() => new Map(tenants.map((tenant) => [tenant.id, tenant.name])), [tenants]);
  const scopedUsers = useMemo(
    () => (tenantScope === "all" ? users : users.filter((user) => user.tenantId === tenantScope)),
    [users, tenantScope]
  );
  const levelOptions = useMemo(
    () => ["all", ...Array.from(new Set(scopedUsers.map((user) => user.level))).sort()],
    [scopedUsers]
  );
  const filteredUsers = useMemo(
    () => (levelFilter === "all" ? scopedUsers : scopedUsers.filter((user) => user.level === levelFilter)),
    [scopedUsers, levelFilter]
  );
  const selectedUser = filteredUsers.find((user) => user.childId === selectedChildId) ?? filteredUsers[0] ?? null;

  function handleLevelFilterChange(value: string) {
    setLevelFilter(value);
    setSelectedChildId(null);
  }

  return (
    <div className="page-grid">
      <section className="page-header wide">
        <p className="eyebrow">ParentAccount / ChildProfile</p>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </section>

      <section className="surface wide filter-bar" aria-label={copy.filters}>
        <label>
          <span>{copy.level}</span>
          <select aria-label={copy.levelFilter} value={levelFilter} onChange={(event) => handleLevelFilterChange(event.target.value)}>
            {levelOptions.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? copy.all : option}
              </option>
            ))}
          </select>
        </label>
        <span className="filter-summary">{dataMode === "live" ? copy.liveHint : copy.mockHint}</span>
      </section>

      <section className="surface table-panel span-8">
        <div className="section-title">
          <div>
            <h2>{copy.roster}</h2>
            <p>
              {filteredUsers.length} / {scopedUsers.length} {copy.childrenInScope}
            </p>
          </div>
        </div>
        {filteredUsers.length > 0 ? (
          <div className="table-scroll">
            <table className="pipeline-table">
              <thead>
                <tr>
                  <th>{copy.tenant}</th>
                  <th>{copy.parent}</th>
                  <th>{copy.child}</th>
                  <th>{copy.age}</th>
                  <th>{copy.level}</th>
                  <th>{copy.materials}</th>
                  <th>{copy.speaking}</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.childId} className={selectedUser?.childId === user.childId ? "selected-row" : ""}>
                    <td>{tenantNameById.get(user.tenantId) ?? user.tenantId}</td>
                    <td>{user.parentName}</td>
                    <td>
                      <button
                        type="button"
                        className="table-link-button"
                        aria-label={`${copy.inspect} ${user.childName}`}
                        onClick={() => setSelectedChildId(user.childId)}
                      >
                        {user.childName}
                      </button>
                      <small>{user.childId}</small>
                    </td>
                    <td>{user.age}</td>
                    <td>{user.level}</td>
                    <td>{user.materialsCount}</td>
                    <td>
                      <StatusChip tone={user.speakingAttempts > 0 ? "success" : "neutral"}>{user.speakingAttempts}</StatusChip>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pipeline-empty">
            <strong>{copy.emptyFiltered}</strong>
            <p>{copy.emptyFilteredDetail}</p>
          </div>
        )}
      </section>

      <aside className="surface span-4 inspector" role="complementary" aria-label={copy.inspectorAria}>
        <div className="section-title">
          <div>
            <h2>{copy.inspector}</h2>
            <p>{selectedUser ? copy.selectedHint : copy.noSelection}</p>
          </div>
        </div>
        {selectedUser ? (
          <ChildInspector user={selectedUser} tenantName={tenantNameById.get(selectedUser.tenantId)} copy={copy} />
        ) : (
          <div className="pipeline-empty inspector-empty">
            <strong>{copy.emptyInspector}</strong>
            <p>{copy.emptyInspectorDetail}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function ChildInspector({
  user,
  tenantName,
  copy
}: {
  user: AdminUserAccount;
  tenantName: string | undefined;
  copy: typeof zhCopy;
}) {
  return (
    <>
      <h3>{copy.inspectorDetail}</h3>
      <dl className="detail-list compact">
        <dt>{copy.child}</dt>
        <dd>
          {user.childName}
          <small>{user.childId}</small>
        </dd>
        <dt>{copy.parentChild}</dt>
        <dd>
          {user.parentName} / {tenantName ?? user.tenantId}
        </dd>
        <dt>{copy.age}</dt>
        <dd>{user.age}</dd>
        <dt>{copy.level}</dt>
        <dd>{user.level}</dd>
        <dt>{copy.learningGoal}</dt>
        <dd>{user.learningGoal || copy.none}</dd>
        <dt>{copy.reviewMinutes}</dt>
        <dd>{user.preferredReviewDurationMinutes} min</dd>
        <dt>{copy.parentNotes}</dt>
        <dd>{user.parentNotes || copy.none}</dd>
        <dt>{copy.materials}</dt>
        <dd>{user.materialsCount}</dd>
        <dt>{copy.speaking}</dt>
        <dd>{user.speakingAttempts}</dd>
        <dt>{copy.weeklyReport}</dt>
        <dd>{user.latestWeeklyReportId || copy.none}</dd>
      </dl>
    </>
  );
}

const zhCopy = {
  title: "用户与孩子",
  subtitle: "按租户浏览家长账户下的孩子档案,以及讲义数量与口语练习等快速统计。",
  filters: "用户筛选",
  level: "级别",
  levelFilter: "级别筛选",
  all: "全部",
  liveHint: "live 数据:来自 /v1/admin/users。",
  mockHint: "mock 数据:未连接 live admin API。",
  roster: "孩子名册",
  childrenInScope: "个孩子",
  tenant: "租户",
  parent: "家长",
  child: "孩子",
  age: "年龄",
  materials: "讲义数",
  speaking: "口语练习",
  inspect: "查看",
  inspector: "当前选中",
  inspectorDetail: "孩子详情",
  inspectorAria: "选中孩子详情",
  selectedHint: "查看下方孩子档案明细",
  noSelection: "未选择孩子",
  parentChild: "家长 / 租户",
  learningGoal: "学习目标",
  reviewMinutes: "偏好复习时长",
  parentNotes: "家长备注",
  weeklyReport: "最近周报",
  none: "无",
  emptyFiltered: "没有符合当前筛选的孩子。",
  emptyFilteredDetail: "切换级别或租户范围查看其他孩子。",
  emptyInspector: "当前筛选没有可检查孩子。",
  emptyInspectorDetail: "Inspector 会在有结果时显示孩子档案与统计。"
};

const enCopy: typeof zhCopy = {
  title: "Users & Children",
  subtitle: "Browse tenant-scoped child profiles under parent accounts, with worksheet counts and speaking-practice stats.",
  filters: "User filters",
  level: "Level",
  levelFilter: "Level filter",
  all: "All",
  liveHint: "Live data from /v1/admin/users.",
  mockHint: "Mock data: live admin API not connected.",
  roster: "Children roster",
  childrenInScope: "children in scope",
  tenant: "Tenant",
  parent: "Parent",
  child: "Child",
  age: "Age",
  materials: "Worksheets",
  speaking: "Speaking",
  inspect: "Inspect",
  inspector: "Selected child",
  inspectorDetail: "Child detail",
  inspectorAria: "Selected child inspector",
  selectedHint: "See child profile detail below",
  noSelection: "No child selected",
  parentChild: "Parent / tenant",
  learningGoal: "Learning goal",
  reviewMinutes: "Preferred review duration",
  parentNotes: "Parent notes",
  weeklyReport: "Latest weekly report",
  none: "None",
  emptyFiltered: "No children match this filter.",
  emptyFilteredDetail: "Change level or tenant scope to inspect other children.",
  emptyInspector: "No child is available for inspection.",
  emptyInspectorDetail: "The inspector shows the child profile and stats when the filter has results."
};
