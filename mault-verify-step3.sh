#!/usr/bin/env bash
# Step 3/9 Verification: Containerization
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
echo " Step 3/9: Containerization"
echo "========================================"

check 1 "Dockerfile exists" "$([ -f Dockerfile ] && echo PASS || echo FAIL)"
check 2 "docker-compose.yml exists" "$([ -f docker-compose.yml ] && echo PASS || echo FAIL)"
check 3 ".dockerignore exists" "$([ -f .dockerignore ] && echo PASS || echo FAIL)"
check 4 "Dockerfile uses multi-stage build" "$(grep -q 'AS builder' Dockerfile 2>/dev/null && echo PASS || echo FAIL)"
check 5 ".dockerignore excludes .env" "$(grep -q '^\.env$' .dockerignore 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP3-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step3.proof
  echo " ✅ Step 3 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
