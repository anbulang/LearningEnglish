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
- [ ] `make mobile-ios-archive` 成功
- [ ] `make mobile-ios-ipa` 成功
- [ ] `dist/ios/` 下存在 archive 和导出产物
- [x] 至少一台 iOS 模拟器跑通当前 UI
- [ ] Android debug APK fallback 成功

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
验收时间：2026-04-29  
验收环境：本机开发环境，stub providers，Docker Compose Postgres / Redis / MinIO / API / worker，iOS Simulator  

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
- [ ] `make mobile-ios-archive`
- [ ] `make mobile-ios-ipa`
- [ ] `make mobile-apk`

验收日志：
- `dist/harness/mvp-readiness.log`

### 关键截图
- [x] 登录页截图
- [ ] 绑定手机号截图
- [ ] 上传讲义截图
- [ ] AI 校对截图
- [ ] 课程详情截图
- [ ] 报告页截图

已产出：
- `dist/harness/screens/login-screen.png`
- `dist/harness/screens/home-screen.png`
- `dist/harness/screens/upload-screen.png`
- `dist/harness/screens/report-screen.png`

未完成截图说明：
- 绑定手机号截图未在本轮重置模拟器状态后补齐，当前模拟器存在历史已登录状态。
- AI 校对和课程详情截图未补齐，原因是当前模拟器本地缓存 token 与重置后的 Docker Postgres 数据不一致，真实 UI 上传返回 `Invalid access token`；对应主链已由 API smoke 和 mobile widget test 覆盖。

### 已知限制
- 真实微信、真实短信、真实 OCR/LLM 仍未接入
- 当前环境仍依赖 stub provider
- iOS 安装到真机仍依赖本机 Apple Development 签名能力
- 当前机器的钥匙串里存在 Apple Development identity，iOS 工程已统一为 Team `4PZWF88ND8` 与 Bundle ID `com.anbulang.learningenglish`，但 Xcode 未登录对应 Team，导致 `xcodebuild archive` 无法自动生成 provisioning profile
- 因此本轮已验证到 `Runner.app` 构建成功和模拟器 UI 成功启动，尚未拿到可安装的 Debug IPA
- Android fallback 也未产出，当前机器未配置 Android SDK，`flutter build apk --debug` 返回 `No Android SDK found`
- `api-migrate` 已修正为默认迁移 Docker Postgres；如果只想使用 SQLite，需要显式覆盖 `API_DATABASE_URL`

### 交付判断
- [ ] 可以交给内部测试用户
- [x] 仍需补充处理

补充处理项：
1. 在 Xcode Accounts 中登录有效的 Apple 开发账号，并让 Team `4PZWF88ND8` 可用于自动签名
2. 重新执行 `make mobile-ios-ipa`
3. 产出 IPA 后补一轮真机安装验证
4. 如需 Android fallback，安装 Android SDK 并设置 `ANDROID_HOME` 后执行 `make mobile-apk`
5. 如需补齐真实截图，先清理模拟器 App 数据，再从登录页完整走一遍主链
