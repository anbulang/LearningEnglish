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

`infra/env/local.example.env` 默认使用 `AI_PROVIDER=stub`，可以无外部密钥跑通 MVP 主链。
同一份示例环境也默认使用 `SPEECH_PROVIDER=stub`，这是当前唯一完成端到端验证的口语评分模式。

如需 Docker Compose 下的 API / worker 调用 Doubao，需要在 `infra/.env` 中配置：

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<your-volcengine-ark-api-key>
DOUBAO_VISION_MODEL_OR_ENDPOINT=<your-vision-model-or-endpoint>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<your-text-model-or-endpoint>
AI_REQUEST_TIMEOUT_SECONDS=180
```

如果当前网络必须通过系统代理访问外部 provider，再显式设置：

```bash
AI_HTTP_TRUST_ENV=true
```

默认值是 `false`，即使 shell 中存在 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`，API 和 worker 的 AI HTTP client 也不会自动继承代理。

## Speaking 配置边界

当前 speaking 默认走 deterministic stub 评分，便于本地回归和 Harness 验证。`services/api/app/core/settings.py` 已预留 `SPEECH_ASSESSMENT_*` 配置边界，但真实 Aliyun speech assessment 适配器还没有完成签名请求实现，因此当前不要把它当成可验收能力。

Use [docker-compose.yml](/Users/chaucermini/Code/LearningEnglish/infra/docker-compose.yml) for local orchestration.
