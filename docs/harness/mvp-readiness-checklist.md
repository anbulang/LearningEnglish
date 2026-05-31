# LearningEnglish MVP Readiness Checklist

## 目标
把当前 MVP 从“开发可运行”提升到“可交付、可复现、可验收”。

## 验收清单

### A. 工程与基础设施
- [x] `infra/env/local.example.env` 可复制为 `infra/.env`
- [x] `make infra-up` 可启动 Postgres / Redis / MinIO
- [x] `make api-install` 成功
- [x] `make worker-install` 成功
- [x] `make api-migrate` 成功

### B. 自动化检查
- [x] `make api-test` 成功
- [x] `make worker-test` 成功
- [x] `make mobile-bootstrap` 成功
- [x] `make mobile-test` 成功
- [x] `make mobile-analyze` 成功
- [x] `make harness-main-chain-smoke` 成功

### C. iOS 交付链
- [x] `make mobile-ios-prep` 成功
- [x] `make mobile-ios-archive` 成功
- [x] `make mobile-ios-ipa` 成功，默认产出 Profile/Internal 包
- [x] `dist/ios/` 下存在 archive 和导出产物
- [x] 至少一台 iOS 模拟器跑通当前 UI
- [x] iOS 真机安装并启动成功
- [x] Android debug APK fallback 已明确记录为本机 Flutter/Android 工具链环境阻塞

### D. 主链复现
- [x] 登录页面与会话恢复已验证
- [x] 绑定手机号链路已由 API 测试覆盖
- [x] 创建孩子档案已由 API 测试覆盖
- [x] 上传讲义已由 API 测试覆盖
- [x] AI 校对已由 API 测试覆盖
- [x] 课程详情数据链已由 API 测试覆盖
- [x] 完成复习已由 API 测试覆盖
- [x] 查看报告已由 API 测试覆盖
- [x] 移动端上传成功后跳转 AI 校对页已由 widget 测试覆盖
- [x] 移动端 AI 校对确认后跳转课程详情已由 widget 测试覆盖
- [x] 移动端 AI 校对页对 `processing` job 持续自动轮询，直到进入 `needs_review`，且仍保留手动“刷新结果”兜底入口
- [x] 首页和资料库对未完成资料统一进入 AI 校对页，不再提前进入课程详情

### E. Admin 后端 Phase 2
- [x] configured admin actors 已由 `ADMIN_API_CREDENTIALS_JSON`、SHA-256 `token_sha256`、`status` 和 exact `permissions` 覆盖；回归入口为 `services/api/tests/test_admin_auth_config.py` 和 `services/api/tests/test_admin_phase2_api.py`
- [x] `admin.operations.read`、`admin.impersonation.read`、`admin.impersonation.end` 已进入默认本地 admin 权限集合，并在 Phase 2 API 测试中覆盖 allow/deny 边界；既有 mutation 权限仍要求 `reason` 和 high-risk audit
- [x] `GET /v1/admin/audit-events` 已覆盖 tenant scope、`action`、`resource_type`、`risk_level`、`result`、`actor_id` 过滤，以及 `limit` 夹取和 cursor 分页
- [x] `GET /v1/admin/tenants/{tenant_id}` 已覆盖单租户 read model、tenant scope no-disclosure、recent audit history 权限门控和 bounded latest lists
- [x] `GET /v1/admin/operations` 已覆盖 material jobs、media generation、speaking attempts、provider runtime readiness、secret presence 布尔值和 tenant override bounded lists；当前不做 Celery broker introspection
- [x] `GET /v1/admin/impersonation-sessions` 和 `POST /v1/admin/impersonation-sessions/{session_id}/end` 已覆盖 list/end/idempotent end、tenant scope no-disclosure 和 audit 记录
- [ ] Admin UI 尚未接入 Phase 2 新读模型；`apps/admin` 当前仍主要调用 Phase 1 live endpoints：dashboard、access、material retry/archive、provider policy override、tenant module toggle、impersonation start
- [ ] 完整 admin login/SSO、DB token rotation、role mutation 和 permission mutation 仍不是当前 Phase 2 能力

## 本次验收记录
执行人：Codex
验收时间：2026-04-29，iOS IPA 与真机补充验收：2026-05-01，AI 校对轮询真机补测：2026-05-22
验收环境：本机开发环境，Docker Compose Postgres / Redis / MinIO / API / worker，默认 `AI_PROVIDER=qwen` + DashScope 媒体/语音 provider，测试时显式切换 stub/mock，iOS Simulator，iPhone 真机 `Chaucer`

### 命令结果
- [x] `HARNESS_RESET=1 make harness-mvp-readiness`
- [x] `make infra-reset`
- [x] `make infra-up`
- [x] `make api-install`
- [x] `make worker-install`
- [x] `make api-migrate`
- [x] `make api-test`
- [x] `make worker-test`
- [x] `make mobile-bootstrap`
- [x] `make mobile-test`
- [x] `make mobile-analyze`
- [x] `make harness-main-chain-smoke`
- [x] `make mobile-ios-prep`
- [x] `make mobile-ios-archive`
- [x] `make mobile-ios-ipa`
- [x] `xcrun devicectl device install app --device Chaucer dist/ios/LearningEnglish-Internal.xcarchive/Products/Applications/Runner.app --timeout 120`
- [x] `xcrun devicectl device process launch --device Chaucer --terminate-existing com.anbulang.learningenglish --timeout 60`
- [x] `make mobile-apk` blocked：全局 Flutter SDK cache 写入受限，`flutter build apk --debug` 返回 `/opt/homebrew/share/flutter/bin/cache/engine.stamp: Operation not permitted`；改用 `/private/tmp/learningenglish-flutter/bin/flutter` 后进入下一层 blocker：`No Android SDK found`；未产出 APK
- [x] `make harness-doubao-smoke` pass：Doubao 调用已对齐 ReceiptLens 的 `/responses` 方式（文本 `input_text`，视觉 `input_image`）；2026-05-04 08:12 真实 provider smoke 已通过，日志包含 `text_ok`、`vision_ok` 和 `PASS: Doubao provider smoke`

验收日志：
- `dist/harness/mvp-readiness.log`

### Harness evidence 目录约定
- 最新兼容日志：`dist/harness/mvp-readiness.log`
- HN-001 readiness 日志：`dist/harness/HN-001/mvp-readiness.log`
- HN-003 UI 截图证据：`dist/harness/HN-003/screens/`
- HN-006 Doubao smoke 日志：`dist/harness/HN-006/doubao-smoke.log`
- 历史兼容截图目录：`dist/harness/screens/`
- `dist/` 是本地运行产物，不进 git；需要归档时应上传到 CI/artifact 或另行附带截图包；checklist 只记录路径约定和本地验证状态。

### 关键截图
- [x] login：`dist/harness/screens/login-screen.png`
- [x] phone-binding：`dist/harness/screens/phone-binding-screen.png`
- [x] home：`dist/harness/screens/home-screen.png`
- [x] upload：`dist/harness/screens/upload-screen.png`
- [x] ai-review：`dist/harness/screens/ai-review-screen.png`
- [x] lesson-detail：`dist/harness/screens/lesson-detail-screen.png`
- [x] report：`dist/harness/screens/report-screen.png`

截图采集命令：
```bash
make harness-capture-ios-screen SCREEN=login-screen
make harness-capture-ios-screen SCREEN=phone-binding-screen
make harness-capture-ios-screen SCREEN=home-screen
make harness-capture-ios-screen SCREEN=upload-screen
make harness-capture-ios-screen SCREEN=ai-review-screen
make harness-capture-ios-screen SCREEN=lesson-detail-screen
make harness-capture-ios-screen SCREEN=report-screen
```

已产出：
- `dist/harness/screens/login-screen.png`
- `dist/harness/screens/home-screen.png`
- `dist/harness/screens/upload-screen.png`
- `dist/harness/screens/report-screen.png`

补充截图说明：
- 绑定手机号截图已从 `dist/harness/HN-003/screens/ios-simulator-phone-binding.png` 同步到标准截图路径。
- AI 校对和课程详情截图已在 2026-05-23 用 iOS 模拟器、临时 SQLite API 和 HN-014 mock 讲义资料补齐。
- 本次截图中发现 SVG mock 资源不能直接由 `Image.network` 渲染，已补 `RemoteAssetImage` 统一处理 SVG / 位图远程资源。

### Clean-state UI 验证流程
1. 后端执行 reset，清理测试账号、孩子档案、讲义、课程与报告数据。
2. 执行 `make harness-reset-ios-sim`，清理 iOS 模拟器 App 数据和历史会话状态。
3. 重新安装并运行 App，确保从未登录状态进入主链。
4. 依次完成 login、phone-binding、home、upload、ai-review、lesson-detail、report 页面验证并逐页截图。
5. 截图同时保存到 HN-003 目录和 legacy screens 目录。

### 已知限制
- 真实微信、真实短信仍未接入
- 当前登录仍是开发态登录，不是生产微信/短信闭环
- 真实 OCR / 媒体 / 语音 provider 已接入，但 readiness 仍依赖网络、密钥和真机证据
- iOS Profile/Internal IPA 已导出：`dist/ios/export/learning_english_mobile.ipa`
- iOS 工程使用 Team `95RDXKW54K` 与 Bundle ID `com.anbulang.learningenglish`，本机签名 identity 为 `Apple Development: shenchao.bupt@gmail.com (4PZWF88ND8)`
- Flutter Debug 包不能作为普通内测包从桌面直接启动；iOS 14+ 下会报 `Cannot create a FlutterEngine instance in debug mode without Flutter tooling or Xcode` 并闪退。因此 `make mobile-ios-ipa` 已改为默认产出 Profile/Internal 包
- Profile/Internal IPA 仍属于 development provisioning 分发，真实测试设备必须被纳入 provisioning profile；当前真机 `Chaucer` 已验证可安装并启动
- 真机测试包最近一次使用局域网 API：`http://192.168.2.15:8000/v1`，对应后端健康检查 `http://192.168.2.15:8000/healthz` 返回 `{"status":"ok"}`
- Android fallback 也未产出，当前机器运行全局 Flutter 会在 cache 写入阶段失败：`/opt/homebrew/share/flutter/bin/cache/engine.stamp: Operation not permitted`；复制一份可写 Flutter SDK 到 `/private/tmp/learningenglish-flutter` 后，`FLUTTER=/private/tmp/learningenglish-flutter/bin/flutter make mobile-apk` 进入下一层 blocker：`No Android SDK found`
- Doubao provider smoke 曾出现网络/代理阻塞；当前仓库保留的最新成功证据为 `2026-05-04 08:12` 的 `dist/harness/HN-006/doubao-smoke.log`。后续如果更换网络环境，需要重新验证一次真实 provider 连通性；如需继承系统代理，API/worker 进程要显式设置 `AI_HTTP_TRUST_ENV=true`
- `api-migrate` 已修正为默认迁移 Docker Postgres；如果只想使用 SQLite，需要显式覆盖 `API_DATABASE_URL`

### 交付判断
- [x] 可以交给内部测试用户（仅限已纳入 development provisioning 的设备）
- [x] 仍需补充处理

补充处理项：
1. 如需发给更多内部测试人员，收集并注册测试设备 UDID，或改走 TestFlight
2. 将真机主链操作截图补回本 checklist
3. 如 Mac 局域网 IP 变化，重新用新的 `IOS_API_BASE_URL` 导出测试包
4. 如需 Android fallback，先修复 Flutter SDK cache 写入权限或改用当前用户可写的 Flutter SDK，再安装/配置 Android SDK / `ANDROID_HOME` 后执行 `make mobile-apk`
5. 如需补齐真实截图，先清理模拟器 App 数据，再从登录页完整走一遍主链

## 下一批需求：讲义上传识别链路

需求来源：2026-05-05 真机上传测试。用户反馈“上传讲义图片并不能识别”，并指出上传页表单逻辑不符合“拍照后自动识别”的预期。

需求文档：
- `docs/harness/upload-recognition-loop.md`

实施计划：
- `docs/superpowers/plans/2026-05-05-upload-recognition-loop.md`

当前根因记录：
- 真机上传成功创建 `material_5adf552647dd` 和 `job_18ded7aa35de`。
- job 进入 `failed`，错误为 `Doubao request timeout after 60s`。
- material 仍停在 `processing`，资料库状态不清晰。
- 当前识别是在前端请求 `/material-jobs/{jobId}` 时同步触发，不是上传成功后后台自动完成。
- 未 ready 的材料从资料库进入课程详情会请求 `/knowledge-packs/{materialId}` 并得到 `404`，用户会误以为没有识别。

下一批需求编号：
- `HN-008`：上传页改为拍照优先的无表单识别入口。
- `HN-009`：上传后必须进入识别轮询页。
- `HN-010`：识别失败时 material 和 job 状态一致。
- `HN-011`：Doubao 超时和重试体验清晰化。
- `HN-012`：真机上传识别 harness 记录。
- `HN-013`：图片级讲义记录与解析留存。
- `HN-014`：讲义学习资产自动生成。
- `HN-015`：课程资料左滑删除。
- `HN-016`：真实媒体生成 Provider。
- `HN-016A`：DashScope 国内媒体 Provider。
- `HN-017`：孩子录音上传与 AI 语音评分。
- `HN-018`：学习资产掌握度进入独立报告页。

当前实施状态：
- [x] `HN-008` 上传页已改为拍照/相册优先，不再要求用户填写标题、老师名、主题。
- [x] `HN-009` API 材料响应已包含 `parse_job_id`，移动端资料库未就绪材料会进入 AI 状态页。
- [x] `HN-010` job 失败时 material 同步为 `failed`；retry 后同步回 `processing`。
- [x] `HN-011` timeout 失败在移动端显示中文重试说明。
- [x] `HN-012` Profile 真机包已重新安装；真实手机已补齐上传识别日志和 job/material JSON 证据。
- [x] `HN-013` API 和移动端已支持图片级记录；真机证据随 `HN-012` 补齐。
- [x] `HN-014` 讲义学习资产自动生成：API/worker/mock media 自动化、job/material JSON 摘录、AI 校对页截图和课程详情截图已补齐。
- [x] `HN-015` 课程资料左滑删除：API、worker、Flutter 左滑删除、自动化 Harness 日志和人工截图已补齐。
- [x] `HN-016` 真实媒体生成 Provider：默认已切到 DashScope 真实配图与 US/UK TTS，课程详情 widget 和 iOS 模拟器 App shell 截图证据已补齐；OpenAI 路径仍保留但不作为当前默认验收路径。
- [x] `HN-016A` DashScope 国内媒体 Provider：DashScope 直连 provider smoke、worker/storage 回填、课程详情 widget UI 截图、iOS 模拟器完整 App shell 截图和自动化回归已通过。
- [x] `HN-017` 孩子录音上传与 AI 语音评分：录音上传、音频 storage、worker stub 评分、DashScope ASR + Qwen 评分 provider、真实 provider smoke、真实 worker smoke、公网 `/uploads` 隧道 smoke、结果页、自动化测试、公网音频 URL 改写配置、iOS 模拟器 App shell 结果页截图、物理手机 speaking 上传/真实评分回写和真机结果页截图已完成。
- [x] `HN-018` 学习资产掌握度进入独立报告页：API 已返回 `asset_mastery` / `material_summaries`，移动端 `/reports` 已改为独立 `ReportsScreen`，报告 JSON、widget UI 截图和 iOS 模拟器完整 App shell 截图证据已进入 `dist/harness/HN-018/`。

`HN-012` 当前补测进展：
- Profile 真机包已用 `API_BASE_URL=http://192.168.2.15:8000/v1` 构建、安装并启动成功。
- API/worker 已重建到当前分支代码，确认后端合约包含 `failed` 状态和 `parse_job_id`。
- 拍照入口首次真机测试直接闪退，crash report 显示 iOS TCC 因缺少 `NSCameraUsageDescription` 终止 App。
- 已补齐相机/相册用途说明并重新安装启动；crash report 证据见 `dist/harness/HN-012/Runner-2026-05-05-154100.ips`。
- 2026-05-22 重新删除并安装真机 App 后，设备 `Chaucer` 从 `192.168.2.16` 访问 `http://192.168.2.15:8000/v1`。
- 真机日志已捕获 `POST /v1/auth/wechat/login`、`POST /v1/children`、`POST /v1/materials`，其中上传请求返回 `201 Created`。
- 真机上传生成 `material_d23e45e7b76f` 和 `job_d5219576911b`；worker 处理完成后 job 状态为 `needs_review`。
- `job.draft_image_records` 为 4 条，`job.draft_learning_assets` 为 12 条；`material.image_records` 为 4 条，状态为 `needs_review`。
- 证据见 `dist/harness/HN-012/real-device-summary.json`、`real-device-job-final.json`、`real-device-material-detail.json`、`real-device-material-list.json`。

`HN-014` 验收证据：
- `dist/harness/HN-014/job-learning-assets.json`
- `dist/harness/HN-014/material-learning-assets.json`
- `dist/harness/HN-014/review-learning-assets.png`
- `dist/harness/HN-014/lesson-learning-assets.png`

`HN-015` 验收证据：
- `dist/harness/HN-015/material-delete-api.log`
- `dist/harness/HN-015/material-delete-worker.log`
- `dist/harness/HN-015/material-delete-mobile.log`
- `dist/harness/HN-015/material-delete-screen.png`

- HN-016 真实媒体 provider 证据：`dist/harness/HN-016/`
- HN-016A DashScope 国内媒体 provider 证据：`dist/harness/HN-016A/`
  - 已有：`dashscope-provider-smoke-summary.json`、`dashscope-reference-edit-smoke-summary.json`、`worker-dashscope-real-summary.json`、生成图片与 US/UK TTS 文件。
  - 已有：课程详情页展示真实 DashScope 图片和音频状态的 widget UI 截图 `lesson-detail-dashscope-media-screen.png`。
  - 已有：iOS 模拟器完整 App shell 截图 `ios-simulator-app-shell-lesson-detail-dashscope-media-screen.png` 和摘要 `ios-simulator-app-shell-summary.json`。
  - 复现步骤：`docs/harness/provider-readiness-runbook.md`。
- HN-017 speaking evidence：`dist/harness/HN-017/`
  - 已有：`speaking-attempt-upload.json`、`speaking-attempt-scored.json`、`speaking-worker.log`、`api-worker-summary.json`、`real-device-install-summary.json`、`real-device-apps.json`、`real-device-lock-state.json`、`real-device-processes.json`。
  - 已有：`dashscope-speech-smoke-summary.json`、`dashscope-speech-smoke-result.json`、`dashscope-worker-smoke-summary.json`、`dashscope-worker-smoke-attempt.json`、`public-uploads-tunnel-smoke-summary.json`、`public-uploads-tunnel-smoke-result.json` 和 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` worker URL 改写回归。
  - 已有：iOS 模拟器完整 App shell 评分结果截图 `ios-simulator-app-shell-speaking-result-screen.jpg` 和摘要 `ios-simulator-app-shell-speaking-summary.json`。
  - 已有：物理手机 `Chaucer` speaking 上传与 DashScope scored 回写证据 `real-device-speaking-summary.json`、`real-device-speaking-attempt.json`、`real-device-speaking-worker.log`、`real-device-speaking-api.log`。
  - 已有：物理手机 iPhone Mirroring 结果页截图 `real-device-speaking-result-screen.png` 和裁剪版 `real-device-speaking-result-screen-cropped.png`。
- HN-018 reports evidence：`dist/harness/HN-018/`
  - 已有：`weekly-report.json`、`summary.json`、`reports-screen.png`。
  - 已有：iOS 模拟器完整 App shell 截图 `ios-simulator-app-shell-reports-screen.png` 和摘要 `ios-simulator-app-shell-summary.json`。

## 当前结论

- HN-001 到 HN-018 的核心代码链路已经落地，当前仓库具备“上传 -> AI 校对 -> 课程详情 -> 复习 / 口语评分 -> 报告”的可回归主链。
- 当前最大剩余缺口不在主链功能本身，而在 Android 交付链、文档真相源治理、evidence 索引和更稳定的环境自动化。

本轮自动化验证：
- `services/api/.venv/bin/python -m pytest services/api/tests -q`：`68 passed`
- `services/workers/.venv/bin/python -m pytest services/workers/tests -q`：`9 passed`
- `cd apps/mobile && flutter test`：`35 passed`
- `cd apps/mobile && flutter analyze`：`No issues found`

2026-05-29 Admin Phase 2 文档收口验证：
- `make api-test`：`191 passed`
- `git diff --check`：无输出
- owned docs/config secret scan：未发现 admin test token、provider test key 或 OpenAI-style secret 明文

2026-05-31 Admin Operations Platform Phase 3 验证项：
- [x] Backend service tests：admin identity、permissions、scope、audit、read models、operations 和 action result 已拆入服务层并由 `make api-test` 覆盖。
- [x] API compatibility：现有 `/v1/admin/...` route path 未重命名，Phase 2 response keys 保留，`/v1/admin/operations` 增加 `issues`，mutation response 增加 `action_result`。
- [x] Admin UI test/build：`apps/admin` 已接入 operations、tenant detail、audit filters / pagination 和 impersonation sessions；需以 `cd apps/admin && npm test` 与 `cd apps/admin && npm run build` 作为前端 gate。
- [x] Phase 3 non-goals：SSO / magic link、DB-backed role mutation、permission mutation、真实 worker broker introspection、queue depth 和 worker heartbeat 不属于本阶段完成范围。

2026-05-23 P0 收口补充：
- [x] 资料跳转规则已抽到 `material_navigation.dart`，首页和资料库共用同一套 ready / review 路由判断。
- [x] AI 校对页长耗时轮询回归已覆盖连续多次 `processing` 后进入 `needs_review` 的场景。
- [x] `infra/env/local.example.env` 已补齐 Doubao provider 和 `AI_HTTP_TRUST_ENV` 示例配置。
- [x] `docs/project/README.md` 已说明状态文档、文章草稿和素材目录边界。
- [x] 人工截图证据已补齐：AI 校对、课程详情、学习资产和删除确认截图。

2026-05-30 文档治理补充：
- [x] 项目状态快照已切到 `docs/project/2026-05-31-status-and-todo.md`。
- [x] README 与 `docs/project/README.md` 已同步最新状态快照链接。
- [x] `docs/harness/README.md` 已补齐 `HN-*` 证据索引和真相源边界说明。
- [x] `HN-017` readiness 摘要与上传识别链路文档已去掉过时“待补真机证据”语气，统一为当前仓库事实。

2026-05-31 HN-019 治理补充：
- [x] `docs/project/2026-05-31-status-and-todo.md` 已替换前一版状态快照。
- [x] `docs/harness/device-regression-runbook.md` 已说明 R0/R1/R2/R3 回归边界。
- [x] `docs/harness/evidence-archive-policy.md` 已说明证据保留、脱敏和替代规则。
- [x] `scripts/harness/generate_evidence_index.py` 与 `make harness-evidence-index` 已提供统一索引入口。
- [x] `HN-017` 既有真机 speaking evidence 保持已闭环状态，复跑时按现有 `dist/harness/HN-017/real-device-*` 命名续证，不重新标为待补。
