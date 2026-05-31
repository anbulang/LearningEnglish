# HN-017 口语评分 Readiness 摘要

更新时间：2026-05-31

## 当前结论

`HN-017` 的代码链路已经落地：孩子录音上传、音频 storage、异步 worker、DashScope ASR、Qwen 评分、结果页展示和周报回填都已有自动化或 Harness 证据。

物理手机 `Chaucer` 发起的 speaking attempt 已补齐：真机从 `192.168.2.12` 访问局域网 API，完成 `POST /v1/speaking-attempts`，本地 watcher 调用 DashScope ASR + Qwen 后把 `attempt_b0e110c126d1` 写回 `scored`，并通过 iPhone Mirroring 保存了真机结果页截图。

## 已验证内容

- API multipart 上传会创建 speaking attempt，并保存音频对象。
- worker `speaking.score_attempt` 可把 attempt 推进到 `scored`。
- DashScope ASR provider 已覆盖任务创建、轮询、转写结果下载和 Qwen JSON 评分。
- worker 可通过 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 把本地 object key 改写为公网 `/uploads/{object_key}`，避免把局域网 URL 交给 DashScope。
- cloudflared 临时 HTTPS 隧道已验证 DashScope 可拉取本项目 `/uploads/{object_key}` 音频。
- iOS 模拟器 App shell 已展示真实 worker-smoke 评分结果，包括总分、维度分、转写、逐词反馈和建议。
- 物理手机已完成一次 speaking 上传，API 日志、worker 日志、scored attempt JSON 和真机结果页截图已保存。
- 周报聚合可读取 scored speaking attempt，用于 HN-018 的口语表现统计。

## 证据位置

- API / worker 基础证据：`dist/harness/HN-017/speaking-attempt-upload.json`、`dist/harness/HN-017/speaking-attempt-scored.json`、`dist/harness/HN-017/speaking-worker.log`
- DashScope provider smoke：`dist/harness/HN-017/dashscope-speech-smoke-summary.json`、`dist/harness/HN-017/dashscope-speech-smoke-result.json`
- 真实 worker smoke：`dist/harness/HN-017/dashscope-worker-smoke-summary.json`、`dist/harness/HN-017/dashscope-worker-smoke-attempt.json`
- 公网 `/uploads` smoke：`dist/harness/HN-017/public-uploads-tunnel-smoke-summary.json`、`dist/harness/HN-017/public-uploads-tunnel-smoke-result.json`
- iOS 模拟器结果页：`dist/harness/HN-017/ios-simulator-app-shell-speaking-result-screen.jpg`、`dist/harness/HN-017/ios-simulator-app-shell-speaking-summary.json`
- 物理手机 speaking 上传与评分：`dist/harness/HN-017/real-device-speaking-summary.json`、`dist/harness/HN-017/real-device-speaking-attempt.json`、`dist/harness/HN-017/real-device-speaking-worker.log`、`dist/harness/HN-017/real-device-speaking-api.log`、`dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

## 本轮验证命令

```bash
cd apps/mobile
flutter analyze
flutter test test/features/speaking/presentation/speaking_partner_screen_test.dart tool/harness/lesson_detail_dashscope_media_capture_test.dart tool/harness/reports_screen_capture_test.dart
flutter run -d 5458B2B5-3DEC-426B-997F-6C612CF5ABB5 -t tool/harness/main_app_shell_harness.dart --dart-define=HARNESS_SCREEN=speaking --no-resident
```

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py services/api/tests/test_speaking_assessment_provider.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q
git diff --check
```

```bash
set -a; source infra/.env; set +a; APP_ENV=testing DATABASE_URL=sqlite:////private/tmp/learningenglish-hn017-device.db LOCAL_STORAGE_PATH=/private/tmp/learningenglish-hn017-device-uploads PUBLIC_BASE_URL=http://192.168.2.15:8000 STORAGE_BACKEND=local .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
set -a; source infra/.env; set +a; APP_ENV=testing DATABASE_URL=sqlite:////private/tmp/learningenglish-hn017-device.db LOCAL_STORAGE_PATH=/private/tmp/learningenglish-hn017-device-uploads PUBLIC_BASE_URL=http://192.168.2.15:8000 STORAGE_BACKEND=local HN017_PUBLIC_AUDIO_URL=https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav services/api/.venv/bin/python scripts/harness/watch_hn017_speaking_attempts.py
cd apps/mobile
flutter run -d 00008150-00094D0A0A78401C --profile -t tool/harness/real_device_speaking_upload_harness.dart --dart-define=API_BASE_URL=http://192.168.2.15:8000/v1 --no-resident
xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish --timeout 60
```

## 待补内容

- 暂无 HN-017 readiness 必需证据缺口。
