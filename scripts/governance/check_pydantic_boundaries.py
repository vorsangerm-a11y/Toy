#!/usr/bin/env python3
"""
SCHEMA VALIDATION GATE (Pydantic Boundaries)
Policy: System boundary files must use Pydantic models for validation.
Boundaries: API routes, database queries, external API calls.

Usage:
    python check_pydantic_boundaries.py  # Full scan
"""

import sys
from pathlib import Path

# ADAPT: Project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

# ADAPT: File patterns that indicate system boundaries
BOUNDARY_PATTERNS = [
    "routes/",
    "api/",
    "endpoints/",
    "views/",
    "repositories/",
    "adapters/",
    "clients/",
]
# ADAPT: Patterns that indicate Pydantic validation
PYDANTIC_PATTERNS = ["BaseModel", "pydantic", "Field(", "validator", "model_validate"]


def is_boundary_file(file_path):
    rel = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return any(p in rel for p in BOUNDARY_PATTERNS)


def has_pydantic(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
        return any(p in content for p in PYDANTIC_PATTERNS)
    except (OSError, UnicodeDecodeError):
        return False


def main():
    if not SRC_DIR.exists():
        print("Pydantic Boundaries: No source directory found.")
        sys.exit(0)

    boundary_files = [f for f in SRC_DIR.rglob("*.py") if is_boundary_file(f)]
    if not boundary_files:
        print("Pydantic Boundaries: No boundary files found.")
        sys.exit(0)

    missing = []
    for f in boundary_files:
        if f.name == "__init__.py":
            continue
        if not has_pydantic(f):
            rel = str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")
            missing.append(rel)

    if missing:
        print(f"BLOCKED: {len(missing)} boundary file(s) lack Pydantic validation\n")
        for f in missing:
            print(f"  {f}")
        print("\nFix: Add Pydantic BaseModel for request/response validation.")
        print("     from pydantic import BaseModel")
        sys.exit(1)

    print(f"Pydantic Boundaries PASSED — {len(boundary_files)} boundary file(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
