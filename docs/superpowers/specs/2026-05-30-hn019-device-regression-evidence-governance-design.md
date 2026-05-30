# HN-019：真机回归与证据治理硬化设计

## 背景

`HN-016A`、`HN-017`、`HN-018` 已经把真实 provider、真机 speaking、独立报告页推进到可验证状态。当前风险不再是主链功能是否存在，而是三件事还不够可移交：

1. 真机回归依赖操作者记住本机网络、设备、API、worker 和截图顺序。
2. provider 运行手册分散在 README、Harness 文档、环境示例和历史计划里。
3. `dist/harness/` 证据目录越来越多，但缺少统一索引、保留规则和归档边界。

HN-019 的目标是把这些经验固化为工程资产，让下一位开发者能按文档复跑、排障、归档，而不是依赖历史上下文。

## 目标

- 建立一份真机回归 runbook，覆盖 iPhone 真机从安装启动到上传讲义、AI 校对、课程详情、speaking、reports 的最短复查路径。
- 强化 provider readiness runbook，把 Qwen / DashScope / Doubao / OpenAI 的默认关系、环境变量、代理、公网 `/uploads` 和失败判定集中说明。
- 建立 evidence 归档策略，明确 `dist/harness/HN-*` 下哪些文件是关键证据、哪些可重生成、如何命名、如何脱敏、如何生成索引。
- 新增一个轻量 evidence index 脚本，用本地文件系统扫描生成 `dist/harness/evidence-index.json`，避免人工猜测每个 HN 有哪些证据。
- 更新项目状态和入口文档，让“当前真相源”和“历史设计/计划材料”边界清楚。

## 非目标

- 不新增新的产品功能页面。
- 不改变现有 provider 实现、worker 队列、移动端主链或 API 合同。
- 不把 `dist/harness/` 大体积证据纳入 git；证据仍默认留在本地或外部归档介质。
- 不要求本阶段必须重新跑一次完整真机回归；实现阶段可以先把 runbook 与索引脚本补齐，再按设备状态决定是否复跑。

## 方案概览

采用“文档真相源 + 可执行索引脚本 + 可选真机复跑”的小闭环：

- 文档真相源放在 `docs/harness/` 和 `docs/project/`。
- 证据实体仍放在 `dist/harness/HN-*`。
- 脚本只扫描本地证据并输出 JSON 索引，不上传、不删除、不改写原始证据。
- 真机回归按分层等级执行，避免每次都要求完整真实 provider 成本。

## 真机回归设计

新增 `docs/harness/device-regression-runbook.md`，把真机验收拆为四个等级：

| 等级 | 目的 | 必需条件 | 证据 |
| --- | --- | --- | --- |
| R0 | 本地构建和文档准备 | 不需要真机 | 命令输出、环境检查结果 |
| R1 | 真机安装启动 | iPhone 解锁、签名可用 | 设备信息、安装/启动日志、首页截图 |
| R2 | 主链体验回归 | API/worker 可访问，App 指向局域网 API | 上传、AI 校对、课程详情、报告页截图和 API 日志 |
| R3 | 真实 provider 回归 | `DASHSCOPE_API_KEY`、公网 `/uploads` 或对象存储 URL | provider summary、worker log、scored JSON、真机结果页截图 |

runbook 需要明确：

- 如何确认设备状态，例如 `xcrun devicectl device info lockState`。
- 如何确认 App 使用的 `API_BASE_URL`。
- 如何启动 API 和 worker。
- 如何保存 API log、worker log、截图和 summary JSON。
- 真机锁屏、网络不可达、provider 无法访问公网音频 URL 时如何判断为 blocked，而不是误判为功能失败。

## Provider 运行手册设计

继续使用并扩展 `docs/harness/provider-readiness-runbook.md`，把 provider 说明收敛成五块：

1. 默认路径：`AI_PROVIDER=qwen`、`MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`。
2. provider 矩阵：Qwen/DashScope 为当前默认；Doubao/OpenAI 是兼容或对照路径。
3. 环境变量：只引用 `infra/env/local.example.env`，避免继续出现不存在或过时的 `.env.example` 入口。
4. 网络与代理：明确 `*_HTTP_TRUST_ENV=false` 默认不继承系统代理；需要代理时显式开启并记录。
5. 失败分类：配置缺失、DNS/网络不可达、公网 `/uploads` 不可拉取、provider 超时、provider 返回格式不合法。

手册不得打印真实 key，不把包含 token、签名 URL、完整 provider 请求体的内容写入公开文档。

## Evidence 归档策略设计

新增 `docs/harness/evidence-archive-policy.md`，定义以下规则：

- 每个 HN 目录应优先保留 `summary.json` 或等价摘要文件，摘要内记录时间、命令、环境、结果、关键证据文件相对路径。
- API/worker 日志必须脱敏；不能包含 API key、Authorization header、签名 URL 或完整 secret。
- 截图保留最终用户可见状态；失败截图应配套失败原因 summary。
- 大文件、重复截图、临时数据库、原始 provider 响应默认不提交 git，只在本地或外部归档介质保留。
- 证据命名优先稳定文件名；如果同一 HN 多次复跑，在 summary 中记录 `run_id`、`device`、`started_at`，必要时按日期建子目录。
- 已被新证据取代的旧证据不得直接删除，除非已经有 summary 说明替代关系。

## Evidence Index 脚本设计

新增 `scripts/harness/generate_evidence_index.py`：

- 扫描 `dist/harness/` 下的 `HN-*` 目录。
- 识别常见证据类型：`summary*.json`、`*.log`、`*.png`、`*.jpg`、`*.mp3`、`*.wav`、`*.json`。
- 输出 `dist/harness/evidence-index.json`。
- 输出内容只包含相对路径、文件大小、mtime、类型推断和是否存在 summary。
- 不读取或打印敏感内容，不上传，不删除，不压缩。

后续可以再扩展成归档包生成，但 HN-019 第一版只做索引。

## 文档更新边界

实现阶段应更新：

- `README.md`：把项目状态页链接和 Harness 入口指向最新文档。
- `docs/project/README.md`：明确同一时间只保留最新状态快照。
- 最新 `docs/project/YYYY-MM-DD-status-and-todo.md`：把真机回归、provider runbook、evidence governance 纳入 P0/P1。
- `docs/harness/mvp-readiness-checklist.md`：补充 HN-019 的验收项，不把已有 HN-017 证据重新标成待补。
- `docs/harness/provider-readiness-runbook.md`：按本设计收敛 provider 操作说明。

历史 `docs/superpowers/specs/*` 和 `docs/superpowers/plans/*` 作为设计/计划记录保留，不作为当前运行真相源。

## 验证计划

- 文档检查：
  - `git diff --check`
  - 定向 stale grep：`2026-05-27`、`待补证据`、`infra/.env.example`
  - 检查新文档链接路径存在。
- 脚本检查：
  - 在没有 `dist/harness/` 时能输出空索引或清晰提示。
  - 在已有 HN evidence 时能生成 `evidence-index.json`。
  - 输出 JSON 可通过 `python -m json.tool`。
- 回归检查：
  - R0 可以在无真机状态下完成。
  - R1/R2/R3 在真机和 provider 条件满足时按 runbook 执行并保存证据。

## 验收标准

- 新同学能从 `docs/harness/device-regression-runbook.md` 判断需要什么设备、服务、网络和证据文件。
- provider 运行手册能解释默认 provider、如何切换、如何处理代理和公网 `/uploads`。
- `dist/harness/` 的关键证据能被 index 脚本发现，并形成可读 JSON。
- 项目状态文档不再把已经闭环的 HN-017 真机 evidence 写成待补。
- HN-019 不引入新的业务主链行为变化。

## 风险与处理

- 真机不可用：按 R0 完成文档和索引脚本，R1/R2/R3 标记为 blocked 并说明设备状态。
- provider 不可用：保留 provider smoke 的 blocked 结果，不回退 mock 冒充真实证据。
- evidence 泄密：脚本只做文件元数据索引，不读取敏感文件内容；文档明确脱敏要求。
- 文档漂移：把 stale grep 和 `git diff --check` 写入 HN-019 收尾条件。
