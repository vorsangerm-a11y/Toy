#!/usr/bin/env python3
"""
COVERAGE FORTRESS (Per-File Ratchet)
Policy: Per-file coverage cannot regress beyond tolerance. New files need 80% floor.
Reason: AI coders write code without adequate test coverage, causing silent regressions.

Thresholds:
    Global minimum:       70% (entire project)
    New file floor:       80% (files not in baseline)
    Regression tolerance: 0.2% (existing files cannot drop more than this)

Reads: coverage.json from coverage.py (--json output)

Usage:
    python check_per_file_baseline.py                    # CI mode
    python check_per_file_baseline.py --init             # Initialize baseline
    python check_per_file_baseline.py --global-min 75    # Custom global threshold
    python check_per_file_baseline.py --new-floor 85     # Custom new-file threshold

Prerequisites:
    pip install coverage
    coverage run -m pytest && coverage json
"""

import json
import sys
from pathlib import Path

# ADAPT: Project root and coverage paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_JSON = PROJECT_ROOT / "coverage.json"
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "coverage-baseline.json"

# ADAPT: Thresholds
DEFAULT_GLOBAL_MIN = 70
DEFAULT_NEW_FLOOR = 80
REGRESSION_TOLERANCE = 0.2

# ADAPT: Files excluded from per-file checking
EXCLUDE_PATTERNS = [
    r"__init__\.py$",
    r"conftest\.py$",
    r"setup\.py$",
    r"test_",
    r"_test\.py$",
    r"tests/",
    r"test/",
    r"migrations/",
    r"alembic/",
    r"\.venv/",
    r"venv/",
]


def parse_args():
    args = sys.argv[1:]
    config = {
        "init": "--init" in args,
        "global_min": DEFAULT_GLOBAL_MIN,
        "new_floor": DEFAULT_NEW_FLOOR,
        "tolerance": REGRESSION_TOLERANCE,
    }
    if "--global-min" in args:
        idx = args.index("--global-min")
        config["global_min"] = float(args[idx + 1])
    if "--new-floor" in args:
        idx = args.index("--new-floor")
        config["new_floor"] = float(args[idx + 1])
    return config


def load_coverage():
    """Load coverage.json (coverage.py format)."""
    if not COVERAGE_JSON.exists():
        print(f"Coverage data not found: {COVERAGE_JSON}", file=sys.stderr)
        print("Run your test suite with coverage first:", file=sys.stderr)
        print("  coverage run -m pytest && coverage json", file=sys.stderr)
        print("  OR: pytest --cov --cov-report=json", file=sys.stderr)
        sys.exit(1)
    return json.loads(COVERAGE_JSON.read_text())


def load_baseline():
    try:
        if BASELINE_PATH.exists():
            return json.loads(BASELINE_PATH.read_text())
        return None
    except Exception:
        return None


def save_baseline(data):
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2))


def is_excluded(filepath: str) -> bool:
    import re

    return any(re.search(p, filepath) for p in EXCLUDE_PATTERNS)


def get_file_coverage(cov_data):
    """Extract per-file line coverage from coverage.json."""
    file_coverages = {}
    files = cov_data.get("files", {})
    for filepath, data in files.items():
        rel = (
            str(Path(filepath).relative_to(PROJECT_ROOT))
            if Path(filepath).is_absolute()
            else filepath
        )
        if is_excluded(rel):
            continue
        summary = data.get("summary", {})
        pct = summary.get("percent_covered", 0)
        file_coverages[rel] = round(pct, 2)
    return file_coverages


# --- Main ---
config = parse_args()
cov_data = load_coverage()

# Extract global coverage
totals = cov_data.get("totals", {})
global_coverage = round(totals.get("percent_covered", 0), 2)

# Extract per-file coverage
file_coverages = get_file_coverage(cov_data)

if config["init"]:
    save_baseline(
        {
            "global_coverage": global_coverage,
            "files": file_coverages,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    print(f"Coverage Baseline initialized: {len(file_coverages)} files tracked")
    print(f"  Global: {global_coverage}%")
    sys.exit(0)

baseline = load_baseline()
violations = []

print(f"Coverage Fortress: Global {global_coverage}% (min: {config['global_min']}%)\n")

# CHECK 1: Global minimum
if global_coverage < config["global_min"]:
    violations.append(
        {
            "type": "global",
            "message": f"Global coverage {global_coverage}% below minimum {config['global_min']}%",
        }
    )

# CHECK 2: Per-file regressions
if baseline and baseline.get("files"):
    regressions = 0
    new_files = 0

    for filepath, current_pct in file_coverages.items():
        baseline_pct = baseline["files"].get(filepath)

        if baseline_pct is None:
            # New file — must meet floor
            new_files += 1
            if current_pct < config["new_floor"]:
                violations.append(
                    {
                        "type": "new-file",
                        "message": f"{filepath}: {current_pct}% (new file floor: {config['new_floor']}%)",
                    }
                )
        else:
            # Existing file — check for regression
            drop = baseline_pct - current_pct
            if drop > config["tolerance"]:
                regressions += 1
                violations.append(
                    {
                        "type": "regression",
                        "message": f"{filepath}: {current_pct}% (was {baseline_pct}%, dropped {drop:.1f}%, "
                        f"tolerance: {config['tolerance']}%)",
                    }
                )

    print(f"  Files tracked: {len(file_coverages)}")
    print(f"  New files:     {new_files}")
    print(f"  Regressions:   {regressions}")
else:
    print("  No baseline found. Run with --init to create one.")
    print("  Checking global minimum only.\n")

if not violations:
    # Ratchet: update baseline if coverage improved
    if baseline and baseline.get("files"):
        improved = False
        new_baseline = dict(baseline)
        new_baseline["files"] = dict(baseline["files"])

        for filepath, current_pct in file_coverages.items():
            baseline_pct = new_baseline["files"].get(filepath)
            if baseline_pct is None or current_pct > baseline_pct:
                new_baseline["files"][filepath] = current_pct
                improved = True

        if improved:
            new_baseline["global_coverage"] = global_coverage
            new_baseline["timestamp"] = __import__("datetime").datetime.now().isoformat()
            save_baseline(new_baseline)
            print("\n  Baseline improved (ratcheted up)")

    print("\nCoverage Fortress: PASSED")
    sys.exit(0)

print(f"\nBLOCKED: {len(violations)} coverage violation(s)\n", file=sys.stderr)
for v in violations:
    print(f"  [{v['type']}] {v['message']}", file=sys.stderr)
print("\nFix: Add tests to cover the regressed or under-covered files.", file=sys.stderr)
print(f"New files must have >= {config['new_floor']}% coverage.", file=sys.stderr)
print(f"Existing files cannot drop more than {config['tolerance']}%.\n", file=sys.stderr)
sys.exit(1)
