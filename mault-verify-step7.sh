#!/usr/bin/env bash
# Step 7/9 Verification: Mault Enforcement
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
echo " Step 7/9: Mault Enforcement"
echo "========================================"

check 1 "docs/mault.yaml exists" "$([ -f docs/mault.yaml ] && echo PASS || echo FAIL)"
check 2 "version: 1 set" "$(grep -q 'version: 1' docs/mault.yaml 2>/dev/null && echo PASS || echo FAIL)"
ENABLED_COUNT=$(grep -c 'enabled: true' docs/mault.yaml 2>/dev/null || echo 0)
check 3 "≥7 detectors enabled (found $ENABLED_COUNT)" "$([ "$ENABLED_COUNT" -ge 7 ] && echo PASS || echo FAIL)"
check 4 "deprecatedPatterns configured" "$(grep -q 'deprecatedPatterns:' docs/mault.yaml 2>/dev/null && echo PASS || echo FAIL)"
check 5 "directoryReinforcement configured" "$(grep -q 'directoryReinforcement:' docs/mault.yaml 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP7-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step7.proof
  echo " ✅ Step 7 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
