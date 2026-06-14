# LearningEnglish Admin

LearningEnglish Admin 是面向多租户运营场景的后台原型。当前已进入 Phase 3：在保留 LearningEnglish 温暖品牌识别的前提下，开始消费后端 admin operations、tenant detail、audit events 和 impersonation session 合同。

## 范围

- 默认使用 typed mock data，保证没有后端时页面仍可打开。
- 可通过 `VITE_ADMIN_API_BASE_URL` 和 `VITE_ADMIN_API_TOKEN` 接入本地 FastAPI admin API；live load 失败时页面回退到 mock 或已加载的本地 state，不阻断 UI 打开。
- 首版 admin auth 使用本地 `X-Admin-Token` 静态 token；当前已落库管理员身份和 read audit event，生产级 admin session / role mutation 仍在后续阶段。
- 已支持首批受控 mutation：Content Pipeline live mode 可带 reason 重试 material job 或归档 material，Provider Ops live mode 可写入 tenant provider policy override，Tenant Detail live mode 可切换 tenant module access，Audit & Access live mode 可创建和结束受监督 impersonation session；所有变更都会写入 `AuditEvent`。
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

前端直接使用的环境变量：

- `VITE_ADMIN_API_BASE_URL`：FastAPI admin API base URL，例如 `http://127.0.0.1:8000`。
- `VITE_ADMIN_API_TOKEN`：发送到后端 `X-Admin-Token` 的 admin token；本地默认可使用 `local-admin-token`。

`make admin-dev-live` 默认连接本地 `/v1/admin/dashboard`、`/v1/admin/access`、`/v1/admin/operations`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/audit-events` 和 `/v1/admin/impersonation-sessions`，并使用 `ADMIN_API_TOKEN=local-admin-token`。如需改地址：

```bash
ADMIN_API_BASE_URL=http://127.0.0.1:8000 ADMIN_API_TOKEN=local-admin-token make admin-dev-live
```

## 已实现页面

- Command Center：Phase 3 已接入 `/v1/admin/operations` 的 `issues`、severity、recommended action 和 action drawer。
- Tenant Detail：Phase 3 已接入 `/v1/admin/tenants/{tenant_id}` 的 children、materials、weekly reports、speaking attempts、module settings 和 risk summary。
- Content Pipeline
- Provider Ops
- Audit & Access：Phase 3 已接入 `/v1/admin/audit-events` filters / cursor pagination、`/v1/admin/impersonation-sessions` 列表和 end flow。

## 当前仍是占位的页面

- Users & Children
- Learning Assets
- Learning Outcomes
- Infrastructure
- Developer API

这些页面当前只保留导航入口和租户范围上下文。后续仍需要补齐独立 admin session、SSO / magic link、DB-backed role mutation、权限变更、saved filters、bulk actions、audit export 和真实 worker broker introspection 后才能作为完整生产后台能力使用。

## 验证

```bash
cd apps/admin && npm test
cd apps/admin && npm run build
```
