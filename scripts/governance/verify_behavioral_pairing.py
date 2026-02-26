#!/usr/bin/env python3
"""
BEHAVIORAL TEST PAIRING (Perception Check)
Policy: I/O adapters (database, filesystem, network) must have behavioral tests.
Behavioral tests use REAL I/O, not mocks.

Usage:
    python verify_behavioral_pairing.py                      # Full scan
    python verify_behavioral_pairing.py --changed-files f.py # Incremental
    python verify_behavioral_pairing.py --update-baseline     # Amnesty
"""

import argparse
import ast
import json
import sys
from pathlib import Path

# ADAPT: Project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TEST_DIR = PROJECT_ROOT / "tests"
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "behavioral-pairing.json"

# ADAPT: Filename patterns that indicate I/O adapters
IO_PATTERNS = ["*_repository.py", "*_adapter.py", "*_client.py", "*_store.py"]
# ADAPT: Import modules that indicate I/O operations
IO_MODULES = {
    "psycopg2",
    "sqlalchemy",
    "sqlite3",
    "aiohttp",
    "requests",
    "httpx",
    "boto3",
    "redis",
    "pymongo",
    "supabase",
    "stripe",
    "openai",
}


def is_io_adapter(file_path):
    """Check if file is an I/O adapter by name or imports."""
    reasons = []
    for pat in IO_PATTERNS:
        if file_path.match(pat):
            reasons.append(f"filename matches {pat}")
            break
    try:
        tree = ast.parse(file_path.read_text(), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in IO_MODULES:
                        reasons.append(f"imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in IO_MODULES:
                    reasons.append(f"imports {node.module}")
    except (OSError, SyntaxError):
        pass
    return len(reasons) > 0, reasons


def find_behavioral_tests():
    """Find modules with behavioral/integration test coverage."""
    # ADAPT: Test directory patterns for behavioral tests
    covered = set()
    behavioral_dirs = ["integration", "behavioral", "e2e", "adapters"]
    if not TEST_DIR.exists():
        return covered
    for tf in TEST_DIR.rglob("test_*.py"):
        in_behavioral = any(d in tf.parts for d in behavioral_dirs)
        is_behavioral = any(
            p in tf.name for p in ["_integration", "_e2e", "_behavioral", "_adapter"]
        )
        if in_behavioral or is_behavioral:
            mod = tf.stem[5:] if tf.stem.startswith("test_") else tf.stem
            covered.add(mod)
            for suffix in ["_repository", "_adapter", "_client", "_store"]:
                if mod.endswith(suffix):
                    covered.add(mod[: -len(suffix)])
    return covered


def load_baseline():
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text())


def main():
    parser = argparse.ArgumentParser(description="Behavioral Test Pairing")
    parser.add_argument("--changed-files", nargs="*", default=None)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    baseline = load_baseline()
    adapters = []
    if args.changed_files:
        for p in args.changed_files:
            path = Path(p) if Path(p).is_absolute() else PROJECT_ROOT / p
            if path.exists() and path.suffix == ".py":
                is_adapter, reasons = is_io_adapter(path)
                if is_adapter:
                    adapters.append((path, reasons))
    else:
        if SRC_DIR.exists():
            for f in SRC_DIR.rglob("*.py"):
                if f.name == "__init__.py":
                    continue
                is_adapter, reasons = is_io_adapter(f)
                if is_adapter:
                    adapters.append((f, reasons))

    if not adapters:
        print("Behavioral Pairing: No I/O adapters found.")
        sys.exit(0)

    behavioral = find_behavioral_tests()
    missing = []
    for path, reasons in adapters:
        mod = path.stem
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if mod not in baseline and mod not in behavioral:
            missing.append((rel, mod, reasons))

    if args.update_baseline:
        for _, mod, _ in missing:
            baseline[mod] = True
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
        print(f"Baseline updated: {len(missing)} adapter(s) grandfathered")
        sys.exit(0)

    if missing:
        print(f"Behavioral Pairing FAILED — {len(missing)} adapter(s) without tests")
        for rel, mod, reasons in missing:
            print(f"  {rel}: {', '.join(reasons)}")
        print("\nFix: Create behavioral tests in tests/integration/adapters/")
        print("     Behavioral tests use REAL I/O (not mocks) to verify behavior.")
        sys.exit(1)

    print(f"Behavioral Pairing PASSED — {len(adapters)} adapter(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
