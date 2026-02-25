#!/usr/bin/env python3
"""
Iron Dome — Type Safety Gate (Ratchet)
=======================================
The Ratchet Rule: Type-safety holes can only DECREASE, never increase.

Type Safety Holes tracked:
  - type: ignore
  - # type: ignore
  - Any (from typing)
  - cast() usage
  - # noqa

Reads baseline from .memory-layer/baselines/type-safety.json
Blocks commit if current count exceeds baseline.
Updates baseline only when count decreases.
"""

import json
import re
import sys
from pathlib import Path

BASELINE_FILE = Path(".memory-layer/baselines/type-safety.json")

HOLE_PATTERNS = [
    (r"#\s*type:\s*ignore", "type: ignore"),
    (r"\bAny\b", "Any usage"),
    (r"\bcast\s*\(", "cast() usage"),
    (r"#\s*noqa", "noqa comment"),
]


def count_holes(src_path: Path = Path("src")) -> dict[str, int]:
    """Count all type safety holes in src/."""
    counts: dict[str, int] = {name: 0 for _, name in HOLE_PATTERNS}
    total = 0

    if not src_path.exists():
        return {"total": 0}

    for py_file in src_path.rglob("*.py"):
        content = py_file.read_text()
        for pattern, name in HOLE_PATTERNS:
            matches = len(re.findall(pattern, content))
            counts[name] += matches
            total += matches

    counts["total"] = total
    return counts


def load_baseline() -> dict[str, int]:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())  # type: ignore[no-any-return]
    return {}


def save_baseline(counts: dict[str, int]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(counts, indent=2))


def check_type_safety() -> int:
    current = count_holes()
    baseline = load_baseline()

    print("=== Layer 8: Type Safety Gate ===")
    print(f"Current holes: {current}")

    if not baseline:
        print("No baseline found — creating baseline now.")
        save_baseline(current)
        print(f"PASS: Baseline set at {current['total']} holes")
        return 0

    current_total = current.get("total", 0)
    baseline_total = baseline.get("total", 0)

    if current_total > baseline_total:
        added = current_total - baseline_total
        print(
            f"FAIL: Type safety holes INCREASED by {added} (baseline: {baseline_total}, current: {current_total})"
        )
        print("  → Remove the new type: ignore / Any / cast() usages")
        return 1

    if current_total < baseline_total:
        reduced = baseline_total - current_total
        print(f"PASS: Type safety improved by {reduced} holes (new baseline: {current_total})")
        save_baseline(current)
    else:
        print(f"PASS: Type safety stable at {current_total} holes")

    return 0


if __name__ == "__main__":
    sys.exit(check_type_safety())
