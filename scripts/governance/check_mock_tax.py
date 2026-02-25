#!/usr/bin/env python3
"""
Rising Tide — Mock Tax Checker (2x Rule)
=========================================
The 2x Rule: If a unit test file is more than 2x the size of its source file,
delete the unit test and write an integration test instead.

Test:Source Ratio    Interpretation        Action
< 1.0x               Under-tested          Add more test cases
1.0x - 2.0x          Healthy               Maintain
2.0x - 3.0x          Mock Tax Warning      Consider integration test
> 3.0x               Excessive             Delete, rewrite as integration test

Also scans for adversarial mocking patterns (--scan-only mode).
"""
import argparse
import ast
import sys
from pathlib import Path


MOCK_PATTERNS = [
    "mock.patch",
    "patch(",
    "MagicMock(",
    "Mock(",
    "mocker.patch",
    "monkeypatch.setattr",
]

ADVERSARIAL_PATTERNS = [
    "mock.patch.object",
    "patch.object(",
]


def count_lines(path: Path) -> int:
    """Count non-empty, non-comment lines."""
    try:
        lines = path.read_text().splitlines()
        return sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
    except Exception:
        return 0


def count_mock_calls(path: Path) -> int:
    """Count mock usage in a test file."""
    content = path.read_text()
    return sum(content.count(pattern) for pattern in MOCK_PATTERNS)


def find_source_file(test_file: Path) -> Path | None:
    """Find the source file corresponding to a test file."""
    # test_foo.py -> src/foo.py or src/**/foo.py
    stem = test_file.stem.removeprefix("test_").removesuffix("_test")
    candidates = list(Path("src").rglob(f"{stem}.py")) if Path("src").exists() else []
    return candidates[0] if candidates else None


def check_mock_tax(scan_only: bool = False) -> int:
    """
    Returns 0 if all checks pass, 1 if violations found.
    """
    violations = 0
    test_files = list(Path("tests/unit").rglob("test_*.py")) if Path("tests/unit").exists() else []

    if not test_files:
        print("PASS: No unit test files found (nothing to check)")
        return 0

    if scan_only:
        print("=== Layer 4: Adversarial Mock Scan ===")
        for test_file in test_files:
            content = test_file.read_text()
            for pattern in ADVERSARIAL_PATTERNS:
                if pattern in content:
                    print(f"  WARNING: {test_file} uses adversarial mock pattern: {pattern}")
                    # Warn only, don't fail
        print("PASS: Adversarial mock scan complete")
        return 0

    print("=== Layer 2: Rising Tide (Mock Tax — 2x Rule) ===")
    for test_file in test_files:
        source_file = find_source_file(test_file)
        if not source_file:
            continue  # Can't compare without source file

        test_loc = count_lines(test_file)
        src_loc = count_lines(source_file)

        if src_loc == 0:
            continue

        ratio = test_loc / src_loc

        if ratio > 3.0:
            print(f"  FAIL: {test_file} is {ratio:.1f}x its source ({test_file} has {test_loc} LOC, {source_file} has {src_loc} LOC)")
            print(f"        → Delete unit test and write integration test instead")
            violations += 1
        elif ratio > 2.0:
            print(f"  WARN: {test_file} is {ratio:.1f}x its source — consider integration test")
        else:
            print(f"  OK:   {test_file} ratio {ratio:.1f}x (healthy)")

    if violations:
        print(f"\nFAIL: {violations} Mock Tax violation(s) found")
        return 1

    print("PASS: All unit tests within 2x Mock Tax limit")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-only", action="store_true", help="Only scan for adversarial patterns")
    args = parser.parse_args()
    sys.exit(check_mock_tax(scan_only=args.scan_only))
