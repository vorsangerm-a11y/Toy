#!/usr/bin/env python3
"""
GOVERNANCE METRICS REPORTER
Generates markdown report with pass/fail thresholds.
For CI: writes GitHub Actions Summary. For local: console output.

Usage:
    python report_metrics.py
"""

import json
import os
import sys
from pathlib import Path

# ADAPT: Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRICS_FILE = PROJECT_ROOT / ".metrics" / "current-metrics.json"

# ADAPT: Thresholds for pass/fail
THRESHOLDS = {
    "type_ignores": {"fail": 50, "description": "type: ignore comments"},
    "any_annotations": {"fail": 30, "description": "Any type annotations"},
    "noqa_comments": {"fail": 20, "description": "noqa suppressions"},
    "test_source_ratio": {"fail_below": 0.5, "description": "Test-to-source ratio"},
}


def main():
    if not METRICS_FILE.exists():
        print("No metrics file found. Run collect_metrics.py first.")
        sys.exit(1)

    metrics = json.loads(METRICS_FILE.read_text())
    lines = ["# Governance Metrics Report\n"]
    failures = []

    lines.append("| Metric | Value | Status |")
    lines.append("|--------|-------|--------|")

    for key, value in metrics.items():
        if key == "timestamp":
            continue
        status = "PASS"
        if key in THRESHOLDS:
            t = THRESHOLDS[key]
            if "fail" in t and value > t["fail"]:
                status = "FAIL"
                failures.append(f"{t['description']}: {value} (max: {t['fail']})")
            elif "fail_below" in t and value < t["fail_below"]:
                status = "FAIL"
                failures.append(f"{t['description']}: {value} (min: {t['fail_below']})")
        lines.append(f"| {key} | {value} | {status} |")

    report = "\n".join(lines)
    print(report)

    # Write GitHub Actions Summary if in CI
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report + "\n")

    if failures:
        print(f"\nBLOCKED: {len(failures)} metric(s) exceed thresholds")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)

    print("\nAll metrics within thresholds")
    sys.exit(0)


if __name__ == "__main__":
    main()
