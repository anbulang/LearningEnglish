#!/usr/bin/env bash
set -euo pipefail

BUNDLE_ID="${IOS_BUNDLE_ID:-com.anbulang.learningenglish}"
DEVICE="${IOS_SIMULATOR_DEVICE:-booted}"

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
  echo "Start a simulator first, then run: make harness-reset-ios-sim"
  exit 1
fi

echo "Resetting app state for $BUNDLE_ID on simulator $DEVICE"
container_error=""
if container_error="$(xcrun simctl get_app_container "$DEVICE" "$BUNDLE_ID" data 2>&1 >/dev/null)"; then
  xcrun simctl uninstall "$DEVICE" "$BUNDLE_ID"
  echo "PASS: uninstalled $BUNDLE_ID from $DEVICE"
else
  container_status=$?
  shopt -s nocasematch
  if [[ "$container_error" =~ no[[:space:]]+such[[:space:]]+app ]] ||
    [[ "$container_error" =~ no[[:space:]]+app.*bundle ]] ||
    [[ "$container_error" =~ app.*not[[:space:]]+installed ]] ||
    [[ "$container_error" =~ bundle.*not[[:space:]]+found ]] ||
    [[ "$container_error" =~ application.*not[[:space:]]+found ]]; then
    shopt -u nocasematch
    echo "PASS: $BUNDLE_ID is not installed on $DEVICE"
  else
    shopt -u nocasematch
    echo "FAIL: unable to inspect app container for $BUNDLE_ID on $DEVICE"
    if [[ -n "$container_error" ]]; then
      echo "$container_error"
    fi
    exit "$container_status"
  fi
fi
