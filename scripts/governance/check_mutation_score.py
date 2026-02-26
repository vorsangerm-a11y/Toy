#!/usr/bin/env python3
"""
MUTATION TESTING GATE (mutmut)
Policy: 70% mutation score on PR-changed files.
Runs incrementally — only mutates files changed in the current PR.
Amnesty Protocol: legacy files excluded (HITL required to add).

Usage:
    python check_mutation_score.py                          # CI mode
    python check_mutation_score.py --changed-files f.py     # Specific files
    python check_mutation_score.py --threshold 80           # Custom threshold

Prerequisites:
    pip install mutmut
"""

import argparse
import json
import os
import sys
from pathlib import Path
from subprocess import run

# ADAPT: Project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MUTATION_THRESHOLD = 70
AMNESTY_FILE = PROJECT_ROOT / ".memory-layer" / "baselines" / "mutation-amnesty.json"

# ADAPT: Files exempt from mutation testing (by category)
DEFAULT_AMNESTY = {
    "config": ["src/config.py", "src/settings.py"],
    "migrations": ["src/migrations/"],
    "generated": ["src/generated/"],
}


def get_changed_files():
    try:
        base = os.environ.get("GITHUB_BASE_REF", "main")
        result = run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", f"origin/{base}...HEAD"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        return [
            f
            for f in result.stdout.strip().split("\n")
            if f.endswith(".py") and f.startswith("src/") and not f.endswith("__init__.py")
        ]
    except Exception:
        return []


def load_amnesty():
    if AMNESTY_FILE.exists():
        try:
            return json.loads(AMNESTY_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_AMNESTY


def is_exempt(file_path, amnesty):
    for category, patterns in amnesty.items():
        for pattern in patterns:
            if file_path.startswith(pattern) or file_path == pattern:
                return True
    return False


def run_mutmut(files, threshold):
    """Run mutmut on specific files and check score."""
    if not files:
        print("Mutation Testing: No files to test.")
        return 0

    # Run mutmut for each file
    total_mutants, total_killed = 0, 0
    for f in files:
        result = run(
            ["mutmut", "run", "--paths-to-mutate", f, "--no-progress"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        # Parse results
        result_check = run(
            ["mutmut", "results"], capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        output = result_check.stdout
        # Extract killed/survived counts
        for line in output.splitlines():
            if "killed" in line.lower():
                parts = line.split()
                for i, p in enumerate(parts):
                    if p.isdigit():
                        total_killed += int(p)
                        break
            if "survived" in line.lower() or "total" in line.lower():
                parts = line.split()
                for p in parts:
                    if p.isdigit():
                        total_mutants += int(p)
                        break

    if total_mutants == 0:
        print("Mutation Testing: No mutants generated.")
        return 0

    score = (total_killed / total_mutants) * 100
    print(f"Mutation Testing: {score:.1f}% ({total_killed}/{total_mutants} killed)")

    if score < threshold:
        print(f"\nBLOCKED: Mutation score {score:.1f}% below threshold {threshold}%")
        print("Fix: Strengthen tests to detect more mutations.")
        return 1

    print(f"  Mutation Testing PASSED (>= {threshold}%)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Mutation Testing Gate")
    parser.add_argument("--changed-files", nargs="*", default=None)
    parser.add_argument("--threshold", type=int, default=MUTATION_THRESHOLD)
    args = parser.parse_args()

    amnesty = load_amnesty()
    files = args.changed_files or get_changed_files()
    files = [f for f in files if not is_exempt(f, amnesty)]

    if not files:
        print("Mutation Testing: No non-exempt files changed.")
        sys.exit(0)

    print(f"Mutation Testing — {len(files)} file(s), threshold {args.threshold}%")
    sys.exit(run_mutmut(files, args.threshold))


if __name__ == "__main__":
    main()
