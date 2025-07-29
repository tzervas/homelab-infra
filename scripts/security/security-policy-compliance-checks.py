#!/usr/bin/env python3
"""
Security Policy Compliance Checks
Validates security policy compliance across the homelab infrastructure.
"""

import logging
import os
import subprocess
import sys
from dataclasses import dataclass

import yaml


# Configure logging with user rule compliance
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/security-compliance.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class Policy:
    """Security policy data class."""

    name: str
    description: str
    check_command: list[str]
    expected_output: str
    compliance_category: str


@dataclass
class ComplianceResult:
    """Compliance result data class."""

    policy: Policy
    passed: bool
    output: str


class SecurityComplianceChecker:
    """Security compliance checker class."""

    def __init__(self, config_file: str = "/etc/security/security-compliance-config.yaml") -> None:
        """Initialize the compliance checker."""
        self.config = self._load_config(config_file)
        self.policies: list[Policy] = []

    def _load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {"policies": []}

    def _load_policies(self) -> None:
        """Load security policies from configuration."""
        for policy_data in self.config.get("policies", []):
            policy = Policy(
                name=policy_data["name"],
                description=policy_data.get("description", ""),
                check_command=policy_data["check_command"],
                expected_output=policy_data["expected_output"],
                compliance_category=policy_data.get("compliance_category", "general"),
            )
            self.policies.append(policy)

    def check_compliance(self) -> list[ComplianceResult]:
        """Check compliance for all configured policies."""
        compliance_results = []

        # Execute each policy check command
        for policy in self.policies:
            passed, output = self._execute_check(policy)
            compliance_results.append(
                ComplianceResult(
                    policy=policy,
                    passed=passed,
                    output=output,
                ),
            )

        return compliance_results

    def _execute_check(self, policy: Policy) -> (bool, str):
        """Execute a compliance check command."""
        try:
            result = subprocess.run(
                policy.check_command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            passed = policy.expected_output in result.stdout
            return passed, result.stdout
        except subprocess.TimeoutExpired:
            logger.exception(f"Policy check '{policy.name}' timed out")
            return False, "Timeout"
        except Exception as e:
            logger.exception(f"Error executing policy check '{policy.name}': {e}")
            return False, str(e)

    def generate_report(self, results: list[ComplianceResult]) -> str:
        """Generate a compliance report."""
        report_lines = [
            "Security Compliance Report",
            "============================",
            f"Generated at: {os.path.basename(__file__)}",
            "",
        ]

        for result in results:
            status = "PASSED" if result.passed else "FAILED"
            report_lines.append(
                f"Policy: {result.policy.name} - {status}\n"
                f"Description: {result.policy.description}\n"
                f"Compliance Category: {result.policy.compliance_category}\n"
                f"Output: {result.output.strip()}\n",
            )

        return "\n".join(report_lines)

    def save_report(self, report: str, report_path: str) -> None:
        """Save the compliance report to a file."""
        with open(report_path, "w") as report_file:
            report_file.write(report)
        logger.info(f"Compliance report saved to {report_path}")

    def run_compliance_checks(
        self,
        report_file: str = "/var/log/security-compliance-report.txt",
    ) -> None:
        """Run compliance checks and save report."""
        logger.info("Starting security policy compliance checks")
        self._load_policies()
        results = self.check_compliance()
        report = self.generate_report(results)
        self.save_report(report, report_file)
        logger.info("Security policy compliance checks completed")
        # Log failed results
        failed_results = [r for r in results if not r.passed]
        if failed_results:
            logger.warning("Failed compliance checks:")
            for result in failed_results:
                logger.warning(f"  {result.policy.name} - {result.output.strip()}")


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Security Policy Compliance Checks")
    parser.add_argument(
        "--config",
        default="/etc/security/security-compliance-config.yaml",
        help="Configuration file path",
    )
    parser.add_argument(
        "--report",
        default="/var/log/security-compliance-report.txt",
        help="Report file path",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        checker = SecurityComplianceChecker(args.config)
        checker.run_compliance_checks(args.report)
    except Exception as e:
        logger.exception(f"Compliance checks failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
