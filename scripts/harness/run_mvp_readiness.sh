#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"
LOG_DIR="$ROOT/dist/harness"
LOG_FILE="$LOG_DIR/mvp-readiness.log"

mkdir -p "$LOG_DIR"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
}

run_step() {
  local name="$1"
  shift
  log "START: $name"
  if "$@" 2>&1 | tee -a "$LOG_FILE"; then
    log "PASS: $name"
  else
    log "FAIL: $name"
    return 1
  fi
}

log "MVP readiness harness started"

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
run_step "Mobile analyze" make -C "$ROOT" mobile-analyze

if make -C "$ROOT" mobile-ios-ipa 2>&1 | tee -a "$LOG_FILE"; then
  log "PASS: iOS Debug IPA"
else
  log "WARN: iOS Debug IPA export failed; inspect log for Xcode account/signing issues"
fi

log "MVP readiness harness finished"
