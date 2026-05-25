# LearningEnglish 项目进度与 ToDo（2026-05-25）

## 目的

这份文档基于当前仓库代码、测试、`Makefile`、`docs/harness/`、服务 README 与本轮文档治理结果，回答四个问题：

1. 这个项目今天已经做到哪一步。
2. 哪些能力已经稳定成为主线事实。
3. 哪些工作已经写进代码，但还没有完成 readiness 验证。
4. 接下来应该按什么顺序推进项目级 ToDo。

## 当前阶段

当前处于 **MVP 主链已打通，真实媒体 provider readiness 待补截图，HN-017 口语评分闭环代码已落地但真机证据待补** 的阶段。

一句话概括：

> 登录、上传、AI 校对、课程详情、复习、口语评分、周报这条链已经具备代码、测试和 Harness 抓手；当前最需要收口的是 HN-016 / HN-016A 真实媒体证据，以及 HN-017 真机录音上传证据。

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
| `HN-014` 学习资产自动生成 | 已完成 | `learning_assets`、mock 媒体、课程详情媒体状态与主发音切换已接通 |
| `HN-015` 课程资料左滑删除 | 已完成 | API、worker、Flutter 和 Harness 已覆盖 |
| 文档治理第二轮 | 已完成 | README、架构文档、Harness 文档、服务 README、项目状态页已重新对齐当前实现 |
| 资料路由一致性收口 | 已完成 | `material_navigation.dart` 已成为首页/资料库共享路由规则，相关回归测试已存在 |
| `HN-016` 真实媒体 Provider（OpenAI） | 代码已完成，readiness 待证据 | `MEDIA_PROVIDER=real` + OpenAI image/TTS 已接入，仍需补 Harness 证据与环境说明 |
| `HN-016A` DashScope 国内媒体 Provider | 后端媒体链路已验证，readiness 待 UI 证据 | DashScope provider 直连和 worker/storage 回填已通过，仍需补课程详情截图 |
| `HN-017` 孩子录音上传与 AI 语音评分 | 代码已完成，readiness 待真机证据 | 已接入 multipart 录音上传、音频 storage、worker stub 评分、结果页轮询和周报回填 |
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
- 已支持学习资产英美音主发音切换，以及图片、US TTS、UK TTS 的独立状态展示。
- 学习资产媒体 provider 已抽象成 `mock`、OpenAI、DashScope 可配置组合。

### 3. 工程与验收

- `Makefile` 已提供 API、worker、mobile、harness 的稳定入口。
- `docs/harness/` 已形成 requirement/evidence 约定。
- API、worker、Flutter widget/test 已覆盖关键主链。
- iOS Profile/Internal 包、真机安装和局域网 API 测试链路已跑通过。
- 文档入口现在已经能较稳定地指向真实代码、真实命令和真实现状，而不是未来态描述。

## 当前主要缺口

### 1. 真实媒体与语音闭环还没真正“验收完成”

- `HN-016A` 已补 DashScope provider 直连与 worker/storage 回填证据；`HN-016` 仍缺 OpenAI 真实 provider 证据，二者都还缺课程详情截图闭环。
- speaking 已具备录音上传、音频 storage、stub 异步评分、结果页和周报回填；仍缺真实语音评分 provider 适配和真机证据。
- 周报还没有基于学习资产掌握度、练习结果和口语表现给出更可信的学习分析。

### 2. 交付与环境稳定性仍偏“开发者友好”

- Android fallback 仍卡在本机 Flutter/Android SDK 环境。
- Doubao / OpenAI / DashScope 真依赖在部分网络环境下仍可能受代理继承影响，需要显式配置 `AI_HTTP_TRUST_ENV=true` 或 `MEDIA_HTTP_TRUST_ENV=true`。
- `dist/harness/` 证据目前仍主要留在本机路径，没有统一归档面。
- provider 和真机验证已经可做，但还没有形成固定化的“每次变更后如何补证据”的短流程。

### 3. 体验层仍有几处“先复用后独立”的模块

- `/reports` 当前仍复用 `ReviewTasksScreen(reportMode: true)`，还不是独立报告模块。
- 平板端虽然已有适配，但 AI 校对页、课程详情页、资料库的系统性人工验收仍不完整。
- speaking 入口已推进到“可录、可传、可评、可展示”；下一步要补真机证据，并为真实语音评分 provider 设计适配与验收路径。

## 项目级 ToDo

### P0：把真实媒体 provider 从“代码已落地”推进到“readiness 可复查”

- [ ] 跑通 `HN-016` OpenAI 媒体链路，保存 worker log、material JSON、storage 文件清单和课程详情截图到 `dist/harness/HN-016/`。
- [x] 跑通 `HN-016A` DashScope provider 直连与 worker/storage 回填链路，保存配置摘要、material JSON、storage 文件清单到 `dist/harness/HN-016A/`。
- [ ] 补齐 `HN-016A` 课程详情截图，证明真实 DashScope 图片与 US/UK TTS 状态能在移动端展示。
- [ ] 在 `README.md`、`infra/env/local.example.env`、API/worker README 中补全 OpenAI / DashScope / 代理继承的最小配置说明。
- [ ] 明确 `MEDIA_PROVIDER=mock`、`MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER`、`MEDIA_TTS_PROVIDER` 的推荐使用场景，避免本地回归和真实 provider 验证混淆。
- [ ] 为 provider readiness 留一份“最短复现步骤”说明，确保后续不是只有知道上下文的人才能补证据。

完成标准：

- `HN-016` 和 `HN-016A` 都有本地可复查证据目录。
- 新同学可以按文档切换 mock / OpenAI / DashScope，并理解什么时候需要代理继承。

### P0：继续保持文档真相源一致

- [ ] 每次新增状态快照时删除旧的 `docs/project/*-status-and-todo.md`，保持目录中只有最新一份运行状态文档。
- [ ] 把 provider、路由、截图、验证命令的变化优先同步到 README、`docs/harness/`、架构文档和服务 README。
- [ ] 避免在“当前状态”文档里继续使用“本分支”“待 PR 合并”“未来将支持”这类历史语境。
- [ ] 对文档治理变更保留 `rg` 定向搜索与 `git diff --check` 作为固定收尾动作。

完成标准：

- 文档里的“当前状态”可以直接映射到当前代码，而不是某次开发中的临时上下文。

### P1：完成 HN-017 到 HN-018 的学习闭环

- [x] 完成 `HN-017` 中文设计 spec：`docs/superpowers/specs/2026-05-25-hn017-speaking-assessment-design.md`。
- [x] 完成 `HN-017` implementation plan：`docs/superpowers/plans/2026-05-25-hn017-speaking-assessment.md`。
- [x] 实现孩子录音上传接口、对象存储落盘和移动端上传入口。
- [x] 实现 speaking 结果合同，至少包括转写文本、评分、维度反馈和失败态。
- [x] 接入可替换的 speech assessment provider 骨架，并保留 deterministic stub 作为本地默认。
- [x] 把 speaking 评分结果与 `WeeklyReport` 关联起来；`PracticeSession`、`ReviewTask` 更深层掌握度口径放入 HN-018。
- [x] 为口语闭环增加 API、worker、Flutter 和 Harness 验证路径。
- [ ] 补齐 HN-017 真机录音上传、worker 日志、attempt JSON 和结果页截图证据。
- [ ] 定义 HN-018 周报字段：学习资产掌握度、复习完成度、口语表现、家长建议。

完成标准：

- 学习资产不再停留在“可展示、可听”，而是进入“可练、可评、可汇总”。

### P1：补齐移动端体验薄弱点

- [ ] 把 `/reports` 从 `ReviewTasksScreen(reportMode: true)` 演进为独立报告体验。
- [ ] 复查 home / materials / lesson / review 之间的空态、错误态和归档后返回路径。
- [ ] 为平板布局补一轮针对 AI 校对页、课程详情页、资料库的人工验收。
- [ ] 评估上传中断、校对中断、媒体生成失败时是否需要更强的恢复机制。

完成标准：

- 用户不会因为状态切换、资料删除、页面刷新或媒体失败而迷失上下文。

### P2：提升工程交付与环境稳定性

- [ ] 修复 Android SDK / Flutter cache 问题，真正产出 `make mobile-apk` fallback。
- [ ] 增加 CI 或至少本地脚本化的统一验证入口，减少 API、worker、mobile 分头验证的成本。
- [ ] 规范 `dist/harness/` 的归档策略，明确哪些证据必须保留、哪些仅本地临时使用。
- [ ] 补齐 provider、网络代理、局域网 API、签名配置的运维说明。
- [ ] 评估是否需要把常用 readiness 验证转成一键脚本或 checklist。

完成标准：

- 项目不再强依赖“知道历史上下文的人”才能跑通或补证据。

### P2：准备下一轮数据与模型演进

- [ ] 评估 `learning_assets`、`image_records`、`review_tasks.content_json` 的 JSON-heavy 结构是否需要拆表。
- [ ] 设计学习资产版本化和重生成策略，避免后续接入更多 provider 后难以回溯。
- [ ] 规划报告统计口径，明确哪些数据来自复习、哪些来自口语、哪些来自家长确认。
- [ ] 评估 speaking 与 report 的数据闭环是否需要独立事件表或聚合层。

## 建议执行顺序

1. 先完成 `HN-016` / `HN-016A` readiness 证据与环境文档，避免真实媒体能力长期停留在“代码存在但没验收”。
2. 然后补齐 HN-017 真机录音上传证据，确认 speaking 结果页在真实设备上可用。
3. 再做 `HN-018` 报告深化，把学习资产掌握度、复习完成度和口语表现接进周报。
4. 最后处理 Android、CI、证据归档和数据模型演进。

## 当前结论

- 这个项目最难的“上传识别主链”已经不是空白，文档体系也已经从“设计态描述”回到了“代码态事实”。
- 当前最该优先做的不是继续堆新页面，而是把 `HN-016` / `HN-016A` / `HN-017` 从代码能力补到 readiness 证据。
- 只要真实媒体证据、语音评分闭环和报告深化补上，项目就会从“可跑的家庭英语学习 MVP”明显进入“可持续迭代的学习产品基础版”。
