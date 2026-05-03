# Harness Engineering MVP Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐第一批 `HN-001` 到 `HN-007` 需求，让 MVP readiness 具备清晰日志、provider 分层验证、clean-state UI 证据流程、Android/iOS 交付说明和稳定证据目录约定。

**Architecture:** 保留现有 `make` 入口和 shell harness，不引入新的任务框架。新增少量 `scripts/harness` helper，把证据写入 `dist/harness/HN-*`，同时保留 `dist/harness/mvp-readiness.log` 和 `dist/harness/screens` 这两个已有路径，避免破坏当前文档引用。

**Tech Stack:** Bash、Makefile、Flutter CLI、xcrun simctl/devicectl、FastAPI/pytest、Flutter test、Markdown 文档。

---

## 文件结构

- 修改：`scripts/harness/run_mvp_readiness.sh`
  - 负责完整 MVP readiness 执行、日志分级、Profile/Internal IPA 命名、Android fallback 环境提示、可选 provider smoke 入口。
- 新建：`scripts/harness/run_doubao_smoke.sh`
  - 负责把 Doubao provider smoke 输出写入 `dist/harness/HN-006/doubao-smoke.log`，并保留 Python 脚本的退出码语义。
- 新建：`scripts/harness/reset_ios_simulator_app.sh`
  - 负责只卸载 booted iOS simulator 上的 `com.anbulang.learningenglish`，用于清理移动端 token/session 状态。
- 新建：`scripts/harness/capture_ios_simulator_screen.sh`
  - 负责从 booted iOS simulator 截图，写入 `dist/harness/HN-003/screens`，并同步一份到 `dist/harness/screens`。
- 修改：`Makefile`
  - 增加 `harness-doubao-smoke`、`harness-reset-ios-sim`、`harness-capture-ios-screen` targets。
- 修改：`docs/harness/mvp-readiness-checklist.md`
  - 将第一批需求的验收状态、证据目录、clean-state 流程、Android/iOS/provider 说明落到 checklist。
- 修改：`README.md`
  - 补充中文 harness 操作说明，覆盖 Android fallback、iOS 内测包、Doubao smoke、UI 证据采集。

## 实施顺序

先做脚本能力，再补文档，最后运行轻量验证。`HARNESS_RESET=1 make harness-mvp-readiness` 是重型验证，放到最后由执行者根据环境决定是否运行。

### Task 1: 规范 MVP readiness harness 日志和可选步骤

**需求覆盖：** `HN-001`、`HN-002`、`HN-005`、部分 `HN-007`

**Files:**
- Modify: `scripts/harness/run_mvp_readiness.sh`

- [ ] **Step 1: 写入新的 harness shell 结构**

用下面内容替换 `scripts/harness/run_mvp_readiness.sh` 的主体。保留 shebang 和 `set -euo pipefail`，其余内容按下面版本更新。

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"
HARNESS_ROOT="$ROOT/dist/harness"
LOG_DIR="$HARNESS_ROOT/HN-001"
LOG_FILE="$LOG_DIR/mvp-readiness.log"
LEGACY_LOG_FILE="$HARNESS_ROOT/mvp-readiness.log"
RESET="${HARNESS_RESET:-0}"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
}

sync_legacy_log() {
  mkdir -p "$HARNESS_ROOT"
  cp "$LOG_FILE" "$LEGACY_LOG_FILE"
}

run_step() {
  local name="$1"
  shift
  local started
  started=$(date +%s)
  log "START: $name"
  if "$@" 2>&1 | tee -a "$LOG_FILE"; then
    log "PASS: $name ($(( $(date +%s) - started ))s)"
  else
    log "FAIL: $name ($(( $(date +%s) - started ))s)"
    sync_legacy_log
    return 1
  fi
}

run_optional_step() {
  local name="$1"
  shift
  local started
  started=$(date +%s)
  log "START optional: $name"
  if "$@" 2>&1 | tee -a "$LOG_FILE"; then
    log "PASS optional: $name ($(( $(date +%s) - started ))s)"
    return 0
  fi
  log "WARN optional: $name ($(( $(date +%s) - started ))s)"
  return 0
}

log_android_environment() {
  log "Android fallback artifact: apps/mobile/build/app/outputs/flutter-apk/app-debug.apk"
  if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
    log "Android SDK hint: ANDROID_HOME and ANDROID_SDK_ROOT are not set; Flutter may still locate Android SDK from its config."
  else
    log "Android SDK hint: ANDROID_HOME=${ANDROID_HOME:-unset}; ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT:-unset}"
  fi
}

log_ios_delivery_context() {
  log "iOS package type: Profile/Internal IPA"
  log "iOS artifact: dist/ios/export/learning_english_mobile.ipa"
  log "iOS API base URL: ${IOS_API_BASE_URL:-Makefile default}"
}

log "MVP readiness harness started"
log "HARNESS_RESET=$RESET"
log "Evidence directory: $LOG_DIR"

if [[ "$RESET" == "1" ]]; then
  run_step "Reset infrastructure volumes" make -C "$ROOT" infra-reset
fi

if [[ ! -f "$ROOT/infra/.env" ]]; then
  cp "$ROOT/infra/.env.example" "$ROOT/infra/.env"
  log "Copied infra/.env.example to infra/.env"
fi

run_step "Infrastructure" make -C "$ROOT" infra-up
run_step "API dependencies" make -C "$ROOT" api-install
run_step "Worker dependencies" make -C "$ROOT" worker-install
run_step "Database migration" make -C "$ROOT" api-migrate
run_step "API tests" make -C "$ROOT" api-test
run_step "Worker tests" make -C "$ROOT" worker-test
run_step "Mobile bootstrap" make -C "$ROOT" mobile-bootstrap
run_step "Mobile tests" make -C "$ROOT" mobile-test
run_step "Mobile analyze" make -C "$ROOT" mobile-analyze
run_step "Main chain smoke" make -C "$ROOT" harness-main-chain-smoke

log_ios_delivery_context
if make -C "$ROOT" mobile-ios-ipa 2>&1 | tee -a "$LOG_FILE"; then
  log "PASS optional: iOS Profile/Internal IPA"
else
  log "WARN optional: iOS Profile/Internal IPA export failed; inspect log for Xcode account, provisioning, device membership, or signing issues"
  log_android_environment
  run_optional_step "Android debug APK fallback" make -C "$ROOT" mobile-apk
fi

if [[ -x "$ROOT/scripts/harness/run_doubao_smoke.sh" ]]; then
  run_optional_step "Doubao provider smoke" make -C "$ROOT" harness-doubao-smoke
else
  log "WARN optional: Doubao provider smoke script is not installed yet"
fi

log "MVP readiness harness finished"
sync_legacy_log
```

- [ ] **Step 2: 运行 shell 语法检查**

Run:

```bash
bash -n scripts/harness/run_mvp_readiness.sh
```

Expected: 命令无输出，退出码为 `0`。

- [ ] **Step 3: 验证不再出现误导性 iOS Debug 标签**

Run:

```bash
rg -n "iOS Debug IPA|Debug IPA" scripts/harness/run_mvp_readiness.sh
```

Expected: 无匹配，`rg` 退出码为 `1`。

- [ ] **Step 4: 提交本任务**

```bash
git add scripts/harness/run_mvp_readiness.sh
git commit -m "fix: normalize mvp readiness harness logging"
```

### Task 2: 增加 Doubao provider smoke 日志包装入口

**需求覆盖：** `HN-006`、部分 `HN-007`

**Files:**
- Create: `scripts/harness/run_doubao_smoke.sh`
- Modify: `Makefile`

- [ ] **Step 1: 新建 Doubao smoke wrapper**

Create `scripts/harness/run_doubao_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"
LOG_DIR="$ROOT/dist/harness/HN-006"
LOG_FILE="$LOG_DIR/doubao-smoke.log"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
}

log "Doubao provider smoke started"
log "Required variables: ARK_API_KEY, DOUBAO_VISION_MODEL_OR_ENDPOINT, DOUBAO_TEXT_MODEL_OR_ENDPOINT"

set +e
cd "$ROOT"
services/api/.venv/bin/python scripts/harness/smoke_doubao.py 2>&1 | tee -a "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

case "$status" in
  0)
    log "PASS: Doubao provider smoke"
    ;;
  2)
    log "BLOCKED: Doubao provider smoke missing required configuration"
    ;;
  *)
    log "FAIL: Doubao provider smoke exited with status $status"
    ;;
esac

exit "$status"
```

- [ ] **Step 2: 让 wrapper 可执行**

Run:

```bash
chmod +x scripts/harness/run_doubao_smoke.sh
```

Expected: 命令无输出，退出码为 `0`。

- [ ] **Step 3: 给 Makefile 增加 target**

在 `Makefile` 的 `.PHONY` 行末尾增加：

```makefile
harness-doubao-smoke
```

在文件末尾增加：

```makefile
harness-doubao-smoke:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/run_doubao_smoke.sh
```

- [ ] **Step 4: 验证缺失配置时不泄露 secrets**

Run:

```bash
make harness-doubao-smoke
```

Expected when Doubao env is not configured: 输出包含 `BLOCKED: Doubao provider smoke missing required configuration`，退出码为 `2`，`dist/harness/HN-006/doubao-smoke.log` 中只出现变量名，不出现任何 API key 值。

Expected when Doubao env is configured: 输出包含 `PASS: Doubao provider smoke`，退出码为 `0`，日志包含 `text_ok` 和 `vision_ok`。

- [ ] **Step 5: 提交本任务**

```bash
git add Makefile scripts/harness/run_doubao_smoke.sh
git commit -m "chore: add doubao smoke harness wrapper"
```

### Task 3: 增加 iOS simulator clean-state helper

**需求覆盖：** `HN-004`

**Files:**
- Create: `scripts/harness/reset_ios_simulator_app.sh`
- Modify: `Makefile`

- [ ] **Step 1: 新建 clean-state helper**

Create `scripts/harness/reset_ios_simulator_app.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

BUNDLE_ID="${IOS_BUNDLE_ID:-com.anbulang.learningenglish}"
DEVICE="${IOS_SIMULATOR_DEVICE:-booted}"

if ! command -v xcrun >/dev/null 2>&1; then
  echo "FAIL: xcrun is not available"
  exit 1
fi

if ! xcrun simctl list devices booted | rg -q "\(Booted\)"; then
  echo "FAIL: no booted iOS simulator found"
  echo "Start a simulator first, then run: make harness-reset-ios-sim"
  exit 1
fi

echo "Resetting app state for $BUNDLE_ID on simulator $DEVICE"
if xcrun simctl get_app_container "$DEVICE" "$BUNDLE_ID" data >/dev/null 2>&1; then
  xcrun simctl uninstall "$DEVICE" "$BUNDLE_ID"
  echo "PASS: uninstalled $BUNDLE_ID from $DEVICE"
else
  echo "PASS: $BUNDLE_ID is not installed on $DEVICE"
fi
```

- [ ] **Step 2: 让 helper 可执行**

Run:

```bash
chmod +x scripts/harness/reset_ios_simulator_app.sh
```

Expected: 命令无输出，退出码为 `0`。

- [ ] **Step 3: 给 Makefile 增加 target**

在 `Makefile` 的 `.PHONY` 行末尾增加：

```makefile
harness-reset-ios-sim
```

在文件末尾增加：

```makefile
harness-reset-ios-sim:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/reset_ios_simulator_app.sh
```

- [ ] **Step 4: 验证无 booted simulator 时的失败信息**

Run when no iOS simulator is booted:

```bash
make harness-reset-ios-sim
```

Expected: 输出包含 `FAIL: no booted iOS simulator found`，退出码为 `1`。

Run when an iOS simulator is booted:

```bash
make harness-reset-ios-sim
```

Expected: 输出 `PASS: uninstalled com.anbulang.learningenglish from booted` 或 `PASS: com.anbulang.learningenglish is not installed on booted`。

- [ ] **Step 5: 提交本任务**

```bash
git add Makefile scripts/harness/reset_ios_simulator_app.sh
git commit -m "chore: add ios simulator reset harness"
```

### Task 4: 增加 iOS simulator 截图采集 helper

**需求覆盖：** `HN-003`、部分 `HN-007`

**Files:**
- Create: `scripts/harness/capture_ios_simulator_screen.sh`
- Modify: `Makefile`

- [ ] **Step 1: 新建截图 helper**

Create `scripts/harness/capture_ios_simulator_screen.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"
SCREEN_NAME="${1:-${SCREEN:-}}"
DEVICE="${IOS_SIMULATOR_DEVICE:-booted}"
HN_DIR="$ROOT/dist/harness/HN-003/screens"
LEGACY_DIR="$ROOT/dist/harness/screens"

if [[ -z "$SCREEN_NAME" ]]; then
  echo "FAIL: screen name is required"
  echo "Usage: make harness-capture-ios-screen SCREEN=login-screen"
  exit 1
fi

if [[ "$SCREEN_NAME" != *-screen ]]; then
  echo "FAIL: screen name must end with -screen"
  echo "Example: phone-binding-screen"
  exit 1
fi

if ! command -v xcrun >/dev/null 2>&1; then
  echo "FAIL: xcrun is not available"
  exit 1
fi

if ! xcrun simctl list devices booted | rg -q "\(Booted\)"; then
  echo "FAIL: no booted iOS simulator found"
  exit 1
fi

mkdir -p "$HN_DIR" "$LEGACY_DIR"
TARGET="$HN_DIR/$SCREEN_NAME.png"
LEGACY_TARGET="$LEGACY_DIR/$SCREEN_NAME.png"

xcrun simctl io "$DEVICE" screenshot "$TARGET"
cp "$TARGET" "$LEGACY_TARGET"

echo "PASS: captured $TARGET"
echo "PASS: copied $LEGACY_TARGET"
```

- [ ] **Step 2: 让 helper 可执行**

Run:

```bash
chmod +x scripts/harness/capture_ios_simulator_screen.sh
```

Expected: 命令无输出，退出码为 `0`。

- [ ] **Step 3: 给 Makefile 增加 target**

在 `Makefile` 的 `.PHONY` 行末尾增加：

```makefile
harness-capture-ios-screen
```

在文件末尾增加：

```makefile
harness-capture-ios-screen:
	bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/capture_ios_simulator_screen.sh "$(SCREEN)"
```

- [ ] **Step 4: 验证缺少 SCREEN 时的失败信息**

Run:

```bash
make harness-capture-ios-screen
```

Expected: 输出包含 `FAIL: screen name is required`，退出码为 `1`。

- [ ] **Step 5: 手工采集主链截图**

先启动 API、worker 和 iOS simulator，确保 App 指向同一个后端环境。每进入一个页面后执行对应命令：

```bash
make harness-capture-ios-screen SCREEN=login-screen
make harness-capture-ios-screen SCREEN=phone-binding-screen
make harness-capture-ios-screen SCREEN=home-screen
make harness-capture-ios-screen SCREEN=upload-screen
make harness-capture-ios-screen SCREEN=ai-review-screen
make harness-capture-ios-screen SCREEN=lesson-detail-screen
make harness-capture-ios-screen SCREEN=report-screen
```

Expected: 每个命令都输出 `PASS: captured ...` 和 `PASS: copied ...`，并生成 `dist/harness/HN-003/screens/*.png` 与 `dist/harness/screens/*.png`。

- [ ] **Step 6: 提交本任务**

```bash
git add Makefile scripts/harness/capture_ios_simulator_screen.sh
git commit -m "chore: add ios screenshot evidence harness"
```

### Task 5: 更新 MVP readiness checklist

**需求覆盖：** `HN-001` 到 `HN-007`

**Files:**
- Modify: `docs/harness/mvp-readiness-checklist.md`

- [ ] **Step 1: 更新验收清单中的 Android fallback 状态描述**

将 `### C. iOS 交付链` 下的：

```markdown
- [ ] Android debug APK fallback 成功
```

替换为：

```markdown
- [ ] Android debug APK fallback 成功，或明确记录为本机 Android SDK 环境阻塞
```

- [ ] **Step 2: 更新命令结果列表**

将命令结果中的：

```markdown
- [ ] `make mobile-apk`
```

替换为：

```markdown
- [ ] `make mobile-apk`，成功时产物为 `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`；失败时必须记录是否为 Android SDK 环境阻塞
- [ ] `make harness-doubao-smoke`，真实 provider 配置存在时应通过；配置缺失时记录为 provider-readiness blocked
```

- [ ] **Step 3: 更新关键截图清单**

将关键截图区改为：

```markdown
### 关键截图
- [x] 登录页截图：`dist/harness/screens/login-screen.png`
- [ ] 绑定手机号截图：`dist/harness/screens/phone-binding-screen.png`
- [x] 首页截图：`dist/harness/screens/home-screen.png`
- [x] 上传讲义截图：`dist/harness/screens/upload-screen.png`
- [ ] AI 校对截图：`dist/harness/screens/ai-review-screen.png`
- [ ] 课程详情截图：`dist/harness/screens/lesson-detail-screen.png`
- [x] 报告页截图：`dist/harness/screens/report-screen.png`

截图采集命令：
```bash
make harness-capture-ios-screen SCREEN=login-screen
make harness-capture-ios-screen SCREEN=phone-binding-screen
make harness-capture-ios-screen SCREEN=home-screen
make harness-capture-ios-screen SCREEN=upload-screen
make harness-capture-ios-screen SCREEN=ai-review-screen
make harness-capture-ios-screen SCREEN=lesson-detail-screen
make harness-capture-ios-screen SCREEN=report-screen
```
```

- [ ] **Step 4: 新增 clean-state 流程**

在 `未完成截图说明` 后新增：

```markdown
### Clean-state UI 验证流程
1. 如需重置后端，执行 `HARNESS_RESET=1 make harness-mvp-readiness` 或单独执行 `make infra-reset && make infra-up && make api-migrate`。
2. 如需清理 iOS simulator App 状态，先启动目标 simulator，再执行 `make harness-reset-ios-sim`。
3. 重新安装或运行 App，并确保 `API_BASE_URL` 指向当前后端。
4. 从登录页重新走主链，逐页执行 `make harness-capture-ios-screen SCREEN=<name>`。
5. 截图同时保存到 `dist/harness/HN-003/screens/` 和 `dist/harness/screens/`。
```

- [ ] **Step 5: 新增证据目录约定**

在 `验收日志` 后新增：

```markdown
### Harness evidence 目录约定
- 最新兼容日志：`dist/harness/mvp-readiness.log`
- HN-001 readiness 日志：`dist/harness/HN-001/mvp-readiness.log`
- HN-003 UI 截图证据：`dist/harness/HN-003/screens/`
- HN-006 Doubao smoke 日志：`dist/harness/HN-006/doubao-smoke.log`
- 历史兼容截图目录：`dist/harness/screens/`
```

- [ ] **Step 6: 提交本任务**

```bash
git add docs/harness/mvp-readiness-checklist.md
git commit -m "docs: update mvp readiness harness evidence checklist"
```

### Task 6: 更新 README 的 harness 操作说明

**需求覆盖：** `HN-002`、`HN-004`、`HN-005`、`HN-006`、`HN-007`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 在 `## Short MVP Delivery Flow` 后新增中文 harness 说明**

在该章节的步骤列表之后新增：

```markdown
## Harness Engineering 验证入口

后续需求默认使用中文文档和 Harness Engineering 验收方式。每条需求都要说明自动化命令、人工证据和证据目录。

常用命令：
```bash
HARNESS_RESET=1 make harness-mvp-readiness
make harness-main-chain-smoke
make harness-doubao-smoke
make harness-reset-ios-sim
make harness-capture-ios-screen SCREEN=login-screen
```

证据目录：
- 最新 readiness 日志：`dist/harness/mvp-readiness.log`
- 需求分目录：`dist/harness/HN-*/`
- UI 截图兼容目录：`dist/harness/screens/`

Clean-state UI 验证建议顺序：
1. 重置后端或确认后端数据仍可用。
2. 启动 iOS simulator。
3. 执行 `make harness-reset-ios-sim` 清理 App 本地 session。
4. 用当前 API URL 运行 App。
5. 逐页执行 `make harness-capture-ios-screen SCREEN=<name>` 保存证据。
```

- [ ] **Step 2: 更新 Android APK 说明**

将：

```markdown
Build a local Android test APK:
```bash
make mobile-apk
```
```

扩展为：

```markdown
Build a local Android test APK:
```bash
make mobile-apk
```

成功时 APK 位于 `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`。如果命令返回 `No Android SDK found`，这是本机 Android SDK 环境阻塞，不代表 Flutter 代码或 MVP 主链失败。
```

- [ ] **Step 3: 更新 Doubao smoke 说明**

将 Doubao smoke 命令：

```bash
services/api/.venv/bin/python scripts/harness/smoke_doubao.py
```

替换为：

```bash
make harness-doubao-smoke
```

并在命令后追加：

```markdown
该命令会把 provider smoke 证据写入 `dist/harness/HN-006/doubao-smoke.log`。缺少配置时会记录 blocked 状态；配置完整且 provider 可用时应出现 `text_ok`、`vision_ok` 和 `PASS: Doubao provider smoke`。
```

- [ ] **Step 4: 提交本任务**

```bash
git add README.md
git commit -m "docs: document harness engineering verification flow"
```

### Task 7: 运行轻量验证

**需求覆盖：** 全部第一批需求的计划级验证

**Files:**
- No source edits expected

- [ ] **Step 1: shell 语法检查**

Run:

```bash
bash -n scripts/harness/run_mvp_readiness.sh
bash -n scripts/harness/run_doubao_smoke.sh
bash -n scripts/harness/reset_ios_simulator_app.sh
bash -n scripts/harness/capture_ios_simulator_screen.sh
```

Expected: 所有命令无输出，退出码为 `0`。

- [ ] **Step 2: Makefile target 可发现性检查**

Run:

```bash
make -n harness-doubao-smoke
make -n harness-reset-ios-sim
make -n harness-capture-ios-screen SCREEN=login-screen
```

Expected: 每个命令输出对应 `bash /Users/chaucermini/Code/LearningEnglish/scripts/harness/...` 调用，不实际执行脚本。

- [ ] **Step 3: 缺少参数的截图 helper 检查**

Run:

```bash
make harness-capture-ios-screen
```

Expected: 输出包含 `FAIL: screen name is required`，退出码为 `1`。

- [ ] **Step 4: 文档禁用词检查**

Run:

```bash
PATTERN="$(printf '%s|%s|%s|%s|%s %s|%s %s' T""BD TO""DO 待""补 占""位 fi""ll i""n imple""ment la""ter)"
rg -n "$PATTERN" README.md docs/harness/mvp-readiness-checklist.md docs/superpowers/plans/2026-05-03-harness-engineering-mvp-readiness.md
```

Expected: 无匹配，`rg` 退出码为 `1`。

- [ ] **Step 5: 可选完整 readiness 验证**

Run when Docker、Flutter、uv、Xcode signing 环境可用：

```bash
HARNESS_RESET=1 make harness-mvp-readiness
```

Expected:
- mandatory 步骤通过：infra、api install、worker install、migration、api tests、worker tests、mobile bootstrap、mobile tests、mobile analyze、main-chain smoke。
- iOS Profile/Internal IPA 成功时，日志出现 `PASS optional: iOS Profile/Internal IPA`。
- iOS 失败时，日志出现 `WARN optional: iOS Profile/Internal IPA export failed...`，随后尝试 Android fallback。
- `dist/harness/HN-001/mvp-readiness.log` 和 `dist/harness/mvp-readiness.log` 都存在。

- [ ] **Step 6: 提交验证记录文档更新**

如果 Step 5 实际执行并产生新结果，更新 `docs/harness/mvp-readiness-checklist.md` 的“本次验收记录”。然后提交：

```bash
git add docs/harness/mvp-readiness-checklist.md
git commit -m "docs: record latest mvp readiness evidence"
```

如果 Step 5 因本机环境限制没有执行，不提交空变更，在最终回复中明确说明未运行完整 readiness。

## 自检清单

- `HN-001` 对应 Task 1 和 Task 5。
- `HN-002` 对应 Task 1、Task 5 和 Task 6。
- `HN-003` 对应 Task 4 和 Task 5。
- `HN-004` 对应 Task 3、Task 5 和 Task 6。
- `HN-005` 对应 Task 1、Task 5 和 Task 6。
- `HN-006` 对应 Task 2、Task 5 和 Task 6。
- `HN-007` 对应 Task 1、Task 2、Task 4 和 Task 5。
- 计划中没有要求把大型二进制产物提交进 git。
- 计划保留现有 `dist/harness/mvp-readiness.log` 和 `dist/harness/screens` 兼容路径。
- 后续执行本计划时，文档内容继续使用中文；命令、路径和代码标识符保持原样。
