# LearningEnglish Mobile

Flutter 客户端，覆盖家长登录、资料上传、AI 校对、课程详情、复习、报告和个人页，支持手机/平板自适应布局。

## 当前范围

- `Splash -> Login -> Phone Bind -> Home` 会话主链
- `资料库 -> 上传 -> AI 校对 -> 课程详情` 讲义主链
- `复习 -> 口语陪练 -> 亲子陪练 -> 报告模式`
- 资料左滑删除
- 学习资产媒体状态展示与主发音切换
- 设计 token 和插画资源接入

## 当前实现特点

- 通过 `go_router` 管理主路由。
- 通过 `flutter_riverpod` 管理页面状态和 session。
- 通过 `dio` 访问 API，并在 `401` 后自动刷新会话。
- 通过 `packages/contracts` 复用 Dart 契约。
- `home`、`materials` 等入口共用 `features/materials/presentation/material_navigation.dart` 做资料跳转决策，保证未完成资料统一进入 AI 校对页。
- 未接入 `Drift`，当前以远端 API + 内存态 provider 为主。

## 本地命令

```bash
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
```

## 当前限制

- speaking 页已有入口，但真实录音上传与 AI 评分尚未完成。
- `/reports` 当前复用 `ReviewTasksScreen(reportMode: true)`，还不是独立复杂报告模块。
- 真机和模拟器截图证据未全部补齐，详见 `docs/harness/`。
