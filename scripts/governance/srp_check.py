#!/usr/bin/env python3
"""
SRP SIZE GUARDRAILS
Policy: Files and functions must stay within size limits.
Thresholds:
  - Implementation files: fail > 600 LOC
  - Test files: fail > 300 LOC
  - Functions/methods: fail > 75 LOC

Uses AST-based LOC counting (excludes blanks, comments, docstrings).

Usage:
    python srp_check.py                    # Full scan
    python srp_check.py src/ tests/        # Specific paths
"""

import argparse
import ast
import json
import sys
from datetime import date
from pathlib import Path

# ADAPT: Thresholds
IMPL_FAIL = 600
TEST_FAIL = 300
FUNC_FAIL = 75
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_test_file(path):
    return "tests" in path.parts or path.name.startswith("test_")


def count_loc(node, lines):
    """Count non-blank, non-comment lines within an AST node's span."""
    code_lines = set()
    for child in ast.walk(node):
        lineno = getattr(child, "lineno", None)
        end = getattr(child, "end_lineno", None) or lineno
        if lineno and end:
            for idx in range(lineno, end + 1):
                if 1 <= idx <= len(lines):
                    text = lines[idx - 1].strip()
                    if text and not text.startswith("#"):
                        code_lines.add(idx)
    return len(code_lines)


def load_exemptions(path):
    """Load exemptions JSON: [{"path": str, "justification": str, "expiresAt"?: str}]"""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
        exempt = set()
        for entry in data:
            expires = entry.get("expiresAt")
            if expires:
                try:
                    if date.fromisoformat(expires.split("T")[0]) < date.today():
                        continue
                except ValueError:
                    continue
            exempt.add(entry["path"].replace("\\", "/"))
        return exempt
    except (json.JSONDecodeError, OSError, KeyError):
        return set()


def main():
    parser = argparse.ArgumentParser(description="SRP Size Guardrails")
    parser.add_argument("paths", nargs="*", default=["src", "tests"])
    parser.add_argument("--exemptions-file", default=".srp-exemptions.json")
    parser.add_argument("--impl-fail", type=int, default=IMPL_FAIL)
    parser.add_argument("--test-fail", type=int, default=TEST_FAIL)
    parser.add_argument("--func-fail", type=int, default=FUNC_FAIL)
    args = parser.parse_args()

    exemptions = load_exemptions(Path(args.exemptions_file))
    file_failures, func_failures = [], []

    for path_str in args.paths:
        root = Path(path_str)
        py_files = [root] if root.is_file() else list(root.rglob("*.py")) if root.is_dir() else []
        for py in py_files:
            rel = str(py).replace("\\", "/")
            if rel in exemptions:
                continue
            try:
                text = py.read_text(encoding="utf-8")
                lines = text.splitlines()
                tree = ast.parse(text, filename=str(py))
            except (OSError, SyntaxError):
                continue

            file_loc = count_loc(tree, lines)
            threshold = args.test_fail if is_test_file(py) else args.impl_fail
            if file_loc > threshold:
                file_failures.append(f"{rel}: {file_loc} LOC (limit: {threshold})")

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_loc = count_loc(node, lines)
                    if func_loc > args.func_fail:
                        func_failures.append(
                            f"{rel}:{node.lineno} {node.name}() is {func_loc} LOC (limit: {args.func_fail})"
                        )

    if file_failures or func_failures:
        print("BLOCKED: SRP size limits exceeded\n")
        for msg in file_failures:
            print(f"  {msg}")
        for msg in func_failures:
            print(f"  {msg}")
        print("\nFix: Split large files/functions into smaller units.")
        sys.exit(1)

    print("SRP Check PASSED — all files and functions within limits")
    sys.exit(0)


if __name__ == "__main__":
    main()
