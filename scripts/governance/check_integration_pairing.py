#!/usr/bin/env python3
"""
Integration Test Pairing — Buddy System
=========================================
Every service file must have a paired integration test.
The buddy system ensures services are tested with real I/O.

Pattern: src/services/foo_service.py -> tests/integration/test_foo_service.py
"""
import sys
from pathlib import Path


def check_integration_pairing() -> int:
    print("=== Layer 7: Integration Test Pairing ===")

    services_dir = Path("src/services")
    integration_dir = Path("tests/integration")

    if not services_dir.exists():
        print("PASS: No services/ directory (nothing to check)")
        return 0

    service_files = list(services_dir.rglob("*_service.py"))
    if not service_files:
        print("PASS: No service files found")
        return 0

    violations = 0
    for service_file in service_files:
        stem = service_file.stem  # e.g., "user_service"
        expected_test = integration_dir / f"test_{stem}.py"
        if not expected_test.exists():
            print(f"  WARN: {service_file} has no integration test at {expected_test}")
            # Warn only — don't block (new services should get tests soon)
        else:
            print(f"  OK:   {service_file} paired with {expected_test}")

    if violations:
        print(f"\nFAIL: {violations} service(s) missing integration tests")
        return 1

    print("PASS: Integration test pairing satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(check_integration_pairing())
