# Harness 文档索引

更新时间：2026-06-10

## 这份目录的作用

`docs/harness/` 只保留当前可复查链路的验收入口、runbook 和 readiness 结论，用来回答三个问题：

1. 现在应该跑哪条命令。
2. 证据应该落到哪个 `dist/harness/HN-*/` 目录。
3. 哪些结论是当前仓库事实，哪些只是历史背景。

## 当前真相源

当前仓库中，与 Harness / readiness 直接相关的真相源限定为：

- `README.md`
- `Makefile`
- `docs/architecture/*`
- `docs/harness/*`
- `docs/project/2026-06-10-status-and-todo.md`
- `services/api/README.md`
- `services/workers/README.md`
- `infra/env/local.example.env`

以下内容可以保留，但默认不作为当前 readiness 结论来源：

- `docs/superpowers/specs/*`
- `docs/superpowers/plans/*`

## 本地 evidence 目录

`dist/harness/` 是本地验收 evidence 目录，不是源码真相源；它用于复查运行证据、排障和交接说明。文档结论与 evidence 冲突时，先更新当前真相源，再补充 summary 说明 evidence 变化。

## 常用命令

```bash
HARNESS_RESET=1 make harness-mvp-readiness
make harness-main-chain-smoke
make harness-doubao-smoke
API_BASE_URL=http://<current-host-ip>:8000/v1 SOURCE_IMAGE_URLS=https://example.com/page-1.jpg,https://example.com/page-2.jpg make harness-hn019-real-device-main-chain
make harness-evidence-index
make harness-reset-ios-sim
make harness-capture-ios-screen SCREEN=login-screen
```

## 当前 Harness 真相源文档

- `mvp-readiness-checklist.md`：MVP readiness 总表。
- `upload-recognition-loop.md`：上传识别主链相关 HN 的背景、收敛状态和验收要求。
- `provider-readiness-runbook.md`：真实 provider 配置、smoke 和失败分类。
- `device-regression-runbook.md`：R0/R1/R2/R3 真机回归路径。
- `evidence-archive-policy.md`：`dist/harness/` 证据保留、脱敏和索引规则。
- `non-technical-pilot-guide.md`：给产品或内部测试同学的试用说明。

## Evidence 目录

| 目录 | 说明 | 关键证据 | 复查入口 |
| --- | --- | --- | --- |
| `dist/harness/HN-003/` | 主链 UI 截图和 clean-state 截图归档 | summary、主链基础页面截图 | `docs/harness/mvp-readiness-checklist.md` |
| `dist/harness/HN-006/` | Doubao provider smoke | `doubao-smoke.log` | `README.md`、`docs/harness/mvp-readiness-checklist.md` |
| `dist/harness/HN-012/` | 真机上传识别 | `real-device-summary.json`、`real-device-job-final.json`、`real-device-material-detail.json` | `docs/harness/upload-recognition-loop.md` |
| `dist/harness/HN-014/` | 学习资产自动生成 | `job-learning-assets.json`、`material-learning-assets.json`、`lesson-learning-assets.png` | `docs/harness/upload-recognition-loop.md` |
| `dist/harness/HN-015/` | 资料删除 | `material-delete-api.log`、`material-delete-worker.log`、`material-delete-screen.png` | `docs/harness/upload-recognition-loop.md` |
| `dist/harness/HN-016A/` | Qwen 识别 + DashScope 媒体 provider | `qwen-material-smoke-summary.json`、`dashscope-provider-smoke-summary.json`、`worker-dashscope-real-summary.json`、`worker-reference-crop.png`、课程详情与 App shell 截图 | `docs/harness/provider-readiness-runbook.md` |
| `dist/harness/HN-017/` | 口语评分 | `dashscope-worker-smoke-summary.json`、`public-uploads-tunnel-smoke-summary.json`、`real-device-speaking-summary.json`、真机结果页截图 | `docs/harness/hn017-speaking-readiness-summary.md`、`docs/harness/provider-readiness-runbook.md` |
| `dist/harness/HN-018/` | 独立报告页 | `weekly-report.json`、`summary.json`、`reports-screen.png` | `docs/harness/provider-readiness-runbook.md` |
| `dist/harness/HN-019/` | 真机回归与 evidence 治理 | `real-device-main-chain-summary.json`、`real-device-main-chain-material.json`、`real-device-main-chain-job.json`、`real-device-main-chain-media-summary.json`、主链 API/worker 日志；历史证据仍保留 `device-main-chain-summary.json` 等 | `docs/harness/device-regression-runbook.md`、`docs/harness/evidence-archive-policy.md` |
| `dist/harness/screens/` | 标准截图路径 | `login-screen.png`、`phone-binding-screen.png`、`upload-screen.png`、`ai-review-screen.png`、`lesson-detail-screen.png`、`report-screen.png` | `docs/harness/mvp-readiness-checklist.md` |

## 当前结论

- 当前主链已经覆盖上传、AI 校对、课程详情、复习、口语评分和报告，不再是只到上传识别的半链路。
- 当前默认真实 provider 路径是 `qwen + DashScope media + DashScope speech`。
- `HN-017` 真机 speaking evidence 已存在；`HN-019` 已完成至少一轮真机安装和主链回归证据归档。
- `HN-019` 现在不只是 runbook 入口；`scripts/harness/run_hn019_real_device_main_chain.py` 已形成独立真机 harness，并带有针对局域网 `healthz` no-proxy 探测的 focused test。
- 当前剩余问题主要在 Android / iOS 交付手册收口、R0/R1/R2/R3 固定复跑纪律、admin 原型向可运营边界收口，以及对非开发成员更短的交付入口。
- `Makefile` 默认 `IOS_API_BASE_URL` 已回到 `http://127.0.0.1:8000/v1`；真机导包必须显式覆盖为当前局域网 API 地址，不能假设某个历史 `192.168.*` 仍然有效。
- 最新项目级进度与 ToDo 统一以 `docs/project/2026-06-10-status-and-todo.md` 为准；旧快照不再并存。

## 使用约定

- 更新 readiness 结论时，优先改当前真相源，不要只改历史 spec / plan。
- 新增 evidence 时，尽量沿用既有文件名；如果必须改名，在 summary JSON 中写清时间戳、设备和用途。
- 交付或文档治理收尾时，至少执行一次：

```bash
rg -n "2026-06-08-status-and-todo|2026-06-07-status-and-todo|2026-06-06-status-and-todo|2026-06-05-status-and-todo|2026-06-04-status-and-todo|2026-06-03-status-and-todo|2026-06-02-status-and-todo|2026-06-01-status-and-todo|2026-05-31-status-and-todo|待生成|预期目录|待补真机证据|infra/\\.env\\.example" README.md docs apps services infra --glob '!docs/superpowers/**'
git diff --check
```
