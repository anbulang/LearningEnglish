# LearningEnglish 项目进度与 ToDo（2026-06-13）

## 目的

这份快照只基于当前仓库可直接核对的真相源整理：

- 代码目录与路由
- `Makefile`
- `README.md`
- `docs/harness/*`
- `docs/architecture/*`
- `services/api/README.md`
- `services/workers/README.md`
- `apps/mobile/README.md`
- `apps/admin/README.md`

它回答四个问题：

1. 当前项目已经做到哪里。
2. 哪些结论能被当前仓库直接证明。
3. 哪些只是历史 evidence，本轮没有重新验证。
4. 接下来整个项目最该按什么顺序推进。

## 当前结论

LearningEnglish 当前处于 **家庭英语学习主链已经闭环、默认真实 provider 路径已确定、admin 后台停留在“可 live 读取和有限受控 mutation 的运营控制台原型”、HN-019 真机 harness 已脚本化，而项目当前最需要继续收口的是交付流程、验收执行纪律和文档入口一致性** 的阶段。

一句话概括：

> 这个项目的核心矛盾已经不是“功能有没有”，而是“现有能力能不能被团队稳定复查、稳定交付、稳定接手”。

## 项目进度

### 1. 家长端主链：已闭环

- 家长登录、手机号绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练和独立报告页都已落到当前代码目录。
- API 已包含 `children`、`materials`、`material-jobs`、`review-tasks`、`practice-sessions`、`speaking-attempts`、`reports/weekly` 等主链路由。
- worker 已实现 `materials.process_material_job`、`materials.process_learning_asset_media`、`speaking.score_attempt` 和 `reporting.aggregate_weekly_report`。
- 移动端 README 与架构文档都能对应到登录、资料库、上传、AI 校对、课程详情、复习、报告与个人页。

### 2. 默认真实 provider 路径：已明确

- `infra/env/local.example.env` 当前默认 `AI_PROVIDER=qwen`。
- 学习资产媒体默认是 `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`。
- 口语评分默认是 `SPEECH_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`。
- `doubao` 与 OpenAI 兼容路径仍保留，但都不是当前默认主线。

### 3. Admin / 运维后台：已进入 live 原型阶段

- 后端已提供 `/v1/admin/dashboard`、`/v1/admin/access`、`/v1/admin/audit-events`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/operations`、`/v1/admin/impersonation-sessions` 以及多条受控 mutation API。
- `apps/admin` 当前已实现 5 个业务页面：`Command Center`、`Tenant Detail`、`Content Pipeline`、`Provider Ops`、`Audit & Access`。
- 当前后台更准确的定位是“具备 live read 与部分受控 mutation 的运营控制台原型”，不是完整的生产级 admin 平台。
- `Users & Children`、`Learning Assets`、`Learning Outcomes`、`Infrastructure`、`Developer API` 仍只是占位导航入口，不应被写成已交付能力。

### 4. Harness / 真机回归：入口已形成，HN-019 已脚本化

- `Makefile` 已提供 `harness-mvp-readiness`、`harness-main-chain-smoke`、`harness-doubao-smoke`、`harness-evidence-index`、`harness-hn019-real-device-main-chain`、`harness-hn020-parent-pilot-template` 等统一入口。
- `docs/harness/device-regression-runbook.md`、`provider-readiness-runbook.md`、`evidence-archive-policy.md` 已形成真机回归、真实 provider 和 evidence 治理的核心入口。
- `scripts/harness/run_hn019_real_device_main_chain.py` 已形成独立真机主链 harness，并带 focused test 覆盖局域网 `healthz` no-proxy 探测。

### 5. 文档治理：主入口已收敛，但仍需继续减重

- `README.md`、`docs/project/README.md`、`docs/harness/README.md` 已形成项目入口、项目状态入口和 harness/readiness 入口。
- `docs/project/` 当前治理目标仍是只保留 `README.md` 与一份最新状态快照；旧快照应被替换，不再并存。
- `docs/design/` 中不再直接参与当前工程治理的过程性设计提示文档已清理，避免设计草稿与当前真相源竞争。

## 当前可直接证明的仓库事实

### 代码与页面

- API 当前通过 `/v1` 前缀同时挂载 parent 与 admin 路由。
- worker 当前确实有真实讲义处理、学习资产媒体补齐和 speaking 评分任务，不是只剩 stub。
- `apps/admin/src/pages` 当前有 11 个文件，其中只有 5 个业务页面与 1 个占位页面实现文件；并不存在更多已落地后台页面。
- `apps/mobile/assets/images/` 当前已存在登录、首页、上传、AI 校对、课程详情、报告、speaking 等插画资源，不再只是文档占位。

### 文档与命令入口

- `Makefile` 的 `mobile-bootstrap` 依赖 `packages/contracts`、`packages/design_tokens` 和 `apps/mobile` 三处 `flutter pub get`。
- `IOS_API_BASE_URL` 默认仍是 `http://127.0.0.1:8000/v1`；真机导包必须显式覆盖当前局域网地址。
- `apps/admin/README.md`、`services/api/README.md` 与当前代码一致地表述了 admin 仍处于原型到运营控制台收口阶段，而不是完整后台。
- `docs/harness/` 当前仍是 readiness / runbook 主文档目录，`dist/harness/` 只是本地证据输出目录。

### 当前仓库规模

- API 测试文件：`27` 个 `test_*.py`
- worker 测试文件：`2` 个 `test_*.py`
- admin 前端测试文件：`5` 个 `*.test.tsx`
- 真机 / UI harness 脚本：`apps/mobile/tool/harness/*` 与 `scripts/harness/*` 均已存在

## 已完成但未在本轮重新执行的事项

下面这些内容在文档和 evidence 中已有明确历史记录，但本轮没有重新跑命令或真机回归，只能视为“已有历史证据，未做当日复验”：

- `HN-017` speaking 真机证据存在。
- `HN-019` 真机主链回归证据目录存在。
- iOS internal/Profile 导包链路曾跑通。
- Doubao provider smoke 曾通过。

这些结论仍可作为项目背景，但不应表述成本轮新鲜验证结果。

## 当前缺口与未证实项

### 1. 跨设备交付仍未收口

- Android 交付仍没有稳定、可复查的当前产物结论；仓库里更多是历史 blocker 与环境说明。
- iOS 虽然已有 internal/Profile 打包与真机证据，但分发策略仍停留在 development provisioning / UDID 管理层面。
- 面向非开发成员的最短交付手册仍不够短，局域网 API、公网 `/uploads`、代理继承、IPA/APK 产物和常见失败排查仍分散在多份文档中。

### 2. HN-019 已有 harness，但执行纪律还不够硬

- 主链 summary、material、job、media、API/worker log 的输出文件已经固定，但截图清单、交接模板和团队复跑节奏尚未完全固化。
- `dist/harness/evidence-index.json` 可以生成，但不同 `HN-*` 目录的 summary 风格仍未完全统一。
- 部分 harness 长文仍保留较多历史过程，需要继续压缩成“当前入口 / 当前结论 / 历史 evidence”分层结构。

### 3. Admin 已可 live 使用，但仍不是完整运营后台

- 当前没有完整 admin login / SSO。
- 当前没有 DB-backed role mutation、permission mutation 和更完整的账号治理流程。
- `operations` 当前是数据库与配置快照，不代表真正的 broker queue depth、worker heartbeat 或完整运维观测。

### 4. 家长试用闭环仍未真正执行

- `HN-020` 已经有模板和验收清单，但 `dist/harness/HN-020/` 仍缺一轮真实家长或非技术试用者的正式证据。
- 当前还没有把上传、AI 校对、课程详情、复习和报告页的真实可用性问题按 `P0/P1/P2` 和 Batch 0-4 收口。

## 项目级 ToDo

### P0：交付链收口

#### 目标

把项目从“熟悉当前机器的人能装起来”推进到“团队成员按文档即可安装、连接并完成基本回归”。

#### 细化清单

- [ ] 在当前机器上重新确认 Android 交付链，明确是仓库能力缺失还是本机 SDK / 权限环境缺失。
- [ ] 明确 Android 的项目承诺：`debug APK`、QA 包，还是暂不承诺 Android 分发。
- [ ] 明确 iOS 内部测试分发策略：继续 development provisioning + UDID，还是转 TestFlight。
- [ ] 整理一份最短交付手册，只保留安装、局域网 API、公网 `/uploads`、代理继承、产物路径和常见失败排查。
- [ ] 固化 iOS 真机导包模板命令，统一使用 `LAN_IP=<current-host-ip>` 占位，不再散落历史 IP。

### P0：HN-020 家长试用闭环

#### 目标

把“功能存在”推进到“非开发成员能按同一清单完成主链试用并反馈问题”。

#### 细化清单

- [ ] 按 `docs/harness/hn020-parent-pilot-acceptance.md` 组织一轮真实家长或非技术试用者验收。
- [ ] 生成并填写 `dist/harness/HN-020/parent-pilot-summary.json` 与 `parent-pilot-notes.md`。
- [ ] 固定上传、AI 校对、课程详情、复习、报告 5 张最小截图清单。
- [ ] 把试用问题按 `P0/P1/P2` 与 Batch 0-4 归档，而不是散落在聊天记录中。
- [ ] 区分“试用阻断问题”和“产品优化建议”，避免 backlog 混写。

### P1：HN-019 执行化

#### 目标

把真机回归从“有 runbook、有 harness”收口成“有固定截图清单、固定交接模板和固定复跑节奏”的可交接流程。

#### 细化清单

- [ ] 固化 `R0/R1/R2/R3` 每一级最小必需证据，不再允许只凭口头描述判定通过。
- [ ] 基于当前 `HN-019` harness 输出，补齐目录级交接模板，明确哪些字段必须人工补充。
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

### P2：文档入口继续收敛

#### 目标

缩短新成员理解项目、启动项目、复跑主链和定位证据所需的阅读路径。

#### 细化清单

- [ ] 持续把 harness 长文改成“当前入口 / 当前结论 / 历史 evidence”结构。
- [ ] 保持 `docs/project/` 同一时间只保留最新一份状态快照。
- [ ] 持续清理不再服务当前工程治理的过程性设计提示、临时旁路索引和过时快照。
- [ ] 持续清理仍会把历史固定 IP、旧命令或过时结论伪装成当前操作步骤的文档。
- [ ] 把交付、真机复跑、provider 依赖和非开发试用入口压缩成更短导读，而不是依赖多篇长文往返跳转。

## 建议执行顺序

1. 先收口交付策略，尤其是 Android 是否承诺分发、iOS 是否继续走 UDID 方案。
2. 再按 HN-020 跑一轮真实家长或非技术试用，把主链可用性问题转成修复批次。
3. 然后固化 HN-019 的截图清单、目录模板和复跑节奏，确保团队能按同一格式复跑和交接。
4. 接着决定 admin 是继续维持原型，还是正式进入可运营收口阶段。
5. 最后持续压缩文档入口，把历史说明继续剥离到 evidence 背景层。

## 当前判断

- LearningEnglish 已经不再是“验证上传识别能不能跑”的项目，而是“把已有主链变成可复查、可交付、可运营系统”的项目。
- 当前最大不确定性不在主链功能是否存在，而在交付流程、真机回归执行纪律、家长试用闭环与 admin 运营边界是否足够清楚。
- 如果 P0 的交付手册、HN-020 试用归档和 HN-019 执行模板都收口，这个仓库会更明确地从“开发者可运行 MVP”进入“团队可持续验证的 MVP”。
