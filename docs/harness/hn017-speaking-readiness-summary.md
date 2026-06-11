# HN-017 口语评分 Readiness 摘要

更新时间：2026-06-10

## 这份文档现在回答什么

这份文档只回答两件事：

1. `HN-017` 当前在仓库里是不是一条已经落地的能力链路。
2. 如果要复查 speaking readiness，应该看哪些入口与证据。

它不再把某一次真机运行过程直接当成当前事实。

## 当前结论

`HN-017` 已经从“需求定义”进入“现有能力治理”阶段。

当前仓库中可以直接对应到 speaking 主链的事实包括：

- API 有 `GET /v1/speaking-attempts`、`POST /v1/speaking-attempts`、`GET /v1/speaking-attempts/{attempt_id}`、`POST /v1/speaking-attempts/{attempt_id}/retry`。
- worker 有 `speaking.score_attempt` 任务。
- 本地默认 speaking provider 路径是 `DashScope ASR + Qwen 评分`。
- 文档已明确：真实回归时，`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 必须提供公网可访问录音 URL。

## 当前入口

### 代码与命令入口

- 项目级状态快照：`docs/project/2026-06-11-status-and-todo.md`
- 真机回归分级：`docs/harness/device-regression-runbook.md`
- provider 运行入口：`docs/harness/provider-readiness-runbook.md`
- readiness 总表：`docs/harness/mvp-readiness-checklist.md`
- speaking 相关 smoke / harness 脚本：`scripts/harness/run_hn017_dashscope_speech_smoke.py`、`scripts/harness/run_hn017_dashscope_worker_smoke.py`、`scripts/harness/run_hn017_public_uploads_tunnel_smoke.py`

### 最小复查命令

```bash
set -a; source infra/.env; set +a
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_speech_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py
```

如需补真机结果页与完整 speaking 证据，再按 `docs/harness/device-regression-runbook.md` 的 `R3` 流程执行。

## 当前已确认的能力边界

- speaking 上传不是同步等待评分；API 负责接收音频、创建 attempt，worker 异步评分。
- worker 会把本地或局域网音频地址改写为公网 `/uploads/{object_key}`，前提是已配置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`。
- provider smoke 只能证明真实依赖可用，不能单独替代完整的真机 speaking 通过结论。

## 当前未在本轮重新验证的事项

以下内容在 `dist/harness/HN-017/` 中存在历史证据，但本轮没有重新执行：

- 真机 speaking 上传与评分回写
- 真机结果页截图
- cloudflared / 公网 `/uploads` 可达性

因此它们仍应表述为“已有历史 evidence”，不是“今天刚复验通过”。

## 证据位置

- API / worker 基础证据：`dist/harness/HN-017/speaking-attempt-upload.json`、`dist/harness/HN-017/speaking-attempt-scored.json`、`dist/harness/HN-017/speaking-worker.log`
- DashScope provider smoke：`dist/harness/HN-017/dashscope-speech-smoke-summary.json`、`dist/harness/HN-017/dashscope-speech-smoke-result.json`
- 真实 worker smoke：`dist/harness/HN-017/dashscope-worker-smoke-summary.json`、`dist/harness/HN-017/dashscope-worker-smoke-attempt.json`
- 公网 `/uploads` smoke：`dist/harness/HN-017/public-uploads-tunnel-smoke-summary.json`、`dist/harness/HN-017/public-uploads-tunnel-smoke-result.json`
- 真机 speaking 历史证据：`dist/harness/HN-017/real-device-speaking-summary.json`、`dist/harness/HN-017/real-device-speaking-attempt.json`、`dist/harness/HN-017/real-device-speaking-worker.log`、`dist/harness/HN-017/real-device-speaking-api.log`、`dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

## 历史 evidence 说明

- 历史真机记录里出现的固定 `192.168.*` 地址只代表当时的 LAN 环境，不是当前默认值。
- 后续复跑时应使用当前机器可访问的 `API_BASE_URL` / `PUBLIC_BASE_URL` / `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`，不要直接复用旧 IP。

## 结论

- `HN-017` 当前不是待设计问题，而是现有 speaking 能力、provider 依赖和真机 evidence 的治理问题。
- 后续文档与回归都应优先回答“当前怎么复查、缺什么证据、还差哪个 gate”，不要再把历史运行细节写成当前结论。
