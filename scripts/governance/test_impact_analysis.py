#!/usr/bin/env python3
"""
TEST IMPACT ANALYSIS (TIA)
Local: Run only tests affected by changed files (pytest-testmon).
CI: Safety Latch — always run ALL tests.

Usage:
    python test_impact_analysis.py          # Auto-detect CI vs local
    python test_impact_analysis.py --local  # Force local mode
    python test_impact_analysis.py --ci     # Force CI mode

Prerequisites (local only):
    pip install pytest-testmon
"""

import os
import sys
from subprocess import run


def main():
    is_ci = os.environ.get("CI") == "true"

    if is_ci or "--ci" in sys.argv:
        # CI Safety Latch: run ALL tests
        print("Test Impact Analysis: CI mode — running ALL tests")
        result = run(["pytest", "--tb=short", "-q"], cwd=os.getcwd())
        sys.exit(result.returncode)
    else:
        # Local: run only affected tests via testmon
        print("Test Impact Analysis: Local mode — running affected tests only")
        result = run(["pytest", "--testmon", "--tb=short", "-q"], cwd=os.getcwd())
        if result.returncode != 0:
            # Fallback to full suite if testmon fails
            print("  testmon failed, falling back to full suite")
            result = run(["pytest", "--tb=short", "-q"], cwd=os.getcwd())
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
