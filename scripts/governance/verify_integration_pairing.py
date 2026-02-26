#!/usr/bin/env python3
"""
INTEGRATION TEST PAIRING (Buddy System)
Policy: Every route/endpoint must have a corresponding integration test.
Uses AST to find route decorators and matches to test function names.

Usage:
    python verify_integration_pairing.py                          # Full scan
    python verify_integration_pairing.py --changed-files route.py # Incremental
    python verify_integration_pairing.py --update-baseline         # Amnesty
"""

import argparse
import ast
import json
import sys
from pathlib import Path

# ADAPT: Project root, routes directory, test directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROUTES_DIR = PROJECT_ROOT / "src" / "routes"  # ADAPT: Flask/FastAPI routes location
TEST_DIR = PROJECT_ROOT / "tests"
BASELINE_PATH = PROJECT_ROOT / ".memory-layer" / "baselines" / "integration-pairing.json"


class RouteVisitor(ast.NodeVisitor):
    """AST visitor to extract route decorators."""

    def __init__(self):
        self.routes = []

    def visit_FunctionDef(self, node):
        for dec in node.decorator_list:
            route = self._extract_route(dec)
            if route:
                path, methods = route
                for m in methods:
                    self.routes.append((path, m.upper(), node.lineno))
        self.generic_visit(node)

    def _extract_route(self, dec):
        if not isinstance(dec, ast.Call):
            return None
        if isinstance(dec.func, ast.Attribute) and dec.func.attr != "route":
            return None
        if not dec.args or not isinstance(dec.args[0], ast.Constant):
            return None
        path = dec.args[0].value
        methods = ["GET"]
        for kw in dec.keywords:
            if kw.arg == "methods" and isinstance(kw.value, ast.List):
                methods = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
        return path, methods


def find_test_functions():
    """Find all test_* function names in test directory."""
    funcs = set()
    if not TEST_DIR.exists():
        return funcs
    for tf in TEST_DIR.rglob("test_*.py"):
        try:
            tree = ast.parse(tf.read_text(), filename=str(tf))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    funcs.add(node.name.lower())
        except (OSError, SyntaxError):
            pass
    return funcs


def route_to_patterns(route_path, method):
    """Generate possible test function names for a route."""
    parts = route_path.strip("/").split("/")
    while parts and parts[0] in ("api", "v1", "v2"):
        parts.pop(0)
    clean = [p[1:-1] if p.startswith("<") and p.endswith(">") else p for p in parts]
    slug = "_".join(clean).lower()
    m = method.lower()
    return [
        f"test_{m}_{slug}",
        f"test_{slug}_{m}",
        f"test_{slug}",
        f"test_{m}_{clean[0]}" if clean else "",
        f"test_{clean[0]}_endpoint" if clean else "",
    ]


def load_baseline():
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text())


def main():
    parser = argparse.ArgumentParser(description="Integration Test Pairing")
    parser.add_argument("--changed-files", nargs="*", default=None)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    baseline = load_baseline()
    route_files = []
    if args.changed_files:
        route_files = [Path(f) for f in args.changed_files if Path(f).exists()]
    elif ROUTES_DIR.exists():
        route_files = list(ROUTES_DIR.glob("*.py"))

    all_routes = []
    for rf in route_files:
        try:
            tree = ast.parse(rf.read_text(), filename=str(rf))
        except (OSError, SyntaxError):
            continue
        visitor = RouteVisitor()
        visitor.visit(tree)
        rel = str(rf.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for path, method, lineno in visitor.routes:
            all_routes.append((path, method, lineno, rel))

    if not all_routes:
        print("Integration Pairing: No routes found.")
        sys.exit(0)

    test_funcs = find_test_functions()
    missing = []
    for path, method, lineno, file in all_routes:
        key = f"{method} {path}"
        if key in baseline:
            continue
        patterns = route_to_patterns(path, method)
        if not any(p in test_funcs for p in patterns if p):
            missing.append((path, method, file, lineno))

    if args.update_baseline:
        for path, method, _, _ in missing:
            baseline[f"{method} {path}"] = True
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
        print(f"Baseline updated: {len(missing)} route(s) grandfathered")
        sys.exit(0)

    if missing:
        print(f"Integration Pairing FAILED — {len(missing)} route(s) without tests")
        for path, method, file, lineno in missing:
            print(f"  {method} {path} ({file}:{lineno})")
        print("\nFix: Create integration test in tests/test_<module>_endpoints.py")
        sys.exit(1)

    print(f"Integration Pairing PASSED — {len(all_routes)} route(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
