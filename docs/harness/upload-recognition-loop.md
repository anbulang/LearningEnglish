# 讲义上传识别链路 Harness 需求

## 背景

2026-05-05 真机验证中，用户在 iPhone 真机上传讲义后反馈“不能识别”，同时指出上传页要求填写课程标题、老师名、主题的表单不符合预期。用户期望的主流程是：直接拍照或选择讲义图片，由系统识别标题、主题、词汇和句型，家长只在 AI 草稿阶段做校对。

这份文档保留了问题来源、需求拆解和 Harness 验收要求。需要注意：HN-008 到 HN-015 当前已经基本落地，下面的“当时现状”主要用于解释为什么会产生这批需求，不代表仓库此刻仍停留在那个阶段。

当前仍未完全收口的部分主要有三类：

- Android 交付链仍受本机 Flutter / Android SDK 环境阻塞，`make mobile-apk` 还没有形成可复查产物。
- Doubao、OpenAI、DashScope 真依赖在部分网络环境下仍可能受代理继承影响；如果 shell 已配置 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` 但 API / worker 仍无法访问外网，需要额外设置 `AI_HTTP_TRUST_ENV=true` 或 `MEDIA_HTTP_TRUST_ENV=true`。
- 文档与 evidence 目录已经比较完整，但还缺一个统一索引来说明每个 `HN-*` 目录的关键文件与复查入口。

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
- HN-012 到 HN-018 都已经有代码和证据落点；HN-017 的物理手机结果页截图已补齐。
- 真实 provider 的最短复现步骤见 `docs/harness/provider-readiness-runbook.md`。

### HN-019：真机回归与 evidence 治理

HN-019 不改变上传识别主链，也不新增上传、AI 校对、课程详情或报告页的业务要求；它只收敛真机回归、provider 运行和 `dist/harness/` 证据归档方式，让既有主链可以被复查。

执行入口：

- `docs/harness/device-regression-runbook.md`
- `docs/harness/provider-readiness-runbook.md`
- `docs/harness/evidence-archive-policy.md`

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
- 自动化：
  ```bash
  MAC_IP=192.168.2.15
  flutter build ios --profile --dart-define=API_BASE_URL="http://${MAC_IP}:8000/v1"
  ```
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
- `docs/harness/provider-readiness-runbook.md`

**当前证据记录（2026-05-24）：**
- DashScope 直连 provider smoke 已通过，证据：
  - `dist/harness/HN-016A/dashscope-provider-smoke-summary.json`
  - `dist/harness/HN-016A/dashscope-rabbit-image.png`
  - `dist/harness/HN-016A/dashscope-reference-edit-image.png`
  - `dist/harness/HN-016A/dashscope-tts-word-us.mp3`
  - `dist/harness/HN-016A/dashscope-tts-word-uk.mp3`
  - `dist/harness/HN-016A/dashscope-tts-sentence-us.mp3`
  - `dist/harness/HN-016A/dashscope-tts-sentence-uk.mp3`
- DashScope worker / storage 回填 smoke 已通过，证据：
  - `dist/harness/HN-016A/worker-dashscope-real-summary.json`
  - `dist/harness/HN-016A/worker-storage/generated/media/material_dashscope_real/asset_rabbit/`
- 课程详情 widget UI 截图和 iOS 模拟器完整 App shell 截图已补齐，可作为 `HN-016A` readiness 证据。

**当前代码状态：**
- `MEDIA_PROVIDER` 默认已从 mock 切到 `real`，图片与 TTS 默认 provider 均为 DashScope。
- DashScope TTS 请求会按 US / UK voice 分别生成音频；若 AI 返回 `/.../` 或 `[...]` 音标，worker 会使用原始英文单词/句子作为 TTS 输入，避免把音标读出来。
- 自动化回归已覆盖 DashScope 图片、TTS、worker/storage 回填；课程详情 widget 和 iOS 模拟器 App shell 证据已补齐。
- 已补课程详情 UI 截图 Harness，使用真实 DashScope 生成的 PNG、US TTS、UK TTS 文件渲染课程详情：
  - `dist/harness/HN-016A/lesson-detail-dashscope-media-screen.png`
  - `dist/harness/HN-016A/lesson-detail-dashscope-media-summary.json`
- 已补 iOS 模拟器完整 App shell 截图，使用真实 DashScope 生成的 PNG、US TTS、UK TTS 文件经本地 HTTP 服务加载：
  - `dist/harness/HN-016A/ios-simulator-app-shell-lesson-detail-dashscope-media-screen.png`
  - `dist/harness/HN-016A/ios-simulator-app-shell-summary.json`

### HN-017：孩子录音上传与 AI 语音评分

**目标：** 孩子围绕讲义核心词句录音后，系统保存音频、异步转写评分，并在结果页和周报中展示反馈。

**当前状态：** 已完成录音上传、音频 storage、worker 异步评分、结果页轮询、stub 回归路径和 DashScope ASR + Qwen 真实 provider 代码实现。真机安装启动、局域网 API 连通、API multipart 上传、音频 storage、worker stub 评分和 scored attempt JSON 证据已存在。DashScope ASR 任务创建、轮询、转写结果下载、Qwen JSON 评分、本地/内网音频 URL 拒绝测试、阿里官方公开 sample audio 真实 provider smoke、公网 `/uploads/{object_key}` worker URL 改写、真实 worker -> DashScope -> scored attempt -> 周报回填 smoke、cloudflared 临时 HTTPS 隧道拉取验证、iOS 模拟器完整 App shell 评分结果页截图均已补齐。物理手机 `Chaucer` speaking 上传、DashScope scored 回写和 iPhone Mirroring 结果页截图也已补齐：真机从 `192.168.2.12` 访问局域网 API，创建 `attempt_b0e110c126d1`，watcher 调用 DashScope 后写回 `scored`。

**范围内：**
- 移动端 speaking 页支持录音、重录、上传、处理中、评分成功和失败重试。
- 后端 `POST /v1/speaking-attempts` 接收 multipart 音频并保存到 storage。
- `SpeakingAttempt` 合同扩展为包含目标文本、音频 object key、转写文本、总分、发音分、准确度、完整度、流利度、逐词反馈和中文建议。
- worker 注册 `speaking.score_attempt`，异步调用 speech assessment provider。
- 默认 `SPEECH_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`；自动化测试显式设置 `stub` 保持稳定。
- DashScope ASR 需要公网可访问音频 URL；本地 `localhost`、`testserver`、`192.168.*` 等地址会被提前拒绝并给出失败原因。
- 真机调试时可设置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，worker 会用它拼出公网 `/uploads/{object_key}`；留空则沿用 `PUBLIC_BASE_URL` 生成的录音 URL。
- `scripts/harness/run_hn017_public_uploads_tunnel_smoke.py` 会临时启动 FastAPI `/uploads` 和 cloudflared HTTPS 隧道，证明 DashScope 可以拉取同一份 `object_key` 音频。
- 评分成功后累计 `WeeklyReport.speaking_attempts`，低分词句写入 `weak_items`。

**范围外：**
- 自由对话陪练。
- 实时流式评分。
- 音频波形编辑、裁剪、降噪。
- 音素级可视化结果页。
- HN-018 的独立报告深化。

**验收标准：**
- `POST /v1/speaking-attempts` multipart 上传音频后返回 `recording_uploaded` 或 `transcribing`，不等待 provider 完成。
- storage 中存在 `owner_type=speaking_attempt` 的音频对象。
- worker `speaking.score_attempt` 成功后 attempt 进入 `scored`。
- scored attempt 包含 `transcript`、`overall_score`、`pronunciation_score`、`accuracy_score`、`fluency_score`、`completeness_score`、`word_feedback` 和中文 `feedback`。
- failed attempt 在移动端显示中文失败原因，并可重新评分。
- archived material 不能创建或 retry speaking attempt。
- 真机录音上传后保存 API 日志、worker 日志、attempt JSON 和结果页截图。
- DashScope provider 单元测试覆盖 ASR 创建、任务轮询、结果下载和 Qwen 评分 JSON 解析。
- worker URL 改写测试覆盖 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，证明不会把局域网录音 URL 交给 DashScope。
- 真实 provider smoke 产物：
  - `dist/harness/HN-017/dashscope-speech-smoke-summary.json`
  - `dist/harness/HN-017/dashscope-speech-smoke-result.json`
- 真实 worker smoke 产物：
  - `dist/harness/HN-017/dashscope-worker-smoke-summary.json`
  - `dist/harness/HN-017/dashscope-worker-smoke-attempt.json`
- 公网 `/uploads` 隧道 smoke 产物：
  - `dist/harness/HN-017/public-uploads-tunnel-smoke-summary.json`
  - `dist/harness/HN-017/public-uploads-tunnel-smoke-result.json`
- iOS 模拟器 App shell 评分结果页产物：
  - `dist/harness/HN-017/ios-simulator-app-shell-speaking-result-screen.jpg`
  - `dist/harness/HN-017/ios-simulator-app-shell-speaking-summary.json`
- 物理手机结果页截图产物：
  - `dist/harness/HN-017/real-device-speaking-result-screen.png`
  - `dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py services/api/tests/test_speaking_assessment_provider.py -q`
- 自动化：`services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q`
- 自动化：`cd apps/mobile && flutter test test/features/materials/data/app_repository_test.dart test/features/speaking/presentation/speaking_partner_screen_test.dart`
- 真实 worker smoke：`set -a; source infra/.env; set +a; services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py`
- 公网 `/uploads` 隧道 smoke：`set -a; source infra/.env; set +a; services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py`
- iOS 模拟器 App shell 截图：`cd apps/mobile && flutter run -d 5458B2B5-3DEC-426B-997F-6C612CF5ABB5 -t tool/harness/main_app_shell_harness.dart --dart-define=HARNESS_SCREEN=speaking --no-resident`，滚动到结果卡后截图保存到 `dist/harness/HN-017/`。
- 真机安装/连通：`xcrun devicectl device install app --device Chaucer ...`、`xcrun devicectl device process launch --device Chaucer ...`；API 日志已出现 iPhone `GET /healthz`。
- 本地闭环证据：`POST /v1/speaking-attempts` multipart 上传后保存 attempt JSON，手动执行 `score_speaking_attempt()` 后保存 worker log 和 scored attempt JSON。
- 物理手机 speaking 上传与真实评分：启动局域网 API、启动 `scripts/harness/watch_hn017_speaking_attempts.py`，真机运行 `tool/harness/real_device_speaking_upload_harness.dart` 后保存 `real-device-speaking-summary.json`、`real-device-speaking-attempt.json`、`real-device-speaking-worker.log`、`real-device-speaking-api.log`。
- 当前证据摘要：`docs/harness/hn017-speaking-readiness-summary.md`。
- 物理手机结果页截图：`dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`。

**证据位置：**
- `dist/harness/HN-017/`
  - `speaking-attempt-upload.json`
  - `speaking-attempt-scored.json`
  - `speaking-worker.log`
  - `api-worker-summary.json`
  - `real-device-install-summary.json`
  - `real-device-apps.json`
  - `real-device-lock-state.json`
  - `real-device-processes.json`
  - `seed-summary.json`
  - `dashscope-speech-smoke-summary.json`
  - `dashscope-speech-smoke-result.json`
  - `dashscope-worker-smoke-summary.json`
  - `dashscope-worker-smoke-attempt.json`
  - `public-uploads-tunnel-smoke-summary.json`
  - `public-uploads-tunnel-smoke-result.json`
  - `ios-simulator-app-shell-speaking-result-screen.jpg`
  - `ios-simulator-app-shell-speaking-summary.json`
  - `real-device-speaking-summary.json`
  - `real-device-speaking-attempt.json`
  - `real-device-speaking-worker.log`
  - `real-device-speaking-api.log`
  - `real-device-speaking-result-screen.png`
  - `real-device-speaking-result-screen-cropped.png`

### HN-018：学习资产掌握度进入报告页

**目标：** 报告页不再只展示轻量周报统计，而是基于 `learning_assets`、复习任务、练习记录和口语 attempt 生成可解释的学习资产掌握度。

**范围内：**
- `GET /v1/reports/weekly` 返回 `report_summary`、`material_summaries` 和 `asset_mastery`。
- 每个学习资产包含资料标题、文本、释义、配图 URL、主发音音频 URL、掌握分、掌握状态、复习任务完成情况、口语次数、最佳/最近口语分、薄弱点和推荐动作。
- archived material 不进入报告聚合。
- 移动端 `/reports` 使用独立 `ReportsScreen`，不再复用 `ReviewTasksScreen(reportMode: true)`。

**范围外：**
- 新增数据库 schema 保存历史快照。
- AI 自动生成长篇诊断报告。
- 多周趋势图和跨孩子对比。

**验收标准：**
- 周报 API 能从同一份讲义的 `learning_assets` 聚合出资产级掌握度。
- completed / pending review task 会影响资产掌握状态。
- scored speaking attempt 会进入资产和讲义汇总。
- practice session 的 weak points 会进入对应资产的弱项提示。
- `/reports` 独立展示讲义汇总、词句掌握度、口语表现和推荐动作。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_review_report_failures.py -q`
- 自动化：`cd apps/mobile && flutter test test/features/profiles/presentation/report_profile_display_test.dart`
- 自动化：`cd apps/mobile && flutter analyze`
- 证据生成：`services/api/.venv/bin/python scripts/harness/generate_hn018_report_evidence.py`
- 证据生成：`cd apps/mobile && flutter test tool/harness/reports_screen_capture_test.dart`
- iOS 模拟器 App shell 证据：`flutter run -d <simulator> -t tool/harness/main_app_shell_harness.dart --dart-define=HARNESS_SCREEN=reports` 后执行 `xcrun simctl io <simulator> screenshot ...`
- 人工：真机或模拟器打开报告页，保存截图和 `/v1/reports/weekly` JSON 摘录。

**证据位置：**
- `dist/harness/HN-018/`
  - `weekly-report.json`
  - `summary.json`
  - `reports-screen.png`
  - `ios-simulator-app-shell-reports-screen.png`
  - `ios-simulator-app-shell-summary.json`

**设计与计划：**
- `docs/superpowers/specs/2026-05-25-hn017-speaking-assessment-design.md`
- `docs/superpowers/plans/2026-05-25-hn017-speaking-assessment.md`
