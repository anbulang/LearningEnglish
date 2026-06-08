# LearningEnglish 项目进度与 ToDo（2026-06-07）

## 目的

这份状态快照只基于当前仓库中的代码、测试目录、`Makefile`、`docs/harness/`、`docs/architecture/`、服务 README、移动端 / 后台 README，以及现有 `dist/harness/` 证据路径，回答四个问题：

1. 当前项目从整个系统角度已经做到哪里。
2. 哪些能力可以视为当前仓库事实。
3. 哪些仍是项目级缺口、风险或治理问题。
4. 接下来应该按什么顺序推进。

## 当前结论

当前项目处于 **家庭英语学习主链已闭环、默认真实 provider 路径已稳定、speaking 与周报闭环已落地、admin backend contract 已具备 Phase 2 所需主要 read/write API、admin UI 已可运行但 live read 仍未跟上、跨设备交付与真机回归治理仍待收口** 的阶段。

一句话概括：

> LearningEnglish 当前最需要的不是再证明“功能能做出来”，而是把已有主链、真机回归和交付流程压缩成团队可重复执行的标准操作。

## 当前项目进度

### 1. 用户主链：已闭环

- 家长登录、手机号绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练和独立报告页已串成完整主链。
- 上传讲义后会创建 `CourseMaterial` 和 `MaterialParseJob`，worker 异步处理后推进到 `needs_review`；移动端 AI 校对页会持续轮询 `processing` 状态并保留手动刷新兜底。
- 家长确认草稿后，系统会生成 `KnowledgePack`、`ReviewTask`、`ParentCoachingScript`，并继续补齐学习资产图片与英美音 TTS。
- `/reports` 已是独立报告页，能展示周报基础统计、讲义汇总、`asset_mastery`、复习表现、口语表现与推荐动作。

### 2. AI / Provider 主线：默认真实路径已收敛

- worksheet OCR / parsing 默认走 `AI_PROVIDER=qwen`，由 DashScope compatible Qwen-VL + Qwen text 完成真实识别和结构化抽取。
- 学习资产媒体默认走 `MEDIA_PROVIDER=real` + `MEDIA_IMAGE_PROVIDER=dashscope` + `MEDIA_TTS_PROVIDER=dashscope`。
- 口语评分默认走 `SPEECH_PROVIDER=dashscope` + `SPEECH_ASSESSMENT_PROVIDER=dashscope`，由 DashScope ASR + Qwen 评分完成转写、打分和中文反馈。
- `doubao` 与 OpenAI 媒体路径仍保留为兼容或对照路径，但都不是当前默认验收主线。

### 3. Admin / 运维能力：backend contract 已落地，UI 仍偏 prototype

- `services/api` 已具备 admin read/write API、`AuditEvent`、`TenantProviderPolicy`、`TenantModuleSetting`、`AdminImpersonationSession` 等后台基础能力。
- `apps/admin` 已有五个已实现页面：`Command Center`、`Tenant Detail`、`Content Pipeline`、`Provider Ops`、`Audit & Access`。
- admin UI 当前 live mode 只直接消费 `dashboard`、`access` 两组 live read，并叠加 material retry/archive、provider policy override、tenant module toggle、impersonation start 这些受控 mutation；`audit-events`、`operations`、单租户详情、impersonation list/end 等新读模型还没有全面接入当前前端数据层。
- 因此当前后台更准确的状态是“可演示、可做部分 live 操作的运营控制台原型”，还不是已完成权限治理与运维闭环的生产后台。

### 4. Harness / 文档治理：入口结构已形成

- `README.md`、`docs/project/README.md`、`docs/harness/README.md` 已形成项目入口、状态入口、验收入口三层结构。
- `Makefile` 已包含 `harness-mvp-readiness`、`harness-main-chain-smoke`、`harness-doubao-smoke`、`harness-evidence-index`、`harness-hn019-real-device-main-chain` 等入口；`IOS_API_BASE_URL` 默认已回到 `127.0.0.1`，真机导包必须显式覆盖当前局域网地址。
- `docs/harness/device-regression-runbook.md`、`provider-readiness-runbook.md`、`evidence-archive-policy.md` 已形成真机回归、真实 provider 与 evidence 治理入口。
- 本轮已按仓库事实重新替换项目状态快照，并把入口文档同步切到单一最新版本。

### 5. 当前代码、测试与文档规模

- API 测试目录当前有 `20` 个 `test_*.py` 文件。
- worker 测试目录当前有 `2` 个 `test_*.py` 文件。
- mobile `test/` 与 `tool/harness/` 当前共有 `19` 个 Dart 测试 / harness 文件。
- admin 前端当前有 `9` 个 `*.test.ts` / `*.test.tsx` 文件。
- `docs/` 当前共有 `44` 个 Markdown / SVG 文档文件。

## 当前可以视为仓库事实的内容

- 当前默认真实路径是 `qwen + DashScope media + DashScope speech`，不是 stub-only，也不是 Doubao-first。
- speaking 已具备真实录音上传、异步评分、结果页展示和周报回填，不再只是 smoke 样例。
- `HN-017` 真机 speaking evidence 与 `HN-019` 真机主链回归 evidence 路径都已经存在。
- `apps/admin` 已从纯静态稿进入“有真实 live mode 和受控 mutation 的后台原型”；但它仍未完整消费所有 Phase 2 新读模型。
- `docs/superpowers/*` 仍应视为历史 spec / plan，不应替代 `README.md`、`docs/harness/*`、`docs/architecture/*`、服务 README 和 `Makefile`。

## 当前未证实或仍有缺口的内容

### 1. 跨设备交付仍偏单机化

- Android 交付仍未跑通，`make mobile-apk` 还没有形成稳定、可复查的真实产物。
- iOS 仍主要依赖 development provisioning 的 internal/Profile 包；如果要扩大试用范围，必须明确 UDID 管理或 TestFlight 路线。
- 局域网 API、IPA/APK 产物、公网 `/uploads`、代理继承这些前置条件虽然散落在文档里，但还没有收敛成一份最短交付手册。
- 真机 iOS 导包现在必须显式覆盖 `IOS_API_BASE_URL=http://<current-host-ip>:8000/v1`；如果团队成员忽略这一步，仍会把本机默认值误当真机默认配置。

### 2. Admin live mode 落后于 backend contract

- `apps/admin/src/domain/adminApi.ts` 当前仍只直接加载 `dashboard` 和 `access` 两组 live read 数据。
- `GET /v1/admin/audit-events`、`GET /v1/admin/operations`、`GET /v1/admin/tenants/{tenant_id}`、`GET /v1/admin/impersonation-sessions` 与 `POST .../end` 还没有以完整 live 读写体验进入 UI。
- 当前后台更像“可演示、部分可 live 操作的控制台”，而不是已完成权限治理与运维闭环的运营后台。

### 3. 真机回归入口已形成，但执行纪律仍不够稳定

- `dist/harness/evidence-index.json` 可以生成，但不同 `HN-*` 目录的 summary 字段仍有新旧混用。
- `HN-019` runbook 与一键 harness 已存在，但 `R0/R1/R2/R3` 还没有形成固定复跑节奏与统一摘要模板。
- 历史局域网 IP 作为 evidence 背景仍分散出现在部分长文档中；虽然文档已说明不可直接复用，但当前入口仍可继续压缩。

### 4. 项目级文档入口仍可继续收敛

- README、harness runbook、服务 README 已基本形成真相源，但部分长文档仍保留较多历史过程。
- 非开发者试用、交付、排障入口仍然偏开发者视角，产品/测试同学要完整复跑仍需要工程人员口头补充。
- 后续仍需持续保持“同一时间只保留最新一份状态快照”的纪律。

## 项目级 ToDo

下面按整个项目推进面组织，不只按 HN 编号罗列。

### P0：跨设备交付收口

#### 目标

让项目从“熟悉当前机器的人可以装起来”变成“团队成员按文档就能安装、连接、回归”。

#### 细化清单

- [ ] 跑通一次当前机器上的 `make mobile-apk`，把真实 blocker、前置条件、命令、SDK 要求和产物路径写回文档。
- [ ] 明确 Android 最低交付标准：先提供 debug APK，还是直接要求可分发的测试包。
- [ ] 明确 iOS 内部测试分发策略：继续 development provisioning、集中收集 UDID，还是转 TestFlight。
- [ ] 新增一份最短交付手册，覆盖 `infra/.env`、局域网 API、IPA/APK 产物、公网 `/uploads`、代理继承和常见失败排查。
- [ ] 给 iOS 导包补一条固定命令模板：`LAN_IP=<current-host-ip>; make mobile-ios-ipa IOS_API_BASE_URL="http://${LAN_IP}:8000/v1"`，避免每次手填时继续散落历史 IP。
- [ ] 把“当前机器已产出什么”和“新机器要先准备什么”拆成两段，避免非开发同学把历史产物误当默认能力。

#### 完成标准

- 项目不再只适合熟悉当前机器的人来安装和复现。

### P0：HN-019 执行化

#### 目标

让真机回归从“知道应该怎么做”变成“按同一模板稳定复跑并形成可读 evidence”。

#### 细化清单

- [ ] 用当前 `docs/harness/device-regression-runbook.md` 和 `make harness-hn019-real-device-main-chain` 再补一轮最新 `R0`、`R1`、`R2` summary。
- [ ] 明确 `R3` 的最小通过标准：provider smoke、worker 证据、scored JSON、真机 speaking 结果页四者缺一不可。
- [ ] 统一新 summary 推荐字段：`run_id`、`started_at`、`device`、`result`、`key_files`、`notes`。
- [ ] 校验 `make harness-evidence-index` 对新人是否足够；如不足，再补目录级 summary 模板和示例。
- [ ] 把“需要手工截图补存”的页面清单固定下来，避免每轮回归漏同一批页面。

#### 完成标准

- 新人只看 runbook 和 evidence index，就能知道该跑什么、该看哪里、哪份证据是当前格式。

### P1：Admin live mode 跟上 backend contract

#### 目标

让后台前端不再停留在“有信息架构、少量 live mutation”的状态，而是把现有 backend contract 真正消费起来。

#### 细化清单

- [ ] 先明确 `apps/admin` 的下一阶段定位：继续保持 prototype-first，还是进入真实运营控制台收敛。
- [ ] 如果进入真实运营阶段，优先接入 `/v1/admin/operations`、`/v1/admin/audit-events`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/impersonation-sessions`。
- [ ] 为 live mode 页面补“允许做什么 / 不建议做什么 / 失败后怎么回滚”的页面级说明。
- [ ] 增加 admin UI 对 permission deny / scope deny / no-disclosure 的显式交互和测试。
- [ ] 清理只保留导航入口的 placeholder 页面，至少把它们明确标成“未进入当前阶段”的导航保留位，而不伪装成现成功能。

#### 完成标准

- 后台能力的“可演示”与“可运营”边界清楚，UI 不再落后于 backend contract。

### P1：主链验收矩阵补强

#### 目标

让主链不仅“功能存在”，也能在设备、网络、异常状态下被稳定解释和复现。

#### 细化清单

- [ ] 做一轮平板关键页面人工验收，覆盖 AI 校对、课程详情、报告页、空态和失败态。
- [ ] 决定 `HN-016` OpenAI 媒体路径的项目承诺：继续保留并补最小 evidence，还是明确降级为非默认兼容路径。
- [ ] 复查 speaking、媒体、讲义上传在弱网、代理、缺少公网音频 URL 时的文案与恢复路径。
- [ ] 补一份失败态证据矩阵，把 provider 失败、worker 未启动、token 失效、局域网不可达等常见问题对齐到固定说明。

#### 完成标准

- 主链不仅“功能存在”，而且在设备、网络和异常状态下也更可解释。

### P2：文档入口继续收敛

#### 目标

缩短新成员理解项目、启动项目、复跑主链、定位证据所需的阅读路径。

#### 细化清单

- [ ] 把非开发者试用、项目交付、真机复跑、provider 依赖整理成更短的入口图，而不是依赖多份长文档交叉阅读。
- [ ] 把 `docs/harness/upload-recognition-loop.md` 和 `docs/harness/hn017-speaking-readiness-summary.md` 中纯历史过程压缩为“背景 / 当前入口 / 历史 evidence”三段式。
- [x] README 的“文档入口”已增加每份文档的适用人群说明，后续只需保持与入口文档同步。
- [ ] 每次替换 `docs/project/YYYY-MM-DD-status-and-todo.md` 时，同步删除前一版，保持状态快照单一。

#### 完成标准

- 新成员能在更少文档中完成“理解项目、启动项目、复跑主链、定位证据”。

### P2：工程化与数据演进

#### 目标

为后续报告增强、运维观测和更复杂学习分析预留稳定边界。

#### 细化清单

- [ ] 评估把关键 smoke / capture / evidence 入口进一步收敛成更统一的一键编排。
- [ ] 梳理 provider / worker 失败日志结构、重试规则和证据落盘方式，降低后续排障成本。
- [ ] 评估 `learning_assets`、`image_records`、`ReviewTask.content_json`、speaking / report 聚合数据的拆分时机。
- [ ] 为多周趋势、解释层和更稳定的学习分析预留事件化或聚合化数据结构。

#### 完成标准

- 后续做报告增强、运维观测或更复杂学习分析时，不会先被当前工程边界卡住。

## 建议执行顺序

1. 先收口 Android / iOS 交付策略，把项目从“当前作者可装机”推进到“团队可复现”。
2. 再按 HN-019 runbook 补一轮新 summary，验证文档治理和 evidence index 是否足以支撑交接。
3. 然后决定 admin 是继续停留在 prototype，还是正式进入运营控制台阶段，并据此推进 UI 接口对齐。
4. 最后再推进文档入口压缩、日志结构、编排和数据模型演进。

## 当前判断

- LearningEnglish 的核心价值已经从“证明能上传识别”转向“把已有 AI 学习主链变成可复查、可交付、可运营的系统”。
- 当前最大的剩余不确定性不在主链功能是否存在，而在跨设备交付、admin UI/backend 对齐、以及治理流程能否稳定复跑。
- 如果 P0 的交付手册与 HN-019 执行化能收口，这个仓库会更明确地从“开发者可运行 MVP”进入“团队可持续验证的 MVP”。
