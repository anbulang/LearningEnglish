# LearningEnglish 项目进度与 ToDo（2026-06-03）

## 目的

这份状态快照只基于当前仓库中的代码、测试目录、`Makefile`、`docs/harness/`、`docs/architecture/`、服务 README、移动端 / 后台 README，以及现有 `dist/harness/` 证据路径来回答四个问题：

1. 当前项目从整个系统角度已经做到哪里。
2. 哪些能力可以视为当前仓库事实。
3. 哪些仍是项目级缺口、风险或治理问题。
4. 接下来应该按什么顺序推进。

## 当前结论

当前项目处于 **学习主链、真实 provider 默认路径、speaking 闭环、admin backend Phase 2、HN-019 真机回归治理入口都已落地，但跨设备交付、admin UI 对齐、证据复跑纪律与非开发者交付手册仍未收口** 的阶段。

一句话概括：

> LearningEnglish 已经具备本地可运行、可回归、可保存证据的 MVP 主链；当前主要问题不再是“功能是否存在”，而是“团队能否稳定复现、交付和运营”。

## 当前项目进度

### 1. 用户主链

- 家长登录、手机号绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练和报告页已串成完整主链。
- 上传讲义后会创建 `CourseMaterial` 和 `MaterialParseJob`，worker 异步处理后推进到 `needs_review`；移动端 AI 校对页会持续轮询 `processing` 状态并保留手动刷新兜底。
- 家长确认草稿后，系统会生成 `KnowledgePack`、`ReviewTask`、`ParentCoachingScript`，并继续补齐学习资产图片与英美音 TTS。
- `/reports` 已是独立报告页，能展示周报基础统计、讲义汇总、`asset_mastery`、复习表现、口语表现与推荐动作。

### 2. AI / Provider 主线

- worksheet OCR / parsing 默认走 `AI_PROVIDER=qwen`，由 DashScope compatible Qwen-VL + Qwen text 完成真实识别和结构化抽取。
- 学习资产媒体默认走 `MEDIA_PROVIDER=real` + `MEDIA_IMAGE_PROVIDER=dashscope` + `MEDIA_TTS_PROVIDER=dashscope`。
- 口语评分默认走 `SPEECH_PROVIDER=dashscope` + `SPEECH_ASSESSMENT_PROVIDER=dashscope`，由 DashScope ASR + Qwen 评分完成转写、打分和中文反馈。
- `doubao` 与 OpenAI 媒体路径仍保留为兼容或对照路径，但都不是当前默认验收主线。

### 3. Admin / 运维能力

- `services/api` 已具备 admin read/write API、`AuditEvent`、`TenantProviderPolicy`、`TenantModuleSetting`、`AdminImpersonationSession` 等最小后台支撑。
- `apps/admin` 已不是纯静态稿：默认可用 mock data 启动，也可接本地 admin API 查看 dashboard / access，并执行 material retry/archive、provider policy override、tenant module toggle、impersonation start 等受控 mutation。
- admin backend Phase 2 的读模型和权限边界已经落地，但 admin UI 仍未完整接入 `audit-events`、`operations`、`tenant detail`、`impersonation list/end` 等新增能力。

### 4. Harness / 文档治理

- `docs/harness/README.md`、`docs/harness/device-regression-runbook.md`、`docs/harness/provider-readiness-runbook.md`、`docs/harness/evidence-archive-policy.md` 已形成统一入口。
- `Makefile` 已包含 `harness-mvp-readiness`、`harness-main-chain-smoke`、`harness-doubao-smoke`、`harness-evidence-index`、`harness-hn019-real-device-main-chain` 等入口。
- `dist/harness/HN-017/` 已保留 speaking 真机证据；`dist/harness/HN-019/` 已有一轮真机安装和主链回归证据命名约定与 runbook。

### 5. 当前代码与测试规模

- API 测试目录当前有 `19` 个 `test_*.py` 文件。
- worker 测试目录当前有 `2` 个 `test_*.py` 文件。
- mobile `test/` 与 `tool/` 当前共有 `19` 个 Dart 测试 / harness 文件。
- admin 前端当前有 `9` 个 `*.test.ts` / `*.test.tsx` 文件。
- `docs/` 当前共有 `44` 个 Markdown / SVG 文档文件，已形成 README、architecture、harness、project、superpowers 的分层。

## 当前可以视为仓库事实的内容

- 当前默认真实路径是 `qwen + DashScope media + DashScope speech`，不是 stub-only，也不是 Doubao-first。
- speaking 已具备真实录音上传、异步评分、结果页展示和周报回填，不再只是 smoke 样例。
- `HN-017` 真机 speaking evidence 与 `HN-019` 真机主链回归 evidence 路径都已经存在。
- admin backend 已从“后续再做”进入“有真实权限边界与受控 mutation 的本地运营后端”；admin UI 仍处于 mock/live 混合态。
- `docs/superpowers/*` 仍应视为历史 spec / plan，不应替代 `README.md`、`docs/harness/*`、`docs/architecture/*`、服务 README 和 `Makefile`。

## 当前未证实或仍有缺口的内容

### 1. 跨设备交付仍偏单机化

- Android 交付仍未跑通，`make mobile-apk` 还没有形成稳定、可复查的真实产物。
- iOS 仍主要依赖 development provisioning 的 internal/Profile 包；如果要扩大试用范围，必须明确 UDID 管理或 TestFlight 路线。
- 局域网 API、IPA/APK 产物、公网 `/uploads`、代理继承这些前置条件虽然散落在文档里，但还没有收敛成一份最短交付手册。

### 2. Admin UI 落后于 backend Phase 2

- `apps/admin` 还没有把 `/v1/admin/audit-events`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/operations`、`/v1/admin/impersonation-sessions` 的读模型接完整。
- 当前后台更像“可演示、部分可 live 操作的控制台”，而不是已完成权限治理与运维闭环的运营后台。

### 3. 证据治理入口已形成，但执行纪律仍不够稳定

- `dist/harness/evidence-index.json` 可以生成，但不同 `HN-*` 目录的 summary 字段仍有新旧混用。
- `HN-019` runbook 与一键 harness 已存在，但 `R0/R1/R2/R3` 没有形成固定复跑频率与固定摘要模板。
- 文档已经强调历史 `192.168.*` 仅是 evidence，但部分历史章节仍保留旧 IP 文字作为背景，后续需要继续压缩“历史细节”与“当前入口”的混杂。

### 4. 项目级文档仍需继续做入口收敛

- README、harness runbook、服务 README 已基本形成真相源，但 `docs/harness/upload-recognition-loop.md`、`hn017-speaking-readiness-summary.md` 仍承载较多历史过程。
- 非开发者试用、交付、排障入口仍然偏开发者视角，产品/测试同学要完整复跑仍需要工程人员口头补充。

## 项目级 ToDo

下面按整个项目推进面组织，不只按 HN 编号罗列。

### P0：跨设备交付收口

- [ ] 跑通一次当前机器上的 `make mobile-apk`，把真实 blocker、前置条件、命令、SDK 要求和产物路径写回文档。
- [ ] 明确 Android 最低交付标准：先提供 debug APK，还是直接要求可分发的测试包。
- [ ] 明确 iOS 内部测试分发策略：继续 development provisioning、集中收集 UDID，还是转 TestFlight。
- [ ] 新增一份最短交付手册，覆盖 `infra/.env`、局域网 API、IPA/APK 产物、公网 `/uploads`、代理继承和常见失败排查。

完成标准：

- 项目不再只适合熟悉当前机器的人来安装和复现。

### P0：HN-019 执行化

- [ ] 用当前 `docs/harness/device-regression-runbook.md` 和 `make harness-hn019-real-device-main-chain` 再补一轮最新 `R0/R1/R2` summary。
- [ ] 明确 `R3` 的最小通过标准：provider smoke、worker 证据、真机 speaking 结果页三者缺一不可。
- [ ] 统一新 summary 推荐字段：`run_id`、`started_at`、`device`、`result`、`key_files`、`notes`。
- [ ] 校验 `make harness-evidence-index` 对新人是否足够；如不足，再补目录级 summary 模板和示例。

完成标准：

- 新人只看 runbook 和 evidence index，就能知道该跑什么、该看哪里、哪份证据是当前格式。

### P1：Admin UI 跟上 backend Phase 2

- [ ] 先明确 `apps/admin` 的下一阶段定位：继续保持 prototype-first，还是进入真实运营控制台收敛。
- [ ] 如果进入真实运营阶段，优先接入 `/v1/admin/operations`、`/v1/admin/audit-events`、`/v1/admin/tenants/{tenant_id}`、`/v1/admin/impersonation-sessions`。
- [ ] 为 live mode 页面补“允许做什么 / 不建议做什么 / 失败后怎么回滚”的页面级说明。
- [ ] 增加 admin UI 对权限 deny / scope deny / no-disclosure 的显式交互和测试。

完成标准：

- 后台能力的“可演示”与“可运营”边界清楚，UI 不再落后于 backend contract。

### P1：主链验收矩阵补强

- [ ] 做一轮平板关键页面人工验收，覆盖 AI 校对、课程详情、报告页、空态和失败态。
- [ ] 决定 `HN-016` OpenAI 媒体路径的项目承诺：继续保留并补最小 evidence，还是明确降级为非默认兼容路径。
- [ ] 复查 speaking、媒体、讲义上传在弱网、代理、缺少公网音频 URL 时的文案与恢复路径。
- [ ] 补一份失败态证据矩阵，把 provider 失败、worker 未启动、token 失效、局域网不可达等常见问题对齐到固定说明。

完成标准：

- 主链不仅“功能存在”，而且在设备、网络和异常状态下也更可解释。

### P2：文档入口继续收敛

- [ ] 把非开发者试用、项目交付、真机复跑、provider 依赖整理成更短的入口图，而不是依赖多份长文档交叉阅读。
- [ ] 把 `docs/harness/upload-recognition-loop.md` 和 `docs/harness/hn017-speaking-readiness-summary.md` 中纯历史过程压缩为“背景 / 当前入口 / 历史 evidence”三段式。
- [ ] 为 README 的“文档入口”增加每份文档的适用人群说明，减少新成员误读历史 spec 为当前真相源。

完成标准：

- 新成员能在更少文档中完成“理解项目、启动项目、复跑主链、定位证据”。

### P2：工程化与数据演进

- [ ] 评估把关键 smoke / capture / evidence 入口进一步收敛成更统一的一键编排。
- [ ] 梳理 provider / worker 失败日志结构、重试规则和证据落盘方式，降低后续排障成本。
- [ ] 评估 `learning_assets`、`image_records`、`ReviewTask.content_json`、speaking / report 聚合数据的拆分时机。
- [ ] 为多周趋势、解释层和更稳定的学习分析预留事件化或聚合化数据结构。

完成标准：

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
