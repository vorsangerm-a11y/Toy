#!/usr/bin/env bash
# =============================================================================
# MAULT STEP 8 VERIFICATION SCRIPT — Governance Testing
# =============================================================================
# 17-CHECK verification for Step 8 (Governance Testing Setup)
# Language-aware: checks for TS/JS (.js/.mjs) OR Python (.py) script variants.
#
# Usage:
#   chmod +x mault-verify-step8.sh
#   ./mault-verify-step8.sh
#
# Exit codes:
#   0 = All 17 checks PASS
#   1 = One or more checks FAIL
# =============================================================================

set -euo pipefail

PASS=0
FAIL=0
TOTAL=17
RESULTS=()

check() {
  local num="$1"
  local name="$2"
  local result="$3"

  if [ "$result" = "PASS" ]; then
    PASS=$((PASS + 1))
    RESULTS+=("CHECK $num: PASS — $name")
    echo "  ✓ CHECK $num: $name"
  else
    FAIL=$((FAIL + 1))
    RESULTS+=("CHECK $num: FAIL — $name")
    echo "  ✗ CHECK $num: $name"
  fi
}

# Helper: check if TS/JS OR Python variant exists
has_script() {
  local js_name="$1"
  local py_name="$2"
  [ -f "scripts/governance/$js_name" ] || [ -f "scripts/governance/$py_name" ]
}

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  MAULT STEP 8 VERIFICATION — Governance Testing"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Detect stack
STACK="unknown"
if [ -f "package.json" ] && { [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; }; then
  STACK="fullstack"
elif [ -f "package.json" ]; then
  STACK="node"
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
  STACK="python"
fi
echo "  Detected stack: $STACK"
echo ""

# ---------------------------------------------------------------------------
# CHECK 1: Step 7 prerequisite
# ---------------------------------------------------------------------------
if [ -f ".mault/verify-step7.proof" ]; then
  check 1 "Step 7 prerequisite (.mault/verify-step7.proof)" "PASS"
else
  check 1 "Step 7 prerequisite (.mault/verify-step7.proof)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 2: Directory structure
# ---------------------------------------------------------------------------
DIR_OK="PASS"
[ ! -d "scripts/governance" ] && DIR_OK="FAIL"
[ ! -d ".memory-layer/baselines" ] && DIR_OK="FAIL"
check 2 "Directory structure (scripts/governance, .memory-layer/baselines)" "$DIR_OK"

# ---------------------------------------------------------------------------
# CHECK 3: Iron Dome — type safety ratchet script exists
# ---------------------------------------------------------------------------
if has_script "check-any-usage.js" "check_type_holes.py"; then
  check 3 "Iron Dome: type safety ratchet (check-any-usage.js | check_type_holes.py)" "PASS"
else
  check 3 "Iron Dome: type safety ratchet (check-any-usage.js | check_type_holes.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 4: Iron Dome — silent catch detection exists
# ---------------------------------------------------------------------------
if has_script "check-silent-catches.js" "check_silent_catches.py"; then
  check 4 "Iron Dome: silent catch detection (check-silent-catches.js | check_silent_catches.py)" "PASS"
else
  check 4 "Iron Dome: silent catch detection (check-silent-catches.js | check_silent_catches.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 5: Escape Hatch — suppression gate exists
# ---------------------------------------------------------------------------
if has_script "check-eslint-disable.js" "check_noqa.py"; then
  check 5 "Escape Hatch: suppression gate (check-eslint-disable.js | check_noqa.py)" "PASS"
else
  check 5 "Escape Hatch: suppression gate (check-eslint-disable.js | check_noqa.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 6: Test Quality — mock-tax + adversarial/conformance exist
# ---------------------------------------------------------------------------
TQ_OK="PASS"
if ! has_script "check-mock-tax.js" "check_mock_tax.py"; then
  TQ_OK="FAIL"
fi
if ! has_script "check-adversarial-mocks.js" "check_mock_conformance.py"; then
  TQ_OK="FAIL"
fi
check 6 "Test Quality: mock tax + mock quality gate" "$TQ_OK"

# ---------------------------------------------------------------------------
# CHECK 7: Buddy System — integration + behavioral pairing exist
# ---------------------------------------------------------------------------
BS_OK="PASS"
if ! has_script "verify-integration-pairing.js" "verify_integration_pairing.py"; then
  BS_OK="FAIL"
fi
if ! has_script "verify-behavioral-pairing.js" "verify_behavioral_pairing.py"; then
  BS_OK="FAIL"
fi
check 7 "Buddy System: integration pairing + behavioral pairing" "$BS_OK"

# ---------------------------------------------------------------------------
# CHECK 8: Supply Chain — hallucinations + security-critical exist
# ---------------------------------------------------------------------------
SC_OK="PASS"
if ! has_script "check-hallucinations.js" "check_hallucinations_pypi.py"; then
  SC_OK="FAIL"
fi
if ! has_script "check-security-critical.js" "check_security_critical.py"; then
  SC_OK="FAIL"
fi
check 8 "Supply Chain: hallucination detector + security-critical gate" "$SC_OK"

# ---------------------------------------------------------------------------
# CHECK 9: Code Quality — circular-deps + duplicate-code + schema boundaries
# ---------------------------------------------------------------------------
CQ_OK="PASS"
if ! has_script "check-circular-deps.js" "check_circular_deps.py"; then
  CQ_OK="FAIL"
fi
if ! has_script "check-duplicate-code.js" "duplication_check.py"; then
  CQ_OK="FAIL"
fi
if ! has_script "check-zod-boundaries.js" "check_pydantic_boundaries.py"; then
  CQ_OK="FAIL"
fi
check 9 "Code Quality: circular deps + duplicate code + schema boundaries" "$CQ_OK"

# ---------------------------------------------------------------------------
# CHECK 10: Mutation Testing — mutation score script exists
# ---------------------------------------------------------------------------
if has_script "check-mutation-score.js" "check_mutation_score.py"; then
  check 10 "Mutation Testing: mutation score gate" "PASS"
else
  check 10 "Mutation Testing: mutation score gate" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 11: Pre-commit wiring — governance hooks configured
# ---------------------------------------------------------------------------
WIRE_OK="FAIL"
if [ -f ".pre-commit-config.yaml" ]; then
  if grep -q "check-mock-tax\|check_mock_tax\|check-any-usage\|check_type_holes\|mock-tax\|type-safety\|governance" .pre-commit-config.yaml 2>/dev/null; then
    WIRE_OK="PASS"
  fi
elif [ -f ".pre-commit-config-ts.yaml" ]; then
  if grep -q "check-mock-tax\|check-any-usage\|mock-tax\|type-safety\|governance" .pre-commit-config-ts.yaml 2>/dev/null; then
    WIRE_OK="PASS"
  fi
elif [ -f "package.json" ]; then
  if grep -q "check-mock-tax\|check-any-usage\|governance" package.json 2>/dev/null; then
    WIRE_OK="PASS"
  fi
fi
check 11 "Pre-commit wiring: governance hooks configured" "$WIRE_OK"

# ---------------------------------------------------------------------------
# CHECK 12: Size & Complexity Gate — SRP enforcement script exists
# ---------------------------------------------------------------------------
if has_script "guardrails-check.js" "guardrails_check.py"; then
  check 12 "Size & Complexity: SRP enforcement (guardrails-check.js | guardrails_check.py)" "PASS"
else
  check 12 "Size & Complexity: SRP enforcement (guardrails-check.js | guardrails_check.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 13: Code Health Gate — orphan detection script exists
# ---------------------------------------------------------------------------
if has_script "code-health-check.js" "code_health_check.py"; then
  check 13 "Code Health: orphan detection (code-health-check.js | code_health_check.py)" "PASS"
else
  check 13 "Code Health: orphan detection (code-health-check.js | code_health_check.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 14: Coverage Fortress — per-file coverage ratchet exists
# ---------------------------------------------------------------------------
CF_OK="FAIL"
if [ -f "scripts/governance/check-per-file-baseline.mjs" ] || [ -f "scripts/governance/check_per_file_baseline.py" ]; then
  CF_OK="PASS"
fi
check 14 "Coverage Fortress: per-file ratchet (check-per-file-baseline.mjs | check_per_file_baseline.py)" "$CF_OK"

# ---------------------------------------------------------------------------
# CHECK 15: Skipped Tests Gate — skip enforcer script exists
# ---------------------------------------------------------------------------
if has_script "check-skipped-tests.js" "check_skipped_tests.py"; then
  check 15 "Skipped Tests: skip enforcer (check-skipped-tests.js | check_skipped_tests.py)" "PASS"
else
  check 15 "Skipped Tests: skip enforcer (check-skipped-tests.js | check_skipped_tests.py)" "FAIL"
fi

# ---------------------------------------------------------------------------
# CHECK 16: CI Security — gitleaks or secret detection configured
# ---------------------------------------------------------------------------
SEC_OK="FAIL"
if ls .github/workflows/*.yml 2>/dev/null | xargs grep -l "gitleaks" 2>/dev/null | head -1 > /dev/null 2>&1; then
  SEC_OK="PASS"
elif ls .github/workflows/*.yaml 2>/dev/null | xargs grep -l "gitleaks" 2>/dev/null | head -1 > /dev/null 2>&1; then
  SEC_OK="PASS"
elif [ -f ".gitleaks.toml" ]; then
  SEC_OK="PASS"
elif [ -f ".gitlab-ci.yml" ] && grep -q "gitleaks\|secret" .gitlab-ci.yml 2>/dev/null; then
  SEC_OK="PASS"
fi
check 16 "CI Security: secret detection configured (gitleaks)" "$SEC_OK"

# ---------------------------------------------------------------------------
# CHECK 17: Handshake — governance-manifest.json + [mault-step8] commit
# ---------------------------------------------------------------------------
HS_OK="FAIL"
if [ -f ".mault/governance-manifest.json" ]; then
  if git log --oneline -20 2>/dev/null | grep -q "\[mault-step8\]"; then
    HS_OK="PASS"
  fi
fi
check 17 "Handshake: governance-manifest.json + [mault-step8] commit" "$HS_OK"

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
echo ""
echo "─────────────────────────────────────────────────────────────"
echo "  RESULTS: $PASS/$TOTAL PASS, $FAIL FAIL"
echo "─────────────────────────────────────────────────────────────"

if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo "  ALL 17 CHECKS PASS — Step 8 Governance Testing verified!"
  echo ""

  # Generate proof file
  mkdir -p .mault
  SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")
  EPOCH=$(date +%s)
  TOKEN="MAULT-STEP8-${SHA}-${EPOCH}-${PASS}/${TOTAL}"

  cat > .mault/verify-step8.proof << PROOF_EOF
{
  "step": 8,
  "name": "Governance Testing",
  "token": "${TOKEN}",
  "checks": ${PASS},
  "total": ${TOTAL},
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%Y-%m-%dT%H:%M:%SZ)",
  "results": [
$(for i in "${!RESULTS[@]}"; do
  if [ "$i" -lt $((${#RESULTS[@]} - 1)) ]; then
    echo "    \"${RESULTS[$i]}\","
  else
    echo "    \"${RESULTS[$i]}\""
  fi
done)
  ]
}
PROOF_EOF

  echo "  Proof file: .mault/verify-step8.proof"
  echo "  Token: ${TOKEN}"
  echo ""
  exit 0
else
  echo ""
  echo "  Step 8 verification INCOMPLETE — $FAIL check(s) need attention."
  echo ""
  exit 1
fi
