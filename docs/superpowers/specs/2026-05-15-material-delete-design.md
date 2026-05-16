# HN-015：课程资料左滑删除设计

## 背景

当前资料库中的课程资料只能新增和查看，不能删除。家长在真实使用时会反复拍照、上传、测试识别结果，如果误传图片或识别失败，旧资料会长期留在资料库、课程详情和复习任务中，影响后续复习与报告判断。

HN-015 的目标是让家长可以在资料库列表通过 iOS 标准左滑手势删除一份课程资料。删除后，该课程资料不再出现在资料库中，对应课程详情不可访问，知识包、亲子陪练脚本和复习任务一起移除。

## 目标

本期实现“课程资料级删除”，覆盖用户可见主链：

1. 家长在资料库列表左滑某一份课程资料。
2. 列表露出红色删除操作。
3. 点击删除后弹出确认提示。
4. 家长确认后，后端删除该资料对应的可复习派生数据，并把课程资料归档。
5. 前端刷新资料库和复习任务列表，已删除资料不再可见。
6. 如果用户停留在旧课程详情、AI 校对或复习入口，接口返回不可访问状态，前端引导回资料库。

## 非目标

本期不做以下能力：

- 删除孩子档案、家长账号或全量用户数据。
- 提供回收站、撤销删除或恢复课程。
- 物理删除对象存储中的原始图片、生成图片和 TTS 音频。
- 回算历史周报、历史练习会话或已经生成的统计数据。
- 批量删除、多选删除或自动清理旧数据。

## 删除语义

课程资料采用“软删除 + 派生数据硬删除”的策略。

软删除对象：

- `CourseMaterialModel`：状态更新为 `archived`，保留原始记录、图片记录、学习资产和审计信息。

硬删除对象：

- `KnowledgePackModel`
- `ReviewTaskModel`
- `ParentCoachingScriptModel`

暂不物理删除的对象：

- `MaterialParseJobModel`：保留历史处理记录，但归档资料对应的 job 不再允许校对、确认或重试。
- `StoredAssetModel` 和对象存储文件：保留原始文件和媒体文件，避免本期引入存储引用计数、异步清理和误删风险。
- `PracticeSessionModel`、`SpeakingAttemptModel`、`WeeklyReportModel`：属于历史行为或统计记录，本期不回算、不清除；用户可见入口随资料和复习任务删除而消失。

删除必须以家长账号所有权为边界。不存在、非当前家长所有的资料返回 `404`。当前家长所有但已经归档的资料再次删除时返回成功，保证前端重复点击或网络重试不会造成异常体验。

## API 设计

新增接口：

```http
DELETE /v1/materials/{material_id}
```

行为：

- 校验当前家长是否拥有该资料所属孩子档案。
- 如果资料不存在或不属于当前家长，返回 `404`。
- 如果资料已归档，返回 `204`。
- 如果资料未归档，在一个数据库事务中：
  - 将 `CourseMaterialModel.status` 更新为 `archived`。
  - 删除该 `material_id` 下的 `KnowledgePackModel`。
  - 删除该 `material_id` 下的 `ReviewTaskModel`。
  - 删除该 `material_id` 下的 `ParentCoachingScriptModel`。
  - 提交后返回 `204`。

现有读取接口调整：

- `GET /v1/materials` 不返回 `archived` 资料。
- `GET /v1/materials/{material_id}` 对 `archived` 资料返回 `404`。
- `PATCH /v1/materials/{material_id}/learning-assets/{asset_id}/primary-accent` 对 `archived` 资料返回 `404`。
- `GET /v1/knowledge-packs/{material_id}` 对 `archived` 资料返回 `404`。
- `GET /v1/material-jobs/{job_id}`、`POST /confirm`、`POST /retry` 如果 job 对应资料已归档，返回 `404`，不再泄露草稿或重新激活资料。

## 后台任务行为

删除可能发生在 AI 识别或媒体生成任务仍在执行时，因此 worker 必须识别归档状态。

`materials.process_material_job`：

- 任务开始时，如果资料已经 `archived`，直接跳过。
- 写回 job/material 前再次检查资料状态。
- 如果资料已归档，不写回 `needs_review`、`ready`、`failed` 等可见状态，不重建知识包和复习任务。

`materials.process_learning_asset_media`：

- 任务开始时，如果资料已经 `archived`，直接跳过。
- 写回学习资产媒体状态前再次检查资料状态。
- 归档资料不再补齐图片或 TTS，不改变可见状态。

这些保护保证用户删除后，不会因为后台任务晚到而让资料重新出现在列表中。

## 移动端设计

资料库列表中每张课程资料卡片支持左滑。

交互：

- 左滑显示红色删除动作，图标使用 `Icons.delete_outline_rounded`，文案为 `删除`。
- 点击删除后弹出确认框：
  - 标题：`删除这份课程资料？`
  - 内容：`删除后课程详情、知识点和复习任务将一起移除。`
  - 取消按钮：`取消`
  - 确认按钮：`删除`
- 用户取消时，不调用 API，卡片保持原状。
- 用户确认时，调用 `DELETE /v1/materials/{id}`。
- 删除中禁用重复提交，并保持列表稳定。
- 删除成功后刷新资料库列表和复习任务列表。
- 删除失败时恢复卡片，显示中文错误提示：`删除失败，请稍后重试。`

页面路由：

- 已删除资料的详情页加载失败时，展示 `课程资料不存在或已删除`，提供 `回到资料库`。
- 复习任务列表刷新后不再展示该资料生成的任务。
- 如果旧路由仍尝试进入本课复习、口语陪练或亲子陪练，依赖后端 `404` 和现有错误面板引导返回。

## 数据一致性

需要满足以下一致性规则：

- 资料库列表和首页最近课程都不能出现 `archived` 资料。
- 知识包、亲子陪练脚本和复习任务必须在删除事务中一起移除。
- 删除已确认课程后，课程详情接口不可访问。
- 删除待校对或处理中课程后，AI 校对页不可继续确认或重试。
- 删除失败不能在前端造成“看似已删、刷新又回来”的状态漂移。
- 后台 worker 不能把已归档资料重新改为 `processing`、`needs_review`、`ready` 或 `failed`。

## Harness 归属

新增需求编号：`HN-015 课程资料左滑删除`。

后续实施计划需要更新：

- `docs/harness/upload-recognition-loop.md`：增加 HN-015 需求、范围、验收标准和证据目录。
- `docs/harness/mvp-readiness-checklist.md`：增加 HN-015 checkbox，未完成前不标记本批资料库可维护性完成。
- 证据目录：`dist/harness/HN-015/`。

## 测试计划

API 测试：

- 删除当前家长拥有的 ready 资料后返回 `204`。
- 删除后 `GET /v1/materials` 不再返回该资料。
- 删除后 `GET /v1/materials/{material_id}` 返回 `404`。
- 删除后 `GET /v1/knowledge-packs/{material_id}` 返回 `404`。
- 删除后对应 `ReviewTaskModel` 和 `ParentCoachingScriptModel` 不存在。
- 删除处理中资料后，`GET /v1/material-jobs/{job_id}`、`confirm`、`retry` 返回 `404`。
- 非当前家长资料删除返回 `404`。
- 重复删除当前家长已归档资料返回 `204`。
- worker 在资料已归档时跳过写回，不会重新创建知识包或复习任务。

Flutter 测试：

- 资料库卡片左滑后显示删除操作。
- 点击删除后显示确认框。
- 点击取消不调用 repository。
- 点击确认调用 repository 的删除方法。
- 删除成功后刷新资料库 provider 和复习任务 provider。
- 删除失败时显示中文错误，并保留卡片。
- 已删除资料详情接口返回错误时，课程详情页展示中文不可用状态。

手工验证：

- 模拟器或真机上传一份讲义并确认课程。
- 在资料库左滑删除该课程。
- 确认资料库不再显示该课程。
- 进入复习页，确认该课程对应复习任务消失。
- 使用 API 抽查 material、knowledge pack、review tasks 状态。
- 保存截图、API JSON 摘录和测试日志到 `dist/harness/HN-015/`。

## 验收标准

- 资料库课程卡片支持左滑删除。
- 删除前有明确确认，不会误触直接删除。
- 删除成功后课程资料、课程详情、知识包、亲子陪练脚本和复习任务对用户不可见。
- 待识别、待校对、识别失败和已确认课程都能删除。
- 删除后后台任务不会把资料重新写回可见状态。
- 自动化测试覆盖 API 删除语义、worker 归档保护和移动端左滑确认流程。
- Harness 文档包含 HN-015，并记录本地验证证据路径。
