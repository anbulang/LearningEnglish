# HN-014：讲义学习资产自动生成设计

## 背景

HN-008 到 HN-013 已经把讲义上传、AI 识别、图片级记录、AI 校对和课程详情打通。当前系统已经能从讲义中抽取标题、主题、词汇、句子和逐页解析，但这些内容还不足以稳定支撑后续的词卡、题库、发音、配图和报告闭环。

HN-014 的目标是把“讲义解析结果”提升为“可复习学习资产”。学习资产会先作为 AI 草稿展示给家长确认，确认后固化到课程详情，并作为后续题库、TTS 发音、孩子录音评分和报告分析的基础数据。

## 目标

上传讲义后，AI 生成一组可直接用于复习的核心学习资产草稿。家长在 AI 校对页查看这些资产，确认后系统把资产长期保存在课程材料中，并让课程详情可以展示这些资产。

本期要证明的主链是：

1. 家长上传讲义图片。
2. AI 识别讲义并生成 `learning_assets` 草稿。
3. AI 校对页展示核心学习资产。
4. 家长确认后，课程材料保存正式 `learning_assets`。
5. 课程详情展示正式学习资产。
6. 现有 `KnowledgePack` 和 `ReviewTask` 可以从学习资产派生，后续继续扩展题库和评分。

## 非目标

本期不做以下能力：

- 家长逐项编辑、增删学习资产。
- 自动生成配图图片文件。
- 自动生成或缓存 TTS 音频文件。
- 孩子录音上传和 AI 语音评分。
- 复杂题库模板管理。
- 多轮 AI 纠错或家长二次确认流程。

## 学习资产定义

每份讲义生成总量 1 到 20 个核心学习资产。AI 根据讲义长度和内容复杂度决定数量，不强行凑数。

资产类型包括：

- `word`：单词，例如 `queen`、`duck`、`rabbit`。
- `phrase`：短语，例如 `question mark`、`run fast`。
- `sentence`：句子或句型，例如 `Find the queen.`、`A rabbit can hop fast.`。

AI 必须过滤：

- 教师说明。
- 页码。
- 版权信息。
- 出版社信息。
- 重复文本。
- 与孩子复习无关的低价值文本。

每条学习资产包含：

- `id`：资产 id。
- `text`：英文原文。
- `kind`：`word | phrase | sentence`。
- `translation`：中文释义。
- `source_page_index`：来源图片页，从 1 开始。
- `pronunciation_text`：用于发音或 TTS 的文本。
- `image_prompt`：后续生成或检索配图时使用的中文提示。
- `difficulty`：`easy | medium | hard`。
- `teaching_note`：给家长的简短教学说明。
- `is_core`：是否核心资产，本期默认保存核心资产。

## 数据模型

新增合约模型 `LearningAsset`。

`MaterialParseJob` 新增：

- `draft_learning_assets: list[LearningAsset]`

`CourseMaterial` 新增：

- `learning_assets: list[LearningAsset]`

数据写入规则：

- 上传时不创建学习资产，只创建图片记录和 job。
- AI 解析完成后写入 `job.draft_learning_assets`。
- AI 校对页读取 `draft_learning_assets` 展示草稿。
- 家长确认后，把 `draft_learning_assets` 固化为 `material.learning_assets`。
- 如果 provider 未返回 `learning_assets`，系统从已有 `draft_vocabulary` 和 `draft_sentences` 生成 fallback 学习资产，保证课程详情不为空。

## AI Provider 要求

Doubao 结构化输出必须新增 `learning_assets` 数组。

提示词要求：

- 只返回可解析 JSON。
- `learning_assets` 总量 1 到 20。
- 优先选择适合低龄儿童复习的词、短语和句子。
- 每条资产必须关联 `source_page_index`。
- 中文释义要短，不写长段解释。
- `image_prompt` 用中文描述可画或可检索的具体画面。
- 不把教师说明、页码、版权、出版社信息放入资产。

provider 输出缺失字段时，后端使用安全默认值补齐。

## 后端行为

上传接口保持当前异步链路：

- `POST /v1/materials` 创建 material/job 并入队。
- worker 执行讲义解析。
- `GET /v1/material-jobs/{job_id}` 只返回当前 job 状态和草稿。
- `POST /v1/material-jobs/{job_id}/confirm` 固化草稿并生成课程详情所需数据。

确认阶段不再等待外部模型。最终 `KnowledgePack` 和 `ReviewTask` 先基于已确认的 `learning_assets` 本地生成，避免再次引入确认超时。

## 移动端行为

AI 校对页新增学习资产区块：

- 标题：`核心学习资产`
- 展示每条资产的英文、中文释义、类型、来源页和家长说明。
- 资产只读，不提供逐项编辑。

课程详情页新增或增强学习资产展示：

- 展示词、短语、句子混合资产。
- 保留来源页信息。
- 展示中文释义和教学说明。
- 后续题库和发音能力从这里继续扩展。

## 验收标准

API 验收：

- 上传两张讲义图片后，job 进入 `needs_review` 时包含 `draft_learning_assets`。
- `draft_learning_assets` 数量在 1 到 20 之间。
- 每条资产包含 `text/kind/translation/source_page_index/pronunciation_text/image_prompt/difficulty/teaching_note/is_core`。
- 确认 job 后，material 包含 `learning_assets`。
- provider 未返回 `learning_assets` 时，fallback 能从词汇和句子生成非空学习资产。

移动端验收：

- AI 校对页展示学习资产草稿。
- 课程详情页展示已确认学习资产。
- 用户不能逐项编辑学习资产。
- 上传、校对、确认、课程详情主链不出现 30 秒确认超时。

Harness 验收：

- 更新 `docs/harness/upload-recognition-loop.md`，新增 HN-014。
- 更新 `docs/harness/mvp-readiness-checklist.md`，新增 HN-014 状态。
- 证据目录使用 `dist/harness/HN-014/`。
- 保存至少一份 material/job JSON 摘录，证明 `draft_learning_assets` 和 `learning_assets` 均存在。

## 测试计划

后端测试：

- 合约序列化和反序列化测试。
- Doubao payload 解析测试。
- fallback 学习资产生成测试。
- worker 成功写入 `draft_learning_assets` 测试。
- confirm 后写入 `material.learning_assets` 测试。
- 确认阶段不调用外部 provider 的回归测试。

Flutter 测试：

- repository 能解析 `learning_assets`。
- AI 校对页展示学习资产。
- 课程详情页展示学习资产。
- 上传到校对到详情的导航测试继续通过。

手工验证：

- 使用 Qq/Rr 两张讲义图上传。
- AI 校对页看到 1 到 20 个核心学习资产。
- 课程详情页能看到相同资产。
- API 日志和数据库记录保留对应 material/job 证据。

## 风险与处理

- provider 可能返回过多或过少资产：后端做数量裁剪，少于 1 时触发 fallback。
- provider 可能把教师说明放入资产：提示词约束并在测试样例里覆盖。
- 中文释义可能过长：后端可保留原值，本期先通过 prompt 控制；后续再加长度约束。
- 配图提示不是图片文件：字段命名为 `image_prompt`，避免误解为已生成图片。
- 题库生成质量依赖资产质量：本期先固化学习资产，题库增强作为后续需求。

## 后续需求候选

- HN-015：基于学习资产生成题库。
- HN-016：标准发音和 TTS 音频生成。
- HN-017：孩子录音上传与 AI 语音评分。
- HN-018：学习资产掌握度进入报告页。
