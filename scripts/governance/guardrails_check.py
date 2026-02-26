#!/usr/bin/env python3
"""
SIZE & COMPLEXITY GATE (SRP Enforcement)
Policy: Block files and functions that exceed size/complexity limits.
Reason: AI coders produce god-files and mega-functions that are untestable.

Thresholds:
    Source file: 600 LOC max
    Test file:   300 LOC max
    Config file:  75 LOC max
    Function:     50 LOC max
    Cyclomatic complexity: 15 per function max

Amnesty Protocol: Legacy violations grandfathered at baseline.
Only NEW violations (above baseline) are blocked.

Usage:
    python guardrails_check.py           # Full scan (CI mode)
    python guardrails_check.py --staged  # Pre-commit mode (staged files only)
    python guardrails_check.py --init    # Initialize amnesty baseline
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from subprocess import run

# ADAPT: Point to your project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "guardrails-baseline.json"

# ADAPT: Thresholds
THRESHOLDS = {
    "source_file_loc": 600,
    "test_file_loc": 300,
    "config_file_loc": 75,
    "function_loc": 50,
    "cyclomatic_complexity": 15,
}

# ADAPT: Patterns to identify file types
TEST_PATTERNS = [r"test_.*\.py$", r".*_test\.py$", r"tests/", r"test/"]
CONFIG_PATTERNS = [r"conftest\.py$", r"settings\.py$", r"config\.py$", r"manage\.py$"]
EXCLUDE_DIRS = {"node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".tox", ".eggs"}


def get_file_type(filepath: str) -> str:
    if any(re.search(p, filepath) for p in TEST_PATTERNS):
        return "test"
    if any(re.search(p, filepath) for p in CONFIG_PATTERNS):
        return "config"
    return "source"


def get_max_loc(file_type: str) -> int:
    if file_type == "test":
        return THRESHOLDS["test_file_loc"]
    if file_type == "config":
        return THRESHOLDS["config_file_loc"]
    return THRESHOLDS["source_file_loc"]


def count_loc(content: str) -> int:
    """Count non-blank, non-comment lines."""
    count = 0
    in_docstring = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                in_docstring = False
                continue
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                continue
            in_docstring = True
            continue
        if in_docstring:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def calculate_cyclomatic_complexity(node) -> int:
    """Calculate cyclomatic complexity of an AST function node."""
    cc = 1  # Base path
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            cc += 1
        elif isinstance(child, ast.For):
            cc += 1
        elif isinstance(child, ast.While):
            cc += 1
        elif isinstance(child, ast.ExceptHandler):
            cc += 1
        elif isinstance(child, ast.With):
            cc += 1
        elif isinstance(child, ast.Assert):
            cc += 1
        elif isinstance(child, ast.BoolOp):
            # and/or add branches
            cc += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            cc += 1 + len(child.ifs)
    return cc


def extract_functions(content: str, filepath: str):
    """Extract functions with LOC and cyclomatic complexity."""
    functions = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return functions

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_lines = content.split("\n")[node.lineno - 1 : node.end_lineno]
            func_content = "\n".join(func_lines)
            loc = count_loc(func_content)
            cc = calculate_cyclomatic_complexity(node)
            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "loc": loc,
                    "cc": cc,
                    "file": filepath,
                }
            )
    return functions


def get_all_files(src_dir: Path):
    """Recursively find Python files."""
    files = []
    if not src_dir.exists():
        return files
    for root, dirs, filenames in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py") and not f.startswith("."):
                files.append(Path(root) / f)
    return files


def get_staged_files():
    """Get staged Python files."""
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
            if f.endswith(".py") and (PROJECT_ROOT / f).exists()
        ]
    except Exception:
        return []


def load_baseline():
    try:
        if BASELINE_PATH.exists():
            return json.loads(BASELINE_PATH.read_text())
        return None
    except Exception:
        return None


def save_baseline(data):
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2))


# --- Main ---
init_mode = "--init" in sys.argv
staged_mode = "--staged" in sys.argv

files = get_staged_files() if staged_mode else get_all_files(SRC_DIR)
if not files:
    print("Guardrails Check: No files to scan.")
    sys.exit(0)

file_violations = []
func_violations = []

for filepath in files:
    content = filepath.read_text(encoding="utf-8", errors="replace")
    rel = str(filepath.relative_to(PROJECT_ROOT))
    file_type = get_file_type(rel)
    max_loc = get_max_loc(file_type)
    loc = count_loc(content)

    if loc > max_loc:
        file_violations.append({"file": rel, "type": file_type, "loc": loc, "max": max_loc})

    funcs = extract_functions(content, rel)
    for fn in funcs:
        if fn["loc"] > THRESHOLDS["function_loc"]:
            func_violations.append(
                {
                    "file": rel,
                    "name": fn["name"],
                    "line": fn["line"],
                    "metric": "LOC",
                    "value": fn["loc"],
                    "max": THRESHOLDS["function_loc"],
                }
            )
        if fn["cc"] > THRESHOLDS["cyclomatic_complexity"]:
            func_violations.append(
                {
                    "file": rel,
                    "name": fn["name"],
                    "line": fn["line"],
                    "metric": "CC",
                    "value": fn["cc"],
                    "max": THRESHOLDS["cyclomatic_complexity"],
                }
            )

total_violations = len(file_violations) + len(func_violations)

if init_mode:
    save_baseline(
        {
            "file_violations": len(file_violations),
            "func_violations": len(func_violations),
            "total": total_violations,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    print(
        f"Guardrails Baseline initialized: {total_violations} violations "
        f"({len(file_violations)} file, {len(func_violations)} function)"
    )
    sys.exit(0)

baseline = load_baseline()
baseline_total = baseline["total"] if baseline else 0

print(f"Guardrails Check: {len(files)} files scanned")
print(f"  File violations:     {len(file_violations)}")
print(f"  Function violations: {len(func_violations)}")
print(f"  Total: {total_violations} | Baseline: {baseline_total}\n")

if total_violations > baseline_total:
    new_count = total_violations - baseline_total
    print(
        f"BLOCKED: {new_count} NEW violation(s) above baseline ({baseline_total} -> {total_violations})\n",
        file=sys.stderr,
    )
    for v in file_violations:
        print(f"  {v['file']} — {v['loc']} LOC ({v['type']} max: {v['max']})", file=sys.stderr)
    for v in func_violations:
        print(
            f"  {v['file']}:{v['line']} {v['name']}() — {v['metric']} {v['value']} (max: {v['max']})",
            file=sys.stderr,
        )
    print(
        "\nFix: Split large files/functions. Extract helpers or use composition.", file=sys.stderr
    )
    print("Baseline can only go DOWN, never UP.\n", file=sys.stderr)
    sys.exit(1)

if total_violations < baseline_total:
    save_baseline(
        {
            "file_violations": len(file_violations),
            "func_violations": len(func_violations),
            "total": total_violations,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    print(f"Baseline improved: {baseline_total} -> {total_violations} (ratcheted down)")

print("Guardrails Check: PASSED")
sys.exit(0)
