# Infrastructure

This directory holds local development infrastructure for LearningEnglish.

## Included
- PostgreSQL
- Redis
- MinIO object storage
- API service container
- Worker service container

## 本地使用

```bash
cp infra/env/local.example.env infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

## AI 与代理

`infra/env/local.example.env` 默认使用阿里云百炼 / DashScope：`AI_PROVIDER=qwen`、`MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope`、`SPEECH_PROVIDER=dashscope`。自动化测试会显式设置 `stub` / `mock`，避免测试依赖外网。

如需 Docker Compose 下的 API / worker 调用 Doubao，需要在 `infra/.env` 中配置：

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<your-volcengine-ark-api-key>
DOUBAO_VISION_MODEL_OR_ENDPOINT=<your-vision-model-or-endpoint>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<your-text-model-or-endpoint>
AI_REQUEST_TIMEOUT_SECONDS=180
```

如需把讲义识别切到阿里云百炼 / DashScope Qwen，需要在 `infra/.env` 中配置：

```bash
AI_PROVIDER=qwen
DASHSCOPE_API_KEY=<your-dashscope-api-key>
DASHSCOPE_COMPATIBLE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_VISION_MODEL=qwen-vl-max-latest
QWEN_MODEL=qwen-plus
AI_REQUEST_TIMEOUT_SECONDS=180
```

学习资产配图与 TTS 默认也走 DashScope：

```bash
MEDIA_PROVIDER=real
MEDIA_IMAGE_PROVIDER=dashscope
MEDIA_TTS_PROVIDER=dashscope
MEDIA_IMAGE_MODEL=wan2.6-image
MEDIA_TTS_MODEL=cosyvoice-v3-flash
MEDIA_TTS_US_VOICE=longanyang
MEDIA_TTS_UK_VOICE=longanhuan
```

口语评分默认走 DashScope ASR + Qwen 评分：

```bash
SPEECH_PROVIDER=dashscope
SPEECH_ASSESSMENT_PROVIDER=dashscope
SPEECH_ASSESSMENT_BASE_URL=https://dashscope.aliyuncs.com/api/v1
SPEECH_ASSESSMENT_ASR_MODEL=paraformer-v2
SPEECH_ASSESSMENT_SCORING_MODEL=qwen-plus
SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL=https://your-public-host.example.com
```

注意：DashScope ASR 需要公网可访问的音频 URL。本地 `localhost`、`testserver`、`192.168.*` 或其他内网地址会被 provider 提前拒绝。真机调试时，`PUBLIC_BASE_URL` 可以继续是给 App 用的局域网 API 地址；`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 单独给 worker 使用，要求它能通过 `/uploads/{object_key}` 暴露同一份录音，例如公网对象存储、CDN 或临时 HTTPS 隧道。

如果当前网络必须通过系统代理访问外部 provider，再显式设置：

```bash
AI_HTTP_TRUST_ENV=true
```

默认值是 `false`，即使 shell 中存在 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`，API 和 worker 的 AI HTTP client 也不会自动继承代理。

## Speaking 配置边界

当前可运行的真实路径是 DashScope ASR + Qwen 结构化评分；`SPEECH_PROVIDER=stub` 仅用于本地回归测试。历史 `aliyun` 适配器仍保留为配置边界，但签名请求未完成，不作为验收路径。

Use [docker-compose.yml](/Users/chaucermini/Code/LearningEnglish/infra/docker-compose.yml) for local orchestration.
