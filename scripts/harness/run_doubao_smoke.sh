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
