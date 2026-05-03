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

sync_legacy_log_on_exit() {
  local status=$?
  if [[ -f "$LOG_FILE" ]]; then
    sync_legacy_log >/dev/null 2>&1 || true
  fi
  return "$status"
}

trap sync_legacy_log_on_exit EXIT

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
    sync_legacy_log >/dev/null 2>&1 || true
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
