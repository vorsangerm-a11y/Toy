#!/usr/bin/env python3
"""
SKIPPED TESTS GATE
Policy: No more than 5% of tests can be skipped.
Reason: AI coders mark failing tests as skip instead of fixing them.

Detection: Scans test files for skip markers:
    @pytest.mark.skip, @unittest.skip, pytest.skip(), .skipTest(),
    @pytest.mark.skipIf, @unittest.skipIf, @unittest.skipUnless

Usage:
    python check_skipped_tests.py             # Full scan (CI mode)
    python check_skipped_tests.py --staged    # Pre-commit mode
    python check_skipped_tests.py --max 3     # Custom max percentage
"""

import ast
import os
import re
import sys
from pathlib import Path
from subprocess import run

# ADAPT: Point to your project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TEST_DIRS = [PROJECT_ROOT / "tests", PROJECT_ROOT / "test", SRC_DIR]

# ADAPT: Max percentage of skipped tests
DEFAULT_MAX_SKIP_PCT = 5

EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".tox",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
}

# Test file patterns
TEST_FILE_PATTERNS = [r"^test_.*\.py$", r".*_test\.py$"]

# Skip markers (searched in source)
SKIP_PATTERNS = [
    r"@pytest\.mark\.skip\b",
    r"@pytest\.mark\.skipIf\b",
    r"@pytest\.mark\.skipif\b",
    r"@unittest\.skip\b",
    r"@unittest\.skipIf\b",
    r"@unittest\.skipUnless\b",
    r"pytest\.skip\s*\(",
    r"self\.skipTest\s*\(",
    r"unittest\.skip\s*\(",
]


def is_test_file(filename: str) -> bool:
    return any(re.search(p, filename) for p in TEST_FILE_PATTERNS)


def get_all_test_files():
    """Find all test files in project."""
    files = []
    for test_dir in TEST_DIRS:
        if not test_dir.exists():
            continue
        for root, dirs, filenames in os.walk(test_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for f in filenames:
                if is_test_file(f):
                    files.append(Path(root) / f)
    return list(set(files))


def get_staged_test_files():
    """Get staged test files."""
    try:
        result = run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        return [
            PROJECT_ROOT / f
            for f in result.stdout.strip().split("\n")
            if is_test_file(Path(f).name) and (PROJECT_ROOT / f).exists()
        ]
    except Exception:
        return []


def count_tests_in_file(filepath: Path):
    """Count total tests and skipped tests using AST parsing."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    total_tests = 0
    skipped_tests = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            total_tests += 1
            # Check decorators for skip markers
            for decorator in node.decorator_list:
                dec_str = ast.dump(decorator)
                if "skip" in dec_str.lower():
                    skipped_tests += 1
                    break

    # Also count skip patterns in source text (catches runtime skips)
    runtime_skips = 0
    for pattern in SKIP_PATTERNS:
        matches = re.findall(pattern, content)
        runtime_skips += len(matches)

    # Avoid double-counting (decorator skips already counted)
    # Use the higher of AST-detected or pattern-detected
    skipped_tests = max(skipped_tests, runtime_skips)

    # If no AST test functions found, try class-based unittest methods
    if total_tests == 0:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                        total_tests += 1

    return total_tests, skipped_tests


# --- Main ---
staged_mode = "--staged" in sys.argv
max_skip_pct = DEFAULT_MAX_SKIP_PCT
if "--max" in sys.argv:
    idx = sys.argv.index("--max")
    max_skip_pct = float(sys.argv[idx + 1])

test_files = get_staged_test_files() if staged_mode else get_all_test_files()
if not test_files:
    print("Skipped Tests Check: No test files found.")
    sys.exit(0)

total_tests = 0
total_skipped = 0
skipped_files = []

for filepath in test_files:
    tests, skipped = count_tests_in_file(filepath)
    total_tests += tests
    total_skipped += skipped
    if skipped > 0:
        rel = str(filepath.relative_to(PROJECT_ROOT))
        skipped_files.append({"file": rel, "skipped": skipped, "total": tests})

skip_pct = (total_skipped / total_tests * 100) if total_tests > 0 else 0

print(f"Skipped Tests Check: {len(test_files)} test files scanned")
print(f"  Total tests:   {total_tests}")
print(f"  Skipped tests: {total_skipped} ({skip_pct:.1f}%)")
print(f"  Max allowed:   {max_skip_pct}%\n")

if skip_pct > max_skip_pct:
    print(f"BLOCKED: {skip_pct:.1f}% tests skipped (max: {max_skip_pct}%)\n", file=sys.stderr)
    for f in skipped_files:
        print(f"  {f['file']}: {f['skipped']} skipped / {f['total']} total", file=sys.stderr)
    print("\nFix: Remove skip markers and fix or delete the failing tests.", file=sys.stderr)
    print(f"Skipped tests must not exceed {max_skip_pct}% of total test count.\n", file=sys.stderr)
    sys.exit(1)

print("Skipped Tests Check: PASSED")
sys.exit(0)
