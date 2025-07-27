#!/usr/bin/env python3
"""Validate Deployment Configuration and Requirements."""

import json
import logging
import os
import sys
from datetime import datetime, timezone


try:
    from testing.rootless_compatibility import RootlessCompatibilityChecker
    from testing.test_reporter import HomelabTestReporter
except ImportError:
    try:
        from rootless_compatibility import RootlessCompatibilityChecker
        from test_reporter import HomelabTestReporter
    except ImportError:
        print("Error: Required testing modules not found.")
        print("Please run this script from the project root directory.")
        sys.exit(1)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def validate_deployment_readiness(
    kubeconfig_path: str | None = None,
    deployment_user: str | None = None,
    *,
    include_workstation: bool = False,
    output_file: str | None = None,
    log_level: str = "INFO",
) -> bool:
    """Validate deployment readiness by running all test suites."""
    logger = setup_logging(log_level)

    logger.info("Starting deployment validation...")

    # Run rootless compatibility check
    logger.info("Running rootless compatibility check...")
    checker = RootlessCompatibilityChecker(kubeconfig_path=kubeconfig_path, log_level=log_level)
    if deployment_user:
        os.environ["HOMELAB_USER"] = deployment_user

    results = checker.run_comprehensive_compatibility_check()
    checker.generate_compatibility_report(results)

    # Generate results
    compatible_count = sum(bool(r.compatible) for r in results)
    total_count = len(results)

    success = compatible_count == total_count
    status = "PASS" if success else "FAIL"
    result_data = {
        "status": status,
        "compatible_components": compatible_count,
        "total_components": total_count,
        "detected_mode": checker.deployment_mode,
        "deployment_user": checker.deployment_user,
        "issues": [
            {"component": r.component, "issues": r.issues, "recommendations": r.recommendations}
            for r in results
            if not r.compatible
        ],
    }

    # Run comprehensive infrastructure tests
    reporter = HomelabTestReporter(kubeconfig_path=kubeconfig_path, log_level=log_level)
    test_results = reporter.run_comprehensive_test_suite(
        include_workstation_tests=include_workstation,
    )

    test_status = "PASS" if test_results.overall_status != "fail" else "FAIL"
    if test_status == "FAIL":
        success = False

    result_data.update(
        {
            "infrastructure_status": test_status,
            "test_duration": test_results.duration,
            "test_summary": {
                "total": sum(1 for result in test_results if result),
                "passed": sum(bool(result.passed) for result in test_results),
                "duration": test_results.duration,
                "recommendations": test_results.recommendations,
            },
        },
    )

    if success:
        logger.info("✅ Deployment validation passed!")
    else:
        logger.error("❌ Deployment validation failed - see report for details")

    # Export validation report
    if not output_file:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        output_file = f"deployment_validation_{timestamp}.json"

    logger.info(f"Writing validation report to {output_file}")
    with open(output_file, "w") as f:
        json.dump(result_data, f, indent=2, default=str)

    return success


def main() -> int:
    """Main function for deployment validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate deployment readiness")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--deployment-user", help="Deployment user name")
    parser.add_argument(
        "--include-workstation",
        action="store_true",
        help="Include workstation perspective tests",
    )
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()

    success = validate_deployment_readiness(
        kubeconfig_path=args.kubeconfig,
        deployment_user=args.deployment_user,
        include_workstation=args.include_workstation,
        output_file=args.output,
        log_level=args.log_level,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
