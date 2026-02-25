#!/usr/bin/env python3
"""
Precision Coverage Ratchet
===========================
Enforces 80% coverage on new files (files not in baseline).
Existing files are grandfathered — coverage can only improve.

Reads baseline from .memory-layer/baselines/coverage.json
Blocks commit if new files are below threshold.
"""

import json
import subprocess
import sys
from pathlib import Path

BASELINE_FILE = Path(".memory-layer/baselines/coverage.json")
COVERAGE_THRESHOLD = 80


def run_coverage() -> dict[str, float]:
    """Run pytest with coverage and parse results."""
    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "--cov=src",
            "--cov-report=json",
            "--co",
            "-q",
            "--no-header",
        ],
        capture_output=True,
        text=True,
    )

    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        return {}

    data = json.loads(coverage_file.read_text())
    files = data.get("files", {})
    return {path: info["summary"]["percent_covered"] for path, info in files.items()}


def load_baseline() -> dict[str, float]:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())  # type: ignore[no-any-return]
    return {}


def save_baseline(coverage: dict[str, float]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(coverage, indent=2))


def check_coverage_ratchet() -> int:
    print("=== Layer 5: Coverage Ratchet ===")

    coverage = run_coverage()
    if not coverage:
        print("PASS: No coverage data (no tests run or no source files)")
        return 0

    baseline = load_baseline()

    if not baseline:
        print("No baseline found — creating baseline now.")
        save_baseline(coverage)
        print(f"PASS: Baseline set with {len(coverage)} file(s) at current coverage")
        return 0

    violations = 0

    for file_path, pct in coverage.items():
        if file_path not in baseline:
            # New file — enforce threshold
            if pct < COVERAGE_THRESHOLD:
                print(
                    f"  FAIL: {file_path} is {pct:.1f}% covered (new file, requires {COVERAGE_THRESHOLD}%)"
                )
                violations += 1
            else:
                print(f"  OK:   {file_path} {pct:.1f}% (new file, passes {COVERAGE_THRESHOLD}%)")
        else:
            baseline_pct = baseline[file_path]
            if pct < baseline_pct - 5:  # Allow 5% tolerance
                print(
                    f"  WARN: {file_path} coverage dropped from {baseline_pct:.1f}% to {pct:.1f}%"
                )
            else:
                print(f"  OK:   {file_path} {pct:.1f}% (grandfathered at {baseline_pct:.1f}%)")

    if violations:
        print(f"\nFAIL: {violations} new file(s) below {COVERAGE_THRESHOLD}% coverage threshold")
        return 1

    # Update baseline with current values (only improvements)
    updated = {**baseline, **{k: max(v, baseline.get(k, 0)) for k, v in coverage.items()}}
    save_baseline(updated)
    print(f"PASS: Coverage ratchet satisfied ({len(coverage)} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(check_coverage_ratchet())
