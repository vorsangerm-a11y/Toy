#!/usr/bin/env bash
# Step 5/9 Verification: TDD Framework
set -euo pipefail
PASS=0; FAIL=0; TOTAL=6

check() {
  local num="$1" name="$2" result="$3"
  if [ "$result" = "PASS" ]; then
    echo "  CHECK $num: PASS — $name"; PASS=$((PASS + 1))
  else
    echo "  CHECK $num: FAIL — $name"; FAIL=$((FAIL + 1))
  fi
}

echo "========================================"
echo " Step 5/9: TDD Framework"
echo "========================================"

check 1 "tests/ directory exists" "$([ -d tests ] && echo PASS || echo FAIL)"
check 2 "tests/unit/ exists" "$([ -d tests/unit ] && echo PASS || echo FAIL)"
check 3 "tests/integration/ exists" "$([ -d tests/integration ] && echo PASS || echo FAIL)"
check 4 "pyproject.toml has pytest config" "$(grep -q '\[tool.pytest.ini_options\]' pyproject.toml 2>/dev/null && echo PASS || echo FAIL)"
check 5 "pyproject.toml has coverage config" "$(grep -q '\[tool.coverage.run\]' pyproject.toml 2>/dev/null && echo PASS || echo FAIL)"
check 6 "requirements-dev.txt has pytest" "$(grep -q 'pytest' requirements-dev.txt 2>/dev/null && echo PASS || echo FAIL)"

echo ""
echo "========================================"
echo " Results: $PASS/$TOTAL PASS"
echo "========================================"

if [ "$PASS" -eq "$TOTAL" ]; then
  mkdir -p .mault
  echo "STEP5-OK-$(date -u +%Y%m%dT%H%M%SZ)" > .mault/verify-step5.proof
  echo " ✅ Step 5 VERIFIED"; exit 0
else
  echo " ❌ $FAIL check(s) failed."; exit 1
fi
