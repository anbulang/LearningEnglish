# Harness Engineering 需求设计

## 目标

LearningEnglish 后续开发默认采用 Harness Engineering 作为需求组织和验收模型。一个需求只有同时说明用户目标、系统边界、验收证据、自动化 harness 命令或人工验证证据，才算进入可开发状态。

第一批需求来自 `docs/harness/mvp-readiness-checklist.md` 中的 MVP 交付缺口。这样可以先补齐当前应用的内测交付能力，再展开更大的产品路线图。

## 文档语言约定

本仓库后续新增或重写的产品、需求、计划、验收、交付文档默认使用中文。

保留英文的内容包括：

- 文件路径、命令、环境变量、API 路径和代码标识符
- 第三方产品名、框架名和标准技术术语
- 已经用于追踪的需求编号，例如 `HN-001`

如果后续需要对外英文材料，应另建英文版本，不覆盖中文主文档。

## 项目背景

当前应用是面向低龄儿童的家长主导英语课后复习产品。已实现的 MVP 主链包括家长登录、手机号绑定、孩子档案创建、讲义上传、AI 解析、家长校对、课程详情、复习任务、口语尝试、亲子陪练和周报。

当前仓库已经具备：

- Flutter 移动端：`apps/mobile`
- FastAPI 服务：`services/api`
- Celery worker：`services/workers`
- 共享 contracts 和 design tokens：`packages`
- 本地基础设施：`infra/docker-compose.yml`
- Harness 脚本：`scripts/harness`
- Readiness 证据：`docs/harness/mvp-readiness-checklist.md` 和 `dist/harness`

## 设计决策

采用 Harness Engineering 作为主要需求结构。

每条需求都作为一个小而可验收的单元追踪，必须包含：

- 稳定需求编号
- 用户或操作者目标
- 当前状态
- 范围内行为
- 范围外行为
- 验收标准
- 自动化 harness 命令
- 自动化不足时的人工证据要求
- 完成定义
- 实施交接说明

这样可以避免把测试、截图、构建日志和 smoke 检查放到开发结束后才补。对于当前应用，harness 必须覆盖三个面：

- API 和 worker 行为
- 移动端 UI 行为
- 打包与设备可用性

## 需求生命周期

### 1. 候选

候选需求可以来自产品设计、缺陷、readiness 缺口、provider 集成或内测反馈。这个阶段可以不完整，但必须说明影响的用户或操作者。

### 2. 可开发

需求只有满足以下条件，才算可开发：

- 系统边界清楚。
- 验收标准写成可观察行为。
- 至少指定一个 harness 路径。
- 对无法完全自动化的流程定义人工证据。
- 范围外说明能够阻止相邻需求蔓延进来。

### 3. 已实现

只有命名的 harness 通过，或者失败被明确记录为环境限制后，代码才可以合并。

### 4. 已验证

需求证据保存到 `dist/harness` 或在需求记录中引用后，才算完成验证。证据可以包括日志、截图、测试输出、构建产物或 provider smoke 输出。

## 需求记录模板

```markdown
### HN-000：需求标题

**目标：** 一句话说明用户、家长、孩子、测试人员或操作者能获得什么结果。

**当前状态：** 今天已经能工作什么，还缺什么。

**范围内：**
- 本需求明确包含的行为。

**范围外：**
- 本需求明确不处理的行为。

**验收标准：**
- 必须成立的可观察条件。
- 必须成立的可观察条件。

**Harness：**
- 自动化：`make <target>` 或精确命令。
- 人工：截图、安装证明、provider 控制台证明或设备证明。

**证据位置：**
- `dist/harness/<requirement-id>/...`

**完成定义：**
- 需求标记完成前必须满足的条件。

**实施说明：**
- 可能涉及的文件、API 或测试。
```

## 第一批需求：MVP Readiness 补齐

### HN-001：规范 MVP readiness harness 报告

**目标：** 操作者运行一个命令后，可以明确知道哪些 MVP readiness 检查通过、警告或失败。

**当前状态：** `make harness-mvp-readiness` 会写入 `dist/harness/mvp-readiness.log`，但 iOS 步骤仍标为 `iOS Debug IPA`，而当前项目实际导出的是 Profile/Internal IPA。

**范围内：**

- 重命名误导性的 harness 步骤标签。
- 保留现有命令入口。
- 保留可选打包 fallback 的 warning 行为。
- 让日志可以直接作为交付证据使用。

**范围外：**

- 改变实际 iOS 构建模式。
- 用新框架替换当前 shell harness。

**验收标准：**

- `HARNESS_RESET=1 make harness-mvp-readiness` 记录 Profile/Internal IPA 语义。
- 日志清楚区分 `PASS`、`WARN` 和 `FAIL`。
- 强制 readiness 失败时命令仍会中止。
- 当核心 MVP harness 已通过时，可选 iOS 或 Android 打包问题仍以 warning 形式可见。

**Harness：**

- 自动化：`HARNESS_RESET=1 make harness-mvp-readiness`
- 人工：检查 `dist/harness/mvp-readiness.log`

**证据位置：**

- `dist/harness/mvp-readiness.log`

**完成定义：** Readiness 日志足够准确，可以直接附到内部测试交付说明中。

**实施说明：** 预计涉及 `scripts/harness/run_mvp_readiness.sh`、`Makefile` 和 `docs/harness/mvp-readiness-checklist.md`。

### HN-002：补齐 Android debug APK fallback readiness

**目标：** 当 iOS provisioning 受阻或不可用时，测试人员仍有 Android fallback 包可用。

**当前状态：** `make mobile-apk` 已存在，但最近的 readiness checklist 记录失败，原因是本机 Android SDK 未配置。

**范围内：**

- 记录 Android SDK 前置条件。
- 让 harness 输出说明失败属于环境问题还是构建问题。
- 构建成功时记录 APK 输出位置。

**范围外：**

- 发布到 Google Play。
- 创建 release 签名 Android 包。
- 支持多个 product flavor。

**验收标准：**

- `make mobile-apk` 要么产出 debug APK，要么以清晰的缺失 SDK 信息失败。
- Readiness checklist 记录精确命令结果和产物路径。
- Android fallback 不再是含糊的未完成项。

**Harness：**

- 自动化：`make mobile-apk`
- 人工：SDK 存在时检查 Flutter 输出的 APK 路径

**证据位置：**

- `dist/harness/mvp-readiness.log`
- `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`

**完成定义：** 开发者可以从证据判断 Android fallback 已就绪，还是仅被本机 SDK 环境阻塞。

**实施说明：** 预计涉及 `README.md`、`docs/harness/mvp-readiness-checklist.md`、`Makefile`，也可能涉及 `scripts/harness/run_mvp_readiness.sh`。

### HN-003：补齐 MVP 主链真实 UI 证据

**目标：** 内部试点评审者可以通过截图确认 App UI 支持主流程。

**当前状态：** 已有登录、首页、上传和报告截图。手机号绑定、AI 校对和课程详情截图缺失或过期，原因是模拟器状态和重置后的后端状态不一致。

**范围内：**

- 定义可重复的 clean-state UI 截图流程。
- 补齐手机号绑定、上传、AI 校对、课程详情和报告截图。
- 将截图保存在稳定位置。

**范围外：**

- 完整视觉回归自动化。
- 像素级截图比对。
- 重设计相关页面。

**验收标准：**

- `dist/harness/screens/` 包含登录、手机号绑定、首页、上传、AI 校对、课程详情和报告截图。
- Checklist 链接或命名每一张截图。
- 截图流程从干净 App 会话和匹配的后端状态开始。

**Harness：**

- 自动化：`make mobile-test` 中的 mobile widget tests
- 人工：模拟器或真机截图

**证据位置：**

- `dist/harness/screens/*.png`
- `docs/harness/mvp-readiness-checklist.md`

**完成定义：** 评审者只看证据目录即可理解完整 MVP UI 路径，不需要自己运行 App。

**实施说明：** 预计涉及 `docs/harness/mvp-readiness-checklist.md`，也可能新增 `scripts/harness` 下的截图辅助脚本。

### HN-004：让移动端会话状态随后端状态一起重置

**目标：** 开发者重置 demo 环境后，不会卡在 invalid-token UI 状态。

**当前状态：** 后端 reset 会让移动端缓存 token 失效。Readiness checklist 记录过 Docker Postgres reset 后，真实 UI 上传返回 `Invalid access token`。

**范围内：**

- 定义模拟器和真机测试的可靠 App 会话重置流程。
- 在 harness 文档中明确什么时候必须清理本地 App 存储。
- 如果能安全自动化，可以考虑一个小型 helper 命令。

**范围外：**

- 生产 token refresh 机制重设计。
- 改变真实认证 provider 行为。

**验收标准：**

- 测试人员在后端 reset 后可以继续跑主 UI 路径，不出现 token mismatch。
- Reset 顺序写入 readiness checklist 或 pilot guide。
- 任何 helper 命令都必须保守，不删除无关开发数据。

**Harness：**

- 自动化：`HARNESS_RESET=1 make harness-mvp-readiness`
- 人工：截图前清理模拟器或真机 App 状态

**证据位置：**

- `dist/harness/mvp-readiness.log`
- `dist/harness/screens/*.png`

**完成定义：** 后端 reset 和移动端 UI 测试不再互相冲突。

**实施说明：** 预计涉及 `docs/harness/mvp-readiness-checklist.md`、`docs/harness/non-technical-pilot-guide.md`，也可能新增 harness helper 脚本。

### HN-005：保留可复现的 iOS 内测包交付流程

**目标：** 内部测试人员可以通过可重复的 Profile/Internal 构建流程安装并启动 iOS App。

**当前状态：** Profile/Internal IPA 导出和一次真机启动已经验证。流程依赖 Team `95RDXKW54K`、Bundle ID `com.anbulang.learningenglish`、已纳入 provisioning 的设备，以及局域网 API URL。

**范围内：**

- 保持 `make mobile-ios-ipa` 作为本地内部包 canonical 命令。
- 记录 API URL 和 provisioning 前置条件。
- 将安装和启动命令作为证据步骤记录。

**范围外：**

- App Store 或 TestFlight 自动化发布。
- 企业分发。
- 自动收集 UDID。

**验收标准：**

- `make mobile-ios-ipa` 导出 `dist/ios/export/learning_english_mobile.ipa`。
- Checklist 记录构建使用的 API base URL。
- 文档记录本地验证用的设备安装和启动命令。

**Harness：**

- 自动化：`make mobile-ios-ipa`
- 人工：`xcrun devicectl device install app ...` 和 `xcrun devicectl device process launch ...`

**证据位置：**

- `dist/ios/export/learning_english_mobile.ipa`
- `dist/harness/mvp-readiness.log`

**完成定义：** 仓库 owner 可以重复执行 iOS 内测包流程，不需要重新摸索签名和 API URL 细节。

**实施说明：** 预计涉及 `README.md`、`Makefile` 和 `docs/harness/mvp-readiness-checklist.md`。

### HN-006：分离 stub provider 和 Doubao provider 验证

**目标：** 开发者可以区分基础 MVP 正确性和真实 AI provider 可用性。

**当前状态：** MVP 默认使用 stub providers。`scripts/harness/smoke_doubao.py` 已有 Doubao 文本和视觉 smoke 检查，但 provider readiness 还不是一条一等需求记录。

**范围内：**

- 保持 stub-provider MVP tests 作为默认 readiness 路径。
- 将 Doubao smoke 定义为可选 provider-readiness 路径。
- 避免在日志中打印 secrets。
- 缺失 provider 配置时明确记录 skipped 或 blocked 状态。

**范围外：**

- 新增更多 AI providers。
- 评估模型质量，超过 connectivity 和 response shape 范围。
- 改变移动端 API contract。

**验收标准：**

- Stub MVP readiness 不需要真实 AI credentials 即可运行。
- 配置 credentials 和 model IDs 后，Doubao smoke 返回文本和视觉成功。
- Doubao 配置缺失时只报告必需变量，不暴露 secret 值。

**Harness：**

- 默认自动化：`make harness-main-chain-smoke`
- Provider 自动化：`services/api/.venv/bin/python scripts/harness/smoke_doubao.py`

**证据位置：**

- `dist/harness/mvp-readiness.log`
- 未来的 provider smoke log，位置在 `dist/harness`

**完成定义：** Readiness 状态可以明确说明失败属于产品主链，还是仅属于外部 provider 配置。

**实施说明：** 预计涉及 `README.md`、`scripts/harness/smoke_doubao.py`、`scripts/harness/run_mvp_readiness.sh` 和 `docs/harness/mvp-readiness-checklist.md`。

### HN-007：建立需求证据包约定

**目标：** 每条未来需求都在可预测位置留下可评审证据。

**当前状态：** `dist/harness` 已经保存证据，但命名约定比较松散。

**范围内：**

- 定义类似 `dist/harness/HN-003/` 的目录约定。
- 定义日志、截图和构建产物的文件命名。
- 后续 specs 和 plans 都引用这些位置。

**范围外：**

- 将大型二进制产物提交进 git。
- 创建远程 artifact store。
- 立即替换已有 `dist/harness/screens`。

**验收标准：**

- 新需求都命名自己的证据目录。
- 日志和截图有稳定文件名。
- Checklist 可以指向证据，不需要描述临时路径。

**Harness：**

- 人工：检查生成的证据包
- 自动化：未来 harness scripts 应写入需求专属目录

**证据位置：**

- `dist/harness/HN-*/`

**完成定义：** 未来 agent 或开发者只读需求记录和证据目录，就能继续工作。

**实施说明：** 预计涉及 `docs/harness/mvp-readiness-checklist.md`、未来 Superpowers specs，以及后续新增的 harness scripts。

## Harness 命令分类

使用以下命令作为初始验证词汇：

- `make api-test`：FastAPI contract、auth、materials、review、report 和 provider failure tests
- `make worker-test`：Celery task boundary tests
- `make mobile-test`：Flutter repository 和 widget tests
- `make mobile-analyze`：Flutter 静态分析
- `make harness-main-chain-smoke`：API 和移动端主链 smoke
- `HARNESS_RESET=1 make harness-mvp-readiness`：带基础设施 reset 的完整本地 readiness 检查
- `make mobile-ios-ipa`：Profile/Internal iOS 包构建
- `make mobile-apk`：Android debug APK fallback
- `services/api/.venv/bin/python scripts/harness/smoke_doubao.py`：真实 Doubao 文本和视觉 connectivity smoke

## 证据规则

- 日志写入 `dist/harness`。
- 在引入需求专属目录前，截图继续放在 `dist/harness/screens`。
- 大型 App 构建产物保留在 `dist/ios` 或 Flutter build 输出路径，在文档中引用。
- Secrets 绝不能打印到日志中。
- Warning 只适用于需求明确标注为可选或环境相关的步骤。
- 强制 harness 失败会阻塞完成。

## 实施计划交接

本设计批准后，下一步在 `docs/superpowers/plans/2026-05-02-harness-engineering-mvp-readiness.md` 编写第一批需求实施计划。

第一份实施计划优先级：

1. HN-001，因为准确的 harness 报告会改善所有后续证据。
2. HN-004，因为 clean state 是可靠截图的前置条件。
3. HN-003，因为可见 UI 证据是当前内部试点最重要的缺口。
4. HN-006，因为 provider 状态不能和产品 readiness 混在一起。
5. HN-002、HN-005 和 HN-007，因为打包和证据约定会补完整个交付闭环。

## 待定决策

- 需求证据可以继续保存在 `dist/harness` 且不进 git，除非后续明确要求把部分证据归档进 docs。
- Android fallback 在开发机确认 Android SDK 可用前，仍保持环境门控状态。
- TestFlight 不属于第一批需求。如果内部分发范围超过 provisioned devices，应单独建立需求。
