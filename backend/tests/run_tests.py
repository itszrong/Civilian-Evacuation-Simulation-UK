#!/usr/bin/env python3
"""
Comprehensive test runner for London Evacuation Planning Tool backend.

This script provides various options for running the test suite with different
configurations and reporting options.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[str] = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_tests(
    test_type: str = "all",
    coverage: bool = True,
    verbose: bool = True,
    parallel: bool = False,
    markers: Optional[str] = None,
    specific_tests: Optional[List[str]] = None,
    html_report: bool = False,
    junit_xml: bool = False
) -> int:
    """
    Run tests with specified configuration.
    
    Args:
        test_type: Type of tests to run (unit, integration, api, all)
        coverage: Whether to collect coverage data
        verbose: Whether to run in verbose mode
        parallel: Whether to run tests in parallel
        markers: Pytest markers to filter tests
        specific_tests: Specific test files or directories to run
        html_report: Whether to generate HTML coverage report
        junit_xml: Whether to generate JUnit XML report
    
    Returns:
        Exit code from pytest
    """
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test paths based on test type
    if test_type == "unit":
        cmd.append("tests/unit")
    elif test_type == "integration":
        cmd.append("tests/integration")
    elif test_type == "api":
        cmd.append("tests/api")
    elif test_type == "all":
        cmd.append("tests/")
    elif specific_tests:
        cmd.extend(specific_tests)
    else:
        cmd.append("tests/")
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=term-missing",
        ])
        
        if html_report:
            cmd.append("--cov-report=html:htmlcov")
        
        cmd.extend([
            "--cov-fail-under=80",
            "--cov-exclude=tests/*",
            "--cov-exclude=test_*.py"
        ])
    
    # Add parallel execution
    if parallel:
        try:
            import pytest_xdist
            cmd.extend(["-n", "auto"])
        except ImportError:
            print("Warning: pytest-xdist not installed, running tests sequentially")
    
    # Add markers filter
    if markers:
        cmd.extend(["-m", markers])
    
    # Add JUnit XML report
    if junit_xml:
        cmd.extend(["--junit-xml=test-results.xml"])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--strict-config"
    ])
    
    # Run the tests
    return run_command(cmd)


def lint_code() -> int:
    """Run code linting checks."""
    print("\n" + "="*60)
    print("Running code linting checks...")
    print("="*60)
    
    exit_codes = []
    
    # Run flake8
    print("\n1. Running flake8...")
    exit_codes.append(run_command([
        "python", "-m", "flake8", 
        "--max-line-length=88",
        "--extend-ignore=E203,W503",
        "."
    ]))
    
    # Run black check
    print("\n2. Running black check...")
    exit_codes.append(run_command([
        "python", "-m", "black", 
        "--check", 
        "--diff",
        "."
    ]))
    
    # Run isort check
    print("\n3. Running isort check...")
    exit_codes.append(run_command([
        "python", "-m", "isort", 
        "--check-only", 
        "--diff",
        "."
    ]))
    
    # Run mypy (if available)
    try:
        import mypy
        print("\n4. Running mypy...")
        exit_codes.append(run_command([
            "python", "-m", "mypy", 
            "--ignore-missing-imports",
            "."
        ]))
    except ImportError:
        print("\n4. Skipping mypy (not installed)")
    
    return max(exit_codes) if exit_codes else 0


def format_code() -> int:
    """Format code using black and isort."""
    print("\n" + "="*60)
    print("Formatting code...")
    print("="*60)
    
    exit_codes = []
    
    # Run black
    print("\n1. Running black...")
    exit_codes.append(run_command([
        "python", "-m", "black", "."
    ]))
    
    # Run isort
    print("\n2. Running isort...")
    exit_codes.append(run_command([
        "python", "-m", "isort", "."
    ]))
    
    return max(exit_codes) if exit_codes else 0


def install_test_dependencies() -> int:
    """Install test dependencies."""
    print("\n" + "="*60)
    print("Installing test dependencies...")
    print("="*60)
    
    # Install dev dependencies
    return run_command([
        "pip", "install", "-e", ".[dev]"
    ])


def clean_test_artifacts():
    """Clean up test artifacts."""
    print("\n" + "="*60)
    print("Cleaning test artifacts...")
    print("="*60)
    
    artifacts = [
        ".coverage",
        "htmlcov/",
        "test-results.xml",
        ".pytest_cache/",
        "__pycache__/",
        "*.pyc",
        ".mypy_cache/"
    ]
    
    for artifact in artifacts:
        if Path(artifact).exists():
            print(f"Removing {artifact}")
            if Path(artifact).is_dir():
                import shutil
                shutil.rmtree(artifact)
            else:
                Path(artifact).unlink()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for London Evacuation Planning Tool backend"
    )
    
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "api", "all"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage collection"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run in quiet mode"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--markers",
        help="Pytest markers to filter tests (e.g., 'unit and not slow')"
    )
    
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--junit-xml",
        action="store_true",
        help="Generate JUnit XML report"
    )
    
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting checks instead of tests"
    )
    
    parser.add_argument(
        "--format",
        action="store_true",
        help="Format code instead of running tests"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean test artifacts"
    )
    
    parser.add_argument(
        "tests",
        nargs="*",
        help="Specific test files or directories to run"
    )
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Handle special commands
    if args.install_deps:
        return install_test_dependencies()
    
    if args.clean:
        clean_test_artifacts()
        return 0
    
    if args.format:
        return format_code()
    
    if args.lint:
        return lint_code()
    
    # Run tests
    print("="*60)
    print("London Evacuation Planning Tool - Backend Test Suite")
    print("="*60)
    
    exit_code = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet,
        parallel=args.parallel,
        markers=args.markers,
        specific_tests=args.tests if args.tests else None,
        html_report=args.html_report,
        junit_xml=args.junit_xml
    )
    
    if exit_code == 0:
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Some tests failed!")
        print("="*60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
