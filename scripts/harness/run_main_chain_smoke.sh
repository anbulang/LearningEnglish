#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/chaucermini/Code/LearningEnglish"

printf '\n[main-chain-smoke] API login/upload/review smoke\n'
cd "$ROOT/services/api"
.venv/bin/pytest tests/test_main_chain_smoke.py

printf '\n[main-chain-smoke] Mobile repository and UI navigation smoke\n'
cd "$ROOT/apps/mobile"
flutter test \
  test/features/materials/data/material_upload_to_review_flow_test.dart \
  test/features/materials/presentation/scan_review_navigation_test.dart
