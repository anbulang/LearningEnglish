# LearningEnglish 项目进度与 ToDo（2026-05-31）

## 目的

这份状态快照只基于当前仓库中的代码、测试目录、`Makefile`、`infra/env/local.example.env`、`dist/harness/` 证据目录、`docs/harness/`、`docs/architecture/`、服务 README 与移动端 / 后台原型现状整理，回答四个问题：

1. 当前项目从整个系统角度已经做到哪里。
2. 哪些能力已经是稳定仓库事实。
3. 哪些仍是项目级风险、交付缺口或治理缺口。
4. 接下来应该按什么顺序推进。

## 当前结论

当前项目处于 **学习主链已成型、默认真实 provider 已切到 Qwen + DashScope、speaking / report / admin phase 1 均已有代码与本地 evidence，且 HN-019 文档治理入口已经补齐，但跨设备交付和后台运营化仍未收口** 的阶段。

一句话概括：

> LearningEnglish 已经是一个可运行、可验证、可复查主链的 MVP；当前工作的重点不再是证明“有没有功能”，而是让这条链路更容易交付、复跑、运营和持续验证。

## 当前项目进度

### 1. 学习产品主链

- 家长登录、手机号绑定、孩子档案、讲义上传、AI 校对、课程详情、复习、口语陪练和报告页已经串成完整主链。
- 上传讲义后会创建 `CourseMaterial` 和 `MaterialParseJob`，worker 异步处理后推进到 `needs_review`；前端 AI 校对页对 `queued` / `processing` 会自动轮询。
- 家长确认草稿后，系统会生成 `KnowledgePack`、`ReviewTask`、`ParentCoachingScript`，并继续异步补齐学习资产配图与英美音 TTS。
- `/reports` 已经是独立报告页，能展示周报基础统计、讲义汇总、`asset_mastery`、复习表现和口语表现。

### 2. Provider 与 AI 能力

- worksheet OCR / parsing 默认走 `AI_PROVIDER=qwen`，由 DashScope compatible Qwen-VL + Qwen text 完成真实识别和结构化抽取。
- 学习资产媒体默认走 `MEDIA_PROVIDER=real` + `MEDIA_IMAGE_PROVIDER=dashscope` + `MEDIA_TTS_PROVIDER=dashscope`。
- 口语评分默认走 `SPEECH_PROVIDER=dashscope` + `SPEECH_ASSESSMENT_PROVIDER=dashscope`，由 DashScope ASR + Qwen 评分完成转写、JSON 打分和反馈生成。
- `doubao` 与 OpenAI 媒体路径仍保留为兼容或对照能力，但都不是当前默认主线。

### 3. 端侧、后台与服务现状

- `apps/mobile` 已覆盖 phone / tablet 的核心页面结构，并有 widget test、harness screen capture 和真机 evidence 入口。
- `apps/admin` 已进入 Phase 1 的 production-shaped 原型阶段：默认使用 mock data 保证可打开，也可接本地 admin API 查看 dashboard / access / audit，并执行少量受控 mutation。
- `services/api` 已具备主链 API、admin read/write API、`AuditEvent`、`TenantProviderPolicy`、`TenantModuleSetting`、`AdminImpersonationSession` 等最小后台支撑。
- `services/workers` 已承接讲义识别、学习资产媒体补齐、speaking 评分和周报聚合，但重试、观测和运维形态仍偏本地验证。

### 4. 验收、证据与治理现状

- `dist/harness/` 当前已有 `HN-003`、`HN-006`、`HN-012`、`HN-014`、`HN-015`、`HN-016A`、`HN-017`、`HN-018` 和 `screens` 目录。
- `HN-017` 不再是“待补真机证据”的状态；当前仓库已保存真机 speaking 上传、worker 回写、attempt JSON、模拟器结果页截图和真机结果页截图。
- `docs/harness/README.md`、`docs/harness/device-regression-runbook.md`、`docs/harness/evidence-archive-policy.md` 已经把真相源、真机层级和证据归档边界收口成统一入口。
- `scripts/harness/generate_evidence_index.py` 已可生成 `dist/harness/evidence-index.json`，减少人工猜测每个 `HN-*` 目录里有哪些证据。

### 5. 当前测试与验证资产

- API 测试目录当前有 `18` 个 `test_*.py` 文件。
- worker 测试目录当前有 `2` 个 `test_*.py` 文件。
- mobile `test/` 与 `tool/harness/` 当前共有 `18` 个测试 / harness 文件。
- admin 前端当前有 `9` 个 `*.test.ts` / `*.test.tsx` 文件。
- `Makefile` 已收口 API / worker / mobile / admin / harness 的主要命令入口。

## 当前可以视为仓库事实的内容

- 当前默认真实路径是 `qwen + DashScope media + DashScope speech`，不是 stub-only，也不是 Doubao-first。
- speaking 已具备真实录音上传、异步评分、结果页展示和周报回填，不再只是 API 预留或 smoke 级样例。
- 后台不再只是“以后再做”的概念稿；`apps/admin` + `/v1/admin/*` 已形成可演示、可继续收敛的第一阶段运营后台骨架。
- HN-019 治理入口已经存在：真机回归、provider 最短复现、evidence 归档和 evidence index 都已经有明确落点。

## 主要缺口

### 1. 跨设备交付仍偏单机化

- Android 交付仍被本机 Flutter / Android SDK 环境阻塞，`make mobile-apk` 还没有形成稳定可复查产物。
- iOS 仍主要依赖 development provisioning 的 Internal/Profile 包；如果要扩大内部试用范围，需要明确设备注册策略或 TestFlight 路线。
- 局域网 API、IPA/APK 产物、公网 `/uploads` 和代理继承这些前置知识虽然已入文档，但还没有形成一套更短的交付手册。

### 2. 文档治理已起步，但复跑纪律还需固化

- runbook 和 archive policy 已补齐，但团队是否持续按同一套文件名、summary 结构和索引入口执行，还需要后续验证。
- `dist/harness/` 仍是本地产物目录，证据是否足够、是否脱敏、是否可替代，仍依赖执行人纪律。

### 3. 后台运营化仍停在 Phase 1

- admin 前端仍以 mock-first 为主，live mode 虽可接本地 API，但还没有完整的 admin session、角色管理、权限变更和更完整的运营页面。
- 当前高风险 mutation 已有最小闭环，但后台仍更像“受控演示原型”，还不是可长期支撑运营工作的产品化控制台。

### 4. 工程化与数据演进仍不足

- Harness 入口已经形成，但还没有把最常见的环境检查、失败分流和证据命名完全自动化。
- provider 网络失败、worker 重试、日志组织和证据归档仍偏本地排障形态。
- 多周趋势、解释层和更稳定的数据分析模型还比较轻，后续增强可能会受当前 JSON-heavy 结构限制。

## 项目级 ToDo

下面按整个项目推进面组织，不再只按单个 HN 编号罗列。

### P0：跨设备交付与真机复跑收口

- [ ] 跑通一次当前机器上的 `make mobile-apk`，把真实 blocker、前置条件、命令和产物路径写回文档。
- [ ] 明确 Android 的最低交付标准：是先拿到 debug APK，还是直接要求可分发测试包。
- [ ] 明确 iOS 内部测试分发策略：继续 development provisioning、集中收集 UDID，还是切到 TestFlight。
- [ ] 写一份最短交付手册，覆盖 `infra/.env`、局域网 API、IPA/APK 产物、公网 `/uploads`、代理继承和常见失败排查。
- [ ] 按 `docs/harness/device-regression-runbook.md` 补一次新的 `HN-019` 真机回归 summary，确认 runbook 不是纸面流程。

完成标准：

- 项目不再只适合熟悉当前机器的人来安装和复现。

### P0：证据治理执行化

- [x] 补齐 `docs/harness/device-regression-runbook.md`。
- [x] 补齐 `docs/harness/evidence-archive-policy.md`。
- [x] 补齐 `make harness-evidence-index` 与 `dist/harness/evidence-index.json` 生成入口。
- [ ] 给新增或替代证据约定统一 summary 字段，至少包括 `run_id`、`started_at`、`device`、`result`、`key_files`。
- [ ] 在下一次 speaking、provider 或主链复跑时验证 evidence index 是否足够支持人工复查。

完成标准：

- 新人只看文档和 evidence index，就能快速知道该看哪个目录、哪个 summary、哪个截图。

### P1：后台从 prototype 推到可运营

- [ ] 明确 `apps/admin` 下一阶段定位：继续作为 IA prototype，还是开始承接真实运营操作。
- [ ] 如果进入真实运营阶段，优先补齐 admin session / auth、角色与权限边界、更多读页和更完整的审计链路。
- [ ] 把已有 live mode 能力按风险分级写清楚：哪些操作可直接演示，哪些仍只建议在本地测试库使用。
- [ ] 为后台 live mode 增加更明确的验收路径、截图证据和失败回滚说明。

完成标准：

- 后台能力的“可演示”与“可运营”边界清楚，不再混在一起。

### P1：主链验收矩阵补强

- [ ] 做一轮平板关键页面人工验收，覆盖 AI 校对、课程详情、报告页、空态和失败态。
- [ ] 决定 `HN-016` OpenAI 媒体路径的项目承诺：继续保留并补最小 evidence，还是明确降级为非默认兼容路径。
- [ ] 复查 speaking、媒体、讲义上传在弱网、代理、缺少公网音频 URL 时的文案与恢复路径。
- [ ] 补一份“失败态证据矩阵”，把 provider 失败、worker 未启动、token 失效、局域网不可达等常见问题对齐到固定说明。

完成标准：

- 主链不仅“功能存在”，而且在设备、网络和异常状态下也更可解释。

### P2：工程化与数据演进

- [ ] 评估把关键 smoke / capture / evidence 入口进一步收敛成更统一的一键编排。
- [ ] 梳理 provider / worker 失败日志结构、重试规则和证据落盘方式，降低后续排障成本。
- [ ] 评估 `learning_assets`、`image_records`、`ReviewTask.content_json`、speaking / report 聚合数据的拆分时机。
- [ ] 为多周趋势、解释层和更稳定的学习分析预留事件化或聚合化数据结构。

完成标准：

- 后续做报告增强、运维观测或更复杂学习分析时，不会先被当前工程边界卡住。

## 建议执行顺序

1. 先用一次真实回归把新的 runbook 和 evidence index 跑通，确认 HN-019 不是只补了文档。
2. 再处理 Android 与 iOS 的交付策略，让项目真正可跨设备复现。
3. 然后决定 admin 是继续停留在 prototype，还是进入真实运营化阶段，并据此收敛后台开发重点。
4. 最后再推进日志、编排、数据模型层面的工程化和下一阶段分析能力。

## 当前判断

- LearningEnglish 的核心价值已经从“证明能上传识别”转向“把已经存在的 AI 学习主链变成可复查、可交付、可运营的系统”。
- 当前最大的剩余不确定性不在主链功能，而在跨设备交付、后台产品化和治理流程是否能持续执行。
- 如果 P0 的真机复跑、交付手册和 evidence 执行纪律能收口，这个仓库会更明确地从“开发者可运行 MVP”进入“团队可持续验证的 MVP”。
