#!/usr/bin/env python3
"""
Pre-submission checklist: verify all requirements are met for hackathon submission.

Usage:
    uv run python scripts/submission_check.py
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

# Resolve project root (two levels up from this script)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


def _run(cmd: list[str], cwd: str | Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or PROJECT_ROOT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_db() -> tuple[bool, str]:
    """Check PostgreSQL is running and reachable on port 5433."""
    try:
        sock = socket.create_connection(("localhost", 5433), timeout=5)
        sock.close()
        return True, "PostgreSQL reachable on localhost:5433"
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        return False, f"Cannot connect to PostgreSQL on 5433: {e}"


def check_backend() -> tuple[bool, str]:
    """Check that the backend module can be imported (basic sanity)."""
    rc, out, err = _run(
        ["uv", "run", "python", "-c", "import trustdesk; print('OK')"],
        cwd=BACKEND_DIR,
    )
    if rc == 0 and "OK" in out:
        return True, "Backend module imports successfully"
    return False, f"Backend import failed: {err.strip()[:200]}"


def check_dashboard_build() -> tuple[bool, str]:
    """Check that the dashboard builds without errors."""
    dashboard_dir = PROJECT_ROOT / "dashboard"
    if not (dashboard_dir / "package.json").exists():
        return False, "dashboard/package.json not found"
    rc, out, err = _run(["npm", "run", "build"], cwd=dashboard_dir, timeout=120)
    if rc == 0:
        dist = dashboard_dir / "dist"
        if dist.exists():
            return True, f"Dashboard builds successfully ({len(list(dist.rglob('*')))} files)"
        return True, "Dashboard build completed (dist dir not checked)"
    return False, f"Dashboard build failed: {err.strip()[:200]}"


def check_contracts() -> tuple[bool, str]:
    """Check that Foundry contracts compile."""
    contracts_dir = PROJECT_ROOT / "contracts"
    if not contracts_dir.exists():
        return False, "contracts/ directory not found"
    rc, out, err = _run(["forge", "build"], cwd=contracts_dir, timeout=120)
    if rc == 0:
        return True, "Contracts compile with forge build"
    return False, f"Contracts failed to compile: {err.strip()[:200]}"


def check_tests() -> tuple[bool, str]:
    """Check that backend tests pass and there are 562+ tests."""
    rc, out, err = _run(
        ["uv", "run", "pytest", "--tb=no", "-q"],
        cwd=BACKEND_DIR,
        timeout=300,
    )
    match = re.search(r"(\d+) passed", out + err)
    if match:
        count = int(match.group(1))
        if rc == 0 and count >= 562:
            return True, f"{count} tests passed"
        elif rc == 0:
            return False, f"Only {count} tests passed (need 562+)"
        else:
            fail_match = re.search(r"(\d+) failed", out + err)
            fail_count = int(fail_match.group(1)) if fail_match else "?"
            return False, f"{count} passed, {fail_count} failed"
    return False, f"Could not parse test output: {(out + err).strip()[:200]}"


def check_coverage() -> tuple[bool, str]:
    """Check test coverage is at 100%."""
    rc, out, err = _run(
        ["uv", "run", "pytest", "--cov=trustdesk", "--cov-report=term-missing", "--tb=no", "-q"],
        cwd=BACKEND_DIR,
        timeout=300,
    )
    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", out + err)
    if match:
        coverage = int(match.group(1))
        if coverage == 100:
            return True, "100% test coverage"
        return False, f"Coverage is {coverage}% (need 100%)"
    return False, f"Could not parse coverage output: {(out + err).strip()[:200]}"


def check_kraken() -> tuple[bool, str]:
    """Check that Kraken CLI is installed."""
    rc, out, err = _run(["kraken", "--version"])
    if rc == 0:
        version = out.strip() or err.strip()
        return True, f"Kraken CLI installed: {version[:80]}"
    return False, "Kraken CLI not found (install: pip install kraken-cli or similar)"


def check_identity() -> tuple[bool, str]:
    """Check that on-chain identity is registered (contract address set in env)."""
    addr = os.environ.get("VALIDATOR_CONTRACT_ADDRESS", "")
    if addr and addr.startswith("0x") and len(addr) == 42:
        return True, f"Validator contract: {addr}"
    return False, "VALIDATOR_CONTRACT_ADDRESS not set or invalid in environment"


def check_env() -> tuple[bool, str]:
    """Check that .env has all required keys."""
    env_file = BACKEND_DIR / ".env"

    if not env_file.exists():
        # Also check project root
        env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return False, ".env file not found in backend/ or project root"

    env_lines = env_file.read_text().splitlines()
    env_keys = set()
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            env_keys.add(key)

    required_keys = [
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
    ]
    missing = [k for k in required_keys if k not in env_keys]
    if missing:
        return False, f"Missing env vars: {', '.join(missing)}"
    return True, f".env has {len(env_keys)} keys, all required keys present"


def check_github() -> tuple[bool, str]:
    """Check that git remote is set and repo is accessible."""
    rc, out, err = _run(["git", "remote", "get-url", "origin"])
    if rc != 0:
        return False, "No git remote 'origin' configured"
    url = out.strip()
    if "sneg55/TrustDesk" not in url:
        return False, f"Unexpected remote: {url}"
    return True, f"GitHub remote: {url}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS: list[tuple[str, object]] = [
    ("PostgreSQL running", check_db),
    ("Backend starts", check_backend),
    ("Dashboard builds", check_dashboard_build),
    ("Contracts compile", check_contracts),
    ("Tests pass (562+)", check_tests),
    ("Coverage 100%", check_coverage),
    ("Kraken CLI installed", check_kraken),
    ("On-chain identity registered", check_identity),
    (".env complete", check_env),
    ("GitHub repo accessible", check_github),
]


def main() -> None:
    print("=" * 60)
    print("  TrustDesk Pre-Submission Checklist")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    results: list[tuple[str, bool, str]] = []

    for name, check_fn in CHECKS:
        print(f"  Checking: {name}...", end=" ", flush=True)
        try:
            ok, detail = check_fn()  # type: ignore[operator]
        except Exception as e:
            ok, detail = False, f"Exception: {e}"
        results.append((name, ok, detail))
        if ok:
            print("OK")
            passed += 1
        else:
            print("FAIL")
            failed += 1

    print()
    print("-" * 60)
    print("  RESULTS")
    print("-" * 60)
    for name, ok, detail in results:
        icon = "[+]" if ok else "[-]"
        status = "PASS" if ok else "FAIL"
        print(f"  {icon} {status}: {name}")
        print(f"         {detail}")
    print()
    print(f"  TOTAL: {passed} passed, {failed} failed out of {len(CHECKS)}")
    print()

    if failed == 0:
        print("  >>> ALL CHECKS PASSED -- Ready for submission! <<<")
    else:
        print(f"  >>> {failed} CHECK(S) FAILED -- Fix before submitting. <<<")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
