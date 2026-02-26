#!/usr/bin/env python3
"""
DEAD CODE GATE (Silent Catch Detection)
Policy: Exception handlers must log+rethrow or be marked intentional.
Uses AST analysis — no regex string matching.

Usage:
    python check_silent_catches.py                      # Full scan
    python check_silent_catches.py --changed-files f.py # Incremental
"""

import argparse
import ast
import sys
from pathlib import Path

# ADAPT: Point to your project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
SILENT_CATCH_MARKER = "SILENT_CATCH:"


class SilentCatchVisitor(ast.NodeVisitor):
    """AST visitor to find silent exception handlers."""

    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.violations = []

    def visit_ExceptHandler(self, node):
        exc_type = "bare except"
        if isinstance(node.type, ast.Name):
            exc_type = node.type.id
        elif isinstance(node.type, ast.Tuple):
            exc_type = "multiple exceptions"

        if self._is_silent(node) and not self._has_marker(node.lineno):
            self.violations.append((node.lineno, exc_type))
        self.generic_visit(node)

    def _is_silent(self, node):
        if not node.body:
            return True
        for stmt in node.body:
            if isinstance(stmt, ast.Pass):
                continue
            if isinstance(stmt, ast.Raise):
                return False
            if isinstance(stmt, ast.Return):
                return False
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                if self._is_logging_call(stmt.value):
                    return False
            if not isinstance(stmt, (ast.Pass, ast.Expr)):
                return False
        return True

    def _is_logging_call(self, call):
        if isinstance(call.func, ast.Attribute):
            if call.func.attr.lower() in {
                "debug",
                "info",
                "warning",
                "error",
                "critical",
                "exception",
                "log",
                "warn",
            }:
                return True
        if isinstance(call.func, ast.Name) and call.func.id == "print":
            return True
        return False

    def _has_marker(self, lineno):
        for offset in [0, -1]:
            idx = lineno + offset - 1
            if 0 <= idx < len(self.source_lines):
                if SILENT_CATCH_MARKER in self.source_lines[idx]:
                    return True
        return False


def check_file(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (OSError, SyntaxError):
        return []
    visitor = SilentCatchVisitor(content.splitlines())
    visitor.visit(tree)
    return visitor.violations


def find_python_files(paths=None):
    if paths:
        return [Path(p) for p in paths if Path(p).exists() and Path(p).suffix == ".py"]
    files = []
    for d in [SRC_DIR, PROJECT_ROOT / "tests"]:
        if d.exists():
            files.extend(d.rglob("*.py"))
    return files


def main():
    parser = argparse.ArgumentParser(description="Silent Catch Detection")
    parser.add_argument("--changed-files", nargs="*", default=None)
    args = parser.parse_args()

    files = find_python_files(args.changed_files)
    if not files:
        print("Silent Catch Check: No files found.")
        sys.exit(0)

    all_violations = []
    for f in files:
        violations = check_file(f)
        for lineno, exc_type in violations:
            rel = str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")
            all_violations.append((rel, lineno, exc_type))

    print("Dead Code Gate (Silent Catch Detection)")
    print(f"  Silent catches found: {len(all_violations)}")

    if all_violations:
        print("\nBLOCKED: Silent exception handlers detected")
        for path, lineno, exc_type in all_violations:
            print(f"  {path}:{lineno} — {exc_type}")
        print("\nFix: Add logging + re-raise, or mark: # SILENT_CATCH: reason")
        sys.exit(1)

    print("  Dead Code Gate passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
