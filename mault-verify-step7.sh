#!/usr/bin/env bash
# mault-verify-step7.sh — Ralph Loop verification for Step 7: Advanced Detection
# 12 CHECKs. Exit 0 only if ALL pass.
set -uo pipefail

PASS_COUNT=0
FAIL_COUNT=0
PENDING_COUNT=0
CHECK_RESULTS=()
TOTAL_CHECKS=12

PROOF_DIR=".mault"
PROOF_FILE="$PROOF_DIR/verify-step7.proof"

# --- Helper functions ---
record_result() { CHECK_RESULTS+=("CHECK $1: $2 - $3"); }
print_pass()    { echo "[PASS]    CHECK $1: $2"; PASS_COUNT=$((PASS_COUNT + 1)); record_result "$1" "PASS" "$2"; }
print_fail()    { echo "[FAIL]    CHECK $1: $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); record_result "$1" "FAIL" "$2"; }
print_pending() { echo "[PENDING] CHECK $1: $2"; PENDING_COUNT=$((PENDING_COUNT + 1)); record_result "$1" "PENDING" "$2"; }

# --- Prereqs ---

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) not installed. https://cli.github.com/"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not a git repository. Complete Step 1 first."
  exit 1
fi

# --- Staleness check ---
if [ -f "$PROOF_FILE" ]; then
  PROOF_SHA=$(grep '^GitSHA:' "$PROOF_FILE" | awk '{print $2}')
  CURRENT_SHA=$(git rev-parse --short HEAD 2>/dev/null)
  if [ "$PROOF_SHA" != "$CURRENT_SHA" ]; then
    echo "Stale proof detected (SHA mismatch: $PROOF_SHA vs $CURRENT_SHA). Deleting."
    rm -f "$PROOF_FILE"
  fi
fi

echo ""
echo "========================================"
echo "  MAULT STEP 7: Advanced Detection"
echo "========================================"
echo ""

# --- Proof File Functions ---

write_proof_file() {
  local sha epoch iso token
  sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  epoch=$(date +%s)
  iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
  token="MAULT-STEP7-${sha}-${epoch}-${TOTAL_CHECKS}/${TOTAL_CHECKS}"

  mkdir -p "$PROOF_DIR"
  if [ ! -f "$PROOF_DIR/.gitignore" ]; then
    printf '*\n!.gitignore\n' > "$PROOF_DIR/.gitignore"
  fi

  {
    echo "MAULT-STEP7-PROOF"
    echo "=================="
    echo "Timestamp: $epoch"
    echo "DateTime: $iso"
    echo "GitSHA: $sha"
    echo "Checks: ${TOTAL_CHECKS}/${TOTAL_CHECKS} PASS"
    for r in "${CHECK_RESULTS[@]}"; do
      echo "  $r"
    done
    echo "=================="
    echo "Token: $token"
  } > "$PROOF_FILE"

  echo ""
  echo "ALL CHECKS PASSED. Step 7 Advanced Detection is complete."
  echo "Proof written to: $PROOF_FILE"
  echo "Token: $token"
}

# Find rulebook
find_rulebook() {
  if [ -f "docs/mault.yaml" ]; then
    echo "docs/mault.yaml"
  elif [ -f "mault.yaml" ]; then
    echo "mault.yaml"
  else
    echo ""
  fi
}

# ============================================================
# CHECK 1: Core Initialize Prerequisite
# ============================================================
check_1() {
  if [ -f ".mault/verify-initialize.proof" ]; then
    local token
    token=$(grep 'MAULT-INIT-' .mault/verify-initialize.proof | head -1) || true
    if [ -n "$token" ]; then
      print_pass 1 "Core Initialize prerequisite verified"
    else
      print_pass 1 "Core Initialize proof file exists"
    fi
  elif [ -f ".mault/verify-step6.proof" ]; then
    # Backward compat: accept Step 6 proof if Core Initialize proof doesn't exist yet
    print_pass 1 "Step 6 prerequisite verified (legacy — Core Initialize proof recommended)"
  else
    print_fail 1 "Core Initialize proof not found (.mault/verify-initialize.proof). Complete Core Initialize first."
  fi
}

# ============================================================
# CHECK 2: Rulebook Exists with Core Config
# ============================================================
check_2() {
  local rulebook
  rulebook=$(find_rulebook)

  if [ -z "$rulebook" ]; then
    print_fail 2 "No mault.yaml found. Complete Core Initialize first."
    return
  fi

  # Verify core config is present (version + Detectors + deprecatedPatterns)
  local has_version=false has_detectors=false has_deprecated=false
  grep -q "^version:" "$rulebook" && has_version=true
  grep -q "^Detectors:" "$rulebook" && has_detectors=true
  grep -q "^deprecatedPatterns:" "$rulebook" && has_deprecated=true

  if $has_version && $has_detectors && $has_deprecated; then
    print_pass 2 "Rulebook found at $rulebook with core config (version + Detectors + deprecatedPatterns)"
  else
    local missing=""
    $has_version || missing+="version "
    $has_detectors || missing+="Detectors "
    $has_deprecated || missing+="deprecatedPatterns "
    print_fail 2 "Rulebook missing core sections: $missing. Complete Core Initialize first."
  fi
}

# ============================================================
# CHECK 3: UC13 — Application Flows Configured
# ============================================================
check_3() {
  local rulebook
  rulebook=$(find_rulebook)

  if [ -z "$rulebook" ]; then
    print_fail 3 "No rulebook found (CHECK 2 must pass first)"
    return
  fi

  local has_flows=false
  grep -q "^applicationFlows:" "$rulebook" && has_flows=true
  grep -q "^flows:" "$rulebook" && has_flows=true

  if $has_flows; then
    print_pass 3 "UC13: applicationFlows/flows section configured"
  else
    print_fail 3 "UC13: No applicationFlows or flows section in $rulebook. Add application flow mappings."
  fi
}

# ============================================================
# CHECK 4: UC14 — Monolith Detection Configured
# ============================================================
check_4() {
  local rulebook
  rulebook=$(find_rulebook)

  if [ -z "$rulebook" ]; then
    print_fail 4 "No rulebook found (CHECK 2 must pass first)"
    return
  fi

  if grep -q "^monolithDetection:" "$rulebook" && grep -q "enabled: true" "$rulebook"; then
    print_pass 4 "UC14: monolithDetection section configured and enabled"
  elif grep -q "^monolithDetection:" "$rulebook"; then
    print_fail 4 "UC14: monolithDetection section exists but may not be enabled. Ensure enabled: true."
  else
    print_fail 4 "UC14: No monolithDetection section in $rulebook. Add monolith detection thresholds."
  fi
}

# ============================================================
# CHECK 5: UC16+UC17 — Pro Detectors Enabled
# ============================================================
check_5() {
  local rulebook
  rulebook=$(find_rulebook)

  if [ -z "$rulebook" ]; then
    print_fail 5 "No rulebook found (CHECK 2 must pass first)"
    return
  fi

  local has_dep_health=false has_prod_readiness=false
  grep -q "dependencyHealth:" "$rulebook" && has_dep_health=true
  grep -q "productionReadiness:" "$rulebook" && has_prod_readiness=true

  if $has_dep_health && $has_prod_readiness; then
    print_pass 5 "UC16+UC17: dependencyHealth + productionReadiness configured"
  else
    local missing=""
    $has_dep_health || missing+="dependencyHealth(UC16) "
    $has_prod_readiness || missing+="productionReadiness(UC17) "
    print_fail 5 "Missing Pro detector sections: $missing"
  fi
}

# ============================================================
# CHECK 6: UC18 — Structural Governance Rules
# ============================================================
check_6() {
  local rulebook
  rulebook=$(find_rulebook)

  if [ -z "$rulebook" ]; then
    print_fail 6 "No rulebook found (CHECK 2 must pass first)"
    return
  fi

  if grep -q "^rules:" "$rulebook" && grep -q "assertions:" "$rulebook"; then
    local rule_count
    rule_count=$(grep -c "^  - id:" "$rulebook" 2>/dev/null || echo "0")
    if [ "$rule_count" -ge 1 ]; then
      print_pass 6 "UC18: $rule_count structural governance rule(s) with assertions"
    else
      print_fail 6 "UC18: rules section exists but no rules with id: found. Add at least 1 rule."
    fi
  else
    print_fail 6 "UC18: No rules section with assertions in $rulebook. Add structural governance rules."
  fi
}

# ============================================================
# CHECK 7: Advanced Canary Evidence
# ============================================================
check_7() {
  if [ -f ".mault/canary-log.json" ]; then
    # Must have scope: "advanced" AND detections for UC14 or UC18 specifically
    # Core Initialize leaves scope: "core" — that must NOT satisfy Step 7
    local scope="" has_uc14=false has_uc18=false detected=0

    if command -v python3 >/dev/null 2>&1; then
      scope=$(python3 -c "import json; d=json.load(open('.mault/canary-log.json')); print(d.get('scope',''))" 2>/dev/null || echo "")
      detected=$(python3 -c "import json; d=json.load(open('.mault/canary-log.json')); print(d.get('totalDetected',0))" 2>/dev/null || echo "0")
      python3 -c "import json; d=json.load(open('.mault/canary-log.json')); exit(0 if any(x.get('uc')=='UC14' for x in d.get('detections',[])) else 1)" 2>/dev/null && has_uc14=true
      python3 -c "import json; d=json.load(open('.mault/canary-log.json')); exit(0 if any(x.get('uc')=='UC18' for x in d.get('detections',[])) else 1)" 2>/dev/null && has_uc18=true
    elif command -v python >/dev/null 2>&1; then
      scope=$(python -c "import json; d=json.load(open('.mault/canary-log.json')); print(d.get('scope',''))" 2>/dev/null || echo "")
      detected=$(python -c "import json; d=json.load(open('.mault/canary-log.json')); print(d.get('totalDetected',0))" 2>/dev/null || echo "0")
      python -c "import json; d=json.load(open('.mault/canary-log.json')); exit(0 if any(x.get('uc')=='UC14' for x in d.get('detections',[])) else 1)" 2>/dev/null && has_uc14=true
      python -c "import json; d=json.load(open('.mault/canary-log.json')); exit(0 if any(x.get('uc')=='UC18' for x in d.get('detections',[])) else 1)" 2>/dev/null && has_uc18=true
    elif command -v node >/dev/null 2>&1; then
      scope=$(node -e "const d=JSON.parse(require('fs').readFileSync('.mault/canary-log.json','utf8')); console.log(d.scope||'')" 2>/dev/null || echo "")
      detected=$(node -e "const d=JSON.parse(require('fs').readFileSync('.mault/canary-log.json','utf8')); console.log(d.totalDetected||0)" 2>/dev/null || echo "0")
      node -e "const d=JSON.parse(require('fs').readFileSync('.mault/canary-log.json','utf8')); process.exit(d.detections?.some(x=>x.uc==='UC14')?0:1)" 2>/dev/null && has_uc14=true
      node -e "const d=JSON.parse(require('fs').readFileSync('.mault/canary-log.json','utf8')); process.exit(d.detections?.some(x=>x.uc==='UC18')?0:1)" 2>/dev/null && has_uc18=true
    fi

    if [ "$scope" = "advanced" ] && ($has_uc14 || $has_uc18) && [ "$detected" -ge 2 ]; then
      print_pass 7 "Advanced canary evidence: scope=$scope, $detected detections, UC14=$has_uc14, UC18=$has_uc18"
    elif [ "$scope" != "advanced" ]; then
      print_fail 7 "Canary log has scope='$scope' (need 'advanced'). Core Initialize evidence does NOT satisfy Step 7. Run Phase 3."
    elif ! $has_uc14 && ! $has_uc18; then
      print_fail 7 "Canary log missing UC14/UC18 detections. Core UCs don't count for Step 7. Run Phase 3."
    else
      print_fail 7 "Advanced canary evidence insufficient: $detected detections (minimum: 2). Re-run Phase 3."
    fi
  else
    print_fail 7 "No canary evidence found (.mault/canary-log.json). Complete Phase 3 first."
  fi
}

# ============================================================
# CHECK 8: Canary Cleanup
# ============================================================
check_8() {
  if [ -d "mault-canary" ]; then
    local file_count
    file_count=$(find mault-canary -type f 2>/dev/null | wc -l)
    if [ "$file_count" -gt 0 ]; then
      print_fail 8 "Canary directory still has $file_count files. Delete mault-canary/ after writing canary-log.json."
    else
      print_pass 8 "Canary directory exists but is empty (acceptable)"
    fi
  else
    if [ -f ".mault/canary-log.json" ]; then
      print_pass 8 "Canary directory cleaned up (canary-log.json preserved)"
    else
      print_pending 8 "No canary evidence yet. Complete Phase 3 first."
    fi
  fi
}

# ============================================================
# CHECK 9: CI Governance Workflow
# ============================================================
check_9() {
  if [ -f ".github/workflows/mault-governance-gate.yml" ] || [ -f ".github/workflows/mault-governance-gate.yaml" ]; then
    print_pass 9 "CI governance workflow found"
  else
    print_fail 9 "No governance gate workflow found. Expected: .github/workflows/mault-governance-gate.yml"
  fi
}

# ============================================================
# CHECK 10: Runtime Hooks Installed
# ============================================================
check_10() {
  local settings_file=".claude/settings.json"
  if [ ! -f "$settings_file" ]; then
    print_fail 10 "No .claude/settings.json found. Runtime hooks not configured."
    return
  fi

  local has_pretool=false has_stop=false
  grep -q '"PreToolUse"' "$settings_file" && has_pretool=true
  grep -q '"Stop"' "$settings_file" && has_stop=true

  if $has_pretool && $has_stop; then
    print_pass 10 "Runtime hooks installed: PreToolUse + Stop in $settings_file"
  else
    local missing=""
    $has_pretool || missing+="PreToolUse "
    $has_stop || missing+="Stop "
    print_fail 10 "Missing runtime hook arrays in $settings_file: $missing"
  fi
}

# ============================================================
# CHECK 11: Handshake Commit
# ============================================================
check_11() {
  local handshake
  handshake=$(git log --oneline --grep="\[mault-step7\]" -1 2>/dev/null)
  if [ -n "$handshake" ]; then
    print_pass 11 "Handshake commit found: $handshake"
  else
    print_fail 11 "No handshake commit with [mault-step7] marker found (see Phase 5)"
  fi
}

# ============================================================
# CHECK 12: Proof File
# ============================================================
check_12() {
  if [ "$FAIL_COUNT" -eq 0 ] && [ "$PENDING_COUNT" -eq 0 ]; then
    print_pass 12 "All prior checks passed — proof file will be written"
  else
    print_fail 12 "Prior checks have failures — fix them first"
  fi
}

# ============================================================
# RUN ALL CHECKS
# ============================================================
check_1
check_2
check_3
check_4
check_5
check_6
check_7
check_8
check_9
check_10
check_11
check_12

# ============================================================
# SUMMARY
# ============================================================
echo ""
echo "========================================"
echo "  PASS: ${PASS_COUNT}/${TOTAL_CHECKS}  FAIL: ${FAIL_COUNT}/${TOTAL_CHECKS}  PENDING: ${PENDING_COUNT}/${TOTAL_CHECKS}"
echo "========================================"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PENDING_COUNT" -eq 0 ]; then
  write_proof_file
  exit 0
elif [ "$FAIL_COUNT" -gt 0 ]; then
  rm -f "$PROOF_FILE"
  echo ""
  echo "${FAIL_COUNT} check(s) FAILED. Fix issues and re-run: bash mault-verify-step7.sh"
  exit 1
else
  rm -f "$PROOF_FILE"
  echo ""
  echo "${PENDING_COUNT} check(s) PENDING. Complete work and re-run: bash mault-verify-step7.sh"
  exit 1
fi
