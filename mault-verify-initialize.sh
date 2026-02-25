#!/usr/bin/env bash
# =============================================================================
# Mault Core Initialize — Verification Script (10 CHECKs)
# =============================================================================
# Verifies that the Mault rulebook (mault.yaml) is correctly configured
# with all core detectors (UC01-UC12).
#
# Usage: ./mault-verify-initialize.sh
# Exit 0 = all checks pass, Exit 1 = one or more checks fail
# =============================================================================

set -euo pipefail

PASS=0
FAIL=0
TOTAL=10

check() {
  local num="$1" name="$2" result="$3"
  if [ "$result" = "PASS" ]; then
    echo "  CHECK $num: PASS — $name"
    PASS=$((PASS + 1))
  else
    echo "  CHECK $num: FAIL — $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=========================================="
echo " Mault Core Initialize — Verification"
echo "=========================================="
echo ""

# --- CHECK 1: mault.yaml exists ---
MAULT_YAML=""
if [ -f "docs/mault.yaml" ]; then
  MAULT_YAML="docs/mault.yaml"
elif [ -f "mault.yaml" ]; then
  MAULT_YAML="mault.yaml"
fi
check 1 "mault.yaml exists" "$([ -n "$MAULT_YAML" ] && echo PASS || echo FAIL)"

# --- CHECK 2: Valid YAML with version: 1 ---
if [ -n "$MAULT_YAML" ]; then
  VERSION_OK="FAIL"
  # Try python3 first, then python
  if command -v python3 &>/dev/null; then
    VERSION_OK=$(python3 -c "
import sys, yaml
try:
    d = yaml.safe_load(open('$MAULT_YAML'))
    print('PASS' if d and d.get('version') == 1 else 'FAIL')
except:
    print('FAIL')
" 2>/dev/null || echo "FAIL")
  elif command -v python &>/dev/null; then
    VERSION_OK=$(python -c "
import sys, yaml
try:
    d = yaml.safe_load(open('$MAULT_YAML'))
    print('PASS' if d and d.get('version') == 1 else 'FAIL')
except:
    print('FAIL')
" 2>/dev/null || echo "FAIL")
  fi
  check 2 "Valid YAML with version: 1" "$VERSION_OK"
else
  check 2 "Valid YAML with version: 1" "FAIL"
fi

# --- CHECK 3: Core detectors enabled (≥7 enabled: true counts) ---
if [ -n "$MAULT_YAML" ]; then
  ENABLED_COUNT=$(grep -c "enabled: true" "$MAULT_YAML" 2>/dev/null || echo "0")
  check 3 "Core detectors enabled (≥7, found $ENABLED_COUNT)" "$([ "$ENABLED_COUNT" -ge 7 ] && echo PASS || echo FAIL)"
else
  check 3 "Core detectors enabled (≥7)" "FAIL"
fi

# --- CHECK 4: deprecatedPatterns has entries ---
if [ -n "$MAULT_YAML" ]; then
  HAS_DEPRECATED=$(grep -c "deprecatedPatterns:" "$MAULT_YAML" 2>/dev/null || echo "0")
  DEP_ENTRIES=$(grep -c "^  - id:" "$MAULT_YAML" 2>/dev/null || echo "0")
  check 4 "deprecatedPatterns has entries (found $DEP_ENTRIES)" "$([ "$HAS_DEPRECATED" -ge 1 ] && [ "$DEP_ENTRIES" -ge 3 ] && echo PASS || echo FAIL)"
else
  check 4 "deprecatedPatterns has entries" "FAIL"
fi

# --- CHECK 5: Detectors.directoryReinforcement has rules ---
if [ -n "$MAULT_YAML" ]; then
  HAS_DIR_RULES=$(grep -c "directoryReinforcement:" "$MAULT_YAML" 2>/dev/null || echo "0")
  DIR_RULE_COUNT=$(grep -c "expectedDir:" "$MAULT_YAML" 2>/dev/null || echo "0")
  check 5 "directoryReinforcement has rules (found $DIR_RULE_COUNT)" "$([ "$HAS_DIR_RULES" -ge 1 ] && [ "$DIR_RULE_COUNT" -ge 3 ] && echo PASS || echo FAIL)"
else
  check 5 "directoryReinforcement has rules" "FAIL"
fi

# --- CHECK 6: Canary log exists with ≥5 core detections ---
if [ -f ".mault/canary-log.json" ]; then
  if command -v python3 &>/dev/null; then
    DETECTED_COUNT=$(python3 -c "
import json
try:
    d = json.load(open('.mault/canary-log.json'))
    count = sum(1 for det in d.get('detections', []) if det.get('detected'))
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")
  elif command -v python &>/dev/null; then
    DETECTED_COUNT=$(python -c "
import json
try:
    d = json.load(open('.mault/canary-log.json'))
    count = sum(1 for det in d.get('detections', []) if det.get('detected'))
    print(count)
except:
    print(0)
" 2>/dev/null || echo "0")
  else
    DETECTED_COUNT=0
  fi
  check 6 "Canary log ≥5 core detections (found $DETECTED_COUNT)" "$([ "$DETECTED_COUNT" -ge 5 ] && echo PASS || echo FAIL)"
else
  check 6 "Canary log exists with ≥5 core detections" "FAIL"
fi

# --- CHECK 7: Canary cleanup (mault-canary/ removed) ---
if [ -d "mault-canary" ]; then
  check 7 "Canary cleanup (mault-canary/ removed)" "FAIL"
else
  check 7 "Canary cleanup (mault-canary/ removed)" "PASS"
fi

# --- CHECK 8: namingConvention.fileNaming is set ---
if [ -n "$MAULT_YAML" ]; then
  HAS_FILE_NAMING=$(grep -c "fileNaming:" "$MAULT_YAML" 2>/dev/null || echo "0")
  check 8 "namingConvention.fileNaming is set" "$([ "$HAS_FILE_NAMING" -ge 1 ] && echo PASS || echo FAIL)"
else
  check 8 "namingConvention.fileNaming is set" "FAIL"
fi

# --- CHECK 9: Handshake commit [mault-initialize] ---
if git log --oneline -20 2>/dev/null | grep -q "\[mault-initialize\]"; then
  check 9 "Handshake commit [mault-initialize]" "PASS"
else
  check 9 "Handshake commit [mault-initialize]" "FAIL"
fi

# --- CHECK 10: Proof file generation ---
PROOF_FILE=".mault/verify-initialize.proof"
if [ "$PASS" -eq $((TOTAL - 1)) ] && [ "$FAIL" -eq 0 ]; then
  # All previous checks passed — CHECK 10 is self-fulfilling
  # Actually recalculate: at this point PASS should be 9
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
  TOKEN="MAULT-INIT-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')-${PASS}/${TOTAL}-${TIMESTAMP}"
  mkdir -p .mault
  echo "$TOKEN" > "$PROOF_FILE"
  check 10 "Proof file generated" "PASS"
elif [ -f "$PROOF_FILE" ]; then
  check 10 "Proof file exists (from previous run)" "PASS"
else
  check 10 "Proof file generated (need all 9 prior checks to pass)" "FAIL"
fi

# --- Summary ---
echo ""
echo "=========================================="
echo " Results: $PASS/$TOTAL PASS"
echo "=========================================="

if [ "$PASS" -eq "$TOTAL" ]; then
  echo ""
  echo " ✅ Core Initialize VERIFIED"
  echo " Proof: $(cat "$PROOF_FILE" 2>/dev/null || echo 'N/A')"
  echo ""
  exit 0
else
  echo ""
  echo " ❌ $FAIL check(s) failed. Fix and re-run."
  echo ""
  exit 1
fi
