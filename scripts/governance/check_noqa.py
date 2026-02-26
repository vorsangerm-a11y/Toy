#!/usr/bin/env python3
"""
NOQA/PYLINT-DISABLE GATE
Policy: No new # noqa or # pylint: disable comments in source code.
Amnesty: Legacy lines with "-- LEGACY" suffix are grandfathered.

Usage:
    python check_noqa.py  # Checks changed files (CI or pre-commit)
"""

import sys
from pathlib import Path
from subprocess import run

# ADAPT: Paths exempt from this rule (test infrastructure, scripts)
EXEMPT_PATHS = ["tests/mocks/", "scripts/", "conftest.py"]

FORBIDDEN_PATTERNS = [
    ("# noqa", "noqa suppression"),
    ("# type: ignore", "type: ignore suppression"),
    ("# pylint: disable", "pylint disable"),
    ("# pylint:disable", "pylint disable"),
]


def is_exempt(file_path):
    return any(e in file_path for e in EXEMPT_PATHS)


def get_changed_files():
    import os

    try:
        if os.environ.get("CI") == "true":
            base = os.environ.get("GITHUB_BASE_REF", "main")
            result = run(
                ["git", "diff", "--name-only", "--diff-filter=ACM", f"origin/{base}...HEAD"],
                capture_output=True,
                text=True,
            )
        else:
            result = run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True,
                text=True,
            )
        return [
            f for f in result.stdout.strip().split("\n") if f.endswith(".py") and not is_exempt(f)
        ]
    except Exception:
        return []


def check_file(file_path):
    if not Path(file_path).exists():
        return []
    violations = []
    for i, line in enumerate(Path(file_path).read_text().splitlines(), 1):
        if "-- LEGACY" in line:
            continue
        for pattern, message in FORBIDDEN_PATTERNS:
            if pattern in line:
                violations.append(
                    {"file": file_path, "line": i, "text": line.strip(), "message": message}
                )
                break
    return violations


def main():
    changed = get_changed_files()
    if not changed:
        print("noqa Gate: No files changed.")
        sys.exit(0)

    violations = []
    for f in changed:
        violations.extend(check_file(f))

    if not violations:
        print("noqa Gate: Passed.")
        sys.exit(0)

    print("BLOCKED: Suppression directives found in new code\n")
    for v in violations:
        print(f"  {v['file']}:{v['line']} — {v['message']}")
        print(f"    {v['text']}\n")
    print("Fix: Resolve the underlying issue instead of suppressing it.")
    print('Legacy: Add "-- LEGACY" suffix for pre-existing suppressions.\n')
    sys.exit(1)


if __name__ == "__main__":
    main()
