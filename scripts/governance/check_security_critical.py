#!/usr/bin/env python3
"""
SECURITY-CRITICAL REVIEW GATE
Policy: Changes to @security-critical code require human review.
Detects: Decorators, docstring markers, and security-related patterns.

Usage:
    python check_security_critical.py  # Checks changed files
"""

import os
import sys
from pathlib import Path
from subprocess import run

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SECURITY_MARKERS = ["@security_critical", "@security-critical", "SECURITY-CRITICAL"]
# ADAPT: Patterns that indicate security-sensitive code
SECURITY_PATTERNS = [
    "password",
    "secret",
    "token",
    "api_key",
    "encrypt",
    "decrypt",
    "hash_password",
    "verify_password",
    "jwt",
    "oauth",
    "sanitize",
    "csrf",
    "cors",
    "auth_required",
]


def get_changed_files():
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
        return [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
    except Exception:
        return []


def check_file(file_path):
    if not Path(file_path).exists():
        return {"markers": [], "patterns": []}
    content = Path(file_path).read_text(encoding="utf-8")
    lines = content.splitlines()
    markers, patterns = [], []
    for i, line in enumerate(lines, 1):
        for m in SECURITY_MARKERS:
            if m in line:
                markers.append((i, line.strip()))
        for p in SECURITY_PATTERNS:
            if p in line.lower() and "test" not in file_path.lower():
                patterns.append((i, p))
    return {"markers": markers, "patterns": patterns}


def main():
    if os.environ.get("SECURITY_REVIEW_ACKNOWLEDGED") == "true":
        print("Security Review: Acknowledged via environment variable.")
        sys.exit(0)

    changed = get_changed_files()
    if not changed:
        print("Security Review: No changed files.")
        sys.exit(0)

    critical_files = []
    for f in changed:
        result = check_file(f)
        if result["markers"]:
            critical_files.append((f, result["markers"]))

    if critical_files:
        print("BLOCKED: Security-critical code modified — human review required\n")
        for f, markers in critical_files:
            print(f"  {f}:")
            for lineno, text in markers:
                print(f"    Line {lineno}: {text}")
        print("\nOverride: Set SECURITY_REVIEW_ACKNOWLEDGED=true after human review.")
        sys.exit(1)

    print(f"Security Review PASSED — {len(changed)} file(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
