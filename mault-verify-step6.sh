#!/usr/bin/env bash
# Step 6/9 Verification: Pre-commit Framework
set -euo pipefail
PASS=0; FAIL=0; TOTAL=4

check() {
  local num="$1" name="$2" result="$3"
  if [ "$result" = "PASS" ]; then
    echo "  CHECK $num: PASS — $name"; PASS=$((PASS + 1))
  else
    echo "  CHECK $num: FAIL — $name"; FAIL=$((FAIL + 1))
  fi
}

echo "========================================"
echo " Step 6/9: Pre-commit Framework"
echo "========================================"

check 1 ".pre-commit-config.yaml exists" "$([ -f .pre-commit-config.yaml ] && echo PASS || echo FAIL)"
check 2 "ruff hook configured" "$(grep -q 'ruff' .pre-commit-config.yaml 2>/dev/null && echo PASS || echo FAIL)"
check 3 "mypy hook configured" "$(grep -q 'mypy' .pre-commit-config.yaml 2>/dev/null && echo PASS || echo FAIL)"
check 4 "security gate configured" "$(grep -q 'pip-audit' .pre-commit-config.yaml 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP6-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step6.proof
  echo " ✅ Step 6 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
