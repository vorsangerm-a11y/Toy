#!/usr/bin/env bash
# Step 8/9 Verification: Governance Testing
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
echo " Step 8/9: Governance Testing"
echo "========================================"

check 1 "scripts/governance/ exists" "$([ -d scripts/governance ] && echo PASS || echo FAIL)"
check 2 "check_mock_tax.py exists" "$([ -f scripts/governance/check_mock_tax.py ] && echo PASS || echo FAIL)"
check 3 "check_type_safety.py exists" "$([ -f scripts/governance/check_type_safety.py ] && echo PASS || echo FAIL)"
check 4 "check_coverage_ratchet.py exists" "$([ -f scripts/governance/check_coverage_ratchet.py ] && echo PASS || echo FAIL)"
check 5 ".memory-layer/baselines/ exists with JSON files" "$([ -f .memory-layer/baselines/type-safety.json ] && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP8-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step8.proof
  echo " ✅ Step 8 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
