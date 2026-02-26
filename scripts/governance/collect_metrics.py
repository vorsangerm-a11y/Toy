#!/usr/bin/env python3
"""
GOVERNANCE METRICS COLLECTOR
Collects governance health metrics for reporting.
Output: .metrics/current-metrics.json

Usage:
    python collect_metrics.py
"""

import json
import sys
from datetime import UTC
from pathlib import Path

# ADAPT: Project root and source/test directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TEST_DIR = PROJECT_ROOT / "tests"
METRICS_DIR = PROJECT_ROOT / ".metrics"


def count_lines(directory, ext=".py"):
    total = 0
    if directory.exists():
        for f in directory.rglob(f"*{ext}"):
            try:
                total += len([l for l in f.read_text().splitlines() if l.strip()])
            except (OSError, UnicodeDecodeError):
                pass
    return total


def count_pattern(directory, pattern, ext=".py"):
    count = 0
    if directory.exists():
        for f in directory.rglob(f"*{ext}"):
            try:
                count += f.read_text().count(pattern)
            except (OSError, UnicodeDecodeError):
                pass
    return count


def main():
    from datetime import datetime

    metrics = {
        "timestamp": datetime.now(UTC).isoformat(),
        "source_loc": count_lines(SRC_DIR),
        "test_loc": count_lines(TEST_DIR),
        "type_ignores": count_pattern(SRC_DIR, "# type: ignore"),
        "any_annotations": count_pattern(SRC_DIR, ": Any"),
        "noqa_comments": count_pattern(SRC_DIR, "# noqa"),
        "pylint_disables": count_pattern(SRC_DIR, "# pylint: disable"),
        "file_count": len(list(SRC_DIR.rglob("*.py"))) if SRC_DIR.exists() else 0,
    }

    # Test-to-source ratio
    if metrics["source_loc"] > 0:
        metrics["test_source_ratio"] = round(metrics["test_loc"] / metrics["source_loc"], 2)
    else:
        metrics["test_source_ratio"] = 0

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    output = METRICS_DIR / "current-metrics.json"
    output.write_text(json.dumps(metrics, indent=2) + "\n")

    # Append to history (rolling 50 entries)
    history_file = METRICS_DIR / "metrics-history.json"
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    history.append(metrics)
    if len(history) > 50:
        history = history[-50:]
    history_file.write_text(json.dumps(history, indent=2) + "\n")

    print(f"Metrics collected: {output}")
    for k, v in metrics.items():
        if k != "timestamp":
            print(f"  {k}: {v}")
    sys.exit(0)


if __name__ == "__main__":
    main()
