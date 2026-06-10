# LearningEnglish 项目进度与 ToDo（2026-06-10）

## 目的

这份快照只基于当前仓库可直接核对的真相源整理：

- 代码目录与路由
- `Makefile`
- `docs/harness/*`
- `docs/architecture/*`
- `services/api/README.md`
- `services/workers/README.md`
- `apps/mobile/README.md`
- `apps/admin/README.md`
- `infra/README.md`

它回答四个问题：

1. 当前项目已经做到哪里。
2. 哪些结论能被当前仓库直接证明。
3. 哪些仍未被当前回合重新验证，或仍存在明确缺口。
4. 接下来该按什么顺序推进。

## 当前结论

LearningEnglish 当前处于 **家庭英语学习主链已经闭环、默认真实 provider 路径已确定、admin 后台原型已接入主要 live read 与受控 mutation、HN-019 真机 harness 已经脚本化，但跨设备交付、真机回归执行纪律与文档入口压缩仍待收口** 的阶段。

一句话概括：

> 当前最重要的工作不是再加一批新功能，而是把已经存在的主链、交付链和运维入口收敛成团队可重复执行的标准流程。

## 项目进度

### 1. 用户主链：已闭环

- 家长登录、手机号绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练和独立报告页都已落到当前代码目录。
- API 已包含 `children`、`materials`、`material-jobs`、`review-tasks`、`practice-sessions`、`speaking-attempts`、`reports/weekly` 等主链路由。
- worker 已实现 `materials.process_material_job`、`materials.process_learning_asset_media`、`speaking.score_attempt` 和 `reporting.aggregate_weekly_report`。
- 移动端 README 与代码目录都表明主链页面已覆盖登录、资料库、上传、AI 校对、课程详情、复习、报告和个人页。

### 2. AI / Provider：默认真实路径已明确

- `infra/env/local.example.env` 当前默认 `AI_PROVIDER=qwen`。
- 学习资产媒体默认是 `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`。
- 口语评分默认是 `SPEECH_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`。
- `doubao`、OpenAI 媒体路径仍保留，但都不是当前默认主线。

### 3. Admin / 运维后台：已进入 live 原型阶段

- 后端已提供 `/v1/admin/dashboard`、`/v1/admin/access`、`/v1/admin/audit-events`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/operations`、`/v1/admin/impersonation-sessions` 以及多条受控 mutation API。
- `apps/admin` 当前已实现 5 个业务页面：`Command Center`、`Tenant Detail`、`Content Pipeline`、`Provider Ops`、`Audit & Access`。
- `Users & Children`、`Learning Assets`、`Learning Outcomes`、`Infrastructure`、`Developer API` 仍是占位导航入口，不应再被写成已完成页面。
- 当前后台更准确的定位是“具备 live read 和受控 mutation 的运营控制台原型”，不是完整的 SSO / 权限治理后台。

### 4. Harness / 真机回归：入口已形成，HN-019 已脚本化

- `Makefile` 已提供 `harness-mvp-readiness`、`harness-main-chain-smoke`、`harness-doubao-smoke`、`harness-evidence-index`、`harness-hn019-real-device-main-chain` 等统一入口。
- `docs/harness/device-regression-runbook.md`、`provider-readiness-runbook.md`、`evidence-archive-policy.md` 已形成真机回归、真实 provider 和 evidence 治理的核心入口。
- `scripts/harness/run_hn019_real_device_main_chain.py` 已形成独立真机主链 harness，可写出固定 summary / material / job / media / log 证据文件。
- `scripts/harness/run_hn019_real_device_main_chain_test.py` 已补 focused test，覆盖局域网 `healthz` 探测不走系统代理。

### 5. 文档治理：入口已收敛到单一最新快照

- `README.md`、`docs/project/README.md`、`docs/harness/README.md` 已形成项目入口、项目快照入口和 harness/readiness 入口。
- `docs/project/` 当前只保留一份最新状态快照，避免旧快照与当前真相源竞争。
- 多份 harness 文档已改写为“当前入口 / 当前结论 / 历史 evidence”结构，不再把历史运行流水直接写成今天的事实。

## 当前可直接证明的仓库事实

### 代码与页面

- API 当前通过 `/v1` 前缀同时挂载 parent 与 admin 路由。
- worker 当前确实有真实讲义处理、学习资产媒体补齐和 speaking 评分任务，不是只剩 stub。
- `apps/admin/src/pages` 当前只有 5 个已实现业务页面和 1 个 `PlaceholderPage`。
- `apps/mobile` 仍依赖 `packages/contracts` 与 `packages/design_tokens`，这两个包目录都存在。

### 文档与命令入口

- `Makefile` 的 `mobile-bootstrap` 依赖 `packages/contracts`、`packages/design_tokens` 和 `apps/mobile` 三处 `flutter pub get`。
- `IOS_API_BASE_URL` 默认仍是 `http://127.0.0.1:8000/v1`；真机导包必须显式覆盖当前局域网地址。
- `docs/harness/` 当前仍是 harness/readiness 的主文档目录，`dist/harness/` 只是证据输出目录。
- `HN-019` harness 对局域网健康检查显式使用 no-proxy 探测，这一点已经有脚本测试覆盖，不再只是 runbook 建议。

### 当前仓库规模

- API 测试文件：`27` 个 `test_*.py`
- worker 测试文件：`2` 个 `test_*.py`
- mobile `test/` 与 `tool/harness/` 文件：`21` 个
- admin 前端测试文件：`10` 个 `*.test.ts` / `*.test.tsx`

## 已完成但未在本轮重新执行的事项

下面这些内容在文档和 evidence 中已有明确历史记录，但本轮没有重新跑命令或真机回归，只能视为“已有历史证据，未做当日复验”：

- `HN-017` speaking 真机证据存在。
- `HN-019` 真机主链回归证据目录存在。
- iOS internal/Profile 导包链路曾跑通。
- Doubao provider smoke 曾通过。

这些结论仍可作为项目背景，但不应表述成本轮新鲜验证结果。

## 当前缺口与未证实项

### 1. 跨设备交付仍未收口

- Android 交付仍没有稳定、可复查的当前产物结论；仓库里只有历史 blocker 记录。
- iOS 虽然已有 internal/Profile 打包与真机证据，但分发策略仍停留在 development provisioning / UDID 管理层面。
- 面向非开发成员的最短交付手册仍不够短，局域网 API、公网 `/uploads`、代理继承、IPA/APK 产物和常见失败排查仍分散在多份文档中。

### 2. HN-019 已有 harness，但执行纪律还不够硬

- 主链 summary、material、job、media、API/worker log 的输出文件已经固定，但截图清单、交接模板和团队复跑节奏尚未完全固化。
- `dist/harness/evidence-index.json` 可以生成，但不同 `HN-*` 目录的 summary 风格仍未完全统一。
- 部分 harness 长文仍保留较多历史过程，需要继续压缩成“当前入口 / 历史 evidence”分层结构。

### 3. Admin 已可 live 使用，但仍不是完整运营后台

- 当前没有完整 admin login/SSO。
- 当前没有 DB-backed role mutation、permission mutation 和更完整的账号治理流程。
- `operations` 当前是数据库与配置快照，不代表真正的 broker queue depth、worker heartbeat 或完整运维观测。

### 4. 文档入口仍可继续减重

- 当前多份 harness 文档仍保留不少历史运行细节，容易让读者把一次历史验收当成当前事实。
- 新成员要完成“理解项目 -> 启动本地环境 -> 真机回归 -> 找证据”的阅读路径仍偏长。

## 项目级 ToDo

### P0：跨设备交付收口

#### 目标

把项目从“熟悉当前机器的人能装起来”推进到“团队成员按文档即可安装、连接并完成基本回归”。

#### 细化清单

- [ ] 在当前机器上重新确认 Android 交付链：区分“仓库能力缺失”与“本机 SDK/权限环境缺失”。
- [ ] 明确 Android 最低交付标准：debug APK、QA 包还是暂不承诺 Android 分发。
- [ ] 明确 iOS 内部测试分发策略：继续 development provisioning + UDID，还是转 TestFlight。
- [ ] 新增一份最短交付手册，只保留安装、局域网 API、公网 `/uploads`、代理继承、产物路径和常见失败排查。
- [ ] 固化 iOS 真机导包模板命令，统一使用 `LAN_IP=<current-host-ip>` 占位，不再散落历史 IP。
- [ ] 把“当前仓库已验证过什么”和“新机器第一次要准备什么”拆成两段，避免混写。

### P0：HN-019 执行化

#### 目标

把真机回归从“有 runbook、有 harness”收口成“有固定截图清单、固定交接模板和固定复跑节奏”的可交接流程。

#### 细化清单

- [ ] 固化 `R0/R1/R2/R3` 每一级最小必需证据，不再允许只凭口头描述判定通过。
- [ ] 基于当前 `HN-019` harness 输出，补齐目录级交接模板，明确哪些字段必须人工补充。
- [ ] 固定主链回归截图清单：上传/AI 校对/课程详情/报告页。
- [ ] 评估 `make harness-evidence-index` 对交接是否足够；如不够，补目录级 summary 模板。
- [ ] 再补一轮按当前模板输出的 `HN-019` summary，验证 runbook 是否足够让新人照做。

### P1：Admin 进入可运营收口

#### 目标

把后台从“可 live 演示的原型”推进到“边界清楚、页面职责清楚、失败语义清楚的运营控制台”。

#### 细化清单

- [ ] 明确 `apps/admin` 下一阶段定位：继续 prototype-first，还是进入真实运营控制台收敛。
- [ ] 为 live mode 页面补“允许做什么 / 不建议做什么 / 失败后如何处理”的页面级说明。
- [ ] 增加 permission deny、scope deny、no-disclosure 的显式 UI 反馈和测试。
- [ ] 处理占位导航页面：要么补齐功能，要么明确标成未进入当前阶段。
- [ ] 明确哪些运维问题继续由 `operations` 快照表达，哪些要进入真正的 telemetry / broker 观测。

### P1：主链验收矩阵补强

#### 目标

让主链不只“功能存在”，也能在设备、网络和失败态下被稳定解释与复现。

#### 细化清单

- [ ] 做一轮平板关键页面人工验收，覆盖 AI 校对、课程详情、报告页、空态和失败态。
- [ ] 决定 `HN-016` OpenAI 媒体路径的项目承诺：继续保留兼容证据，还是明确降为非默认路线。
- [ ] 复查弱网、代理、缺少公网音频 URL 时，上传/媒体/speaking 的文案和恢复路径。
- [ ] 形成失败态证据矩阵，把 provider 失败、worker 未启动、token 失效、局域网不可达等情况写成统一说明。

### P2：文档入口继续收敛

#### 目标

缩短新成员理解项目、启动项目、复跑主链和定位证据所需的阅读路径。

#### 细化清单

- [ ] 把交付、真机复跑、provider 依赖和非开发试用入口压缩成更短的导读，而不是依赖多篇长文往返跳转。
- [ ] 持续把 harness 长文改成“当前入口 / 当前结论 / 历史 evidence”结构。
- [ ] 保持 `docs/project/` 同一时间只保留最新一份状态快照。
- [ ] 持续清理仍会把历史固定 IP、旧命令或过时结论伪装成当前操作步骤的文档。

## 建议执行顺序

1. 先收口交付策略，特别是 Android 是否承诺分发、iOS 是否继续走 UDID 方案。
2. 再把 HN-019 的截图清单、目录模板和复跑节奏固化，确保团队能按同一格式复跑和交接。
3. 然后决定 admin 是继续维持 prototype，还是正式进入可运营收口阶段。
4. 最后持续压缩文档入口，把长历史说明进一步剥离到 evidence 背景层。

## 当前判断

- LearningEnglish 已经不再是“验证上传识别能不能跑”的项目，而是“把已有主链变成可复查、可交付、可运营系统”的项目。
- 当前最大不确定性不在主链功能是否存在，而在交付流程、真机回归执行纪律和 admin 运营边界是否足够清楚。
- 如果 P0 的交付手册和 HN-019 执行模板收口，这个仓库会更明确地从“开发者可运行 MVP”进入“团队可持续验证的 MVP”。
