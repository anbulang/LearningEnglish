# LearningEnglish MVP Readiness Checklist

## 目标
把当前 MVP 从“开发可运行”提升到“可交付、可复现、可验收”。

## 验收清单

### A. 工程与基础设施
- [x] `.env.example` 可复制为 `infra/.env`
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

## 本次验收记录
执行人：Codex  
验收时间：2026-04-29，iOS IPA 与真机补充验收：2026-05-01  
验收环境：本机开发环境，stub providers，Docker Compose Postgres / Redis / MinIO / API / worker，iOS Simulator，iPhone 真机 `Chaucer`  

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
- [ ] phone-binding：`dist/harness/screens/phone-binding-screen.png`
- [x] home：`dist/harness/screens/home-screen.png`
- [x] upload：`dist/harness/screens/upload-screen.png`
- [ ] ai-review：`dist/harness/screens/ai-review-screen.png`
- [ ] lesson-detail：`dist/harness/screens/lesson-detail-screen.png`
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

未完成截图说明：
- 绑定手机号截图未在本轮重置模拟器状态后补齐，当前模拟器存在历史已登录状态。
- AI 校对和课程详情截图未补齐，原因是当前模拟器本地缓存 token 与重置后的 Docker Postgres 数据不一致，真实 UI 上传返回 `Invalid access token`；对应主链已由 API smoke 和 mobile widget test 覆盖。

### Clean-state UI 验证流程
1. 后端执行 reset，清理测试账号、孩子档案、讲义、课程与报告数据。
2. 执行 `make harness-reset-ios-sim`，清理 iOS 模拟器 App 数据和历史会话状态。
3. 重新安装并运行 App，确保从未登录状态进入主链。
4. 依次完成 login、phone-binding、home、upload、ai-review、lesson-detail、report 页面验证并逐页截图。
5. 截图同时保存到 HN-003 目录和 legacy screens 目录。

### 已知限制
- 真实微信、真实短信、真实 OCR/LLM 仍未接入
- 当前环境仍依赖 stub provider
- iOS Profile/Internal IPA 已导出：`dist/ios/export/learning_english_mobile.ipa`
- iOS 工程使用 Team `95RDXKW54K` 与 Bundle ID `com.anbulang.learningenglish`，本机签名 identity 为 `Apple Development: shenchao.bupt@gmail.com (4PZWF88ND8)`
- Flutter Debug 包不能作为普通内测包从桌面直接启动；iOS 14+ 下会报 `Cannot create a FlutterEngine instance in debug mode without Flutter tooling or Xcode` 并闪退。因此 `make mobile-ios-ipa` 已改为默认产出 Profile/Internal 包
- Profile/Internal IPA 仍属于 development provisioning 分发，真实测试设备必须被纳入 provisioning profile；当前真机 `Chaucer` 已验证可安装并启动
- 真机测试包使用局域网 API：`http://192.168.2.5:8000/v1`，对应后端健康检查 `http://192.168.2.5:8000/healthz` 返回 `{"status":"ok"}`
- Android fallback 也未产出，当前机器运行全局 Flutter 会在 cache 写入阶段失败：`/opt/homebrew/share/flutter/bin/cache/engine.stamp: Operation not permitted`；复制一份可写 Flutter SDK 到 `/private/tmp/learningenglish-flutter` 后，`FLUTTER=/private/tmp/learningenglish-flutter/bin/flutter make mobile-apk` 进入下一层 blocker：`No Android SDK found`
- Doubao provider smoke 未通过，配置项存在，但当前机器无法直连解析 `ark.cn-beijing.volces.com`；代理变量存在，但本地 `127.0.0.1:1081` / `127.0.0.1:8888` 代理不可连接，已记录为 provider-readiness blocked
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

当前实施状态：
- [x] `HN-008` 上传页已改为拍照/相册优先，不再要求用户填写标题、老师名、主题。
- [x] `HN-009` API 材料响应已包含 `parse_job_id`，移动端资料库未就绪材料会进入 AI 状态页。
- [x] `HN-010` job 失败时 material 同步为 `failed`；retry 后同步回 `processing`。
- [x] `HN-011` timeout 失败在移动端显示中文重试说明。
- [ ] `HN-012` 仍需重新构建 Profile 真机包并用真实手机补一次上传识别截图/日志证据。
- [x] `HN-013` API 和移动端已支持图片级记录；真机证据随 `HN-012` 补齐。
- [ ] `HN-014` 讲义学习资产自动生成：需要保存 job/material JSON 摘录、AI 校对页截图和课程详情媒体状态截图。

`HN-012` 当前补测进展：
- Profile 真机包已用 `API_BASE_URL=http://192.168.2.5:8000/v1` 构建、安装并启动成功。
- API/worker 已重建到当前分支代码，确认后端合约包含 `failed` 状态和 `parse_job_id`。
- 拍照入口首次真机测试直接闪退，crash report 显示 iOS TCC 因缺少 `NSCameraUsageDescription` 终止 App。
- 已补齐相机/相册用途说明并重新安装启动；crash report 证据见 `dist/harness/HN-012/Runner-2026-05-05-154100.ips`。
- 仍缺少一次实际上传后的 `POST /v1/materials`、material/job 状态和真机截图证据，因此 `HN-012` 不标完成。

`HN-014` 验收证据：
- `dist/harness/HN-014/job-learning-assets.json`
- `dist/harness/HN-014/material-learning-assets.json`
- `dist/harness/HN-014/review-learning-assets.png`
- `dist/harness/HN-014/lesson-learning-assets.png`

本轮自动化验证：
- `services/api/.venv/bin/python -m pytest services/api/tests`：`35 passed`
- `cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test`：`10 passed`
