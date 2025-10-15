#!/usr/bin/env python3
"""
run_tests.py - Test runner for orgphoto application

Runs both unit tests and integration tests with proper setup and reporting.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_unit_tests():
    """Run unit tests using unittest."""
    print("=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "test_op.py"], capture_output=True, text=True, timeout=120
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("Unit tests timed out")
        return False
    except Exception as e:
        print(f"Error running unit tests: {e}")
        return False


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "test_integration.py"],
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=300,
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("Integration tests timed out")
        return False
    except Exception as e:
        print(f"Error running integration tests: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")

    try:
        import hachoir

        print("✓ hachoir available")
    except ImportError:
        print("✗ hachoir not available - install with: pip install hachoir")
        return False

    # Check if op.py exists
    if not Path("op.py").exists():
        print("✗ op.py not found in current directory")
        return False
    else:
        print("✓ op.py found")

    return True


def main():
    """Run all tests."""
    print("orgphoto Test Suite")
    print("=" * 60)

    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependency check failed")
        return 1

    # Run unit tests
    unit_success = run_unit_tests()

    # Run integration tests
    integration_success = run_integration_tests()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Unit Tests: {'✓ PASS' if unit_success else '✗ FAIL'}")
    print(f"Integration Tests: {'✓ PASS' if integration_success else '✗ FAIL'}")

    if unit_success and integration_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
