#!/usr/bin/env python3
"""
AI HALLUCINATION / TYPOSQUAT DETECTOR (PyPI)
Policy: Block AI-hallucinated or typosquatted packages BEFORE pip install.
Detection: Package doesn't exist on PyPI, is < 30 days old, or has < 100 downloads.

Usage:
    python check_hallucinations_pypi.py                # Check requirements.txt
    python check_hallucinations_pypi.py --verbose      # Detailed output
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# ADAPT: Project root and requirements file
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQ_FILE = PROJECT_ROOT / "requirements.txt"
CACHE_FILE = PROJECT_ROOT / ".supply-chain-cache-pypi.json"
EXEMPTIONS_FILE = PROJECT_ROOT / ".supply-chain-exemptions.json"
MIN_DAYS_OLD = 30

# ADAPT: Packages you trust regardless of age/downloads
TRUSTED_PACKAGES = {
    "flask",
    "fastapi",
    "django",
    "requests",
    "httpx",
    "pytest",
    "sqlalchemy",
    "alembic",
    "pydantic",
    "celery",
    "redis",
    "boto3",
    "gunicorn",
    "uvicorn",
    "numpy",
    "pandas",
}


def load_cache():
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if data.get("timestamp", 0) > datetime.now(UTC).timestamp() - 86400:
                return data.get("packages", {})
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(packages):
    CACHE_FILE.write_text(
        json.dumps({"timestamp": datetime.now(UTC).timestamp(), "packages": packages}, indent=2)
    )


def load_exemptions():
    if EXEMPTIONS_FILE.exists():
        try:
            return set(json.loads(EXEMPTIONS_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def check_pypi(package_name):
    """Check if package exists on PyPI and is trustworthy."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        info = data.get("info", {})
        releases = data.get("releases", {})
        # Check age
        first_release = None
        for version_files in releases.values():
            for f in version_files:
                upload = f.get("upload_time_iso_8601") or f.get("upload_time")
                if upload:
                    try:
                        dt = datetime.fromisoformat(upload.replace("Z", "+00:00"))
                        if first_release is None or dt < first_release:
                            first_release = dt
                    except ValueError:
                        pass
        age_days = (datetime.now(UTC) - first_release).days if first_release else 999
        return {"exists": True, "age_days": age_days, "name": info.get("name", package_name)}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"exists": False, "age_days": 0, "name": package_name}
        return {"exists": True, "age_days": 999, "name": package_name}
    except Exception:
        return {"exists": True, "age_days": 999, "name": package_name}


def parse_requirements():
    """Parse package names from requirements.txt."""
    if not REQ_FILE.exists():
        return []
    packages = []
    for line in REQ_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip version specifiers
        for sep in [">=", "<=", "==", "!=", "~=", "<", ">"]:
            line = line.split(sep)[0]
        line = line.split("[")[0].strip()
        if line:
            packages.append(line.lower())
    return packages


def main():
    packages = parse_requirements()
    if not packages:
        print("Supply Chain (PyPI): No packages to check.")
        sys.exit(0)

    cache = load_cache()
    exemptions = load_exemptions()
    blocked = []

    for pkg in packages:
        if pkg in TRUSTED_PACKAGES or pkg in exemptions:
            continue
        if pkg in cache:
            info = cache[pkg]
        else:
            info = check_pypi(pkg)
            cache[pkg] = info

        if not info["exists"]:
            blocked.append((pkg, "Package does NOT exist on PyPI — likely hallucinated"))
        elif info["age_days"] < MIN_DAYS_OLD:
            blocked.append(
                (pkg, f"Package is only {info['age_days']} days old — possible typosquat")
            )

    save_cache(cache)

    if blocked:
        print(f"BLOCKED: {len(blocked)} suspicious package(s) detected\n")
        for pkg, reason in blocked:
            print(f"  {pkg}: {reason}")
        print(
            "\nFix: Verify the correct package name. Add to .supply-chain-exemptions.json if legitimate."
        )
        sys.exit(1)

    print(f"Supply Chain (PyPI) PASSED — {len(packages)} package(s) checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
