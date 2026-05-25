# LearningEnglish Admin

LearningEnglish Admin 是 Phase 1 的 production-shaped 多租户后台原型，用于验证后台信息架构、页面密度、租户范围、双语 UI 和高风险操作模式。

## 范围

- 默认使用 typed mock data，保证没有后端时页面仍可打开。
- 可通过 `VITE_ADMIN_API_BASE_URL` 接入本地 FastAPI read-only admin API。
- 首版 admin auth 使用本地 `X-Admin-Token` 静态 token；生产级 admin session / role / permission 仍在后续阶段。
- 无 production mutation。
- 验证 `Platform -> Tenant -> ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob -> LearningAsset -> ReviewTask / PracticeSession / SpeakingAttempt -> WeeklyReport` 的后台运营视角。
- 支持中文 / English UI 切换。
- API paths、env keys、model names、task names、permission keys 保持 English。

## 命令

```bash
make admin-install
make admin-dev
make admin-dev-live
make admin-test
make admin-build
```

`make admin-dev-live` 默认连接 `http://127.0.0.1:8000/v1/admin/dashboard?tenant_scope=all`，并使用 `ADMIN_API_TOKEN=local-admin-token`。如需改地址：

```bash
ADMIN_API_BASE_URL=http://127.0.0.1:8000 ADMIN_API_TOKEN=local-admin-token make admin-dev-live
```

## 已实现页面

- Command Center
- Tenant Detail
- Content Pipeline

## 目标态占位页面

- Users & Children
- Learning Assets
- Learning Outcomes
- Provider Ops
- Infrastructure
- Audit & Access
- Developer API

这些页面在 Phase 1 只保留导航入口和租户范围上下文；当前已接入最小 read-only dashboard API，后续仍需要补齐独立 admin session、权限模型、审计链路和受控 mutation 后才能作为生产后台能力使用。
