#!/usr/bin/env bash
# Run all test suites
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0
SUITES_PASS=0
SUITES_FAIL=0

for test_file in "$SCRIPT_DIR"/test_*.sh; do
  name=$(basename "$test_file")
  echo ""
  echo "▸ Running $name..."
  if output=$(bash "$test_file" 2>&1); then
    SUITES_PASS=$((SUITES_PASS + 1))
  else
    SUITES_FAIL=$((SUITES_FAIL + 1))
  fi
  # Extract pass/fail counts from output (macOS-compatible)
  pass=$(echo "$output" | sed -n 's/.*Pass: \([0-9]*\).*/\1/p' | tail -1)
  fail=$(echo "$output" | sed -n 's/.*Fail: \([0-9]*\).*/\1/p' | tail -1)
  pass=${pass:-0}
  fail=${fail:-0}
  TOTAL_PASS=$((TOTAL_PASS + pass))
  TOTAL_FAIL=$((TOTAL_FAIL + fail))
  # Show summary line
  echo "$output" | tail -3
done

echo ""
echo "========================================"
echo "ALL SUITES: $((SUITES_PASS + SUITES_FAIL)) | Pass: $SUITES_PASS | Fail: $SUITES_FAIL"
echo "ALL TESTS:  $((TOTAL_PASS + TOTAL_FAIL)) | Pass: $TOTAL_PASS | Fail: $TOTAL_FAIL"
echo "========================================"

[ "$TOTAL_FAIL" -eq 0 ] && exit 0 || exit 1
