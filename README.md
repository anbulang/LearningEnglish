<div align="center">

# LearningEnglish

**把线下讲义变成可复习、可陪练、可追踪的家庭英语学习包。**

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Flutter](https://img.shields.io/badge/Flutter-3.22%2B-02569B.svg)](apps/mobile)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688.svg)](services/api)
[![Harness](https://img.shields.io/badge/Harness-MVP%20readiness-4B5563.svg)](docs/harness/mvp-readiness-checklist.md)

<img src="apps/mobile/assets/images/heroes/home_study_desk.png" alt="LearningEnglish home study desk illustration" width="760" />

`Flutter` mobile app + `FastAPI` API + `Celery` workers + `PostgreSQL` / `Redis` / `MinIO` local infra.

[快速开始](#快速开始) · [MVP 主链](#mvp-主链) · [仓库地图](#仓库地图) · [验证入口](#验证入口) · [文档入口](#文档入口)

</div>

## 项目概览

LearningEnglish 是一个面向早期英语学习家庭的内测 MVP。家长拍照上传线下讲义后，系统会完成讲义存档、AI 识别、家长校对、复习任务生成、口语练习和周报聚合。

| 能力 | 当前状态 |
| --- | --- |
| 讲义导入 | 支持移动端拍照/相册上传，后端保存原始图片和解析任务 |
| AI 校对 | 默认使用阿里云百炼 / DashScope Qwen；测试环境显式切到 stub |
| 复习闭环 | `KnowledgePack`、`ReviewTask`、`PracticeSession`、`WeeklyReport` 已串联 |
| 口语评分 | 移动端录音上传、音频存储、DashScope ASR + Qwen 评分、逐词反馈和结果页已接通；`dist/harness/HN-017/` 已保留真机证据，复跑时仍需提供公网可拉取的录音 URL |
| 移动端 | Flutter 自适应手机/平板页面结构，含登录、资料库、校对、课程、复习、报告 |
| 工程验收 | `make` 入口和 Harness evidence 目录已固定，便于反复回归 |

## 快速开始

### 1. 启动本地基础设施

```bash
cp infra/env/local.example.env infra/.env
make infra-up
```

### 2. 安装依赖并迁移数据库

```bash
make api-install
make worker-install
make api-migrate
```

### 3. 启动 API 和 worker

分别打开两个终端：

```bash
make api-dev
```

```bash
make worker-dev
```

### 4. 运行移动端

```bash
make mobile-bootstrap
make mobile-analyze

cd apps/mobile
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
```

非生产环境的手机号验证码会在 API 响应中返回 `debug_code`，默认值为 `123456`。

## MVP 主链

```mermaid
flowchart LR
    Login["微信登录"] --> Phone["绑定手机号"]
    Phone --> Child["创建孩子档案"]
    Child --> Upload["上传讲义图片"]
    Upload --> Job["AI 识别任务"]
    Job --> Review["家长校对"]
    Review --> Pack["生成课程包"]
    Pack --> Practice["完成复习/口语练习"]
    Practice --> Report["查看周报"]
```

核心后端链路：

```text
ParentAccount -> ChildProfile -> CourseMaterial -> MaterialParseJob
-> KnowledgePack -> ReviewTask -> PracticeSession -> WeeklyReport
```

## 常用命令

| 目标 | 命令 |
| --- | --- |
| 启动本地 infra | `make infra-up` |
| 重置本地 infra | `make infra-reset` |
| API 测试 | `make api-test` |
| Worker 测试 | `make worker-test` |
| Admin 原型安装 | `make admin-install` |
| Admin 原型开发 | `make admin-dev` |
| Admin 连接本地 API | `make admin-dev-live` |
| Admin 原型测试 | `make admin-test` |
| Admin 原型构建 | `make admin-build` |
| Flutter 测试 | `make mobile-test` |
| Flutter 静态检查 | `make mobile-analyze` |
| Android debug APK | `make mobile-apk` |
| iOS internal/Profile IPA | `make mobile-ios-ipa` |
| MVP readiness 回归 | `HARNESS_RESET=1 make harness-mvp-readiness` |
| 主链 smoke | `make harness-main-chain-smoke` |
| Doubao provider smoke | `make harness-doubao-smoke` |

## 仓库地图

| 路径 | 内容 |
| --- | --- |
| [`apps/mobile`](apps/mobile) | Flutter 移动端，覆盖 phone / tablet 自适应体验 |
| [`apps/admin`](apps/admin) | React/Vite 多租户运维管理后台：默认可用 mock 数据启动，也可连接 `/v1/admin/*` live API 查看 read model 并执行受控 mutation |
| [`packages/contracts`](packages/contracts) | Dart 侧共享领域契约，和 API Pydantic models 对齐 |
| [`packages/design_tokens`](packages/design_tokens) | Flutter 设计 token |
| [`services/api`](services/api) | FastAPI 后端服务，内部按 `api/parent`、`api/admin`、`services/parent`、`services/admin`、`services/shared` 区分家长端、运维管理和共享能力 |
| [`services/workers`](services/workers) | Celery worker 和讲义处理任务边界 |
| [`infra`](infra) | Docker Compose 本地依赖：PostgreSQL、Redis、MinIO、API、worker |
| [`docs`](docs) | 产品、设计、架构、Harness 验收文档 |
| [`scripts/harness`](scripts/harness) | MVP readiness、provider smoke、模拟器截图等辅助脚本 |

## 验证入口

后续需求默认使用中文文档和 Harness Engineering 验收方式。每条需求都应说明自动化命令、人工证据和证据目录。

```bash
HARNESS_RESET=1 make harness-mvp-readiness
make harness-main-chain-smoke
make harness-doubao-smoke
make harness-reset-ios-sim
make harness-capture-ios-screen SCREEN=login-screen
```

常用 evidence 目录：

| 证据 | 路径 |
| --- | --- |
| MVP readiness 兼容日志 | `dist/harness/mvp-readiness.log` |
| HN-001 readiness 日志 | `dist/harness/HN-001/mvp-readiness.log` |
| Doubao smoke 日志 | `dist/harness/HN-006/doubao-smoke.log` |
| HN 需求证据 | `dist/harness/HN-*/` |
| UI 截图 | `dist/harness/screens/` |

## AI Provider

本地示例和 Docker Compose 默认使用阿里云百炼 / DashScope：`AI_PROVIDER=qwen`、`MEDIA_PROVIDER=real`、`SPEECH_PROVIDER=dashscope`。自动化测试会显式设置 `stub` / `mock`，用于不依赖外网的回归。

<details>
<summary>启用 Doubao / Volcengine Ark 真实识别</summary>

在 `infra/.env` 以及 API/worker 进程环境中配置同一组变量：

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<your-volcengine-ark-api-key>
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_VISION_MODEL_OR_ENDPOINT=<your-vision-model-or-endpoint>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<your-text-model-or-endpoint>
AI_REQUEST_TIMEOUT_SECONDS=180
AI_MAX_IMAGE_COUNT=5
```

然后运行：

```bash
make harness-doubao-smoke
```

成功日志会写入 `dist/harness/HN-006/doubao-smoke.log`，并包含 `text_ok`、`vision_ok` 和 `PASS: Doubao provider smoke`。缺配置、DNS/网络不可达等情况会记录为 `BLOCKED`，不会打印密钥。

如果 API/worker 运行在需要继承系统代理的网络环境，还要显式配置：

```bash
AI_HTTP_TRUST_ENV=true
```

默认值是 `false`。这意味着即使 shell 里已经有 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`，AI HTTP client 也不会自动继承；在公司网络、代理网络或特定 Wi-Fi 下，这通常会直接影响 Doubao 连通性。

</details>

<details>
<summary>启用阿里云百炼 / DashScope Qwen 真实识别</summary>

在 `infra/.env` 以及 API/worker 进程环境中配置同一组变量：

```bash
AI_PROVIDER=qwen
DASHSCOPE_API_KEY=<your-dashscope-api-key>
DASHSCOPE_COMPATIBLE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_VISION_MODEL=qwen-vl-max
QWEN_MODEL=qwen-plus
AI_REQUEST_TIMEOUT_SECONDS=180
AI_MAX_IMAGE_COUNT=5
AI_HTTP_TRUST_ENV=false
```

`qwen` provider 会使用 Qwen-VL 做讲义图片 OCR 和结构化抽取，再使用 Qwen 文本模型生成知识包草稿。`DASHSCOPE_API_KEY` 也可以继续复用给媒体补齐链路中的 DashScope 图片和 TTS provider。

口语评分默认也走 DashScope ASR + Qwen 评分。真机调试时，App 可以继续访问局域网 API，但 DashScope ASR 必须从公网拉取录音文件；因此需要给 worker 配置一个暴露 `/uploads/{object_key}` 的公网根地址：

```bash
SPEECH_PROVIDER=dashscope
SPEECH_ASSESSMENT_PROVIDER=dashscope
SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL=https://your-public-host.example.com
```

留空时 worker 会沿用 `PUBLIC_BASE_URL` 生成的录音 URL；如果它是 `localhost`、`127.0.0.1`、`192.168.*` 或 `testserver`，DashScope provider 会提前失败并返回中文失败说明。

</details>

## 打包与设备

```bash
make mobile-apk
LAN_IP=<current-host-ip>
make mobile-ios-ipa IOS_API_BASE_URL="http://${LAN_IP}:8000/v1"
```

iOS 目标默认使用 bundle id `com.anbulang.learningenglish` 和 Apple Developer Team `95RDXKW54K`。导出的 internal/Profile IPA 位于 `dist/ios/export/learning_english_mobile.ipa`。

如果要连接非本机 API：

```bash
cd apps/mobile
flutter run --dart-define=API_BASE_URL=http://<host>:8000/v1
```

大陆网络下运行 Flutter 命令前可设置镜像：

```bash
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
export PUB_HOSTED_URL=https://pub.flutter-io.cn
```

## 文档入口

| 主题 | 适用人群 / 用途 | 文档 |
| --- | --- | --- |
| 项目进度与 ToDo | 项目负责人 / 当前阶段判断、项目级 backlog | [`docs/project/2026-06-15-status-and-todo.md`](docs/project/2026-06-15-status-and-todo.md) |
| 系统总览 | 新成员 / 快速理解系统边界与默认技术路径 | [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| 数据模型 | 后端 / 数据层设计核对 | [`docs/architecture/data-models.md`](docs/architecture/data-models.md) |
| 后端架构 | API、worker 开发 / 服务边界核对 | [`docs/architecture/backend-architecture.md`](docs/architecture/backend-architecture.md) |
| 移动端架构 | Flutter 开发 / 主链页面与状态结构核对 | [`docs/architecture/mobile-architecture.md`](docs/architecture/mobile-architecture.md) |
| Harness 文档索引 | 所有人 / 找当前验收入口与真相源 | [`docs/harness/README.md`](docs/harness/README.md) |
| 真机回归 Runbook | iOS 真机回归执行者 / R0-R3 分层复跑 | [`docs/harness/device-regression-runbook.md`](docs/harness/device-regression-runbook.md) |
| iOS TestFlight 分发（停泊，未启用） | iOS 发布执行者 / 当前仍走 UDID，TestFlight 脚手架备查 | [`docs/harness/ios-testflight-runbook.md`](docs/harness/ios-testflight-runbook.md) |
| Evidence 归档策略 | 需要整理 `dist/harness/` 的成员 / 证据治理 | [`docs/harness/evidence-archive-policy.md`](docs/harness/evidence-archive-policy.md) |
| MVP readiness | 需要判断当前是否可交付 / 可验收的成员 | [`docs/harness/mvp-readiness-checklist.md`](docs/harness/mvp-readiness-checklist.md) |
| 上传识别链路 | 需要理解 HN-008~HN-019 背景与当前入口的成员 | [`docs/harness/upload-recognition-loop.md`](docs/harness/upload-recognition-loop.md) |
| 非技术试点指南 | 产品、测试、内部试用同学 / 非开发试用流程 | [`docs/harness/non-technical-pilot-guide.md`](docs/harness/non-technical-pilot-guide.md) |
| 家长试用验收 | 产品、测试、陪跑开发 / HN-020 验收清单与修复批次 | [`docs/harness/hn020-parent-pilot-acceptance.md`](docs/harness/hn020-parent-pilot-acceptance.md) |
| API 服务 | API 开发 / admin 与 parent 接口真相源 | [`services/api/README.md`](services/api/README.md) |
| Worker 服务 | 异步任务开发 / provider 与任务边界真相源 | [`services/workers/README.md`](services/workers/README.md) |

## License

LearningEnglish is licensed under [Apache License 2.0](LICENSE).
