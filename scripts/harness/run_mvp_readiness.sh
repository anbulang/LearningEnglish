#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"
LOG_DIR="$ROOT/dist/harness"
LOG_FILE="$LOG_DIR/mvp-readiness.log"
RESET="${HARNESS_RESET:-0}"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
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
    return 1
  fi
}

log "MVP readiness harness started"
log "HARNESS_RESET=$RESET"

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

if make -C "$ROOT" mobile-ios-ipa 2>&1 | tee -a "$LOG_FILE"; then
  log "PASS: iOS Debug IPA"
else
  log "WARN: iOS Debug IPA export failed; inspect log for Xcode account/signing issues"
  if make -C "$ROOT" mobile-apk 2>&1 | tee -a "$LOG_FILE"; then
    log "PASS: Android debug APK fallback"
  else
    log "WARN: Android debug APK fallback failed; inspect log for Android SDK setup issues"
  fi
fi

log "MVP readiness harness finished"
