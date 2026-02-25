#!/usr/bin/env bash
# Step 4/9 Verification: CI/CD Pipeline
set -euo pipefail
PASS=0; FAIL=0; TOTAL=5

check() {
  local num="$1" name="$2" result="$3"
  if [ "$result" = "PASS" ]; then
    echo "  CHECK $num: PASS — $name"; PASS=$((PASS + 1))
  else
    echo "  CHECK $num: FAIL — $name"; FAIL=$((FAIL + 1))
  fi
}

echo "========================================"
echo " Step 4/9: CI/CD Pipeline"
echo "========================================"

check 1 ".github/workflows/ exists" "$([ -d .github/workflows ] && echo PASS || echo FAIL)"
check 2 "ci.yml exists" "$([ -f .github/workflows/ci.yml ] && echo PASS || echo FAIL)"
check 3 "CI runs on push to main" "$(grep -q 'branches: \[main' .github/workflows/ci.yml 2>/dev/null && echo PASS || echo FAIL)"
check 4 "CI has test job" "$(grep -q 'test:' .github/workflows/ci.yml 2>/dev/null && echo PASS || echo FAIL)"
check 5 "CI has security audit" "$(grep -q 'pip-audit' .github/workflows/ci.yml 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP4-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step4.proof
  echo " ✅ Step 4 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
