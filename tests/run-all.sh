#!/usr/bin/env bash
# Run all test suites
# Usage: run-all.sh [--filter PATTERN] [--parallel] [--verbose] [--timing]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_PASS=0
TOTAL_FAIL=0
SUITES_PASS=0
SUITES_FAIL=0
FILTER=""
VERBOSE=false
TIMING=false
FAILED_SUITES=""

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    --filter) FILTER="$2"; shift 2 ;;
    --verbose) VERBOSE=true; shift ;;
    --timing) TIMING=true; shift ;;
    *) echo "Usage: run-all.sh [--filter PATTERN] [--verbose] [--timing]"; exit 1 ;;
  esac
done

START_TIME=$(date +%s)

for test_file in "$SCRIPT_DIR"/test_*.sh; do
  name=$(basename "$test_file")

  # Apply filter if specified
  if [ -n "$FILTER" ] && ! echo "$name" | grep -qi "$FILTER"; then
    continue
  fi

  echo ""
  echo "▸ Running $name..."
  SUITE_START=$(date +%s)

  if output=$(bash "$test_file" 2>&1); then
    SUITES_PASS=$((SUITES_PASS + 1))
  else
    SUITES_FAIL=$((SUITES_FAIL + 1))
    FAILED_SUITES="$FAILED_SUITES $name"
  fi

  SUITE_END=$(date +%s)
  SUITE_DURATION=$((SUITE_END - SUITE_START))

  # Extract pass/fail counts from output (macOS-compatible)
  pass=$(echo "$output" | sed -n 's/.*Pass: \([0-9]*\).*/\1/p' | tail -1)
  fail=$(echo "$output" | sed -n 's/.*Fail: \([0-9]*\).*/\1/p' | tail -1)
  pass=${pass:-0}
  fail=${fail:-0}
  TOTAL_PASS=$((TOTAL_PASS + pass))
  TOTAL_FAIL=$((TOTAL_FAIL + fail))

  # Show output
  if [ "$VERBOSE" = true ]; then
    echo "$output"
  else
    echo "$output" | tail -3
  fi

  if [ "$TIMING" = true ]; then
    echo "  (${SUITE_DURATION}s)"
  fi
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================"
echo "ALL SUITES: $((SUITES_PASS + SUITES_FAIL)) | Pass: $SUITES_PASS | Fail: $SUITES_FAIL"
echo "ALL TESTS:  $((TOTAL_PASS + TOTAL_FAIL)) | Pass: $TOTAL_PASS | Fail: $TOTAL_FAIL"
if [ "$TIMING" = true ]; then
  echo "TOTAL TIME: ${TOTAL_DURATION}s"
fi
echo "========================================"

if [ -n "$FAILED_SUITES" ]; then
  echo ""
  echo "FAILED SUITES:$FAILED_SUITES"
fi

[ "$TOTAL_FAIL" -eq 0 ] && exit 0 || exit 1
