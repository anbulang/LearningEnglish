# LearningEnglish MVP Readiness Checklist

更新时间：2026-06-12

## 目的

这份 checklist 只保留当前 MVP 是否具备“可运行、可复查、可交付收口”的判断入口，不再把多轮历史验收日志直接当成当前结论。

与 readiness 直接相关的真相源优先级：

1. 代码与测试目录
2. `Makefile`
3. `README.md`
4. `docs/harness/*`
5. `services/api/README.md`、`services/workers/README.md`、`apps/mobile/README.md`、`apps/admin/README.md`

## 当前 readiness 判断

### A. 主链能力

- [x] 家长端主链已在当前代码边界内闭环：登录、绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练、独立报告页。
- [x] API 当前仍提供主链所需的 parent routes。
- [x] worker 当前仍提供讲义处理、学习资产媒体补齐、speaking 评分与周报聚合任务。
- [x] 移动端 README 与目录结构仍能对应到主链页面与状态流转。

### B. 默认真实 provider 路径

- [x] 本地示例环境默认 `AI_PROVIDER=qwen`。
- [x] 学习资产媒体默认 `MEDIA_PROVIDER=real` + `MEDIA_IMAGE_PROVIDER=dashscope` + `MEDIA_TTS_PROVIDER=dashscope`。
- [x] speaking 默认 `SPEECH_PROVIDER=dashscope` + `SPEECH_ASSESSMENT_PROVIDER=dashscope`。
- [x] 文档已经明确：真实 provider 验收需要单独区分于 stub/mock 回归。

### C. Admin / 运维后台

- [x] `/v1/admin/dashboard`
- [x] `/v1/admin/access`
- [x] `/v1/admin/audit-events`
- [x] `/v1/admin/tenants/{tenant_id}`
- [x] `/v1/admin/operations`
- [x] `/v1/admin/impersonation-sessions`
- [x] `apps/admin` 当前已实现 `Command Center`、`Tenant Detail`、`Content Pipeline`、`Provider Ops`、`Audit & Access` 五个业务页面。
- [ ] 完整 admin login/SSO、DB-backed role mutation、permission mutation 和 broker 级运维观测仍不属于当前已完成能力。

### D. Harness / 文档入口

- [x] `README.md` 提供项目入口和常用命令。
- [x] `docs/project/2026-06-12-status-and-todo.md` 提供当前项目级快照。
- [x] `docs/harness/device-regression-runbook.md` 提供 `R0/R1/R2/R3` 真机回归分级。
- [x] `docs/harness/provider-readiness-runbook.md` 提供真实 provider 运行入口。
- [x] `docs/harness/evidence-archive-policy.md` 说明 evidence 归档规则。
- [x] `make harness-evidence-index` 仍是统一索引入口。

## 当前已确认的事实

- 当前仓库已经不是只到“上传识别”的半链路，而是覆盖上传、AI 校对、课程详情、复习、speaking 和报告的完整 MVP 主链。
- 当前默认真实 provider 主线是 `qwen + DashScope media + DashScope speech`。
- `apps/admin` 当前是可 live 读取、可执行部分受控 mutation 的运营控制台原型，不应再写成只有 dashboard/access 的旧状态。
- `IOS_API_BASE_URL` 默认仍是 `http://127.0.0.1:8000/v1`；真机导包时必须显式覆盖当前局域网地址。
- `HN-019` 真机主链 harness 已有独立脚本和 focused test；当前缺的不是入口存在性，而是截图清单和团队执行纪律。
- `HN-020` 已定义家长试用验收清单和修复批次；当前缺的是用真实家长或非技术试用者跑一轮并归档证据。

## 当前未在本轮重新验证的事项

以下内容在仓库文档或 `dist/harness/` 中有历史证据，但本轮没有重新执行命令或真机复验：

- `make mobile-ios-ipa` 的当前机器可用性
- `HN-017` 真机 speaking 复跑
- `HN-019` 真机主链复跑
- `make harness-doubao-smoke` 的当前网络可用性
- Android `make mobile-apk` 的当前环境结论

这些事项应继续保留为“已有历史证据”，而不是写成“本轮已验证通过”。

## 当前 blocker / gap

### 1. 交付链收口不足

- Android 是否承诺分发、如何分发，当前仍没有项目级定论。
- iOS 仍主要依赖 development provisioning / UDID 管理；是否转 TestFlight 仍待决定。
- 非开发成员需要的最短交付步骤仍分散在多份文档。

### 2. 真机回归执行化不足

- `R0/R1/R2/R3` 已有定义，但 summary 模板、截图清单和复跑节奏尚未完全固化。
- `HN-019` harness 已把主链 summary 字段收敛到固定 JSON，但截图补存和目录级说明还未完全统一。
- `dist/harness/evidence-index.json` 已可生成，但不同 `HN-*` summary 仍存在新旧字段风格混用。

### 3. 文档仍需持续减重

- 历史验收记录仍容易被误读成当前 readiness 结论。
- 当前仍需持续把长文改成“当前入口 / 当前结论 / 历史 evidence”结构。

### 4. 家长试用闭环未执行

- `HN-020` 已有验收入口，但还没有一轮真实家长或非技术试用者的 `dist/harness/HN-020/` 证据。
- 当前仍需要把上传、AI 校对、课程详情、复习和报告页的可用性问题按 `P0/P1/P2` 和 Batch 0-4 记录下来。

## 建议作为当前 gate 的最小命令

### 仓库级

```bash
make api-test
make worker-test
make mobile-test
make mobile-analyze
make admin-test
make admin-build
make harness-evidence-index
git diff --check
```

### 家长试用级

```bash
# 先按 docs/harness/non-technical-pilot-guide.md 准备设备和服务
# 再生成 HN-020 记录模板并按 docs/harness/hn020-parent-pilot-acceptance.md 记录试用结果
make harness-hn020-parent-pilot-template
```

### 真机级

```bash
LAN_IP=<current-host-ip>
make mobile-ios-ipa IOS_API_BASE_URL="http://${LAN_IP}:8000/v1"
API_BASE_URL="http://${LAN_IP}:8000/v1" \
SOURCE_IMAGE_URLS=https://example.com/page-1.jpg,https://example.com/page-2.jpg \
make harness-hn019-real-device-main-chain
```

### 真实 provider 级

```bash
set -a; source infra/.env; set +a
services/api/.venv/bin/python scripts/harness/run_hn016a_dashscope_provider_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn016a_worker_dashscope_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_speech_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py
```

## 结论

- 当前 MVP 的核心主链已经存在，真正缺的是交付链、真机回归和 evidence 模板的执行化。
- 这份 checklist 应继续用于回答“现在能不能复查、差在哪里、下一个 gate 是什么”，而不是继续累积历史运行流水账。
