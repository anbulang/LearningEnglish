# 讲义上传识别链路 Harness 需求

## 背景

2026-05-05 真机验证中，用户在 iPhone 真机上传讲义后反馈“不能识别”，同时指出上传页要求填写课程标题、老师名、主题的表单不符合预期。用户期望的主流程是：直接拍照或选择讲义图片，由系统识别标题、主题、词汇和句型，家长只在 AI 草稿阶段做校对。

这份文档保留了问题来源、需求拆解和 Harness 验收要求。需要注意：HN-008 到 HN-015 当前已经基本落地，下面的“当时现状”主要用于解释为什么会产生这批需求，不代表仓库此刻仍停留在那个阶段。

当前仍未收口的部分主要有两类：

- 人工截图证据还没全部补齐，尤其是 AI 校对页、课程详情页和删除成功页。
- Doubao 真识别在部分网络环境下仍可能受代理继承影响；如果 shell 已配置 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` 但 worker 仍无法访问外网，需要额外设置 `AI_HTTP_TRUST_ENV=true`。

## 触发问题时的旧现状

1. 上传页先让用户选择图片。
2. 用户还要填写课程标题、老师名、主题。
3. 后端创建 `CourseMaterial` 和 `MaterialParseJob`。
4. 识别当时没有稳定地通过后台队列自动推进到可校对状态。
5. 如果用户从资料库点进课程详情，前端会请求 `/knowledge-packs/{materialId}`；未确认生成知识包前会返回 `404`。

这会让真实用户误以为“上传后没有识别”。

## 当前收敛状态

- 上传页已经改为拍照/相册优先，不再要求先填表单。
- 上传后会创建后台 job，并进入 AI 校对页。
- AI 校对页会对 `queued` / `processing` 自动轮询。
- 首页与资料库对未完成资料统一进入 AI 校对页。
- `failed`、`needs_review`、`ready`、`archived` 的状态收敛已经体现在 API、Flutter 路由和 Harness 文档中。
- HN-012、HN-013、HN-014、HN-015 都已经有代码和证据落点，剩余主要是截图补齐和下一阶段能力建设。

## 真机问题记录

本次真机上传产生了材料：

- `material_id`: `material_5adf552647dd`
- `material_status`: `processing`
- `job_id`: `job_18ded7aa35de`
- `job_status`: `failed`
- `confidence_summary`: `处理失败：Doubao request timeout after 60s`

这里暴露了两个问题：

- Doubao 视觉识别在真实图片上可能超过 60 秒，真实讲义验证建议 `AI_REQUEST_TIMEOUT_SECONDS=180` 起步。
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
- AI 状态页在 `queued` 或 `processing` 时自动轮询 job，不依赖家长手动点击刷新。
- ready 材料仍进入课程详情。

**Harness：**
- 自动化：移动端 widget test 覆盖资料库路由行为。
- 自动化：API test 覆盖材料响应包含最新 job id。

**证据位置：**
- `dist/harness/HN-009/`

**2026-05-22 补测记录：**
- 真机上传后用户反馈 AI 校对页一直停留在处理中。
- 根因：移动端 `MaterialReviewScreen` 只在进入页面时读取一次 job，`queued/processing` 状态没有自动轮询；worker 完成后页面不会自动切换到家长校对态。
- 修复：AI 校对页在 `queued/processing` 状态下每 3 秒刷新 `materialJobProvider`，进入 `needs_review`、`ready` 或 `failed` 后停止轮询。
- 回归：`flutter test test/features/materials/presentation/scan_review_navigation_test.dart --plain-name "AI review page auto refreshes processing jobs"`。

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

**当前状态：** 已能构建 Profile 包、安装并启动真机；拍照入口曾因 iOS 隐私用途说明缺失直接闪退，已补齐权限配置并重新安装启动。2026-05-22 已补齐一次重新安装 App 后的真机上传识别 material/job 证据。

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

**2026-05-22 真机补测记录：**
- 设备：`Chaucer`，`19586D29-7FF4-5289-8B83-30AA8C3F273D`。
- API base URL：`http://192.168.2.15:8000/v1`。
- 构建：`flutter build ios --profile --dart-define=API_BASE_URL=http://192.168.2.15:8000/v1` 成功，产物为 `apps/mobile/build/ios/iphoneos/Runner.app`。
- 安装：`xcrun devicectl device install app --device 19586D29-7FF4-5289-8B83-30AA8C3F273D build/ios/iphoneos/Runner.app --timeout 120` 成功。
- 启动：`xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish --timeout 60` 成功。
- 真机来源 IP：`192.168.2.16`。
- API 日志：`POST /v1/auth/wechat/login` 返回 `200 OK`，`POST /v1/children` 返回 `201 Created`，`POST /v1/materials` 返回 `201 Created`。
- worker 日志：收到 `materials.process_material_job`，调用 Doubao `/responses` 返回 `200 OK`，最终 `job_d5219576911b` 进入 `needs_review`。
- 结果：`material_d23e45e7b76f` 状态为 `needs_review`；`job.draft_image_records` 为 4 条，`job.draft_learning_assets` 为 12 条。
- 证据：`dist/harness/HN-012/real-device-summary.json`、`real-device-job-final.json`、`real-device-material-detail.json`、`real-device-material-list.json`。

**2026-05-22 真机 AI 校对轮询补测：**
- API base URL：`http://192.168.2.15:8000/v1`，真机来源 IP 为 `192.168.2.16`。
- 修复点：AI 校对页对 `queued` / `processing` job 每 3 秒自动刷新；首页、资料库列表和平板预览统一按资料状态路由，未完成资料进入 AI 校对页，只有 `ready` 资料进入课程详情。
- API 日志：真机删除旧资料后重新上传，`POST /v1/materials` 返回 `201 Created`，随后自动轮询 `GET /v1/material-jobs/job_7ec0b76ec07b`。
- worker 日志：`materials.process_material_job` 调用 Doubao `/responses` 返回 `200 OK`，最终 `job_7ec0b76ec07b` 进入 `needs_review`，耗时约 69 秒。
- 代理诊断：worker 日志显示 `AI_HTTP_TRUST_ENV=false`，环境里存在 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`，但 AI HTTP client 不继承系统代理。
- 结果：`material_d01ce38fc51f` 状态为 `needs_review`；`job.draft_image_records` 为 2 条，`job.draft_learning_assets` 为 12 条，图片来源为 `gallery`。
- 证据：`dist/harness/HN-012/real-device-ai-review-job-2026-05-22.json`、`dist/harness/HN-012/real-device-ai-review-material-2026-05-22.json`。

### HN-013：图片级讲义记录与解析留存

**目标：** 每次拍照或相册选择都要形成可追溯的图片页记录。图片除了参与 AI 解析之外，还要长期保留对应的标题、OCR 文本、单词、句子和细节说明。

**当前状态：** 后端合约已增加 `MaterialImageRecord`；上传、AI 校对和课程详情链路可返回图片级记录。2026-05-22 真机上传证据已随 `HN-012` 补齐，本次 material/job 均返回 4 条图片级记录。

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

### HN-014：讲义学习资产自动生成

**目标：** 讲义识别后生成核心学习资产，常规目标 8-15 个、绝对范围 1-20 个，每条资产保留英文、中文释义、来源页、讲义裁剪区域、发音文本、配图提示、媒体状态和主发音。

**范围：**
- AI 校对页展示文字学习资产和来源讲义裁剪图。
- 家长确认后固化到课程详情。
- 后台异步填充彩色配图和英式/美式 TTS mock 媒体。
- 本期使用 Qq/Rr 预置 mock 媒体，不接真实外部图片/TTS provider。

**验收：**
- `job.draft_learning_assets` 数量为 1-20；常规讲义优先保留 8-15 个核心词、短语或句子。
- `material.learning_assets` 确认后存在。
- 每条资产包含 `source_bbox` 或能回退到来源页缩略图。
- 课程详情展示彩色配图状态和英式/美式 TTS 状态。

**证据目录：** `dist/harness/HN-014/`

### HN-015：课程资料左滑删除

**目标：** 家长可以在资料库左滑删除课程资料；删除后课程详情、知识包、亲子陪练脚本和复习任务一起从用户可见入口移除。

**范围内：**
- 资料库课程卡片支持左滑删除。
- 删除前弹出确认框，说明课程详情、知识点和复习任务会一起移除。
- 后端将课程资料状态更新为 `archived`。
- 后端删除该资料对应的 `KnowledgePackModel`、`ReviewTaskModel` 和 `ParentCoachingScriptModel`。
- 已归档资料不再出现在资料库、课程详情、AI 校对和复习任务接口中。
- worker 识别和媒体任务跳过已归档资料，不把资料重新写回可见状态。

**范围外：**
- 删除孩子档案、家长账号或全量用户数据。
- 回收站、撤销删除或恢复课程。
- 物理删除对象存储中的原始图片、彩色配图和 TTS 音频。
- 回算历史周报和历史练习记录。

**验收标准：**
- 删除当前家长拥有的资料返回 `204`。
- 删除后 `GET /materials` 不再返回该资料。
- 删除后 `GET /materials/{material_id}`、`GET /knowledge-packs/{material_id}`、`GET /parent-coaching/{material_id}` 返回 `404`。
- 删除后该资料对应复习任务不再返回。
- 归档资料对应的 job 不能继续读取、确认或重试。
- 移动端左滑删除支持取消、确认、失败恢复和中文错误提示。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q`
- 自动化：`services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q`
- 自动化：`cd apps/mobile && /opt/homebrew/bin/flutter test test/features/materials/presentation/materials_library_delete_test.dart test/features/lessons/presentation/lesson_detail_deleted_test.dart`
- 人工：模拟器或真机上传并确认一份讲义后，左滑删除并保存截图/API 摘录。

**证据位置：**
- `dist/harness/HN-015/`

### HN-016：真实媒体生成 Provider

**目标：** 家长确认讲义后，后台用真实 provider 为每条学习资产生成彩色配图、美式 TTS 和英式 TTS，并保存到 storage。

**范围内：**
- `MEDIA_PROVIDER=real` 时使用真实外部 provider，不静默回退 mock。
- 图片、US TTS、UK TTS 独立生成和独立失败。
- 生成文件写入 storage 后回填 `material.learning_assets`、`KnowledgePack` 和 `ReviewTask`。
- 移动端课程详情展示生成中、已生成和失败原因。

**范围外：**
- 孩子录音评分。
- 家长编辑 prompt 或 voice。
- 历史 mock 媒体迁移。

**验收标准：**
- 至少一份 Qq/Rr 讲义确认后，`material.learning_assets` 含 `generated_image_url`、`tts_us_url`、`tts_uk_url`。
- storage 中存在对应图片和两份音频对象。
- 单项失败不会阻塞其他媒体成功。
- `MEDIA_PROVIDER=real` 缺少 `OPENAI_API_KEY` 时媒体状态为 `failed`，不展示 mock URL。
- 课程详情显示中文失败原因，不展示 provider 原始英文堆栈。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py services/api/tests/test_storage_media_assets.py -q`
- 自动化：`services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q`
- 自动化：`cd apps/mobile && flutter test test/features/lessons/presentation/lesson_detail_media_test.dart`
- 人工：真机或模拟器确认课程后保存 material JSON、media job 日志和课程详情截图。

**证据位置：**
- `dist/harness/HN-016/`

### HN-016A：DashScope 国内媒体 Provider

**目标：** 在 HN-016 的媒体 provider 抽象上增加 DashScope / 百炼支持，使国内环境可以通过 `MEDIA_IMAGE_PROVIDER=dashscope` 和 `MEDIA_TTS_PROVIDER=dashscope` 生成彩色配图、US TTS 和 UK TTS。

**范围内：**
- DashScope 图片生成 provider，读取 `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`MEDIA_IMAGE_MODEL`、`MEDIA_IMAGE_EDIT_MODEL` 和轮询配置。
- DashScope TTS provider，读取 `MEDIA_TTS_MODEL`、`MEDIA_TTS_US_VOICE`、`MEDIA_TTS_UK_VOICE`。
- `MEDIA_PROVIDER=real` 时允许 OpenAI 与 DashScope 图片/TTS provider 独立组合。
- 生成成功后继续写入现有 storage，并回填 `material.learning_assets`、`KnowledgePack` 和 `ReviewTask`。
- 缺少 DashScope 配置或 provider 返回失败时，记录脱敏中文错误，不暴露 API key。

**范围外：**
- 新增第三方媒体 provider。
- 重做 storage schema 或课程详情 UI。
- 人工编辑 prompt、voice 或历史媒体迁移。

**验收标准：**
- `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope` 时，worker 可以完成图片、US TTS、UK TTS 生成和 storage 回填。
- DashScope 图片任务支持提交、轮询、成功 URL 下载和失败原因处理。
- DashScope TTS 能按 US / UK voice 分别生成音频。
- 缺少 `DASHSCOPE_API_KEY` 时媒体状态进入 `failed`，错误信息脱敏且不回退 mock。
- HN-016 OpenAI provider 默认配置继续保留。

**证据位置：**
- `dist/harness/HN-016A/`
