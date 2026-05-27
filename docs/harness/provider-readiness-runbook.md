# 真实 Provider Readiness 最短复现

更新时间：2026-05-27

## 目的

这份 Runbook 用来复查当前默认真实 provider 链路：

- `HN-016` / `HN-016A`：DashScope 彩色配图 + US/UK TTS。
- `HN-017`：DashScope ASR + Qwen 口语评分。
- `HN-018`：学习资产掌握度进入独立报告页。

所有文档和命令都不保存真实密钥；`dist/harness/` 是本地证据目录，不进入 git。

## 默认配置

`infra/env/local.example.env` 和 `infra/.env.example` 当前都应保持以下默认方向：

```bash
AI_PROVIDER=qwen
MEDIA_PROVIDER=real
MEDIA_IMAGE_PROVIDER=dashscope
MEDIA_TTS_PROVIDER=dashscope
SPEECH_PROVIDER=dashscope
SPEECH_ASSESSMENT_PROVIDER=dashscope
```

`infra/docker-compose.yml` 必须把同一组变量透传给 `api` 和 `worker`：

- `AI_PROVIDER`、`DASHSCOPE_API_KEY`、`DASHSCOPE_COMPATIBLE_BASE_URL`、`QWEN_VISION_MODEL`、`QWEN_MODEL`
- `MEDIA_PROVIDER`、`MEDIA_IMAGE_PROVIDER`、`MEDIA_TTS_PROVIDER`、`MEDIA_IMAGE_MODEL`、`MEDIA_TTS_MODEL`、`MEDIA_TTS_US_VOICE`、`MEDIA_TTS_UK_VOICE`
- `SPEECH_PROVIDER`、`SPEECH_ASSESSMENT_PROVIDER`、`SPEECH_ASSESSMENT_BASE_URL`、`SPEECH_ASSESSMENT_ASR_MODEL`、`SPEECH_ASSESSMENT_SCORING_MODEL`、`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`

自动化测试可以显式设置 `stub` / `mock`，但本地示例和 Compose 默认不应再回到 `MEDIA_PROVIDER=mock` 或 `SPEECH_PROVIDER=stub`。

## HN-016A：DashScope 媒体

1. 准备环境：

```bash
cp infra/env/local.example.env infra/.env
```

在 `infra/.env` 中填入 `DASHSCOPE_API_KEY`。如果当前网络必须走系统代理，再显式设置 `MEDIA_HTTP_TRUST_ENV=true`。

2. 运行真实 provider smoke 和 worker/storage 回填 smoke：

```bash
set -a; source infra/.env; set +a
services/api/.venv/bin/python scripts/harness/run_hn016a_dashscope_provider_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn016a_worker_dashscope_smoke.py
```

3. 复查证据：

```bash
ls -lh dist/harness/HN-016A/
jq '.status, .provider' dist/harness/HN-016A/dashscope-provider-smoke-summary.json
jq '.status' dist/harness/HN-016A/worker-dashscope-real-summary.json
```

4. 移动端 UI 证据：

```bash
cd apps/mobile
flutter test tool/harness/lesson_detail_dashscope_media_capture_test.dart
```

iOS 模拟器完整 App shell 可使用 `tool/harness/main_app_shell_harness.dart` 加载真实生成文件，再保存截图到 `dist/harness/HN-016A/`。

## HN-017：真实口语评分

1. 准备环境：

```bash
set -a; source infra/.env; set +a
```

DashScope ASR 必须能从公网下载音频。本地或真机局域网调试时，`PUBLIC_BASE_URL` 可以继续给 App 使用局域网 API；`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 要单独配置为公网可访问的 `/uploads` 根地址。

2. 运行 provider 和 worker smoke：

```bash
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_speech_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py
```

3. 复查证据：

```bash
jq '.status, .provider, .overall_score' dist/harness/HN-017/dashscope-worker-smoke-summary.json
jq '.status, .provider' dist/harness/HN-017/public-uploads-tunnel-smoke-summary.json
```

4. 结果页 UI 证据：

```bash
cd apps/mobile
flutter run -d 5458B2B5-3DEC-426B-997F-6C612CF5ABB5 \
  -t tool/harness/main_app_shell_harness.dart \
  --dart-define=HARNESS_SCREEN=speaking \
  --no-resident
```

滚动到评分结果卡后保存截图到 `dist/harness/HN-017/ios-simulator-app-shell-speaking-result-screen.jpg`。

物理手机 readiness 还需要补：

- 真机录音提交 API 日志。
- worker 评分日志。
- scored attempt JSON。
- 真机结果页截图。
- `dist/harness/HN-017/real-device-speaking-summary.json`。

## HN-018：独立报告页

1. 生成报告 JSON 证据：

```bash
services/api/.venv/bin/python scripts/harness/generate_hn018_report_evidence.py
```

2. 运行移动端报告页截图测试：

```bash
cd apps/mobile
flutter test tool/harness/reports_screen_capture_test.dart
```

3. iOS 模拟器完整 App shell：

```bash
cd apps/mobile
flutter run -d 5458B2B5-3DEC-426B-997F-6C612CF5ABB5 \
  -t tool/harness/main_app_shell_harness.dart \
  --dart-define=HARNESS_SCREEN=reports \
  --no-resident
```

保存截图到 `dist/harness/HN-018/`。

## 固定收尾检查

```bash
cd /Users/chaucermini/Code/LearningEnglish
flutter analyze
flutter test test/features/speaking/presentation/speaking_partner_screen_test.dart tool/harness/lesson_detail_dashscope_media_capture_test.dart tool/harness/reports_screen_capture_test.dart
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py services/api/tests/test_speaking_assessment_provider.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q
git diff --check
```
