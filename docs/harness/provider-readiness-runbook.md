# 真实 Provider Readiness 最短复现

更新时间：2026-06-10

## 目的

这份 Runbook 用来复查当前默认真实 provider 链路：

- `HN-016` / `HN-016A`：DashScope 彩色配图 + US/UK TTS。
- `HN-017`：DashScope ASR + Qwen 口语评分。

`HN-018` 只作为报告页 UI / 数据聚合证据，不是 provider readiness 证据；它在本文末尾的“非 Provider 证据”小节单独复查。

所有文档和命令都不保存真实密钥；`dist/harness/` 是本地证据目录，不进入 git。

## 默认配置

`infra/env/local.example.env` 当前应保持以下默认方向：

```dotenv
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

## Provider 矩阵

| 能力 | 当前默认 | 兼容/对照路径 | 关键配置 |
| --- | --- | --- | --- |
| 讲义 OCR / parsing | Qwen-VL + Qwen text | Doubao | `AI_PROVIDER=qwen`、`DASHSCOPE_API_KEY`、`DASHSCOPE_COMPATIBLE_BASE_URL`、`QWEN_VISION_MODEL`、`QWEN_MODEL` |
| 学习资产配图 | DashScope image generation | OpenAI image provider | `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`DASHSCOPE_API_KEY`、`MEDIA_IMAGE_MODEL` |
| 英美音 TTS | DashScope TTS | OpenAI TTS provider | `MEDIA_TTS_PROVIDER=dashscope`、`DASHSCOPE_API_KEY`、`MEDIA_TTS_MODEL`、`MEDIA_TTS_US_VOICE`、`MEDIA_TTS_UK_VOICE` |
| speaking 转写与评分 | DashScope ASR + Qwen scoring | `stub` 只用于测试 | `SPEECH_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_BASE_URL`、`SPEECH_ASSESSMENT_ASR_MODEL`、`SPEECH_ASSESSMENT_SCORING_MODEL`、`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` |

## 失败分类

| 类型 | 现象 | 判定 | 处理 |
| --- | --- | --- | --- |
| 配置缺失 | key、model 或 base URL 未配置 | `blocked` | 从 `infra/env/local.example.env` 复制生成并补齐 `infra/.env`，不要用 mock 冒充真实 provider |
| DNS 或网络不可达 | timeout、name resolution 失败 | `blocked` 或 `failed` | 先确认网络和代理，再复跑 smoke |
| 公网音频 URL 不可拉取 | speaking provider 拒绝 `localhost`、`127.0.0.1`、`192.168.*` 或 `testserver` | `blocked` | 设置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` |
| provider 返回格式不合法 | JSON parse 失败或字段缺失 | `failed` | 保留脱敏日志和 summary，修 adapter 或 prompt |
| worker 未运行 | job 或 attempt 长时间不推进 | `blocked` | 启动 worker 并检查队列 |

## HN-016A：DashScope 媒体

1. 准备环境：

```bash
cd /Users/chaucermini/Code/LearningEnglish
cp infra/env/local.example.env infra/.env
```

在 `infra/.env` 中填入 `DASHSCOPE_API_KEY`。如果当前网络必须走系统代理，再显式设置 `MEDIA_HTTP_TRUST_ENV=true`。

2. 运行真实 Qwen 讲义识别 smoke、媒体 provider smoke 和 worker/storage 回填 smoke：

```bash
cd /Users/chaucermini/Code/LearningEnglish
set -a
source infra/.env
set +a
services/api/.venv/bin/python scripts/harness/run_hn016a_qwen_material_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn016a_dashscope_provider_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn016a_worker_dashscope_smoke.py
```

3. 复查证据：

```bash
cd /Users/chaucermini/Code/LearningEnglish
ls -lh dist/harness/HN-016A/
jq '.status, .provider, .vision_model, .learning_asset_count, .learning_assets_with_bbox' dist/harness/HN-016A/qwen-material-smoke-summary.json
jq '.status, .provider' dist/harness/HN-016A/dashscope-provider-smoke-summary.json
jq '.status, .ready_media_count, .source_reference_crop' dist/harness/HN-016A/worker-dashscope-real-summary.json
```

`qwen-material-smoke-summary.json` 必须证明 Qwen-VL 真实返回 `image_records`、`learning_assets`、课程知识包摘要，并且每个 learning asset 都有 `source_bbox`。如果模型没有返回 bbox，后端会生成保守 fallback bbox，确保 worker 仍能裁剪讲义局部。

`worker-reference-crop.png` 是 worker smoke 使用同一裁剪逻辑生成的参考区域；DashScope image edit 要求输入图宽高均不小于 512，因此裁剪结果会等比放大到 provider 最小尺寸后再传给图生图。

4. 移动端 UI 证据：

```bash
cd /Users/chaucermini/Code/LearningEnglish
(
  cd apps/mobile
  flutter test tool/harness/lesson_detail_dashscope_media_capture_test.dart
)
```

iOS 模拟器完整 App shell 可使用 `tool/harness/main_app_shell_harness.dart` 加载真实生成文件，再保存截图到 `dist/harness/HN-016A/`。

## HN-017：真实口语评分

1. 准备环境：

```bash
cd /Users/chaucermini/Code/LearningEnglish
set -a
source infra/.env
set +a
```

DashScope ASR 必须能从公网下载音频。本地或真机局域网调试时，`PUBLIC_BASE_URL` 可以继续给 App 使用局域网 API；`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 要单独配置为公网可访问的 `/uploads` 根地址。

2. 运行 provider 和 worker smoke：

```bash
cd /Users/chaucermini/Code/LearningEnglish
set -a
source infra/.env
set +a
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_speech_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py
```

3. 复查证据：

```bash
cd /Users/chaucermini/Code/LearningEnglish
jq '.status, .provider, .overall_score' dist/harness/HN-017/dashscope-worker-smoke-summary.json
jq '.status, .provider' dist/harness/HN-017/public-uploads-tunnel-smoke-summary.json
```

4. 结果页 UI 证据：

先用 `xcrun simctl list devices booted` 获取 booted simulator id，并替换命令中的 `SIMULATOR_ID`。

```bash
cd /Users/chaucermini/Code/LearningEnglish
xcrun simctl list devices booted
SIMULATOR_ID="5458B2B5-..." # 替换为本机 booted simulator id
(
  cd apps/mobile
  flutter run -d "$SIMULATOR_ID" \
    -t tool/harness/main_app_shell_harness.dart \
    --dart-define=HARNESS_SCREEN=speaking \
    --no-resident
)
```

滚动到评分结果卡后保存截图到 `dist/harness/HN-017/ios-simulator-app-shell-speaking-result-screen.jpg`。

当前仓库已经补齐一轮真机 evidence，至少应能看到以下文件：

- `dist/harness/HN-017/real-device-speaking-summary.json`
- `dist/harness/HN-017/real-device-speaking-attempt.json`
- `dist/harness/HN-017/real-device-speaking-worker.log`
- `dist/harness/HN-017/real-device-speaking-api.log`
- `dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

如果要重新跑一轮真机 readiness，保持同一套文件名或在 summary 中明确新的时间戳与设备信息，避免后续证据索引混乱。

## 非 Provider 证据：HN-018 报告页 UI / 数据聚合

本节用于证明学习资产掌握度进入独立报告页，以及报告页 UI / 数据聚合链路可复查；它不是 provider readiness 证据，也不用于判断 DashScope / Qwen provider 是否 ready。

1. 生成报告 JSON 证据：

```bash
cd /Users/chaucermini/Code/LearningEnglish
services/api/.venv/bin/python scripts/harness/generate_hn018_report_evidence.py
```

2. 运行移动端报告页截图测试：

```bash
cd /Users/chaucermini/Code/LearningEnglish
(
  cd apps/mobile
  flutter test tool/harness/reports_screen_capture_test.dart
)
```

3. iOS 模拟器完整 App shell：

先用 `xcrun simctl list devices booted` 获取 booted simulator id，并替换命令中的 `SIMULATOR_ID`。

```bash
cd /Users/chaucermini/Code/LearningEnglish
xcrun simctl list devices booted
SIMULATOR_ID="5458B2B5-..." # 替换为本机 booted simulator id
(
  cd apps/mobile
  flutter run -d "$SIMULATOR_ID" \
    -t tool/harness/main_app_shell_harness.dart \
    --dart-define=HARNESS_SCREEN=reports \
    --no-resident
)
```

保存截图到 `dist/harness/HN-018/`。

## 固定收尾检查

```bash
cd /Users/chaucermini/Code/LearningEnglish
make mobile-analyze
(
  cd apps/mobile
  flutter test test/features/speaking/presentation/speaking_partner_screen_test.dart tool/harness/lesson_detail_dashscope_media_capture_test.dart tool/harness/reports_screen_capture_test.dart
)
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py services/api/tests/test_speaking_assessment_provider.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q
git diff --check
```
