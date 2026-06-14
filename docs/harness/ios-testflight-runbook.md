# iOS TestFlight 分发 Runbook

更新时间：2026-06-14

把 iOS 内测分发从 development / UDID（`make mobile-ios-ipa` + `ExportOptions.internal.plist`，method=`debugging`）切换到 **TestFlight**。本文是执行清单，区分「可自动化」与「需 Apple 账号人工」两类步骤。

## 背景

- 原方案：`ExportOptions.internal.plist`（method=`debugging`）+ 注册设备 UDID，导出 internal/Profile IPA。
- 新方案：`ExportOptions.appstore.plist`（method=`app-store-connect`）+ Release 归档 + 上传 App Store Connect，经 TestFlight 分发给测试者，无需逐台注册 UDID。
- bundle id：`com.anbulang.learningenglish`；Apple Developer Team：`95RDXKW54K`。

## 一次性前置（需你的 Apple 账号，人工）

1. 拥有有效的 **Apple Developer Program** 会员（团队 `95RDXKW54K`）。
2. 在 **App Store Connect** 创建 App 条目，bundle id 填 `com.anbulang.learningenglish`。
3. 生成 **App Store Connect API Key**（Users and Access → Integrations → App Store Connect API）：
   - 记录 `Key ID` 和 `Issuer ID`；
   - 下载 `.p8` 私钥，放到 `~/.appstoreconnect/private_keys/AuthKey_<KeyID>.p8`。
4. 确认签名证书可用（Automatic signing 会按团队拉取 App Store 分发证书与 profile）。

## 构建（可自动化，本机执行）

```bash
make mobile-ios-testflight-ipa
```

它会：用 Release 配置归档（`dist/ios/LearningEnglish-AppStore.xcarchive`），再用 `ExportOptions.appstore.plist`（`app-store-connect`）导出到 `dist/ios/export-appstore/`。

> 如需指向非本机 API，沿用 `IOS_API_BASE_URL=http://<lan-ip>:8000/v1`（仅影响 app 内置默认；TestFlight 包通常指向可公网访问的 API）。

## 上传 TestFlight（需 Apple 账号凭据）

```bash
export ASC_API_KEY_ID=<your-key-id>
export ASC_API_ISSUER_ID=<your-issuer-id>
make mobile-ios-testflight-upload
```

未设置上述环境变量时该目标会打印 `BLOCKED` 并退出，不会尝试上传。上传成功后构建会出现在 App Store Connect → TestFlight，可分配给内部/外部测试者。

> 也可用 Xcode Organizer（Window → Organizer → Distribute App → App Store Connect → Upload）做图形化上传，等效于上述命令。

## 验证

- `make mobile-ios-testflight-ipa` 在本机成功产出 `dist/ios/export-appstore/learning_english_mobile.ipa`（签名为 App Store 分发证书）。
- 上传后在 App Store Connect TestFlight 看到对应 build，状态从 `Processing` 变为可分发。
- 安装到测试者设备，主链可用（参考 `device-regression-runbook.md`）。

## 当前状态与限制

- ✅ 已加入仓库：`ExportOptions.appstore.plist`、`make mobile-ios-testflight-ipa`、`make mobile-ios-testflight-upload`、本 runbook。
- ⏳ 需人工一次性完成：ASC App 条目、API Key、分发证书确认（依赖你的 Apple 账号）。
- 未做自动化：build number 自增、release notes 自动化、CI 集成（后续按需）。
- `xcrun altool --upload-app` 为当前可用上传方式；若 Apple 后续仅保留 Transporter，可改用 Transporter app 上传同一 IPA。
