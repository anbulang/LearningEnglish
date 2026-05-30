# LearningEnglish 项目进度与 ToDo（2026-05-27）

## 目的

这份文档基于当前仓库代码、测试、`Makefile`、`docs/harness/`、服务 README、`infra/env/local.example.env` 与已落地的脚本/页面路径，回答四个问题：

1. 项目已经做到哪里。
2. 哪些能力已经是当前主线事实。
3. 哪些地方仍然是 readiness 或交付层面的缺口。
4. 接下来应该如何按整个项目视角推进。

## 当前阶段

当前处于 **主链功能已经成型、真实 provider 默认路径已经接通、文档真相源完成新一轮收口，但 readiness 与交付体系还没有完全闭环** 的阶段。

一句话概括：

> 这已经不是“讲义上传 demo”，而是一个具备上传识别、AI 校对、课程详情、复习、口语评分、报告聚合和 Harness 证据约定的家庭英语学习 MVP；当前主要风险不在功能空白，而在真机证据、Android 交付、证据归档和运维化。

## 当前进度概览

### 1. 产品主链

- 家长登录、手机号绑定、孩子档案创建已经具备稳定 API 和移动端路径。
- 讲义上传支持多页图片、`camera` / `gallery` 来源区分和后台异步识别。
- AI 校对页会轮询 `material-jobs`，家长确认后可以生成课程详情、复习任务和陪练脚本。
- 资料删除会同步影响资料库、课程详情、复习入口和下游可见内容。
- `/reports` 已经从旧的复用模式拆成独立 `ReportsScreen`。

### 2. AI 与内容处理

- worksheet OCR / parsing 默认使用 `AI_PROVIDER=qwen`，由 DashScope Qwen-VL + Qwen 文本模型完成识别和结构化抽取。
- Doubao 仍保留为可切换真实 provider，适合做对照 smoke 或网络条件不同的运行环境。
- 学习资产媒体默认走 DashScope：图片生成 + US/UK TTS 已接入并有 worker 回填链路。
- speaking 默认走 DashScope ASR + Qwen 评分，支持 multipart 音频上传、异步 worker 评分、结果页展示和周报回填。

### 3. 移动端体验

- 主路由已稳定：`/home`、`/materials`、`/lessons/:materialId`、`/review`、`/reports`、`/profile`。
- 首页和资料库统一通过 `material_navigation.dart` 决定进入 AI 校对页还是课程详情页。
- AI 校对、课程详情、报告页、口语结果页都已有 widget test 或 harness capture 路径。
- phone / tablet 已有统一语义入口，但平板系统性人工验收还不完整。

### 4. 工程与 Harness

- `Makefile` 已提供 API、worker、mobile、harness 的固定入口。
- `docs/harness/` 已形成 requirement -> command -> evidence path 的复查方式。
- `HN-016A`、`HN-017`、`HN-018` 都已有脚本化 smoke 或 capture 入口。
- 当前文档真相源已经回收到 `README.md`、`docs/architecture/*`、`docs/harness/*`、服务 README 和本状态页。

## 已经可以当作当前事实的内容

- 本地示例和 `docker compose` 默认不是 stub-only，而是 `AI_PROVIDER=qwen` + DashScope media + DashScope speech。
- `speaking_attempts` 不只是预留接口，已经具备上传、轮询、失败重试、真实 provider 和结果页展示。
- `/reports` 不再复用 `ReviewTasksScreen(reportMode: true)`，而是独立报告页。
- `HN-016A`、`HN-017` 和 `HN-018` 可以按文档复查；`HN-017` 已补齐物理手机 speaking 上传、DashScope scored 回写和 iPhone Mirroring 结果页截图。
- 当前最弱的层面是交付与验收，不是主链是否存在。

## 仍然未闭环的地方

### 1. readiness 证据没有全部闭合

- `HN-017` 已有物理手机录音提交、worker 真实评分回写、attempt JSON 和结果页截图。
- `HN-016` OpenAI 媒体路径虽然保留，但当前默认验收集中在 DashScope；如果要继续保留 OpenAI 路径，就需要单独补一轮最小证据。
- 平板关键页面还缺成套人工验收记录。

### 2. 交付路径仍偏开发者友好

- iOS 目前是 Internal/Profile IPA，依赖 development provisioning。
- Android 还没有真正跑出 `make mobile-apk` 可交付结果，当前 blocker 是本机 Android SDK / Flutter 环境。
- provider 切换、代理继承、公网 `/uploads` 暴露等知识仍然分散在多份文档里。

### 3. 工程运维化不足

- `dist/harness/` 的本地证据越来越多，但还没有归档策略、保留规则和统一索引。
- 当前 smoke/test 很多，但还没有形成一个统一的“回归编排层”，执行时仍需要知道历史上下文。
- 日志、重试、监控仍偏本地调试形态。

### 4. 数据与报告层仍偏轻

- 周报已经能返回 `asset_mastery` 和 `material_summaries`，但多周趋势、解释层和更细的分析模型还不强。
- `learning_assets`、`image_records`、`ReviewTask.content_json` 仍是 JSON-heavy 结构，后续扩展要考虑拆分。

## 项目级 ToDo

下面不再只按 HN 编号组织，而按项目推进面组织。

### P0：补齐 readiness 最后缺口

- [x] 用物理手机完成一次 speaking 上传和真实评分回写，保存 API 日志、worker 日志、attempt JSON 到 `dist/harness/HN-017/`。
- [x] 产出 `dist/harness/HN-017/real-device-speaking-summary.json`，把“已验证什么、还剩什么”写清楚。
- [x] 通过 iPhone Mirroring 补齐真机结果页截图。
- [ ] 复查 `docs/harness/provider-readiness-runbook.md` 的命令，确保新同学可以仅按文档复现 `HN-016A` / `HN-017` / `HN-018`。
- [ ] 决定 `HN-016` OpenAI 媒体路径是继续保留并补证据，还是降级为非默认兼容路径。

完成标准：

- 真实语音评分不再停留在模拟器和 smoke 级别。
- 默认真实 provider 路径可被他人按文档复查。

### P0：继续保持文档真相源一致

- [x] 用 `2026-05-27` 状态快照替换 `2026-05-26` 版本，避免并存近似快照。
- [ ] 每次 provider、路由、页面能力变化后，优先同步 `README.md`、`docs/architecture/*`、`docs/harness/*` 和服务 README。
- [ ] 把“当前状态”文档中的历史语境持续清理掉，避免重新出现“本分支”“未来将支持”“待 PR 合并”。
- [ ] 把 `git diff --check` 和定向 stale grep 固化为文档治理收尾动作。

完成标准：

- 用户读入口文档时，不需要猜哪些是旧阶段判断。

### P1：提升交付能力

- [ ] 修复 Android SDK / Flutter 环境，真正产出一次 `make mobile-apk`。
- [ ] 梳理 iOS 包分发策略：继续 development provisioning，还是转 TestFlight / 更标准的内部测试流。
- [ ] 整理 provider 配置、局域网 API、真机包、代理继承和公网 `/uploads` 的最短操作手册。

完成标准：

- 项目不再只适合“熟悉这台机器的人”来安装和验证。

### P1：补齐体验层验收

- [ ] 对 AI 校对页、课程详情页、资料库、报告页做一轮平板人工验收。
- [ ] 复查空态、失败态、归档后返回路径，尤其是 home / materials / lessons / reports 之间的跳转。
- [ ] 评估 speaking 失败、媒体生成失败、上传中断时是否还需要更强的恢复提示。

完成标准：

- 主链不仅能跑通，也能在异常和边界状态下保持方向感。

### P2：工程化与证据治理

- [ ] 给 `dist/harness/` 建立保留规则、目录说明和归档策略。
- [ ] 评估把关键 smoke / capture 入口收敛成更统一的一键命令。
- [ ] 增加更稳定的验证编排，减少“先跑哪个脚本、再看哪个目录”对历史记忆的依赖。
- [ ] 评估 provider 网络问题、worker 重试和失败归类是否需要更明确的运行日志结构。

完成标准：

- readiness 不再只是个人操作经验，而是可移交的工程资产。

### P2：准备下一阶段数据演进

- [ ] 评估 `learning_assets`、`image_records`、`ReviewTask.content_json` 的拆分时机。
- [ ] 设计学习资产版本化/重生成策略，避免后续多 provider 下难以回溯。
- [ ] 评估 speaking / report 是否需要独立事件表或聚合层，支撑更稳定的统计与解释。

完成标准：

- 后续做报告增强或更复杂练习时，不会先被当前 JSON-heavy 结构卡住。

## 建议执行顺序

1. 先补 `HN-017` 物理手机真实评分证据，完成当前最关键的 readiness 缺口。
2. 再决定 `HN-016` OpenAI 路径是否继续维持正式兼容承诺。
3. 随后处理 Android 交付和真机/代理/公网 URL 的最短操作手册。
4. 最后收敛证据归档和回归编排，把当前经验沉淀成更稳定的工程流程。

## 当前结论

- 这个项目现在最重要的不是继续扩页面，而是把已经实现的能力真正变成可复查、可交付、可移交。
- 功能主链已经具备学习产品雏形，下一阶段工作的重心应从“补功能”转向“补证据、补交付、补工程化”。
- 只要补齐 `HN-017` 真机证据并稳定交付链路，LearningEnglish 就会从“开发者可运行 MVP”更明确地进入“团队可持续验证的 MVP”。
