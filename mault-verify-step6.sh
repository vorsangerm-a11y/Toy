#!/usr/bin/env bash
# mault-verify-step6.sh — Ralph Loop verification for Step 6: Pre-commit Hooks
# 12 CHECKs. Exit 0 only if ALL pass.
set -uo pipefail

PASS_COUNT=0
FAIL_COUNT=0
PENDING_COUNT=0
CHECK_RESULTS=()
TOTAL_CHECKS=12

PROOF_DIR=".mault"
PROOF_FILE="$PROOF_DIR/verify-step6.proof"

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

# --- Default branch detection ---
detect_default_branch() {
  local branch
  # Priority 1: GitHub API (authoritative source of truth)
  branch=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null) || true
  if [ -n "$branch" ]; then echo "$branch"; return; fi
  # Priority 2: Local git remote ref (may be stale — run `git remote set-head origin --auto` to fix)
  branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@refs/remotes/origin/@@') || true
  if [ -n "$branch" ]; then echo "$branch"; return; fi
  # Fallback: always main (never master)
  echo "main"
}
DEFAULT_BRANCH=$(detect_default_branch)

# --- Stack detection ---
HAS_PYTHON=false; HAS_NODE=false; HAS_GO=false
[ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ] && HAS_PYTHON=true
[ -f "package.json" ] && HAS_NODE=true
[ -f "go.mod" ] && HAS_GO=true

# Check subdirectories for monorepo stacks
for dir in */; do
  [ -f "${dir}pyproject.toml" ] || [ -f "${dir}setup.py" ] || [ -f "${dir}requirements.txt" ] && HAS_PYTHON=true
  [ -f "${dir}package.json" ] && HAS_NODE=true
  [ -f "${dir}go.mod" ] && HAS_GO=true
done

echo ""
echo "========================================"
echo "  MAULT STEP 6: Pre-commit Hooks"
echo "  Detected: Python=$HAS_PYTHON Node=$HAS_NODE Go=$HAS_GO"
echo "  Default branch: $DEFAULT_BRANCH"
echo "========================================"
echo ""

# --- Proof File Functions ---

write_proof_file() {
  local sha epoch iso token
  sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  epoch=$(date +%s)
  iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
  token="MAULT-STEP6-${sha}-${epoch}-${TOTAL_CHECKS}/${TOTAL_CHECKS}"

  mkdir -p "$PROOF_DIR"
  if [ ! -f "$PROOF_DIR/.gitignore" ]; then
    printf '*\n!.gitignore\n' > "$PROOF_DIR/.gitignore"
  fi

  {
    echo "MAULT-STEP6-PROOF"
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
  echo "ALL CHECKS PASSED. Step 6 Pre-commit Hooks is complete."
  echo "Proof written to: $PROOF_FILE"
  echo "Token: $token"
}

# ============================================================
# CHECK 1: Step 5 Prerequisite
# ============================================================
check_1() {
  if [ -f ".mault/verify-step5.proof" ]; then
    local token
    token=$(grep '^Token:' .mault/verify-step5.proof | awk '{print $2}') || true
    if [ -n "$token" ]; then
      print_pass 1 "Step 5 prerequisite verified (token: $token)"
    else
      print_fail 1 "Step 5 proof file exists but has no token. Re-run mault-verify-step5.sh"
    fi
  else
    print_fail 1 "Step 5 proof file not found (.mault/verify-step5.proof). Complete Step 5 first."
  fi
}

# ============================================================
# CHECK 2: Pre-commit CLI Installed
# ============================================================
check_2() {
  if pre-commit --version &>/dev/null; then
    local ver
    ver=$(pre-commit --version 2>/dev/null)
    print_pass 2 "Pre-commit installed: $ver"
  else
    print_fail 2 "pre-commit not found. Install: pip install pre-commit (see Phase 1)"
  fi
}

# ============================================================
# CHECK 3: Stack Tool Dependencies
# ============================================================
check_3() {
  local MISSING=()
  if $HAS_NODE; then
    command -v npx &>/dev/null || MISSING+=("npx")
    npx eslint --version &>/dev/null || MISSING+=("eslint")
    npx tsc --version &>/dev/null || MISSING+=("tsc (typescript)")
    { npx jest --version &>/dev/null || npx vitest --version &>/dev/null; } || MISSING+=("jest or vitest")
  fi
  if $HAS_PYTHON; then
    command -v black &>/dev/null || MISSING+=("black")
    command -v flake8 &>/dev/null || MISSING+=("flake8")
    command -v isort &>/dev/null || MISSING+=("isort")
    command -v mypy &>/dev/null || MISSING+=("mypy")
    command -v detect-secrets &>/dev/null || MISSING+=("detect-secrets")
  fi
  if $HAS_GO; then
    command -v golangci-lint &>/dev/null || MISSING+=("golangci-lint")
  fi

  if [ ${#MISSING[@]} -eq 0 ]; then
    print_pass 3 "All tool dependencies present for detected stack(s)"
  else
    print_fail 3 "Missing tools: ${MISSING[*]}. Install before proceeding (see Phase 1)."
  fi
}

# ============================================================
# CHECK 4: Config File(s) Exist
# ============================================================
check_4() {
  local found=false configs=""

  # Check root-level configs
  if [ -f ".pre-commit-config.yaml" ]; then
    found=true; configs+=".pre-commit-config.yaml "
  fi
  if [ -f ".pre-commit-config-ts.yaml" ]; then
    found=true; configs+=".pre-commit-config-ts.yaml "
  fi

  # Check subdirectories for monorepo configs
  for dir in */; do
    if [ -f "${dir}.pre-commit-config.yaml" ]; then
      found=true; configs+="${dir}.pre-commit-config.yaml "
    fi
  done

  if $found; then
    print_pass 4 "Config file(s) found: $configs"
  else
    print_fail 4 "No .pre-commit-config*.yaml files found (see Phase 1)"
  fi
}

# ============================================================
# CHECK 5: Git Hook Installed
# ============================================================
check_5() {
  if [ -f ".git/hooks/pre-commit" ] && [ -x ".git/hooks/pre-commit" ]; then
    print_pass 5 "Git pre-commit hook installed and executable"
  elif [ -f ".git/hooks/pre-commit" ]; then
    print_fail 5 "Hook exists but is not executable. Run: chmod +x .git/hooks/pre-commit"
  else
    print_fail 5 "No pre-commit hook found. Run: pre-commit install (see Phase 1)"
  fi
}

# ============================================================
# CHECK 6: Multi-Stack Orchestration
# ============================================================
check_6() {
  local config_count=0
  [ -f ".pre-commit-config.yaml" ] && config_count=$((config_count + 1))
  [ -f ".pre-commit-config-ts.yaml" ] && config_count=$((config_count + 1))

  if [ "$config_count" -ge 2 ]; then
    # Multi-stack: combined hook must reference BOTH configs
    if [ -f ".git/hooks/pre-commit" ] && \
       grep -q "pre-commit-config.yaml" .git/hooks/pre-commit && \
       grep -q "pre-commit-config-ts.yaml" .git/hooks/pre-commit; then
      print_pass 6 "Combined hook runs both configs ($config_count configs detected)"
    else
      print_fail 6 "Multi-stack project ($config_count configs) but hook doesn't reference both. Use install-precommit-hooks.sh (see Phase 1)"
    fi
  elif [ "$config_count" -eq 1 ]; then
    print_pass 6 "Single-stack project, standard hook is sufficient"
  else
    # Check monorepo subdirectories
    local sub_configs=0
    for dir in */; do
      [ -f "${dir}.pre-commit-config.yaml" ] && sub_configs=$((sub_configs + 1))
    done
    if [ "$sub_configs" -gt 0 ]; then
      print_pass 6 "Monorepo: $sub_configs subdirectory config(s) found"
    else
      print_fail 6 "No config files detected — cannot verify orchestration"
    fi
  fi
}

# ============================================================
# CHECK 7: All Hooks Pass
# ============================================================
check_7() {
  local all_pass=true
  local configs_checked=0

  if [ -f ".pre-commit-config.yaml" ]; then
    configs_checked=$((configs_checked + 1))
    if ! pre-commit run --all-files -c .pre-commit-config.yaml &>/dev/null; then
      all_pass=false
    fi
  fi
  if [ -f ".pre-commit-config-ts.yaml" ]; then
    configs_checked=$((configs_checked + 1))
    if ! pre-commit run --all-files -c .pre-commit-config-ts.yaml &>/dev/null; then
      all_pass=false
    fi
  fi

  if [ "$configs_checked" -eq 0 ]; then
    print_fail 7 "No config files to validate"
  elif $all_pass; then
    print_pass 7 "All hooks pass ($configs_checked config(s) validated)"
  else
    print_fail 7 "Some hooks failed. Run: pre-commit run --all-files to see details (see Phase 2)"
  fi
}

# ============================================================
# CHECK 8: Handshake Commit
# ============================================================
check_8() {
  local handshake
  handshake=$(git log --oneline --grep="\[mault-step6\]" -1 2>/dev/null)
  if [ -n "$handshake" ]; then
    print_pass 8 "Handshake commit found: $handshake"
  else
    print_fail 8 "No handshake commit with [mault-step6] marker found (see Phase 3)"
  fi
}

# ============================================================
# CHECK 9: PR Title Validation CI Job
# ============================================================
check_9() {
  local ci_file=""
  for f in .github/workflows/ci.yml .github/workflows/ci.yaml; do
    if [ -f "$f" ]; then ci_file="$f"; break; fi
  done

  if [ -z "$ci_file" ]; then
    print_fail 9 "No CI workflow found at .github/workflows/ci.yml"
    return
  fi
  if grep -q "validate-pr-title" "$ci_file"; then
    print_pass 9 "validate-pr-title job found in $ci_file"
  else
    print_fail 9 "validate-pr-title job not found in $ci_file (see Phase 3)"
  fi
}

# ============================================================
# CHECK 10: Branch Name Validation CI Job
# ============================================================
check_10() {
  local ci_file=""
  for f in .github/workflows/ci.yml .github/workflows/ci.yaml; do
    if [ -f "$f" ]; then ci_file="$f"; break; fi
  done

  if [ -z "$ci_file" ]; then
    print_fail 10 "No CI workflow found at .github/workflows/ci.yml"
    return
  fi
  if grep -q "validate-branch-name" "$ci_file"; then
    print_pass 10 "validate-branch-name job found in $ci_file"
  else
    print_fail 10 "validate-branch-name job not found in $ci_file (see Phase 3)"
  fi
}

# ============================================================
# CHECK 11: Branch Protection Updated
# ============================================================
check_11() {
  local owner repo
  owner=$(gh repo view --json owner -q '.owner.login' 2>/dev/null)
  repo=$(gh repo view --json name -q '.name' 2>/dev/null)

  if [ -z "$owner" ] || [ -z "$repo" ]; then
    print_fail 11 "Cannot determine repo owner/name. Ensure gh CLI is authenticated."
    return
  fi

  local protection
  protection=$(gh api "repos/$owner/$repo/branches/$DEFAULT_BRANCH/protection" 2>/dev/null)
  if [ -z "$protection" ]; then
    print_fail 11 "Cannot read branch protection. Check permissions."
    return
  fi

  # Parse with jq if available, fall back to gh --jq
  local required_checks enforce_admins
  if command -v jq &>/dev/null; then
    required_checks=$(echo "$protection" | jq -r '.required_status_checks.contexts[]' 2>/dev/null)
    enforce_admins=$(echo "$protection" | jq -r '.enforce_admins.enabled' 2>/dev/null)
  else
    # Fallback: re-fetch with gh --jq (avoids jq dependency on Windows/Git Bash)
    required_checks=$(gh api "repos/$owner/$repo/branches/$DEFAULT_BRANCH/protection/required_status_checks" --jq '.contexts[]' 2>/dev/null)
    enforce_admins=$(gh api "repos/$owner/$repo/branches/$DEFAULT_BRANCH/protection/enforce_admins" --jq '.enabled' 2>/dev/null)
  fi

  local MISSING=()
  echo "$required_checks" | grep -q "validate-pr-title" || MISSING+=("validate-pr-title")
  echo "$required_checks" | grep -q "validate-branch-name" || MISSING+=("validate-branch-name")

  if [ ${#MISSING[@]} -eq 0 ] && [ "$enforce_admins" = "true" ]; then
    print_pass 11 "Branch protection includes both CI checks + enforce_admins=true"
  else
    local msg="Missing checks: ${MISSING[*]:-none}, enforce_admins=$enforce_admins"
    print_fail 11 "$msg (see Phase 3)"
  fi
}

# ============================================================
# CHECK 12: Handshake Issue
# ============================================================
check_12() {
  local issue
  issue=$(gh issue list --search "[MAULT] Production Readiness: Step 6" --json number,title -q '.[0].number' 2>/dev/null)
  if [ -z "$issue" ]; then
    # Try closed issues
    issue=$(gh issue list --state closed --search "[MAULT] Production Readiness: Step 6" --json number,title -q '.[0].number' 2>/dev/null)
  fi

  if [ -n "$issue" ]; then
    print_pass 12 "Handshake issue #$issue found"
  else
    print_fail 12 "No GitHub issue with title containing '[MAULT] Production Readiness: Step 6' (see Phase 4)"
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
  echo "${FAIL_COUNT} check(s) FAILED. Fix issues and re-run: bash mault-verify-step6.sh"
  exit 1
else
  rm -f "$PROOF_FILE"
  echo ""
  echo "${PENDING_COUNT} check(s) PENDING. Complete work and re-run: bash mault-verify-step6.sh"
  exit 1
fi
