#!/usr/bin/env python3
"""
CODE HEALTH GATE (Orphan Detection)
Policy: Block unreferenced source files and dead exports.
Reason: AI coders create files that nothing imports, inflating the codebase.

Detection:
    - Orphan files: Source files not imported by any other file
    - Dead exports: __all__ members never imported elsewhere

Amnesty Protocol: Legacy orphans grandfathered at baseline.
Only NEW orphans (above baseline) are blocked.

Usage:
    python code_health_check.py           # Full scan (CI mode)
    python code_health_check.py --init    # Initialize amnesty baseline
    python code_health_check.py --verbose # Show all orphans (including amnestied)
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

# ADAPT: Point to your project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "code-health-baseline.json"

EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".tox",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
}

# ADAPT: Files that are legitimate entry points (not imported by anything)
ENTRY_POINT_PATTERNS = [
    r"__init__\.py$",
    r"__main__\.py$",
    r"manage\.py$",
    r"wsgi\.py$",
    r"asgi\.py$",
    r"conftest\.py$",
    r"setup\.py$",
    r"cli\.py$",
    r"app\.py$",
    r"main\.py$",
    r"test_.*\.py$",
    r".*_test\.py$",
    r"tests/",
    r"test/",
    r"migrations/",
    r"alembic/",
]


def get_all_files(src_dir: Path):
    """Recursively find Python source files."""
    files = []
    if not src_dir.exists():
        return files
    for root, dirs, filenames in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py") and not f.startswith("."):
                files.append(Path(root) / f)
    return files


def is_entry_point(filepath: str) -> bool:
    return any(re.search(p, filepath) for p in ENTRY_POINT_PATTERNS)


def build_import_graph(files):
    """Build import graph: track which modules are imported by any file."""
    imported_modules = set()

    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
                    # Also track sub-modules
                    parts = node.module.split(".")
                    for i in range(1, len(parts)):
                        imported_modules.add(".".join(parts[:i]))

    return imported_modules


def file_to_module(filepath: Path, src_dir: Path) -> str:
    """Convert file path to Python module path."""
    try:
        rel = filepath.relative_to(src_dir)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")
        return ".".join(parts)
    except ValueError:
        return ""


def find_dead_exports(files):
    """Find __all__ members that are never imported by other files."""
    all_exports = {}  # module -> list of exported names
    imported_names = set()
    dead_exports = []

    # Collect __all__ exports
    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel = str(filepath.relative_to(PROJECT_ROOT))

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            names = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    names.append(elt.value)
                            all_exports[rel] = names

    # Collect all imported names
    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        imported_names.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    imported_names.add(parts[-1])

    # Find dead exports
    for filepath, exports in all_exports.items():
        for name in exports:
            if name not in imported_names:
                dead_exports.append({"symbol": name, "file": filepath})

    return dead_exports


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


# --- Main ---
init_mode = "--init" in sys.argv
verbose = "--verbose" in sys.argv

all_files = get_all_files(SRC_DIR)
if not all_files:
    print("Code Health Check: No source files found.")
    sys.exit(0)

# Build import graph
imported_modules = build_import_graph(all_files)

# Find orphan files
orphan_files = []
for filepath in all_files:
    rel = str(filepath.relative_to(PROJECT_ROOT))
    if is_entry_point(rel):
        continue
    module = file_to_module(filepath, SRC_DIR)
    if module and module not in imported_modules:
        # Double-check: also check if any partial module path matches
        parts = module.split(".")
        is_imported = False
        for i in range(len(parts)):
            partial = ".".join(parts[: i + 1])
            if partial in imported_modules:
                is_imported = True
                break
        if not is_imported:
            orphan_files.append(rel)

# Find dead exports
dead_exports = find_dead_exports(all_files)

total_violations = len(orphan_files) + len(dead_exports)

if init_mode:
    save_baseline(
        {
            "orphan_files": len(orphan_files),
            "dead_exports": len(dead_exports),
            "total": total_violations,
            "orphan_list": orphan_files,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    print(
        f"Code Health Baseline initialized: {total_violations} violations "
        f"({len(orphan_files)} orphan files, {len(dead_exports)} dead exports)"
    )
    sys.exit(0)

baseline = load_baseline()
baseline_total = baseline["total"] if baseline else 0

print(f"Code Health Check: {len(all_files)} files scanned")
print(f"  Orphan files:  {len(orphan_files)}")
print(f"  Dead exports:  {len(dead_exports)}")
print(f"  Total: {total_violations} | Baseline: {baseline_total}\n")

if verbose:
    if orphan_files:
        print("Orphan files:")
        for f in orphan_files:
            print(f"  - {f}")
    if dead_exports:
        print("Dead exports:")
        for d in dead_exports[:20]:
            print(f"  - {d['symbol']} in {d['file']}")
        if len(dead_exports) > 20:
            print(f"  ... and {len(dead_exports) - 20} more")
    print()

if total_violations > baseline_total:
    new_count = total_violations - baseline_total
    print(
        f"BLOCKED: {new_count} NEW code health violation(s) above baseline "
        f"({baseline_total} -> {total_violations})\n",
        file=sys.stderr,
    )

    baseline_orphans = set(baseline.get("orphan_list", []) if baseline else [])
    new_orphans = [f for f in orphan_files if f not in baseline_orphans]
    if new_orphans:
        print("New orphan files:", file=sys.stderr)
        for f in new_orphans:
            print(f"  {f}", file=sys.stderr)

    print("\nFix: Delete unused files, or import them from an appropriate module.", file=sys.stderr)
    print("Baseline can only go DOWN, never UP.\n", file=sys.stderr)
    sys.exit(1)

if total_violations < baseline_total:
    save_baseline(
        {
            "orphan_files": len(orphan_files),
            "dead_exports": len(dead_exports),
            "total": total_violations,
            "orphan_list": orphan_files,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
    )
    print(f"Baseline improved: {baseline_total} -> {total_violations} (ratcheted down)")

print("Code Health Check: PASSED")
sys.exit(0)
