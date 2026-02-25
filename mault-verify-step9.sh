#!/usr/bin/env bash
# Step 9/9 Verification: AI Coder Rules
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
echo " Step 9/9: AI Coder Rules"
echo "========================================"

check 1 ".cursorrules exists" "$([ -f .cursorrules ] && echo PASS || echo FAIL)"
check 2 ".github/copilot-instructions.md exists" "$([ -f .github/copilot-instructions.md ] && echo PASS || echo FAIL)"
check 3 ".windsurfrules exists" "$([ -f .windsurfrules ] && echo PASS || echo FAIL)"
check 4 ".cursorrules mentions Mault" "$(grep -q 'Mault' .cursorrules 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP9-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step9.proof
  echo " ✅ Step 9 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
