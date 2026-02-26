#!/usr/bin/env python3
"""
TYPE SAFETY GATE (Type Hole Ratchet)
Policy: Block commits that increase type holes above baseline.
Tracks: `# type: ignore` comments + `Any` type annotations.

Usage:
    python check_type_holes.py                      # Full scan (CI mode)
    python check_type_holes.py --changed-files f.py # Incremental
    python check_type_holes.py --update-baseline     # Initialize/update baseline
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# ADAPT: Point to your project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "type-holes.json"
# ADAPT: Source directory to scan
SRC_DIR = PROJECT_ROOT / "src"

TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore", re.IGNORECASE)


class TypeHoleVisitor(ast.NodeVisitor):
    """AST visitor to find Any type annotations."""

    def __init__(self):
        self.any_count = 0
        self.any_lines = []

    def visit_Name(self, node):
        if node.id == "Any":
            self.any_count += 1
            self.any_lines.append(node.lineno)
        self.generic_visit(node)


def analyze_file(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"type_ignore": 0, "any": 0, "total": 0}

    # Count # type: ignore
    ti_count = len(TYPE_IGNORE_RE.findall(content))

    # Count Any annotations via AST
    try:
        tree = ast.parse(content, filename=str(file_path))
        visitor = TypeHoleVisitor()
        visitor.visit(tree)
        any_count = visitor.any_count
    except SyntaxError:
        any_count = 0

    return {"type_ignore": ti_count, "any": any_count, "total": ti_count + any_count}


def find_python_files(paths=None):
    if paths:
        return [Path(p) for p in paths if Path(p).exists() and Path(p).suffix == ".py"]
    if not SRC_DIR.exists():
        return []
    return [f for f in SRC_DIR.rglob("*.py") if not f.name.startswith(".")]


def load_baseline():
    if not BASELINE_PATH.exists():
        return {"total": 0}
    return json.loads(BASELINE_PATH.read_text())


def save_baseline(data):
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Type Hole Ratchet")
    parser.add_argument("--changed-files", nargs="*", default=None)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    files = find_python_files(args.changed_files)
    if not files:
        print("Type Hole Check: No Python files found.")
        sys.exit(0)

    total_ti, total_any = 0, 0
    for f in files:
        result = analyze_file(f)
        total_ti += result["type_ignore"]
        total_any += result["any"]
    total = total_ti + total_any

    if args.update_baseline:
        save_baseline({"total_type_ignores": total_ti, "total_any": total_any, "total": total})
        print(f"Baseline updated: {total} type holes ({total_ti} type:ignore + {total_any} Any)")
        sys.exit(0)

    baseline = load_baseline()
    baseline_total = baseline.get("total", 0)

    print("Type Safety Gate (Type Hole Ratchet)")
    print(f"  Baseline: {baseline_total} | Current: {total}")

    if total > baseline_total:
        print(f"\nBLOCKED: Type holes increased ({baseline_total} -> {total})")
        print("  Fix: Replace Any with specific types, remove # type: ignore")
        sys.exit(1)

    print("  Type Safety Gate passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
