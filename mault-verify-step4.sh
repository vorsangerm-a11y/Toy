#!/usr/bin/env bash
set -uo pipefail

# ╔══════════════════════════════════════════════════════════════╗
# ║  MAULT RALPH LOOP — Step 4 CI/CD Verification               ║
# ║  Physics, not policy. This script checks REAL STATE.         ║
# ║  Exit 0 = all pass. Exit 1 = work remains.                  ║
# ╚══════════════════════════════════════════════════════════════╝

PASS_COUNT=0
FAIL_COUNT=0
PENDING_COUNT=0
CHECK_RESULTS=()

PROOF_DIR=".mault"
PROOF_FILE="$PROOF_DIR/verify-step4.proof"

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

# --- Default Branch Detection ---

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

# --- Proof File Functions ---

write_proof_file() {
  local sha epoch iso token
  sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  epoch=$(date +%s)
  iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
  token="MAULT-STEP4-${sha}-${epoch}-8/8"

  mkdir -p "$PROOF_DIR"
  if [ ! -f "$PROOF_DIR/.gitignore" ]; then
    printf '*\n!.gitignore\n' > "$PROOF_DIR/.gitignore"
  fi

  {
    echo "MAULT-STEP4-PROOF"
    echo "=================="
    echo "Timestamp: $epoch"
    echo "DateTime: $iso"
    echo "GitSHA: $sha"
    echo "Checks: 8/8 PASS"
    for r in "${CHECK_RESULTS[@]}"; do
      echo "  $r"
    done
    echo "=================="
    echo "Token: $token"
  } > "$PROOF_FILE"

  echo ""
  echo "Proof file written: $PROOF_FILE"
  echo "Token: $token"
}

check_proof_staleness() {
  if [ -f "$PROOF_FILE" ]; then
    local proof_sha current_sha
    proof_sha=$(grep '^GitSHA:' "$PROOF_FILE" | awk '{print $2}')
    current_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    if [ "$proof_sha" != "$current_sha" ]; then
      echo "WARNING: Proof file is STALE (proof: $proof_sha, HEAD: $current_sha). Deleting."
      rm -f "$PROOF_FILE"
    fi
  fi
}

echo "========================================"
echo "  MAULT Step 4 CI/CD Verification"
echo "  Default branch: $DEFAULT_BRANCH"
echo "========================================"
echo ""

# --- CHECK 1: GitHub CLI Authenticated ---

check_1() {
  if gh auth status >/dev/null 2>&1; then
    local user
    user=$(gh auth status 2>&1 | sed -n 's/.*Logged in to github\.com account \([^[:space:]]*\).*/\1/p') || true
    user=${user:-unknown}
    print_pass 1 "GitHub CLI authenticated ($user)"
  else
    print_fail 1 "GitHub CLI not authenticated. Run: gh auth login"
  fi
}

# --- CHECK 2: Project Stack Detected ---

check_2() {
  local detected=""
  { [ -f "package.json" ] || ls */package.json >/dev/null 2>&1; } && detected="${detected}node "
  { [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ] || \
    ls */requirements.txt >/dev/null 2>&1 || ls */pyproject.toml >/dev/null 2>&1 || \
    ls */setup.py >/dev/null 2>&1; } && detected="${detected}python "
  { [ -f "go.mod" ] || ls */go.mod >/dev/null 2>&1; } && detected="${detected}go "
  { [ -f "Cargo.toml" ] || ls */Cargo.toml >/dev/null 2>&1; } && detected="${detected}rust "
  { [ -f "pom.xml" ] || [ -f "build.gradle" ] || \
    ls */pom.xml >/dev/null 2>&1 || ls */build.gradle >/dev/null 2>&1; } && detected="${detected}java "
  { ls ./*.csproj >/dev/null 2>&1 || ls ./*.sln >/dev/null 2>&1 || \
    ls */*.csproj >/dev/null 2>&1 || ls */*.sln >/dev/null 2>&1; } && detected="${detected}dotnet "
  detected=$(echo "$detected" | xargs)
  if [ -n "$detected" ]; then
    print_pass 2 "Stack detected: $detected"
  else
    print_fail 2 "No recognized project stack found"
  fi
}

# --- CHECK 3: CI Workflow Exists ---

check_3() {
  if [ -f ".github/workflows/ci.yml" ] || [ -f ".github/workflows/ci.yaml" ]; then
    print_pass 3 "CI workflow file exists"
  elif ls .github/workflows/*.yml .github/workflows/*.yaml >/dev/null 2>&1; then
    print_pass 3 "Workflow files found (non-standard name)"
  else
    print_pending 3 "No CI workflow found. Create .github/workflows/ci.yml"
  fi
}

# --- CHECK 4: CI Config Committed and Pushed ---

check_4() {
  local ci_file
  ci_file=$(ls .github/workflows/ci.yml .github/workflows/ci.yaml 2>/dev/null | head -1) || true
  if [ -z "$ci_file" ]; then
    print_pending 4 "No CI workflow file yet. Complete CHECK 3 first."
    return
  fi
  if ! git ls-files --error-unmatch "$ci_file" >/dev/null 2>&1; then
    print_fail 4 "CI workflow exists but is NOT committed"
    return
  fi
  local remote_sha
  remote_sha=$(git log -1 --format=%H "origin/${DEFAULT_BRANCH}" -- "$ci_file" 2>/dev/null) || true
  if [ -z "$remote_sha" ]; then
    print_fail 4 "CI workflow committed but NOT pushed to origin/${DEFAULT_BRANCH}"
    return
  fi
  print_pass 4 "CI workflow committed and pushed to origin/${DEFAULT_BRANCH}"
}

# --- CHECK 5: CI Runs Green (NO polling — instant check) ---

check_5() {
  local run_info status conclusion run_id
  run_info=$(gh run list --branch "$DEFAULT_BRANCH" --limit 1 --json databaseId,status,conclusion \
    -q '.[0] | "\(.status)|\(.conclusion)|\(.databaseId)"' 2>/dev/null) || true
  if [ -z "$run_info" ] || [ "$run_info" = "null|null|null" ]; then
    print_pending 5 "No CI runs found on ${DEFAULT_BRANCH}. Push workflow and wait."
    return
  fi
  status=$(echo "$run_info" | cut -d'|' -f1)
  conclusion=$(echo "$run_info" | cut -d'|' -f2)
  run_id=$(echo "$run_info" | cut -d'|' -f3)
  if [ "$status" = "completed" ]; then
    if [ "$conclusion" = "success" ]; then
      print_pass 5 "Latest CI run succeeded (run #${run_id})"
    else
      print_fail 5 "Latest CI run FAILED (conclusion: ${conclusion}). Run: gh run view ${run_id} --log-failed"
    fi
  elif [ "$status" = "in_progress" ] || [ "$status" = "queued" ]; then
    print_pending 5 "CI run #${run_id} is ${status}. Wait 30s and re-run this script."
  else
    print_fail 5 "CI run #${run_id} has unexpected status: ${status}"
  fi
}

# --- CHECK 6: Branch Protection Configured ---

check_6() {
  local owner repo
  owner=$(gh repo view --json owner -q '.owner.login' 2>/dev/null) || true
  repo=$(gh repo view --json name -q '.name' 2>/dev/null) || true
  if [ -z "$owner" ] || [ -z "$repo" ]; then
    print_fail 6 "Cannot determine repo owner/name"
    return
  fi

  local protection
  protection=$(gh api "repos/${owner}/${repo}/branches/${DEFAULT_BRANCH}/protection/required_status_checks" -q '.contexts[]' 2>/dev/null) || true
  if [ -z "$protection" ]; then
    print_fail 6 "No branch protection on ${DEFAULT_BRANCH}. Run Phase 3 to configure."
    return
  fi
  local run_id
  run_id=$(gh run list --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null) || true
  if [ -z "$run_id" ]; then
    print_pending 6 "No CI runs yet — cannot verify check names. Run CI first."
    return
  fi
  local actual_jobs missing_checks=""
  actual_jobs=$(gh run view "$run_id" --json jobs -q '.jobs[].name' 2>/dev/null) || true
  if [ -z "$actual_jobs" ]; then
    print_pending 6 "CI run found but no job names returned. Wait for run to complete."
    return
  fi
  while IFS= read -r job; do
    if ! echo "$protection" | grep -qF "$job" 2>/dev/null; then
      missing_checks="${missing_checks} ${job}"
    fi
  done <<< "$actual_jobs"
  if [ -n "$missing_checks" ]; then
    print_fail 6 "CI jobs missing from required checks:${missing_checks}. Re-run Phase 3."
    return
  fi

  local enforce_admins
  enforce_admins=$(gh api "repos/${owner}/${repo}/branches/${DEFAULT_BRANCH}/protection/enforce_admins" -q '.enabled' 2>/dev/null) || true
  if [ "$enforce_admins" != "true" ]; then
    print_fail 6 "enforce_admins is OFF — agents/admins can bypass all branch rules. Re-run Phase 3."
    return
  fi

  local approval_count
  approval_count=$(gh api "repos/${owner}/${repo}/branches/${DEFAULT_BRANCH}/protection/required_pull_request_reviews" -q '.required_approving_review_count' 2>/dev/null) || true
  if [ -z "$approval_count" ] || [ "$approval_count" -lt 1 ] 2>/dev/null; then
    print_fail 6 "PR approval count is ${approval_count:-0} — must be at least 1. Re-run Phase 3."
    return
  fi

  local check_count
  check_count=$(echo "$actual_jobs" | wc -l | tr -d ' ')
  print_pass 6 "Branch protection: ${check_count} required checks, enforce_admins=ON, approvals=${approval_count}"
}

# --- CHECK 7: PR with Passing Checks ---

check_7() {
  local pr_url
  pr_url=$(gh pr list --state open --limit 1 --json url -q '.[0].url' 2>/dev/null) || true
  if [ -z "$pr_url" ]; then
    pr_url=$(gh pr list --state merged --limit 1 --json url -q '.[0].url' 2>/dev/null) || true
    if [ -n "$pr_url" ]; then
      print_pass 7 "Merged PR found: ${pr_url}"
      return
    fi
    print_pending 7 "No PR found. Create one to verify CI gates."
    return
  fi
  local checks_output exit_code
  checks_output=$(gh pr checks "$pr_url" 2>&1)
  exit_code=$?
  if [ -z "$checks_output" ] || echo "$checks_output" | grep -qi "no checks"; then
    print_pending 7 "No checks reported on PR: ${pr_url}. Wait and re-run."
  elif [ "$exit_code" -eq 0 ]; then
    print_pass 7 "PR with passing checks: ${pr_url}"
  elif echo "$checks_output" | grep -qi "pending"; then
    print_pending 7 "PR has pending checks: ${pr_url}. Wait and re-run."
  else
    print_fail 7 "PR has failing checks: ${pr_url}"
  fi
}

# --- CHECK 8: Handshake Issue Created ---

check_8() {
  local issue_url
  issue_url=$(gh issue list --search "[MAULT] Production Readiness: Step 4" --json url -q '.[0].url' 2>/dev/null) || true
  if [ -z "$issue_url" ]; then
    issue_url=$(gh issue list --state closed --search "[MAULT] Production Readiness: Step 4" --json url -q '.[0].url' 2>/dev/null) || true
  fi
  if [ -n "$issue_url" ]; then
    print_pass 8 "Handshake issue: ${issue_url}"
  else
    print_pending 8 "No handshake issue found. Create it as proof of completion."
  fi
}

# --- Staleness Check ---
check_proof_staleness

# --- Run All Checks ---

check_1
check_2
check_3
check_4
check_5
check_6
check_7
check_8

# --- Summary ---

echo ""
echo "========================================"
echo "  PASS: ${PASS_COUNT}/8  FAIL: ${FAIL_COUNT}/8  PENDING: ${PENDING_COUNT}/8"
echo "========================================"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PENDING_COUNT" -eq 0 ]; then
  write_proof_file
  echo "ALL CHECKS PASSED. Step 4 CI/CD is complete."
  exit 0
elif [ "$FAIL_COUNT" -gt 0 ]; then
  rm -f "$PROOF_FILE"
  echo "${FAIL_COUNT} check(s) FAILED. Fix and re-run: ./mault-verify-step4.sh"
  exit 1
else
  rm -f "$PROOF_FILE"
  echo "${PENDING_COUNT} check(s) PENDING. Complete work and re-run: ./mault-verify-step4.sh"
  exit 1
fi
