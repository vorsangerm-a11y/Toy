#!/usr/bin/env bash
# Step 1/9 Verification: Git Repository Setup
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
echo " Step 1/9: Git Repository Setup"
echo "========================================"

check 1 ".git initialized" "$([ -d .git ] && echo PASS || echo FAIL)"
check 2 ".gitignore exists" "$([ -f .gitignore ] && echo PASS || echo FAIL)"
check 3 ".gitignore has .env rule" "$(grep -q '^\.env$' .gitignore 2>/dev/null && echo PASS || echo FAIL)"
check 4 "On main branch" "$(git rev-parse --abbrev-ref HEAD 2>/dev/null | grep -q 'main' && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP1-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step1.proof
  echo " ✅ Step 1 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
