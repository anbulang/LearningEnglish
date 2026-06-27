import { useMemo, useState } from "react";
import {
  FAMILY_STATUS_META,
  consoleFamilies,
  type ConsoleChild,
  type ConsoleFamily
} from "../domain/consoleData";
import { usersToFamilies } from "../domain/liveMappers";
import { StatusBadge } from "../components/ui";
import { useConfirm, useToast } from "../components/providers";
import { createTranslator, localize } from "../i18n/i18n";
import { PageHeader, PageRoot } from "./shared";
import type { UsersChildrenProps } from "./contracts";

const copy = {
  zh: {
    eyebrow: "内容 / 用户与家庭",
    title: "用户与家庭",
    subtitle: "家长账号与名下孩子拼读档案 · 代登录等敏感操作需二次确认并审计",
    searchPlaceholder: "搜索手机号 / 家庭",
    searchAria: "搜索家庭",
    reg: "注册时间",
    kids: "名下孩子",
    usage: "知识包/复习/发音",
    kidUnit: "名",
    materialsUnit: "讲义",
    imperTitle: "代登录排查 · Impersonation",
    imperDescLead: "以该家长身份只读进入 App 排查问题 · ",
    imperDescWarn: "受审计的敏感操作",
    imperBtn: "发起代登录",
    childrenTitle: "名下孩子档案",
    phonics: "拼读进度",
    lastActive: "最近活跃 · ",
    confirmTitle: "确认发起代登录？",
    confirmLead: "你将以 ",
    confirmMid: " 的身份只读进入家长 App。此操作属于",
    confirmWarn: "受审计的敏感操作",
    confirmTail: "，将完整记录到审计日志。",
    confirmOk: "确认并记录",
    confirmCancel: "取消",
    imperReason: "运维台只读排查",
    toastOk: "代登录会话已开启并记入审计"
  },
  en: {
    eyebrow: "Content / Users & Families",
    title: "Users & Families",
    subtitle:
      "Parent accounts and their children's phonics profiles · impersonation and other sensitive actions require confirmation and are audited",
    searchPlaceholder: "Search phone / family",
    searchAria: "Search families",
    reg: "Registered",
    kids: "Children",
    usage: "Packs / Reviews / Pronunciation",
    kidUnit: "kids",
    materialsUnit: "materials",
    imperTitle: "Impersonation triage · 代登录",
    imperDescLead: "Enter the parent App read-only as this parent to triage issues · ",
    imperDescWarn: "audited sensitive action",
    imperBtn: "Start impersonation",
    childrenTitle: "Children profiles",
    phonics: "Phonics progress",
    lastActive: "Last active · ",
    confirmTitle: "Start impersonation?",
    confirmLead: "You will enter the parent App read-only as ",
    confirmMid: ". This is an ",
    confirmWarn: "audited sensitive action",
    confirmTail: " and will be fully recorded to the audit log.",
    confirmOk: "Confirm & record",
    confirmCancel: "Cancel",
    imperReason: "console read-only triage",
    toastOk: "Impersonation session opened and recorded to audit"
  }
};

function childBarColor(progress: number): string {
  if (progress > 70) return "var(--success)";
  if (progress > 40) return "var(--brand)";
  return "var(--warning)";
}

export function UsersChildren({ language, tenantScope, dataMode, liveUsers, onStartImpersonation }: UsersChildrenProps) {
  const t = createTranslator(language);
  const c = localize(language, copy);
  const toast = useToast();
  const confirm = useConfirm();

  const families = useMemo<ConsoleFamily[]>(() => {
    const source = dataMode === "live" && liveUsers ? usersToFamilies(liveUsers) : consoleFamilies();
    return tenantScope === "all" ? source : source.filter((family) => family.tenant === tenantScope);
  }, [dataMode, liveUsers, tenantScope]);

  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const query = search.trim().toLowerCase();
  const listFamilies = query
    ? families.filter((family) => family.name.toLowerCase().includes(query) || family.phone.toLowerCase().includes(query))
    : families;

  const selected: ConsoleFamily | undefined = families.find((family) => family.id === selectedId) ?? families[0];

  function startImpersonation(family: ConsoleFamily) {
    confirm({
      title: c.confirmTitle,
      body: (
        <>
          {c.confirmLead}
          <span style={{ fontWeight: 600, color: "var(--text)" }}>
            {family.name}（{family.phone}）
          </span>
          {c.confirmMid}
          <span style={{ color: "var(--danger)", fontWeight: 600 }}>{c.confirmWarn}</span>
          {c.confirmTail}
        </>
      ),
      confirmLabel: c.confirmOk,
      cancelLabel: c.confirmCancel,
      onConfirm: () => {
        if (onStartImpersonation) {
          onStartImpersonation({ tenantId: family.tenant, targetParentId: family.parentId, reason: c.imperReason }).catch(
            (error: unknown) => toast(error instanceof Error ? error.message : String(error))
          );
        } else {
          toast(c.toastOk);
        }
      }
    });
  }

  return (
    <PageRoot screen="users">
      <PageHeader eyebrow={c.eyebrow} title={c.title} subtitle={c.subtitle} language={language} tenantScope={tenantScope} />

      <div style={{ display: "grid", gridTemplateColumns: "400px 1fr", gap: 16, alignItems: "start" }}>
        {/* LEFT — family list */}
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            boxShadow: "var(--shadow-sm)",
            overflow: "hidden"
          }}
        >
          <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
            <input
              className="le-input"
              aria-label={c.searchAria}
              placeholder={c.searchPlaceholder}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{
                width: "100%",
                height: 32,
                border: "1px solid var(--border)",
                borderRadius: 7,
                background: "var(--bg-subtle)",
                padding: "0 12px",
                fontSize: 12.5,
                color: "var(--text)",
                outline: "none",
                fontFamily: "inherit",
                boxSizing: "border-box"
              }}
            />
          </div>
          <div>
            {listFamilies.map((family) => {
              const meta = FAMILY_STATUS_META[family.status];
              const active = selected?.id === family.id;
              return (
                <button
                  key={family.id}
                  type="button"
                  onClick={() => setSelectedId(family.id)}
                  className={active ? undefined : "le-hover-soft"}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    display: "flex",
                    alignItems: "center",
                    gap: 11,
                    padding: "12px 14px",
                    borderBottom: "1px solid var(--border)",
                    cursor: "pointer",
                    fontFamily: "inherit",
                    border: "none",
                    background: active ? "var(--brand-subtle)" : "transparent"
                  }}
                >
                  <span
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 9,
                      flex: "none",
                      background: "var(--bg-subtle)",
                      border: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-2)"
                    }}
                  >
                    {family.name.slice(0, 1)}
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{family.name}</span>
                    <span style={{ display: "block", fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)", marginTop: 1 }}>
                      {family.phone}
                    </span>
                  </span>
                  <StatusBadge tone={meta.tone}>{t(meta.labelKey)}</StatusBadge>
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT — identity + children */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {selected && (
            <>
              {/* Identity card */}
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  boxShadow: "var(--shadow-sm)",
                  padding: 18
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 12,
                      flex: "none",
                      background: "var(--brand-subtle)",
                      border: "1px solid var(--brand-border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 19,
                      fontWeight: 700,
                      color: "var(--brand)"
                    }}
                  >
                    {selected.name.slice(0, 1)}
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                      <span style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>{selected.name}</span>
                      <StatusBadge tone={FAMILY_STATUS_META[selected.status].tone}>
                        {t(FAMILY_STATUS_META[selected.status].labelKey)}
                      </StatusBadge>
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-3)", marginTop: 3 }}>
                      {selected.id} · {selected.phone} · {selected.tenant}
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3,1fr)",
                    gap: 1,
                    background: "var(--border)",
                    border: "1px solid var(--border)",
                    borderRadius: 9,
                    overflow: "hidden",
                    marginTop: 16
                  }}
                >
                  <div style={{ background: "var(--surface)", padding: "11px 13px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.reg}</div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--text)", marginTop: 3 }}>{selected.reg}</div>
                  </div>
                  <div style={{ background: "var(--surface)", padding: "11px 13px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.kids}</div>
                    <div style={{ fontSize: 12.5, color: "var(--text)", marginTop: 3 }}>
                      {selected.children.length} {c.kidUnit}
                    </div>
                  </div>
                  <div style={{ background: "var(--surface)", padding: "11px 13px" }}>
                    <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.usage}</div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--text)", marginTop: 3 }}>{selected.usage}</div>
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 16,
                    border: "1px dashed var(--border-strong)",
                    borderRadius: 9,
                    padding: "13px 15px",
                    display: "flex",
                    alignItems: "center",
                    gap: 13
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{c.imperTitle}</div>
                    <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>
                      {c.imperDescLead}
                      <span style={{ color: "var(--warning)", fontWeight: 600 }}>{c.imperDescWarn}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => startImpersonation(selected)}
                    className="le-hover-danger"
                    style={{
                      height: 32,
                      padding: "0 14px",
                      border: "1px solid var(--danger)",
                      borderRadius: 7,
                      background: "transparent",
                      color: "var(--danger)",
                      fontSize: 12.5,
                      fontWeight: 600,
                      cursor: "pointer",
                      fontFamily: "inherit",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {c.imperBtn}
                  </button>
                </div>
              </div>

              {/* Children profiles */}
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  boxShadow: "var(--shadow-sm)",
                  padding: 18
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>{c.childrenTitle}</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
                  {selected.children.map((child: ConsoleChild, index) => (
                    <div
                      key={`${child.name}-${index}`}
                      style={{ border: "1px solid var(--border)", borderRadius: 9, padding: 14 }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 11 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: "50%",
                            flex: "none",
                            background: "linear-gradient(135deg,#6b8cff,#9b6bff)",
                            color: "#fff",
                            fontSize: 13,
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          {child.name.slice(0, 1)}
                        </div>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{child.name}</div>
                          <div style={{ fontSize: 11, color: "var(--text-3)" }}>{child.grade}</div>
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          fontSize: 11,
                          color: "var(--text-3)",
                          marginBottom: 5
                        }}
                      >
                        <span>{c.phonics}</span>
                        <span style={{ fontFamily: "var(--mono)", color: "var(--text-2)", fontWeight: 600 }}>{child.progress}%</span>
                      </div>
                      <div style={{ height: 6, borderRadius: 4, background: "var(--bg-subtle)", overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${child.progress}%`,
                            background: childBarColor(child.progress),
                            borderRadius: 4
                          }}
                        />
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 10 }}>
                        {c.lastActive}
                        {child.lastMaterials != null ? `${child.lastMaterials} ${c.materialsUnit}` : child.last}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </PageRoot>
  );
}
