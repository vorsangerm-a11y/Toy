#!/usr/bin/env bash
# Step 2/9 Verification: Environment Configuration
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
echo " Step 2/9: Environment Configuration"
echo "========================================"

check 1 ".env.example exists" "$([ -f .env.example ] && echo PASS || echo FAIL)"
check 2 ".env.example has APP_ENV" "$(grep -q 'APP_ENV' .env.example 2>/dev/null && echo PASS || echo FAIL)"
check 3 ".env NOT committed (.gitignore has it)" "$(grep -q '^\.env$' .gitignore 2>/dev/null && echo PASS || echo FAIL)"
check 4 ".env file not tracked by git" "$(! git ls-files --error-unmatch .env 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP2-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step2.proof
  echo " ✅ Step 2 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
