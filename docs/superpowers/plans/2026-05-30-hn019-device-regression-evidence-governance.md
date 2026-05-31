# HN-019 Device Regression Evidence Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把真机回归、provider 运行手册和 `dist/harness/` evidence 归档规则固化为可复查、可移交的工程流程。

**Architecture:** 本阶段不改业务主链，只新增/整理 Harness 文档、一个本地 evidence index 脚本和对应测试。`docs/harness/` 承担运行真相源，`docs/project/` 承担项目状态快照，`dist/harness/` 继续作为本地证据实体目录。

**Tech Stack:** Markdown 文档、Python 标准库、现有 `Makefile`、现有 Flutter/API/worker Harness 入口。

---

## 当前工作区约束

- 当前分支应为 `codex/hn019-device-regression-evidence`。
- 已有未提交文档变更是本计划输入，不要回滚：
  - `README.md`
  - `apps/mobile/README.md`
  - `docs/architecture/mobile-architecture.md`
  - `docs/architecture/overview.md`
  - `docs/harness/hn017-speaking-readiness-summary.md`
  - `docs/harness/mvp-readiness-checklist.md`
  - `docs/harness/non-technical-pilot-guide.md`
  - `docs/harness/provider-readiness-runbook.md`
  - `docs/harness/upload-recognition-loop.md`
  - `docs/project/README.md`
  - 删除 `docs/project/2026-05-27-status-and-todo.md`
  - 新增 `docs/project/2026-05-29-status-and-todo.md`
- HN-019 实施时应把状态快照推进到 `2026-05-30`，避免当前日期下继续新增 `2026-05-29` 作为最新状态。

---

### Task 1: 收口项目状态快照和入口链接

**Files:**
- Rename: `docs/project/2026-05-29-status-and-todo.md` -> `docs/project/2026-05-30-status-and-todo.md`
- Delete: `docs/project/2026-05-27-status-and-todo.md`
- Modify: `README.md`
- Modify: `docs/project/README.md`
- Modify: `apps/mobile/README.md`
- Modify: `docs/architecture/overview.md`
- Modify: `docs/architecture/mobile-architecture.md`
- Modify: `docs/harness/non-technical-pilot-guide.md`

- [ ] **Step 1: Confirm current dirty files**

Run:

```bash
git status --short --branch
```

Expected: branch is `codex/hn019-device-regression-evidence`; existing doc changes are visible and should be preserved.

- [ ] **Step 2: Rename latest status snapshot**

Run:

```bash
mv docs/project/2026-05-29-status-and-todo.md docs/project/2026-05-30-status-and-todo.md
```

Expected: `docs/project/2026-05-30-status-and-todo.md` exists and `docs/project/2026-05-29-status-and-todo.md` no longer exists.

- [ ] **Step 3: Update links and date references**

Edit:

```markdown
README.md
- 项目进度与 ToDo link -> docs/project/2026-05-30-status-and-todo.md

docs/project/README.md
- 当前最新快照：`2026-05-30-status-and-todo.md`

docs/harness/non-technical-pilot-guide.md
- 当前版本说明：按 2026-05-30 仓库现状更新
- 当前交付状态：截至 2026-05-30
```

In `apps/mobile/README.md`, `docs/architecture/overview.md`, and `docs/architecture/mobile-architecture.md`, keep the already-correct HN-017 wording: 真机 evidence 已存在，重新验收时仍需公网音频 URL。

- [ ] **Step 4: Update project snapshot content for HN-019**

In `docs/project/2026-05-30-status-and-todo.md`, adjust these sections:

```markdown
## 当前结论

当前项目处于 **学习主链已成型、默认真实 provider 已切到 Qwen + DashScope、speaking / report / admin phase 1 均已有代码与本地 evidence，但真机回归、provider 手册和 evidence 归档还需要工程化收口** 的阶段。

### P0：真机回归与证据治理收口

- [x] 状态快照已切到 `2026-05-30`，替换旧状态快照，避免近似快照并存。
- [x] README 和 `docs/project/README.md` 已同步到最新状态快照链接。
- [x] 明确 `README.md`、`docs/architecture/*`、`docs/harness/*`、服务 README、`Makefile` 才是当前真相源；`docs/superpowers/*` 与文章草稿保留为规划 / 历史材料。
- [ ] 增加 `docs/harness/device-regression-runbook.md`，把 R0/R1/R2/R3 真机回归路径、证据文件和 blocked 判定写清楚。
- [ ] 增加 `docs/harness/evidence-archive-policy.md`，明确 `dist/harness/HN-*` 的保留规则、脱敏要求和命名方式。
- [ ] 增加 `docs/harness/README.md`，说明 `HN-003`、`HN-006`、`HN-012`、`HN-014`、`HN-015`、`HN-016A`、`HN-017`、`HN-018`、`HN-019` 的关键证据文件与复查入口。
- [ ] 增加 `scripts/harness/generate_evidence_index.py`，生成 `dist/harness/evidence-index.json`。
```

- [ ] **Step 5: Run stale reference check for current truth-source docs**

Run:

```bash
rg -n "2026-05-27|2026-05-28-status-and-todo|2026-05-29-status-and-todo|待补证据|infra/.env.example" README.md apps/mobile/README.md docs/architecture docs/harness docs/project
```

Expected: no hits in current truth-source docs. If `docs/harness/provider-readiness-runbook.md` intentionally mentions `infra/env/local.example.env`, that is correct and should not be changed.

---

### Task 2: 新增真机回归 Runbook

**Files:**
- Create: `docs/harness/device-regression-runbook.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Modify: `docs/harness/upload-recognition-loop.md`

- [ ] **Step 1: Create device regression runbook**

Create `docs/harness/device-regression-runbook.md` with this structure:

```markdown
# 真机回归 Runbook

更新时间：2026-05-30

## 目的

这份 runbook 用于复查 LearningEnglish 在真实 iPhone 上的最短链路：安装启动、连接局域网 API、上传讲义、AI 校对、课程详情、口语评分和报告页。它把真机验收拆成 R0 到 R3，避免每次都把“环境不可用”误判成“功能失败”。

## 回归等级

| 等级 | 目标 | 必需条件 | 通过证据 | blocked 判定 |
| --- | --- | --- | --- | --- |
| R0 | 本地准备和文档检查 | 无真机要求 | `git diff --check`、stale grep、evidence index JSON | 本地依赖缺失 |
| R1 | 真机安装启动 | iPhone 已解锁，签名可用 | 设备 lockState、安装/启动日志、首页截图 | 设备锁屏、签名不可用 |
| R2 | 主链体验回归 | API/worker 局域网可访问 | 上传/AI 校对/课程详情/报告页截图，API log | API 不可达、worker 未启动 |
| R3 | 真实 provider 回归 | `DASHSCOPE_API_KEY`，公网 `/uploads` 或对象存储 URL | provider summary、worker log、scored JSON、真机结果页截图 | provider 配置缺失、公网音频 URL 不可拉取 |

## R0：本地准备

```bash
cd /Users/chaucermini/Code/LearningEnglish
git status --short --branch
make mobile-analyze
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_assessment_provider.py services/api/tests/test_review_report_failures.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q
python3 scripts/harness/generate_evidence_index.py
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
git diff --check
```

## R1：真机安装启动

```bash
xcrun devicectl list devices
xcrun devicectl device info lockState --device 19586D29-7FF4-5289-8B83-30AA8C3F273D
make mobile-ios-ipa IOS_API_BASE_URL=http://<LAN_IP>:8000/v1
xcrun devicectl device install app --device 19586D29-7FF4-5289-8B83-30AA8C3F273D dist/ios/export/learning_english_mobile.ipa
xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish --timeout 60
```

## R2：主链体验回归

启动 API 和 worker 后，在真机完成：

1. 登录或进入已有家长身份。
2. 进入资料库上传讲义图片。
3. 等待 AI 校对页进入可确认状态。
4. 确认后进入课程详情。
5. 打开报告页，确认不是空白或旧复习页复用。

证据保存到 `dist/harness/HN-019/`：

- `device-main-chain-api.log`
- `device-main-chain-worker.log`
- `device-upload-review-screen.png`
- `device-lesson-detail-screen.png`
- `device-reports-screen.png`
- `device-main-chain-summary.json`

## R3：真实 provider 回归

R3 只在公网音频 URL 可用时执行。`PUBLIC_BASE_URL` 可以继续给 App 使用局域网地址，但 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` 必须是 DashScope 可访问的 HTTPS 地址。

```bash
SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL=https://<public-host> \
python3 scripts/harness/run_hn017_dashscope_speech_smoke.py
```

真机 speaking 回归证据保存到：

- `dist/harness/HN-017/real-device-speaking-summary.json`
- `dist/harness/HN-017/real-device-speaking-attempt.json`
- `dist/harness/HN-017/real-device-speaking-worker.log`
- `dist/harness/HN-017/real-device-speaking-api.log`
- `dist/harness/HN-017/real-device-speaking-result-screen-cropped.png`

## 结果判定

- `passed`：功能链路完成，证据文件存在，summary 能说明环境和结果。
- `blocked`：设备、签名、网络、provider 配置或公网 URL 不满足，summary 必须写明阻塞条件。
- `failed`：前置条件满足但功能链路异常，必须保留日志和截图。
```

- [ ] **Step 2: Update readiness checklist with HN-019**

In `docs/harness/mvp-readiness-checklist.md`, add an HN-019 row/section:

```markdown
- [ ] HN-019 真机回归与 evidence 治理
  - `docs/harness/device-regression-runbook.md` 已说明 R0/R1/R2/R3。
  - `docs/harness/evidence-archive-policy.md` 已说明证据保留、脱敏和归档规则。
  - `scripts/harness/generate_evidence_index.py` 能生成 `dist/harness/evidence-index.json`。
  - HN-017 既有真机 evidence 保持为已闭环状态，不重新标为待补。
```

- [ ] **Step 3: Link HN-019 from upload recognition loop**

In `docs/harness/upload-recognition-loop.md`, add a short HN-019 subsection under readiness/governance:

```markdown
### HN-019：真机回归与 evidence 治理

HN-019 不改变上传识别主链，而是把真机回归、provider 运行和 `dist/harness/` 证据归档方式写成可复查流程。执行入口见 `docs/harness/device-regression-runbook.md`、`docs/harness/provider-readiness-runbook.md` 和 `docs/harness/evidence-archive-policy.md`。
```

---

### Task 3: 强化 Provider Readiness Runbook

**Files:**
- Modify: `docs/harness/provider-readiness-runbook.md`
- Modify: `infra/env/local.example.env` only if current comments contradict the runbook

- [ ] **Step 1: Add provider matrix**

In `docs/harness/provider-readiness-runbook.md`, add:

```markdown
## Provider 矩阵

| 能力 | 当前默认 | 兼容/对照路径 | 关键配置 |
| --- | --- | --- | --- |
| 讲义 OCR / parsing | Qwen-VL + Qwen text | Doubao | `AI_PROVIDER=qwen`、`DASHSCOPE_API_KEY`、`DASHSCOPE_COMPATIBLE_BASE_URL`、`QWEN_VISION_MODEL`、`QWEN_MODEL` |
| 学习资产配图 | DashScope image generation | OpenAI image provider | `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_IMAGE_MODEL` |
| 英美音 TTS | DashScope TTS | OpenAI TTS provider | `MEDIA_TTS_PROVIDER=dashscope`、`MEDIA_TTS_MODEL`、`MEDIA_TTS_US_VOICE`、`MEDIA_TTS_UK_VOICE` |
| speaking 转写与评分 | DashScope ASR + Qwen scoring | stub 只用于测试 | `SPEECH_ASSESSMENT_PROVIDER=dashscope`、`SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` |
```

- [ ] **Step 2: Add failure classification**

Add:

```markdown
## 失败分类

| 类型 | 现象 | 判定 | 处理 |
| --- | --- | --- | --- |
| 配置缺失 | summary 显示 key/model/base URL missing | `blocked` | 补齐 `infra/.env`，不要回退 mock 冒充真实 provider |
| DNS/网络不可达 | provider request timeout 或 name resolution 失败 | `blocked` 或 `failed` | 先确认代理和网络，再复跑 smoke |
| 公网音频 URL 不可拉取 | speaking provider 拒绝 `localhost`、`127.0.0.1`、`192.168.*` 或 `testserver` | `blocked` | 设置 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL` |
| provider 返回格式不合法 | JSON parse 或字段缺失 | `failed` | 保存脱敏日志和 summary，修 adapter 或 prompt |
| worker 未运行 | API 创建 job/attempt 后状态长期不变 | `blocked` | 启动 worker 并检查队列 |
```

- [ ] **Step 3: Remove stale env references**

Run:

```bash
rg -n "infra/.env.example|\\.env.example" docs/harness/provider-readiness-runbook.md infra README.md docs/project docs/architecture
```

Expected: no current runbook references to `infra/.env.example`. Valid env template reference is `infra/env/local.example.env`.

---

### Task 4: 新增 Evidence 归档策略和 Harness 索引文档

**Files:**
- Create: `docs/harness/evidence-archive-policy.md`
- Create: `docs/harness/README.md`
- Modify: `README.md`

- [ ] **Step 1: Create archive policy**

Create `docs/harness/evidence-archive-policy.md`:

```markdown
# Harness Evidence 归档策略

更新时间：2026-05-30

## 目的

`dist/harness/` 保存本地验收证据。它不是源码真相源，也不默认提交 git；它是复查、排障、交接和 PR 说明的证据来源。

## 目录规则

- 每个需求使用 `dist/harness/HN-XXX/`。
- 每个目录优先保留一个 `summary.json` 或等价摘要文件。
- 多次复跑可以使用稳定文件名覆盖，也可以使用 `YYYYMMDD-HHMMSS/` 子目录；无论哪种方式，summary 必须说明 `run_id`、`started_at`、`device`、`result` 和关键文件。

## 必须保留的证据类型

| 类型 | 示例 | 要求 |
| --- | --- | --- |
| summary | `summary.json`、`real-device-speaking-summary.json` | JSON 可格式化，记录命令、环境、结果、关键文件 |
| API log | `*-api.log` | 脱敏，保留关键 route 和状态码 |
| worker log | `*-worker.log` | 脱敏，保留 job/attempt 状态变化 |
| screenshot | `*.png`、`*.jpg` | 展示用户可见状态，失败截图需要配 summary |
| provider output | `*.json`、`*.mp3`、`*.wav`、`*.png` | 不提交 git，summary 引用相对路径 |

## 脱敏要求

证据中不得包含：

- `DASHSCOPE_API_KEY`
- `OPENAI_API_KEY`
- `ARK_API_KEY`
- `Authorization` header
- 签名 URL 的完整 query string
- 手机号、真实姓名和长期有效 token

## 删除与替代

不要直接删除旧证据。需要替代时，在新的 summary 中写明旧证据路径和替代原因。大文件清理必须先确认路径，只清理明确目标。

## 索引

运行：

```bash
python3 scripts/harness/generate_evidence_index.py
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
```

索引只记录文件元数据，不读取敏感内容。
```

- [ ] **Step 2: Create docs/harness index**

Create `docs/harness/README.md`:

```markdown
# Harness 文档索引

## 当前真相源

- `mvp-readiness-checklist.md`：MVP readiness 总表。
- `upload-recognition-loop.md`：讲义上传、AI 校对、课程详情、媒体、speaking、报告相关 HN。
- `provider-readiness-runbook.md`：真实 provider 配置、smoke、失败分类。
- `device-regression-runbook.md`：真机 R0/R1/R2/R3 回归流程。
- `evidence-archive-policy.md`：`dist/harness/` 证据保留、脱敏和索引规则。
- `non-technical-pilot-guide.md`：非开发试用说明。

## Evidence 目录

| 目录 | 说明 | 关键证据 |
| --- | --- | --- |
| `dist/harness/HN-003/` | 早期主链/截图证据 | summary、截图 |
| `dist/harness/HN-006/` | Doubao provider smoke | doubao smoke log |
| `dist/harness/HN-012/` | 上传识别真机/接口证据 | API log、material/job JSON |
| `dist/harness/HN-014/` | 学习资产生成证据 | asset/pack JSON |
| `dist/harness/HN-015/` | 删除和归档证据 | API/test evidence |
| `dist/harness/HN-016A/` | DashScope 媒体 provider | provider summary、worker storage、课程详情截图 |
| `dist/harness/HN-017/` | speaking 上传和真实评分 | real-device summary、attempt JSON、worker/API log、结果页截图 |
| `dist/harness/HN-018/` | 独立报告页 | weekly-report JSON、报告页截图 |
| `dist/harness/HN-019/` | 真机回归与 evidence 治理 | R0/R1/R2/R3 summary、evidence index |
```

- [ ] **Step 3: Link Harness index from root README**

In `README.md` docs table, add or update:

```markdown
| Harness 文档索引 | [`docs/harness/README.md`](docs/harness/README.md) |
| Evidence 归档策略 | [`docs/harness/evidence-archive-policy.md`](docs/harness/evidence-archive-policy.md) |
| 真机回归 Runbook | [`docs/harness/device-regression-runbook.md`](docs/harness/device-regression-runbook.md) |
```

---

### Task 5: 新增 Evidence Index 脚本和测试

**Files:**
- Create: `scripts/harness/generate_evidence_index.py`
- Create: `scripts/harness/generate_evidence_index_test.py`
- Modify: `Makefile`

- [ ] **Step 1: Write failing script test**

Create `scripts/harness/generate_evidence_index_test.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import generate_evidence_index


class EvidenceIndexTest(unittest.TestCase):
    def test_build_index_lists_hn_directories_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            harness = root / "dist" / "harness"
            hn017 = harness / "HN-017"
            hn017.mkdir(parents=True)
            (hn017 / "real-device-speaking-summary.json").write_text('{"result":"passed"}\n', encoding="utf-8")
            (hn017 / "real-device-speaking-worker.log").write_text("attempt scored\n", encoding="utf-8")
            (hn017 / "real-device-speaking-result-screen-cropped.png").write_bytes(b"PNG")

            index = generate_evidence_index.build_index(root=root)

        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["harness_root"], "dist/harness")
        self.assertEqual(len(index["requirements"]), 1)
        requirement = index["requirements"][0]
        self.assertEqual(requirement["id"], "HN-017")
        self.assertTrue(requirement["has_summary"])
        self.assertEqual(requirement["file_count"], 3)
        self.assertEqual(
            [item["path"] for item in requirement["files"]],
            [
                "dist/harness/HN-017/real-device-speaking-result-screen-cropped.png",
                "dist/harness/HN-017/real-device-speaking-summary.json",
                "dist/harness/HN-017/real-device-speaking-worker.log",
            ],
        )

    def test_write_index_creates_valid_json_for_missing_harness_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = generate_evidence_index.write_index(root=root)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["requirements"], [])
        self.assertEqual(output.relative_to(root).as_posix(), "dist/harness/evidence-index.json")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and confirm it fails**

Run:

```bash
python3 scripts/harness/generate_evidence_index_test.py
```

Expected: FAIL because `scripts/harness/generate_evidence_index.py` does not exist or lacks `build_index`.

- [ ] **Step 3: Implement evidence index script**

Create `scripts/harness/generate_evidence_index.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HARNESS_RELATIVE = Path("dist") / "harness"
OUTPUT_NAME = "evidence-index.json"
EVIDENCE_SUFFIXES = {
    ".json": "json",
    ".log": "log",
    ".png": "screenshot",
    ".jpg": "screenshot",
    ".jpeg": "screenshot",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
}


def build_index(*, root: Path = ROOT) -> dict[str, Any]:
    harness_root = root / HARNESS_RELATIVE
    requirements: list[dict[str, Any]] = []
    if harness_root.exists():
        for requirement_dir in sorted(path for path in harness_root.iterdir() if path.is_dir() and path.name.startswith("HN-")):
            files = [_file_entry(root=root, path=path) for path in _evidence_files(requirement_dir)]
            requirements.append(
                {
                    "id": requirement_dir.name,
                    "path": requirement_dir.relative_to(root).as_posix(),
                    "has_summary": any(_is_summary(Path(item["path"])) for item in files),
                    "file_count": len(files),
                    "total_size_bytes": sum(int(item["size_bytes"]) for item in files),
                    "files": files,
                }
            )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness_root": HARNESS_RELATIVE.as_posix(),
        "requirements": requirements,
    }


def write_index(*, root: Path = ROOT) -> Path:
    harness_root = root / HARNESS_RELATIVE
    harness_root.mkdir(parents=True, exist_ok=True)
    output = harness_root / OUTPUT_NAME
    output.write_text(json.dumps(build_index(root=root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _evidence_files(requirement_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in requirement_dir.rglob("*")
        if path.is_file() and path.name != OUTPUT_NAME and path.suffix.lower() in EVIDENCE_SUFFIXES
    )


def _file_entry(*, root: Path, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": path.relative_to(root).as_posix(),
        "type": EVIDENCE_SUFFIXES.get(path.suffix.lower(), "other"),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "is_summary": _is_summary(path),
    }


def _is_summary(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() == ".json" and "summary" in name


def main() -> None:
    output = write_index()
    print(output.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run script tests**

Run:

```bash
python3 scripts/harness/generate_evidence_index_test.py
```

Expected: `OK`.

- [ ] **Step 5: Add Makefile target**

In `Makefile`, update `.PHONY` and add target:

```make
.PHONY: api-install api-dev api-test api-migrate worker-install worker-dev worker-test admin-install admin-dev admin-dev-live admin-test admin-build infra-up infra-down infra-reset mobile-bootstrap mobile-test mobile-analyze mobile-apk mobile-ios-prep mobile-ios-archive mobile-ios-ipa harness-main-chain-smoke harness-mvp-readiness harness-doubao-smoke harness-reset-ios-sim harness-capture-ios-screen harness-evidence-index

harness-evidence-index:
	$(PYTHON) /Users/chaucermini/Code/LearningEnglish/scripts/harness/generate_evidence_index.py
```

- [ ] **Step 6: Generate and validate local evidence index**

Run:

```bash
make harness-evidence-index
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
```

Expected: command prints `dist/harness/evidence-index.json`; JSON validation passes. `dist/harness/evidence-index.json` remains ignored unless the repo intentionally tracks it.

---

### Task 6: Final verification and commit

**Files:**
- All files touched by Tasks 1-5

- [ ] **Step 1: Run focused verification**

Run:

```bash
python3 scripts/harness/generate_evidence_index_test.py
make harness-evidence-index
python3 -m json.tool dist/harness/evidence-index.json >/tmp/learningenglish-evidence-index-check.json
git diff --check
```

Expected:

- Python test prints `OK`.
- `make harness-evidence-index` prints `dist/harness/evidence-index.json`.
- JSON validation exits `0`.
- `git diff --check` exits `0`.

- [ ] **Step 2: Run stale truth-source grep**

Run:

```bash
rg -n "2026-05-27|2026-05-28-status-and-todo|2026-05-29-status-and-todo|待补证据|infra/.env.example" README.md apps/mobile/README.md docs/architecture docs/harness docs/project
```

Expected: no hits. If a hit appears in `docs/superpowers/`, ignore it only when the command explicitly excludes current truth-source docs; do not ignore hits in README, architecture, harness, or project status docs.

- [ ] **Step 3: Confirm git status**

Run:

```bash
git status --short --branch
```

Expected: only intended HN-019 docs/script/test/Makefile files are changed; `dist/harness/evidence-index.json` should not appear if ignored.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add README.md Makefile apps/mobile/README.md docs/architecture/mobile-architecture.md docs/architecture/overview.md docs/harness/README.md docs/harness/device-regression-runbook.md docs/harness/evidence-archive-policy.md docs/harness/hn017-speaking-readiness-summary.md docs/harness/mvp-readiness-checklist.md docs/harness/non-technical-pilot-guide.md docs/harness/provider-readiness-runbook.md docs/harness/upload-recognition-loop.md docs/project/README.md docs/project/2026-05-30-status-and-todo.md docs/project/2026-05-27-status-and-todo.md scripts/harness/generate_evidence_index.py scripts/harness/generate_evidence_index_test.py
git commit -m "docs: add HN-019 regression evidence governance"
```

Expected: commit succeeds. If `docs/project/2026-05-27-status-and-todo.md` is already deleted in index, `git add` records the deletion.

- [ ] **Step 5: Prepare PR**

Run:

```bash
git status --short --branch
git log -3 --oneline
```

Expected: working tree clean except ignored evidence outputs. Push and PR creation should happen after review, using the usual branch workflow.

---

## Plan Self-Review

- Spec coverage:
  - 真机 runbook covered by Task 2.
  - provider runbook covered by Task 3.
  - evidence archive policy covered by Task 4.
  - evidence index script covered by Task 5.
  - project/entry docs covered by Task 1 and Task 6.
- Placeholder scan:
  - No placeholder or unspecified implementation steps are intentionally left.
  - Optional real-device R1/R2/R3 execution is documented in the runbook; implementation verification only requires R0 and script checks unless the device/provider conditions are available.
- Type consistency:
  - Script functions referenced by tests are `build_index(root=...)` and `write_index(root=...)`.
  - Output file is consistently `dist/harness/evidence-index.json`.
