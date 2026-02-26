#!/usr/bin/env python3
"""
MOCK CONFORMANCE GATE
Policy: No bare Mock() or MagicMock() in test fixtures.
Fix: Use create_autospec(ServiceClass, instance=True) instead.
Reason: Bare mocks accept any method call, masking interface drift.

Usage:
    python check_mock_conformance.py                # Check conftest.py files
    python check_mock_conformance.py --all-files    # Check all test files
"""

import argparse
import ast
import sys
from pathlib import Path

# ADAPT: Project root and test directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = PROJECT_ROOT / "tests"


def find_bare_mocks(file_path):
    """Find bare Mock() and MagicMock() calls via AST."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (OSError, SyntaxError):
        return []

    bare_mocks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("Mock", "MagicMock"):
                bare_mocks.append((node.lineno, node.func.id))
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ("Mock", "MagicMock"):
                bare_mocks.append((node.lineno, node.func.attr))
    return bare_mocks


def main():
    parser = argparse.ArgumentParser(description="Mock Conformance Gate")
    parser.add_argument("paths", nargs="*", default=["tests"])
    parser.add_argument("--all-files", action="store_true")
    args = parser.parse_args()

    files = []
    for p in args.paths:
        path = PROJECT_ROOT / p if not Path(p).is_absolute() else Path(p)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            if args.all_files:
                files.extend(path.rglob("*.py"))
            else:
                files.extend(path.rglob("conftest.py"))

    if not files:
        print("Mock Conformance: No files to check.")
        sys.exit(0)

    violations = 0
    for f in files:
        bare = find_bare_mocks(f)
        if bare:
            violations += len(bare)
            rel = str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")
            print(f"  {rel}:")
            for lineno, mock_type in bare:
                print(f"    Line {lineno}: Bare {mock_type}() found")

    if violations:
        print(f"\nBLOCKED: {violations} bare mock(s) found")
        print("Fix: Replace Mock()/MagicMock() with create_autospec(ServiceClass, instance=True)")
        sys.exit(1)

    print(f"Mock Conformance PASSED — {len(files)} file(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
