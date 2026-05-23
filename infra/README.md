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

Use [docker-compose.yml](/Users/chaucermini/Code/LearningEnglish/infra/docker-compose.yml) for local orchestration.
