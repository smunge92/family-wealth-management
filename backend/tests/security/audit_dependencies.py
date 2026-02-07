"""
Dependency Vulnerability Scanner
Scans Python (pip-audit) and Node.js (npm audit) dependencies for known CVEs.

Usage:
    python tests/security/audit_dependencies.py

Returns exit code 1 if critical/high vulnerabilities are found (for CI/CD integration).
"""

import subprocess
import sys
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def run_pip_audit() -> tuple[bool, str]:
    """
    Run pip-audit on Python dependencies.
    Returns (passed, output).
    """
    print("=" * 60)
    print("  Python Dependency Audit (pip-audit)")
    print("=" * 60)

    # Check if pip-audit is installed
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--version"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("pip-audit not installed. Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pip-audit"],
            capture_output=True, timeout=120
        )

    # Run pip-audit against requirements.txt
    req_file = BACKEND_DIR / "requirements.txt"
    if not req_file.exists():
        print("[SKIP] requirements.txt not found")
        return True, "Skipped - no requirements.txt"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", str(req_file), "--desc"],
            capture_output=True, text=True, timeout=300,
            cwd=str(BACKEND_DIR)
        )

        output = result.stdout + result.stderr
        print(output)

        if result.returncode == 0:
            print("\n[PASS] No known vulnerabilities in Python dependencies")
            return True, output
        else:
            print("\n[FAIL] Vulnerabilities found in Python dependencies")
            return False, output

    except subprocess.TimeoutExpired:
        msg = "[ERROR] pip-audit timed out after 5 minutes"
        print(msg)
        return False, msg
    except Exception as e:
        msg = f"[ERROR] pip-audit failed: {str(e)}"
        print(msg)
        return False, msg


def run_npm_audit() -> tuple[bool, str]:
    """
    Run npm audit on Node.js dependencies.
    Returns (passed, output).
    """
    print("\n" + "=" * 60)
    print("  Node.js Dependency Audit (npm audit)")
    print("=" * 60)

    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        print("[SKIP] package.json not found")
        return True, "Skipped - no package.json"

    # Check if node_modules exists
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("node_modules not found. Run 'npm install' first.")
        return True, "Skipped - no node_modules"

    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True, text=True, timeout=120,
            cwd=str(FRONTEND_DIR),
            shell=True
        )

        # Parse JSON output for summary
        import json
        try:
            audit_data = json.loads(result.stdout)
            vulnerabilities = audit_data.get("metadata", {}).get("vulnerabilities", {})
            critical = vulnerabilities.get("critical", 0)
            high = vulnerabilities.get("high", 0)
            moderate = vulnerabilities.get("moderate", 0)
            low = vulnerabilities.get("low", 0)
            total = vulnerabilities.get("total", 0)

            print(f"  Critical: {critical}")
            print(f"  High:     {high}")
            print(f"  Moderate: {moderate}")
            print(f"  Low:      {low}")
            print(f"  Total:    {total}")

            has_critical = critical > 0 or high > 0
            if has_critical:
                print(f"\n[FAIL] {critical} critical, {high} high vulnerabilities found")

                # Show details for critical/high
                advisories = audit_data.get("advisories", audit_data.get("vulnerabilities", {}))
                for name, info in advisories.items():
                    severity = info.get("severity", "")
                    if severity in ("critical", "high"):
                        title = info.get("title", info.get("name", name))
                        via = info.get("via", [])
                        print(f"  - {name}: {title} ({severity})")
            else:
                print(f"\n[PASS] No critical/high vulnerabilities ({moderate} moderate, {low} low)")

            summary = f"critical={critical}, high={high}, moderate={moderate}, low={low}"
            return not has_critical, summary

        except json.JSONDecodeError:
            # Fallback to plain text output
            print(result.stdout[:2000] if result.stdout else result.stderr[:2000])
            passed = result.returncode == 0
            if passed:
                print("\n[PASS] No vulnerabilities found")
            else:
                print("\n[WARN] npm audit reported issues (see above)")
            return passed, result.stdout[:500]

    except subprocess.TimeoutExpired:
        msg = "[ERROR] npm audit timed out after 2 minutes"
        print(msg)
        return False, msg
    except Exception as e:
        msg = f"[ERROR] npm audit failed: {str(e)}"
        print(msg)
        return False, msg


def main():
    print("Dependency Vulnerability Scanner")
    print(f"Project: {PROJECT_ROOT}\n")

    pip_passed, pip_output = run_pip_audit()
    npm_passed, npm_output = run_npm_audit()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Python (pip-audit): {'PASS' if pip_passed else 'FAIL'}")
    print(f"  Node.js (npm audit): {'PASS' if npm_passed else 'FAIL'}")

    all_passed = pip_passed and npm_passed
    print(f"\n  Overall: {'PASS' if all_passed else 'FAIL - fix critical/high vulnerabilities'}")
    print("=" * 60)

    # Exit with non-zero code if vulnerabilities found (for CI/CD)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
