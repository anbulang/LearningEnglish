# 讲义上传识别链路 Harness 说明

## 背景

这份文档回答两件事：

1. 当初为什么会产生 `HN-008` 到 `HN-019` 这一串需求。
2. 当前如果要复查上传识别主链，应该看什么入口，而不是继续翻历史过程。

2026-05-05 真机验证时，用户反馈“上传讲义图片并不能识别”，并指出上传页要求填写课程标题、老师名、主题的表单不符合预期。用户当时真正想要的是：直接拍照或选择讲义图片，由系统自动识别标题、主题、词汇和句型，家长只在 AI 草稿阶段做校对。

需要注意：下面保留的历史问题和固定 IP 只用于解释需求来源，不代表仓库此刻仍停留在那个阶段。

## 当前入口

上传识别主链现在已经不是一个待设计问题，而是一条可复查的现有链路。

### 当前仓库事实

- 上传页已经改为拍照/相册优先，不再要求先填表单。
- 上传后会创建后台 job，并进入 AI 校对页。
- AI 校对页会对 `queued` / `processing` 自动轮询。
- 首页与资料库对未完成资料统一进入 AI 校对页；只有 `ready` 材料进入课程详情。
- `failed`、`needs_review`、`ready`、`archived` 的状态收敛已经体现在 API、Flutter 路由和 Harness 文档中。
- HN-012 到 HN-018 都已经有代码和证据落点；HN-017 的物理手机结果页截图也已补齐。

### 复查入口

- 项目级现状与缺口：`docs/project/2026-06-10-status-and-todo.md`
- 主链 / 真机回归入口：`docs/harness/device-regression-runbook.md`
- 真实 provider 入口：`docs/harness/provider-readiness-runbook.md`
- evidence 归档规则：`docs/harness/evidence-archive-policy.md`
- 当前 readiness 总表：`docs/harness/mvp-readiness-checklist.md`

### HN-019 的定位

`HN-019` 不改变上传识别业务逻辑，也不新增上传、AI 校对、课程详情或报告页的功能要求；它只收敛真机回归、provider 运行和 `dist/harness/` 证据归档方式，让既有主链更容易被复查。

## 当前剩余问题

- Android 交付链仍受本机 Flutter / Android SDK 环境阻塞，`make mobile-apk` 还没有形成可复查产物。
- iOS 真机包默认不再假设某个固定局域网地址；导包时需要显式提供当前 `IOS_API_BASE_URL=http://<current-host-ip>:8000/v1`。
- Doubao、OpenAI、DashScope 真依赖在部分网络环境下仍可能受代理继承影响；如果 shell 已配置 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` 但 API / worker 仍无法访问外网，需要额外设置 `AI_HTTP_TRUST_ENV=true` 或 `MEDIA_HTTP_TRUST_ENV=true`。
- `make harness-evidence-index` 已能生成统一索引，但各 `HN-*` summary 字段风格还未完全统一。

## 历史问题摘要

下面这些内容是“为什么会有这批 HN”的背景，不是当前待办列表：

### 当时暴露的问题

- 上传页先让用户选择图片，还要求填写课程标题、老师名、主题。
- 识别当时没有稳定地通过后台队列自动推进到可校对状态。
- 如果用户从资料库点进课程详情，前端会请求 `/knowledge-packs/{materialId}`；未确认生成知识包前会返回 `404`。
- 真机首轮上传识别还暴露过超时、状态不一致、用途说明缺失导致的 iOS 闪退等问题。

### 这些问题对应的收敛结果

- `HN-008`：上传页改为无表单拍照/相册入口。
- `HN-009`：上传后统一进入 AI 校对轮询页。
- `HN-010`：job / material 失败状态收敛一致。
- `HN-011`：provider 超时失败有中文说明与重试入口。
- `HN-012`：真机上传识别 evidence 落地。
- `HN-013`：图片级记录与解析结果长期保留。
- `HN-014`：学习资产自动生成接入主链。
- `HN-015`：课程资料左滑删除完成。
- `HN-016` / `HN-016A`：真实媒体 provider 与国内 DashScope 路径落地。
- `HN-017`：孩子录音上传与 AI 语音评分闭环落地。
- `HN-018`：独立报告页落地。
- `HN-019`：真机回归和 evidence 治理收口。

## 历史 evidence 说明

- 本文里出现的 `192.168.*` 地址都只代表当时的历史 LAN 环境，不是当前默认值。
- 新一轮真机主链回归优先参考 `docs/harness/device-regression-runbook.md`，并使用 `make harness-hn019-real-device-main-chain` 触发真机 harness。
- speaking 相关历史固定 IP 同样只用于说明既有 evidence；复跑时要替换成当前机器可访问的 `API_BASE_URL` / `PUBLIC_BASE_URL`。

## 关键 evidence 目录

- `dist/harness/HN-012/`：真机上传识别
- `dist/harness/HN-014/`：学习资产自动生成
- `dist/harness/HN-015/`：资料删除
- `dist/harness/HN-016/`：OpenAI 兼容媒体路径历史证据
- `dist/harness/HN-016A/`：DashScope 国内媒体 provider
- `dist/harness/HN-017/`：speaking 上传与评分
- `dist/harness/HN-018/`：独立报告页
- `dist/harness/HN-019/`：真机回归与 evidence 治理

## 结论

- 上传识别主链本身已经从“问题定义”进入“现有能力治理”阶段。
- 当前最值得继续投入的不是重复描述 HN-008 到 HN-018 当时怎么修，而是让交付、真机复跑、provider 依赖和 evidence 索引更短、更稳定、更可交接。
