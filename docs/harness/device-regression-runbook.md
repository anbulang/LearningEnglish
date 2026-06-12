# 真机回归 Runbook

更新时间：2026-06-12

## 目的

这份 Runbook 把真机回归拆成四个层级，避免把“能编译”“能安装”“能走主链”“能完成真实 speaking/provider 验证”混成同一个结论。

- `R0`：本地代码和自动化前置检查
- `R1`：真机安装与启动
- `R2`：主链体验回归
- `R3`：真实 provider 与 speaking 回归

执行时优先引用：

- `README.md`
- `Makefile`
- `docs/harness/provider-readiness-runbook.md`
- `docs/harness/evidence-archive-policy.md`
- `dist/harness/`

## 回归等级

| 等级 | 目标 | 必需条件 | 通过证据 | blocked 判定 |
| --- | --- | --- | --- | --- |
| `R0` | 本地准备和文档检查 | 无真机要求 | 自动化测试、analyze、`dist/harness/evidence-index.json`、`git diff --check` | 本地依赖缺失、脚本不可运行或证据索引不可生成 |
| `R1` | 真机安装启动 | iPhone 已解锁，签名和 profile 可用 | 设备 `lockState`、安装日志、启动日志、首页截图或启动确认 | 设备锁屏、设备未注册、签名或 profile 不可用 |
| `R2` | 主链体验回归 | API / worker 在局域网可访问 | 上传、AI 校对、课程详情、报告页截图，API / worker log，summary | API 不可达、worker 未启动、本地网络权限未准备好 |
| `R3` | 真实 provider 回归 | `DASHSCOPE_API_KEY`、真实模型配置和公网音频 URL 可用 | provider summary、worker log、scored JSON、真机 speaking 结果页截图 | provider 配置缺失、代理配置缺失、公网音频 URL 不可拉取 |

## R0：前置检查

目标：先确认当前分支、自动化和证据索引没有明显漂移，再进入真机流程。

```bash
cd /Users/chaucermini/Code/LearningEnglish
make api-test
make worker-test
make mobile-test
make mobile-analyze
python3 scripts/harness/generate_evidence_index_test.py
make harness-evidence-index
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
git diff --check
```

通过标准：

- 测试和 analyze 通过。
- `dist/harness/evidence-index.json` 可生成并通过 JSON 格式化检查。
- 当前工作区没有格式错误。

## R1：真机安装启动

目标：确认当前 iOS 包能够安装到已注册设备并成功启动。

```bash
xcrun devicectl list devices
xcrun devicectl device info lockState --device 19586D29-7FF4-5289-8B83-30AA8C3F273D
LAN_IP=<current-host-ip>
make mobile-ios-ipa IOS_API_BASE_URL="http://${LAN_IP}:8000/v1"
xcrun devicectl device install app --device 19586D29-7FF4-5289-8B83-30AA8C3F273D dist/ios/LearningEnglish-Internal.xcarchive/Products/Applications/Runner.app
xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish --timeout 60
```

建议保留证据：

- `dist/harness/HN-019/device-install-summary.json`
- `dist/harness/HN-019/device-install.log`

通过标准：

- 已注册设备可成功安装并启动 `com.anbulang.learningenglish`。

`blocked` 判定：

- 设备未注册到当前 provisioning profile。
- 签名 identity 或 profile 不可用。
- 局域网 API 地址、健康检查或本地网络权限未准备好。

## R2：主链体验回归

目标：验证“登录 -> 上传 -> AI 校对 -> 课程详情 -> 报告”在真机上可复查。

执行前准备：

- API 和 worker 已启动。
- App 指向当前可访问的局域网 API；不要直接沿用 `Makefile` 的默认 `127.0.0.1`，真机导包时必须显式覆盖 `IOS_API_BASE_URL`。
- 如需要 clean state，先清理测试账号或模拟器/真机旧数据。

真机操作步骤：

1. 登录或恢复已有家长会话。
2. 进入资料库并上传讲义图片。
3. 等待 AI 校对页进入 `needs_review` 或明确失败态。
4. 确认草稿后进入课程详情。
5. 打开报告页，确认不是空白页，也不是旧版复习页复用。

如果希望减少人工录入、直接为 `HN-019` 生成一轮主链 summary，可用一键真机 harness：

```bash
cd /Users/chaucermini/Code/LearningEnglish
API_BASE_URL=http://<current-host-ip>:8000/v1 \
SOURCE_IMAGE_URLS=https://example.com/page-1.jpg,https://example.com/page-2.jpg \
make harness-hn019-real-device-main-chain
```

说明：

- `SOURCE_IMAGE_URLS` 需要提供当前可下载的讲义图片 URL。
- 这条 harness 负责登录、建档、上传、轮询、确认、读取报告，并把 material/job/media/API/worker 摘要归档到 `dist/harness/HN-019/`；截图仍需要手工补存。
- harness 内置对局域网 `healthz` 的 no-proxy 探测，避免 shell 里残留 `HTTP_PROXY` / `HTTPS_PROXY` 时把本机 LAN 健康检查误送到代理。
- 默认真机 ID 使用当前开发机上的 `Chaucer`，如设备变化，通过 `DEVICE_ID=<flutter-device-id>` 和 `DEVICETL_DEVICE_ID=<devicectl-device-id>` 覆盖。
- 默认会在验证结束后重新安装 `dist/ios/export/learning_english_mobile.ipa` 并启动正式 App；如只想保留 harness app，可设置 `HN019_RESTORE_APP=0`。
- 历史 evidence 里出现的固定 LAN IP 只代表当时环境，不应当成当前默认值。

建议保留证据到 `dist/harness/HN-019/`：

- `real-device-main-chain-summary.json`
- `real-device-main-chain-material.json`
- `real-device-main-chain-job.json`
- `real-device-main-chain-media-summary.json`
- `real-device-main-chain-api.log`
- `real-device-main-chain-worker.log`
- `device-upload-review-screen.png`
- `device-lesson-detail-screen.png`
- `device-reports-screen.png`

通过标准：

- 主链可走通，或失败时能定位在明确步骤。
- `summary` 中 material/job 均为 `ready`，图片记录数等于上传页数，学习资产和复习任务数量大于 0。
- `media-summary` 中生成图片、美式 TTS、英式 TTS 均为 `ready`。
- summary 里说明设备、API base URL、provider 模式和结果。

`failed` 判定：

- 前置条件满足，但主链功能异常、状态推进错误或页面跳转错误。

## R3：真实 provider 与 speaking 回归

目标：验证当前默认真实 provider 路径，而不是 stub/mock 路径。

执行边界：

- worksheet 识别默认走 `AI_PROVIDER=qwen`。
- 学习资产默认走 DashScope 图片和 TTS。
- speaking 默认走 DashScope ASR + Qwen 评分。
- speaking 只有在公网音频 URL 可用时才执行真实回归。
- `PUBLIC_BASE_URL` 可以继续给 App 使用局域网地址；`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 必须是 DashScope 可访问的 HTTPS 地址。

最小命令：

```bash
cd /Users/chaucermini/Code/LearningEnglish
set -a; source infra/.env; set +a
services/api/.venv/bin/python scripts/harness/run_hn016a_dashscope_provider_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn016a_worker_dashscope_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_speech_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_dashscope_worker_smoke.py
services/api/.venv/bin/python scripts/harness/run_hn017_public_uploads_tunnel_smoke.py
```

真机 speaking 证据重点检查：

- `dist/harness/HN-017/real-device-speaking-summary.json`
- `dist/harness/HN-017/real-device-speaking-attempt.json`
- `dist/harness/HN-017/real-device-speaking-worker.log`
- `dist/harness/HN-017/real-device-speaking-api.log`
- `dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

通过标准：

- provider smoke 只证明真实 provider 依赖可用，不能单独构成完整 `R3 passed`。
- 完整 `R3 passed` 需要同时具备 provider/worker/scored JSON 证据，以及真机 speaking 结果页截图或 summary。
- 如果只完成 provider smoke，或真机 speaking 缺少结果页/summary，则把 `R3` 明确标为 `partial`；如果前置条件不可用，则标为 `blocked`。

`blocked` 判定：

- 缺少 `DASHSCOPE_API_KEY` 或模型配置。
- 当前网络必须走代理，但 `AI_HTTP_TRUST_ENV`、`MEDIA_HTTP_TRUST_ENV` 或 speaking 相关配置未显式开启。
- `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 不可用，导致 DashScope 无法拉取录音。

## 结果分级

| 结果 | 含义 | 要求 |
| --- | --- | --- |
| `passed` | 功能链路完成 | 证据文件齐全，summary 说明环境和结果 |
| `blocked` | 前置条件不满足 | summary 写明设备、签名、网络或 provider 阻塞项 |
| `failed` | 前置满足但功能异常 | 保留日志、截图和失败步骤 |

## 使用约定

- 不要把 `R1` 的安装成功当成 `R2` 或 `R3` 通过。
- 不要把 unsigned compile、simulator 结果或 stub/mock 测试当成真机真实 provider 通过。
- 每次新增真机证据后，执行一次 `make harness-evidence-index`，让证据目录可以被统一复查。
