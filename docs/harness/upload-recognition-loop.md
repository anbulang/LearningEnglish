# 讲义上传识别链路 Harness 需求

## 背景

2026-05-05 真机验证中，用户在 iPhone 真机上传讲义后反馈“不能识别”，同时指出上传页要求填写课程标题、老师名、主题的表单不符合预期。用户期望的主流程是：直接拍照或选择讲义图片，由系统识别标题、主题、词汇和句型，家长只在 AI 草稿阶段做校对。

当前实现更接近开发期表单：

1. 上传页先让用户选择图片。
2. 用户还要填写课程标题、老师名、主题。
3. 后端创建 `CourseMaterial` 和 `MaterialParseJob`。
4. 识别只在前端请求 `/material-jobs/{jobId}` 时同步触发。
5. 如果用户从资料库点进课程详情，前端会请求 `/knowledge-packs/{materialId}`；未确认生成知识包前会返回 `404`。

这会让真实用户误以为“上传后没有识别”。

## 真机问题记录

本次真机上传产生了材料：

- `material_id`: `material_5adf552647dd`
- `material_status`: `processing`
- `job_id`: `job_18ded7aa35de`
- `job_status`: `failed`
- `confidence_summary`: `处理失败：Doubao request timeout after 60s`

这里暴露了两个问题：

- Doubao 视觉识别在真实图片上可能超过当前 `AI_REQUEST_TIMEOUT_SECONDS=60`。
- job 失败后，material 仍停留在 `processing`，资料库状态不清楚。

## 下一批需求

### HN-008：上传页改为拍照优先的无表单识别入口

**目标：** 家长打开上传页后，只需要拍照或从相册选择讲义图片，然后点击“开始识别”。

**当前状态：** 上传页展示课程标题、老师名、主题、自动增强等表单字段，且“拍照上传”实际使用相册选择。

**范围内：**
- 提供“拍照”和“从相册选择”两个入口。
- 支持多页讲义图片预览、继续添加、删除或清空。
- 上传前不要求填写标题、老师名、主题。
- 使用默认元数据创建材料：标题 `待识别讲义`，老师 `外教课`，主题为空，日期为当天。

**范围外：**
- 图像裁切、透视矫正、滤镜增强。
- 批量 PDF 导入。
- 用户手动编辑 AI 草稿前置到上传页。

**验收标准：**
- 上传页不再展示 `课程标题`、`老师名`、`主题` 输入框。
- 真机或模拟器上可以直接拍照或从相册选择图片。
- 点击 `开始识别` 后进入 AI 识别/校对状态页。
- 空图片状态下不能提交。

**Harness：**
- 自动化：`cd apps/mobile && flutter test test/features/materials/presentation/scan_review_navigation_test.dart`
- 人工：真机截图保存到 `dist/harness/HN-008/`

**证据位置：**
- `dist/harness/HN-008/`

### HN-009：上传后必须进入识别轮询页

**目标：** 上传成功后，用户看到的是识别中、待校对或失败可重试，而不是直接进入课程详情。

**当前状态：** 上传成功后理论上会跳 AI 校对页，但资料库卡片对未就绪材料仍会跳课程详情，导致知识包 `404`。

**范围内：**
- 上传成功后强制进入 `/materials/review/{jobId}`。
- 未 ready 的资料库卡片不跳课程详情，而是进入对应 job 的处理/校对页或显示“处理中/失败”状态。
- 课程详情只服务 `ready` 材料。

**范围外：**
- 后台异步队列重构。
- 推送通知。

**验收标准：**
- `processing`、`needs_review`、`failed` 材料不会直接请求 `knowledge-packs`。
- 未确认的材料从资料库点击后进入 AI 状态页。
- ready 材料仍进入课程详情。

**Harness：**
- 自动化：移动端 widget test 覆盖资料库路由行为。
- 自动化：API test 覆盖材料响应包含最新 job id。

**证据位置：**
- `dist/harness/HN-009/`

### HN-010：识别失败时 material 和 job 状态一致

**目标：** AI 识别失败后，资料库明确显示失败/可重试，而不是卡在处理中。

**当前状态：** `MaterialParseJob` 可以进入 `failed`，但 `CourseMaterial` 仍可能停在 `processing`。

**范围内：**
- 增加或映射材料失败状态。
- `/material-jobs/{jobId}` 捕获异常时同步更新 material。
- retry 后 material 回到 `processing`。
- UI 展示“识别失败，可重试”。

**范围外：**
- 失败自动重试策略。
- provider 降级策略。

**验收标准：**
- pipeline 失败后 job 状态为 `failed`，material 状态也可被前端明确识别为失败。
- retry 后 job/material 都回到 `processing`。
- 失败卡片不会进入课程详情。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py`
- 自动化：`cd apps/mobile && flutter test`

**证据位置：**
- `dist/harness/HN-010/`

### HN-011：Doubao 超时和重试体验清晰化

**目标：** 豆包请求超时后，家长看到的是可理解的失败说明和重试入口。

**当前状态：** `Doubao request timeout after 60s` 会写入 job，但移动端体验不够清晰。

**范围内：**
- 保留 provider 原始错误，移动端显示中文说明。
- 失败页提供 `重新识别`。
- 文档记录当前超时配置和真实图片可能触发超时。

**范围外：**
- 改换模型。
- 自动压缩图片。
- 动态超时策略。

**验收标准：**
- timeout 失败显示 `识别超时，请重试` 或同等中文提示。
- 重试后重新触发 `/material-jobs/{jobId}` 处理。

**Harness：**
- 自动化：API failure test。
- 人工：真机失败态截图。

**证据位置：**
- `dist/harness/HN-011/`

### HN-012：真机上传识别 harness 记录

**目标：** 真机验证不只记录“能安装启动”，还要记录上传识别链路的结果。

**当前状态：** 已能构建 Profile 包、安装并启动真机；拍照入口曾因 iOS 隐私用途说明缺失直接闪退，已补齐权限配置并重新安装启动。真机上传识别结果仍缺少一次完整的 material/job 证据。

**范围内：**
- 记录真机 API base URL。
- 记录安装/启动命令。
- 记录一次拍照或相册上传后的材料 ID、job ID、状态和截图。

**范围外：**
- 自动控制真机拍照。
- App Store/TestFlight 分发。

**验收标准：**
- `docs/harness/mvp-readiness-checklist.md` 引用本轮真机上传识别结果。
- `dist/harness/HN-012/` 保存截图或日志。

**Harness：**
- 自动化：`flutter build ios --profile --dart-define=API_BASE_URL=http://<mac-ip>:8000/v1`
- 人工：真机操作截图和 API 日志摘录。

**证据位置：**
- `dist/harness/HN-012/`

**2026-05-05 真机补测记录：**
- 设备：`Chaucer`，`19586D29-7FF4-5289-8B83-30AA8C3F273D`。
- API base URL：`http://192.168.2.5:8000/v1`。
- 后端：API/worker 已用当前分支镜像重建；容器内确认 `MaterialStatus.failed` 和 `CourseMaterial.parse_job_id` 存在。
- 构建：`/private/tmp/learningenglish-flutter/bin/flutter build ios --profile --dart-define=API_BASE_URL=http://192.168.2.5:8000/v1` 成功。
- 安装：`xcrun devicectl device install app --device 19586D29-7FF4-5289-8B83-30AA8C3F273D apps/mobile/build/ios/iphoneos/Runner.app --timeout 120` 成功。
- 启动：`xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish --timeout 60` 成功。
- 拍照闪退根因：真机 crash report 显示 `namespace: TCC`，原因是缺少 `NSCameraUsageDescription`。
- 修复：`apps/mobile/ios/Runner/Info.plist` 已补充 `NSCameraUsageDescription`、`NSPhotoLibraryUsageDescription`、`NSPhotoLibraryAddUsageDescription`。
- 证据：`dist/harness/HN-012/Runner-2026-05-05-154100.ips`。
- 当前未完成：重新启动后 API 只记录到 `healthz`、`auth/refresh`、`materials`、`review-tasks`、`reports/weekly` 首页请求；尚未记录新的 `POST /v1/materials` 上传请求。

### HN-013：图片级讲义记录与解析留存

**目标：** 每次拍照或相册选择都要形成可追溯的图片页记录。图片除了参与 AI 解析之外，还要长期保留对应的标题、OCR 文本、单词、句子和细节说明。

**当前状态：** 后端合约已增加 `MaterialImageRecord`；上传、AI 校对和课程详情链路可返回图片级记录。真机上传证据仍并入 `HN-012` 后续补测。

**范围内：**
- 上传时记录每张图片的 `page_index`、`source_type`、原始文件名、URL、object key、content type 和大小。
- AI 解析后记录每张图片的 `image_title`、`ocr_text`、`vocabulary`、`sentences`、`details`。
- 移动端上传页显示图片来源；AI 校对页和课程详情页展示图片级解析明细。

**范围外：**
- 图片级明细编辑。
- 自动真机拍照。
- 图片裁剪、去噪和手动排序。

**验收标准：**
- 上传两张图片后，`material.image_records` 有两条且来源分别可为 `camera`、`gallery`。
- 轮询 job 后，`job.draft_image_records` 和 `material.image_records` 均包含图片标题、单词、句子和细节。
- 确认 job 后，课程详情接口继续返回 `material.image_records`。
- 移动端上传页、AI 校对页、课程详情页均展示图片级记录。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_main_chain_smoke.py::test_upload_poll_confirm_preserves_image_level_records`
- 自动化：`cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/scan_review_navigation_test.dart`
- 人工：真机上传后保存 material/job JSON 摘录和截图。

**证据位置：**
- `dist/harness/HN-013/`
