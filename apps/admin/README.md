# LearningEnglish 运维控制台 (Admin)

面向多租户运营的 React/Vite 后台，从 Claude Design「LE 运维控制台」重建为 **10 屏**控制台。
采用 **mock-first + 真实 `/v1/admin` 叠加**：默认用设计稿种子数据渲染，设置
`VITE_ADMIN_API_BASE_URL` 后 `dataMode` 翻转为 `live`，把真实后端数据映射进同一套视图模型。
明 / 暗双主题、中英双语（共享词汇走 `i18n/messages.ts`，每屏文案走本地 `copy` 对象）。

## 架构

- **mock 模式**（无 `VITE_ADMIN_API_BASE_URL`）：每屏用 `domain/consoleData.ts` 种子 1:1 还原设计。
- **live 模式**：`App.tsx` 引导加载 `/v1/admin/dashboard` 成功后翻转 `dataMode`，各屏按需拉取并经
  `domain/liveMappers.ts` 映射；live prop 为空时回退到对应空态（不在「真实 API」徽标下展示编造数据）。
- **诚实化**：后端没有接口的控件在 live 模式一律**禁用并标注「原型」徽标**（mock 模式仍可演示）；
  纯原型屏（成本/Token、学习结果）在 live 顶部显示「示例数据」横幅。
- admin 鉴权为本地静态 `X-Admin-Token`；API paths / env keys / model / task / permission 保持英文。

## 命令

```bash
make admin-install
make admin-dev        # mock 数据，默认浅色，可切深浅 / 中英
make admin-dev-live   # 接本地 /v1/admin
make admin-test       # vitest
make admin-build      # tsc -b && vite build
```

前端环境变量：

- `VITE_ADMIN_API_BASE_URL`：FastAPI admin API base URL，例如 `http://127.0.0.1:8000`。
- `VITE_ADMIN_API_TOKEN`：发送到后端 `X-Admin-Token` 的 token；本地默认 `local-admin-token`。

`make admin-dev-live` 默认连本地 admin 接口并使用 `ADMIN_API_TOKEN=local-admin-token`，改地址：

```bash
ADMIN_API_BASE_URL=http://127.0.0.1:8000 ADMIN_API_TOKEN=local-admin-token make admin-dev-live
```

## 屏与后端对接

**已接真后端**（读 + 部分写，live 模式生效）：

- **指挥中心**：`/v1/admin/operations` → 漏斗 / 异常 / KPI 网格 / Provider 面板；带 reason 的
  重试 / 归档受控 mutation（按权限放开）。
- **租户管理**：`/v1/admin/dashboard` → 租户列表；**模块开关** `POST /v1/admin/tenants/{id}/modules/{key}`、
  **租户详情抽屉** `GET /v1/admin/tenants/{id}`。
- **内容管道**：dashboard materials → 任务列表；重试 `POST /v1/admin/material-jobs/{id}/retry`。
- **学习资产**：`GET /v1/admin/learning-assets` → 扁平资产网格（真实媒体状态）。
- **用户与家庭**：`GET /v1/admin/users` → 家庭/孩子；发起代登录 `POST /v1/admin/impersonation-sessions`。
- **Provider 运维**：每租户策略覆写 `POST /v1/admin/providers/policies`。
- **基础设施**：`/v1/admin/operations` 运行时快照。
- **审计与权限**：`/v1/admin/audit-events`（筛选 / cursor 翻页）、`/v1/admin/impersonation-sessions`
  列表与结束会话。

**纯原型**（后端暂无接口，live 模式禁用 + 标注）：成本与 Token、学习结果、角色权限矩阵 + 成员 CRUD、
Provider 连接器 CRUD / 连通自检、租户增 / 改 / 停用 / 删除、单资产重生成 / 编辑 / 删除，以及拼读
课程带 / Scope-and-Sequence / 已就绪趋势线（无时序来源）。

## 验证

```bash
cd apps/admin && npm run build    # tsc -b + vite build
cd apps/admin && npx vitest run   # mock 导航/交互 + live 接线回合测试
```
