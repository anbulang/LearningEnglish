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

if [[ "$SCREEN_NAME" == */* ]] || [[ "$SCREEN_NAME" == *\\* ]] || [[ "$SCREEN_NAME" == *..* ]] ||
  [[ ! "$SCREEN_NAME" =~ ^[A-Za-z0-9._-]+-screen$ ]]; then
  echo "FAIL: screen name must be a safe basename ending with -screen"
  echo "Example: phone-binding-screen"
  exit 1
fi

if ! command -v xcrun >/dev/null 2>&1; then
  echo "FAIL: xcrun is not available"
  exit 1
fi

if ! xcrun simctl list devices booted | awk '
  /^-- / {
    in_ios = ($0 ~ /^-- iOS /)
    next
  }
  in_ios && /\(Booted\)/ {
    found = 1
    exit
  }
  END {
    exit found ? 0 : 1
  }
'; then
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
