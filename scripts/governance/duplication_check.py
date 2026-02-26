#!/usr/bin/env python3
"""
DUPLICATE CODE DETECTOR (DRY Enforcement)
Policy: No copy-paste code blocks. Rising-tide: only fail on changed files.
Dependency-free: uses text-based sliding window, no external tools.

Usage:
    python duplication_check.py                   # Full scan
    python duplication_check.py --changed-files   # Rising-tide (CI mode)
    python duplication_check.py --max-clones 5    # Amnesty tolerance
"""

import argparse
import os
import sys
from pathlib import Path
from subprocess import run

# ADAPT: Project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIN_LINES = 7


def get_changed_files(base_ref="main"):
    try:
        result = run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", f"origin/{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        return {
            f
            for f in result.stdout.strip().split("\n")
            if f.endswith(".py") and f.startswith("src/")
        }
    except Exception:
        return set()


def find_duplicates(paths, min_lines):
    """Find duplicate code blocks using sliding window."""
    occurrences = {}
    for path_str in paths:
        root = PROJECT_ROOT / path_str
        py_files = [root] if root.is_file() else list(root.rglob("*.py")) if root.is_dir() else []
        for py in py_files:
            try:
                lines = py.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            if len(lines) < min_lines:
                continue
            rel = str(py.relative_to(PROJECT_ROOT)).replace("\\", "/")
            for start in range(len(lines) - min_lines + 1):
                window = tuple(l.strip() for l in lines[start : start + min_lines])
                if not any(l and not l.startswith("#") for l in window):
                    continue
                occurrences.setdefault(window, []).append((rel, start + 1))

    groups = []
    for blocks in occurrences.values():
        unique = {(r, s) for r, s in blocks}
        if len(unique) > 1:
            groups.append(list(unique))
    return groups


def main():
    parser = argparse.ArgumentParser(description="Duplicate Code Detection")
    parser.add_argument("paths", nargs="*", default=["src"])
    parser.add_argument("--min-lines", type=int, default=DEFAULT_MIN_LINES)
    parser.add_argument("--max-clones", type=int, default=0)
    parser.add_argument("--changed-files", action="store_true")
    parser.add_argument("--base-ref", default=os.environ.get("BASE_REF", "main"))
    args = parser.parse_args()

    groups = find_duplicates(args.paths, args.min_lines)

    if args.changed_files:
        changed = get_changed_files(args.base_ref)
        if not changed:
            print("Rising-tide: no changed files; skipping.")
            sys.exit(0)
        groups = [g for g in groups if any(r in changed for r, _ in g)]

    if not groups:
        print("Duplicate Code Check PASSED — no duplicates found")
        sys.exit(0)

    if args.max_clones and len(groups) <= args.max_clones:
        print(f"Duplicate Code: {len(groups)} group(s) within tolerance (max={args.max_clones})")
        sys.exit(0)

    print(f"BLOCKED: {len(groups)} duplicate code group(s) detected")
    for group in groups[:10]:
        first = group[0]
        print(f"  Block at {first[0]}:{first[1]}")
        for rel, line in group[1:]:
            print(f"    also at {rel}:{line}")
    print("\nFix: Extract to shared helper or reduce duplication.")
    sys.exit(1)


if __name__ == "__main__":
    main()
