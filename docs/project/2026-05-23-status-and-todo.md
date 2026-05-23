# LearningEnglish 项目进度与 ToDo（2026-05-23）

## 目的

这份文档基于当前仓库代码、测试、`Makefile`、`docs/harness/`、服务 README 与最近一轮文档治理整理项目现状，回答三个问题：

1. 现在这条产品主链已经做到什么程度。
2. 当前还卡在哪些“收口问题”上。
3. 从整个项目角度，下一步应该按什么顺序推进。

## 当前阶段

当前处于 **MVP 主链已打通，正在做文档治理、路由一致性收口和下一阶段能力规划** 的阶段。

一句话概括：

> 登录、上传、AI 校对、课程详情、复习、口语入口、周报这条链已经具备代码、测试和 Harness 抓手；但真实媒体能力、语音评分、报告深化、Android 交付和证据归档还没有完成。

## 里程碑状态

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| `HN-001` ~ `HN-007` Harness Engineering 基础约定 | 已完成 | `make` 入口、证据目录、iOS 内测链路、Doubao smoke 入口已建立 |
| `HN-008` 上传页改为拍照/相册优先 | 已完成 | 上传不再依赖复杂表单 |
| `HN-009` 上传后进入 AI 校对页 | 已完成 | 上传成功、首页、资料库统一走 AI 校对/课程详情分流 |
| `HN-010` job/material 失败状态一致 | 已完成 | API 和移动端已处理失败态与重试 |
| `HN-011` 超时与重试体验 | 已完成 | 有中文错误提示、重试路径和超时文档说明 |
| `HN-012` 真机上传识别证据 | 已完成 | 真机上传、job/material JSON、AI 校对轮询补测已留证据 |
| `HN-013` 图片级记录 | 已完成 | `image_records` 已贯穿上传、校对、详情 |
| `HN-014` 学习资产自动生成 | 已完成 | `learning_assets`、mock 配图与 TTS 已接通 |
| `HN-015` 课程资料左滑删除 | 已完成 | API、worker、Flutter 和 Harness 已覆盖 |
| 文档治理第一轮 | 已完成 | `README`、架构文档、Harness 文档、服务 README 已与当前实现重新对齐 |
| 资料路由一致性收口 | 本分支已完成 | 已抽出 `material_navigation.dart`，并补 home/materials 路由回归测试；待 PR 合并后成为主线事实 |
| `HN-016` 真实 TTS / 标准发音 provider | 未开始 | 当前仍使用 `HN014MockMediaProvider` |
| `HN-017` 孩子录音上传与 AI 语音评分 | 未开始 | speaking 入口已有，真实评分未完成 |
| `HN-018` 学习资产掌握度进入报告页 | 未开始 | 周报仍是轻量聚合 |

## 已经比较稳的部分

### 1. 产品主链

- 家长登录、手机号绑定、孩子档案创建已具备 API 和移动端页面。
- 讲义上传支持多页图片与 `camera` / `gallery` 来源区分。
- 上传会创建后台识别 job，AI 校对页会对 `queued` / `processing` 自动轮询。
- 家长确认后可生成课程详情、知识包、复习任务和亲子陪练脚本。
- 课程资料支持左滑删除，删除后首页、资料库、校对页和下游练习入口会一起收敛。

### 2. AI 与内容结构化

- 已具备 `stub` provider，可在本地无密钥跑通主链。
- 已接入 Doubao OCR / 文本结构化路径，可用于真实识别。
- 已把讲义内容抬升到 `learning_assets` 结构，而不只是词汇/句子列表。
- 已支持学习资产英美音主发音切换。

### 3. 工程与验收

- `Makefile` 已提供 API、worker、mobile、harness 的稳定入口。
- `docs/harness/` 已形成 requirement/evidence 约定。
- API、worker、Flutter widget/test 已覆盖关键主链。
- iOS Profile/Internal 包、真机安装和局域网 API 测试链路已跑通过。
- 文档入口现在已经能较稳定地指向真实代码和真实命令，而不是未来态描述。

## 当前主要缺口

### 1. 真实媒体与语音闭环还没完成

- HN-014 的配图与 TTS 仍是 mock 资源，不是线上 provider。
- speaking 还没有真实录音上传、转写、发音评分和反馈闭环。
- 周报还没有基于学习资产掌握度给出更可信的学习分析。

### 2. 交付与环境稳定性仍偏“开发者友好”

- Android fallback 仍卡在本机 Flutter/Android SDK 环境。
- Doubao 真识别在部分网络环境下依赖 `AI_HTTP_TRUST_ENV=true`，否则 shell 中的代理变量不会被 API/worker 继承。
- `dist/harness/` 证据还主要留在本机路径，没有统一归档面。
- 真机/模拟器人工截图证据仍未完整补齐。

### 3. 体验层还有几处明显“先复用后独立”的模块

- `/reports` 当前仍复用 `ReviewTasksScreen(reportMode: true)`，还不是独立报告模块。
- 平板端虽然已有适配，但 AI 校对页、课程详情页、资料库的人工验收仍不完整。
- 资料路由规则已经在本分支统一为共享 helper，并补齐首页、资料库和长耗时 AI 校对轮询测试；待 PR 合并后成为主线事实。

## 项目级 ToDo

### P0：把当前主链收口成“文档可信、验收可复现”的版本

- [ ] 补齐 `HN-003` / `HN-012` / `HN-014` / `HN-015` 缺失的 AI 校对页、课程详情页、删除成功页截图证据；手机号绑定截图已同步到标准路径。
- [x] 把 `material_navigation.dart` 及 home/materials 路由回归测试合入本分支，避免首页、资料库、复习入口再次分叉。
- [x] 重新跑一轮 API、worker、mobile test 和 mobile analyze，并把最新结果写回 Harness 记录。
- [x] 在 `infra/env/local.example.env`、API、worker 和 infra 文档中补清楚 Doubao 的代理继承说明，明确何时需要 `AI_HTTP_TRUST_ENV=true`。
- [x] 为 `docs/project/` 建立更清晰的“状态文档 vs 文章草稿/素材”边界，避免项目运行文档和内容草稿继续混放。

完成标准：

- 新同学能按 `README` 和 `docs/harness/` 复现主链。
- 首页、资料库、AI 校对页、课程详情的资料跳转规则在代码和文档里保持同一套说法。

### P1：完成 HN-016 到 HN-018 的内容闭环

- [ ] `HN-016`：接入真实 TTS / 标准发音 provider，替换当前 `HN014MockMediaProvider`。
- [ ] `HN-017`：实现孩子录音上传、音频存储、转写和 AI 发音评分。
- [ ] `HN-018`：把学习资产掌握度、复习完成度、口语表现接入周报，而不只是轻量文案聚合。
- [ ] 为学习资产、复习任务、speaking 结果建立更清晰的状态与证据约定。

完成标准：

- 学习资产不再停留在“可展示”，而是进入“可练、可听、可评、可汇总”。

### P1：补齐移动端体验薄弱点

- [ ] 把 `/reports` 从 `ReviewTasksScreen(reportMode: true)` 演进为独立报告体验。
- [ ] 复查 home / materials / lesson / review 之间的空态、错误态和归档后返回路径。
- [ ] 为平板布局补一轮针对 AI 校对页、课程详情页、资料库的人工验收。
- [ ] 评估是否需要为上传中断、校对中断增加更强的恢复机制。

完成标准：

- 用户不会因为状态切换、资料删除、页面刷新而迷失上下文。

### P2：提升工程交付与环境稳定性

- [ ] 修复 Android SDK / Flutter cache 问题，真正产出 `make mobile-apk` fallback。
- [ ] 增加 CI 或至少本地脚本化的统一验证入口，避免 API、worker、mobile 各跑各的。
- [ ] 规范 `dist/harness/` 的归档策略，避免证据只留在本机路径。
- [ ] 补齐 provider、网络代理、局域网 API、签名配置的运维说明。

完成标准：

- 项目不再强依赖“知道历史上下文的人”才能跑通。

### P2：准备下一轮数据与模型演进

- [ ] 评估 `learning_assets`、`image_records`、`review_tasks.content_json` 的 JSON-heavy 结构是否需要拆表。
- [ ] 设计学习资产版本化和重生成策略，避免后续接入真实媒体 provider 后难以回溯。
- [ ] 规划报告统计口径，明确哪些数据来自复习、哪些来自口语、哪些来自家长确认。

## 建议执行顺序

1. 先完成 P0，把当前仓库变成“文档可信、验收可复现、状态一致”的状态。
2. 再推进 HN-016 到 HN-018，真正完成内容与语音闭环。
3. 然后处理 Android、CI、证据归档和环境稳定性。
4. 最后再做数据模型深改和报告体系升级。

## 当前结论

- 这个项目最难的“上传识别主链”已经不是空白，真正风险在于文档、状态机和证据再一次漂移。
- 从项目收益看，最该优先做的不是再堆新页面，而是先把 P0 收口，再接上 HN-016 到 HN-018。
- 当前分支已经完成“资料跳转规则抽共享 helper + 新回归测试 + Harness 记录更新”；下一步是补截图证据并推进 PR 合并。

## 2026-05-23 P0 收口验证

- `services/api/.venv/bin/python -m pytest services/api/tests -q`：`68 passed`
- `services/workers/.venv/bin/python -m pytest services/workers/tests -q`：`9 passed`
- `cd apps/mobile && flutter test`：`33 passed`
- `cd apps/mobile && flutter analyze`：`No issues found`

仍未补齐的 P0 证据：

- `dist/harness/screens/ai-review-screen.png`
- `dist/harness/screens/lesson-detail-screen.png`
- `dist/harness/HN-014/review-learning-assets.png`
- `dist/harness/HN-014/lesson-learning-assets.png`
- `dist/harness/HN-015/material-delete-screen.png`
