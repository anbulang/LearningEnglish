# LearningEnglish 系统总览

## 当前定位

LearningEnglish 当前是一个“家长上传讲义 -> AI 识别 -> 家长校对 -> 课程详情 -> 复习/陪练 -> 周报”的本地可运行 MVP。项目已经不再是纯脚手架，而是具备可验证主链、真机安装链路、Harness 证据约定和一批端到端测试的工作仓库。

## 当前系统形态

```mermaid
flowchart LR
    Mobile["Flutter Mobile App<br/>phone + tablet"] --> API["FastAPI API"]
    API --> Postgres["PostgreSQL"]
    API --> Redis["Redis / Celery broker"]
    API --> Storage["Local storage / MinIO-compatible storage"]
    API --> Workers["Celery Workers"]
    Workers --> OCR["Stub / PaddleOCR / Doubao Vision"]
    Workers --> LLM["Stub / Doubao Text"]
    Workers --> Media["Learning Asset Media Provider<br/>mock / OpenAI / DashScope"]
```

## 当前主链

```mermaid
flowchart TD
    A["家长登录并绑定手机号"] --> B["创建孩子档案"]
    B --> C["上传讲义图片"]
    C --> D["创建 CourseMaterial + MaterialParseJob"]
    D --> E["Celery worker 识别并生成 AI 草稿"]
    E --> F["AI 校对页轮询 job"]
    F --> G["家长确认草稿"]
    G --> H["生成 KnowledgePack / ReviewTask / ParentCoachingScript"]
    H --> I["异步补齐学习资产配图与 TTS"]
    I --> J["课程详情 / 复习 / 口语陪练 / 周报"]
```

## 代码边界

- `apps/mobile`：Flutter 客户端，负责登录、资料库、上传、AI 校对、课程详情、复习、报告和个人页。
- `services/api`：FastAPI API，负责鉴权、同步读写、领域编排和稳定契约。
- `services/workers`：Celery worker，负责讲义识别、学习资产媒体生成、周报聚合等异步任务。
- `packages/contracts`：Dart 侧共享契约，和 API `Pydantic` model 对齐。
- `packages/design_tokens`：Flutter UI token。
- `scripts/harness`：MVP readiness、主链 smoke、Doubao smoke、iOS 模拟器辅助脚本。

## 当前不是的东西

- 还不是生产级多环境系统：目前以本地 `Docker Compose` + 本地/局域网验证为主。
- 还没有真实语音评分闭环：`speaking_attempts` 已有接口和 UI 入口，但评分仍是 stub。
- HN-016 / HN-016A 后，真实媒体 provider 可通过 `MEDIA_PROVIDER=real` 启用，并按 `MEDIA_IMAGE_PROVIDER` / `MEDIA_TTS_PROVIDER` 选择 OpenAI 或 DashScope；本地测试默认仍使用 mock provider。
- 还没有完整 Android 可交付链路：iOS 内测链路已跑通，Android 仍受本机 SDK 环境阻塞。
