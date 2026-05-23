# 移动端架构

## 技术栈

- `Flutter`
- `flutter_riverpod`
- `go_router`
- `dio`
- `flutter_secure_storage`
- `image_picker`
- `flutter_svg`

当前没有接入 `Drift` 或其他本地数据库，状态主要由 API + 内存态 provider 驱动。

## 当前路由结构

```text
/splash
/auth/login
/auth/bind
/home
/materials
/materials/scan
/materials/review/:jobId
/lessons/:materialId
/review
/review/session/:materialId
/review/speaking/:materialId
/review/coaching/:materialId
/reports
/profile
```

其中 `/reports` 当前复用 `ReviewTasksScreen(reportMode: true)`，还没有单独的 `reports` feature 目录。

## 当前模块划分

- `session`
  - 启动态、登录态、手机号绑定态、已登录态
- `auth`
  - 登录页、手机号绑定页
- `home`
  - 首页摘要、最近资料与快捷入口
- `materials`
  - 资料库、上传页、AI 校对页、路由决策
- `lessons`
  - 课程详情、学习资产媒体状态
- `review`
  - 复习任务列表、复习执行页、报告模式
- `speaking`
  - 口语陪练入口
- `coaching`
  - 亲子陪练页
- `profiles`
  - 个人/档案页

## 当前交互原则

### 自适应

- 手机端优先单列纵向流
- 平板端通过 `AdaptiveLayout` 和 `AppShell` 调整导航与布局密度
- 同一个业务目标在 phone / tablet 上保持同一语义入口

### 资料路由规则

- `ready` 材料进入 `/lessons/:materialId`
- 仍在 `processing`、`needs_review` 或 `failed` 的材料进入 `/materials/review/:jobId?materialId=...`
- 首页和资料库统一复用 `features/materials/presentation/material_navigation.dart`，避免未就绪资料提前进入课程详情或复习页

### AI 校对页

- 上传成功后直接进入 AI 校对页
- 对 `queued` / `processing` job 自动轮询
- `needs_review` 时展示可确认草稿
- `failed` 时展示中文错误与重试入口

## 数据流

1. UI 通过 Riverpod provider 发起请求。
2. `AppRepository` 用 `dio` 调用 API，并处理 `401` 后自动刷新 session。
3. 共享契约来自 `packages/contracts`。
4. 页面按 `loading / error / ready / empty` 状态渲染。
5. 异步结果主要通过轮询 `material-jobs` 拉取，而不是推送。

## 当前与文档曾经设想的差异

- 没有本地 `Drift` 缓存层。
- 没有 PIN child mode。
- 报告页仍是复用实现，不是独立复杂模块。
- speaking 流程已有入口，但真实录音上传和 AI 评分尚未完成。

## 可靠性关注点

- 上传页支持多页讲义和图片来源标记（`camera` / `gallery`）。
- 资料删除后，列表、详情、AI 校对和复习入口会一起收敛。
- 真机主链与关键路由已有 widget test 和 Harness 证据约定，但截图证据仍未全量补齐。
