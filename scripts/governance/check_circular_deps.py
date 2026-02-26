#!/usr/bin/env python3
"""
CIRCULAR DEPENDENCY DETECTOR
Policy: No circular import cycles in source code.
Uses: import-linter (pip install import-linter) or AST-based fallback.

Usage:
    python check_circular_deps.py       # Full scan
"""

import sys
from pathlib import Path
from subprocess import run

# ADAPT: Project root and source package
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PACKAGE = "src"  # ADAPT: Your Python package name


def check_with_import_linter():
    """Use import-linter if available."""
    result = run(["lint-imports"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("BLOCKED: Circular import dependencies detected\n")
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return 1
    print("Circular Dependency Check PASSED (import-linter)")
    return 0


def check_with_ast_fallback():
    """AST-based fallback for circular import detection."""
    import ast

    src_dir = PROJECT_ROOT / SRC_PACKAGE
    if not src_dir.exists():
        print(f"Circular Dependency Check: {SRC_PACKAGE}/ not found, skipping.")
        return 0

    # Build import graph
    graph = {}
    for py in src_dir.rglob("*.py"):
        mod = str(py.relative_to(PROJECT_ROOT)).replace("/", ".").replace("\\", ".")[:-3]
        imports = set()
        try:
            tree = ast.parse(py.read_text(), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
        except (OSError, SyntaxError):
            pass
        graph[mod] = {i for i in imports if i.startswith(SRC_PACKAGE + ".")}

    # Detect cycles via DFS
    cycles = []
    visited, rec_stack = set(), set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        for dep in graph.get(node, []):
            if dep in rec_stack:
                cycle = path[path.index(dep) :] + [dep]
                cycles.append(cycle)
            elif dep not in visited:
                dfs(dep, path + [dep])
        rec_stack.discard(node)

    for mod in graph:
        if mod not in visited:
            dfs(mod, [mod])

    if cycles:
        print(f"BLOCKED: {len(cycles)} circular import cycle(s) detected\n")
        for cycle in cycles[:5]:
            print(f"  {' -> '.join(cycle)}")
        return 1

    print("Circular Dependency Check PASSED")
    return 0


def main():
    # Try import-linter first, fall back to AST
    try:
        run(["lint-imports", "--version"], capture_output=True, check=True)
        sys.exit(check_with_import_linter())
    except (FileNotFoundError, Exception):
        sys.exit(check_with_ast_fallback())


if __name__ == "__main__":
    main()
