#!/usr/bin/env python3
"""Layer 10: Dead Code Gate — reject bare except clauses."""

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["grep", "-rn", "except:", "src/"],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print("FAIL: bare except found (use specific exception types):")
        print(result.stdout)
        return 1
    print("PASS: no bare excepts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
