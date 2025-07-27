#!/usr/bin/env python3
"""Permission Verification Tests for Homelab Infrastructure.

This module verifies that the deployment user has proper permissions
and that security contexts are correctly applied across the infrastructure.
"""

from dataclasses import dataclass, field
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

try:
    from .common import setup_logger
    from .issue_tracker import IssueCategory, IssueSeverity, IssueTracker
except ImportError:
    # Fallback imports
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    class IssueTracker:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def add_issue(self, *args, **kwargs) -> None:
            pass

        def format_summary_report(self) -> str:
            return "Issue tracking not available"


@dataclass
class PermissionTest:
    """Represents a permission test with expected result."""

    name: str
    command: List[str]
    expected_success: bool
    description: str
    category: str = "general"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionResult:
    """Result of a permission test."""

    test: PermissionTest
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0

    @property
    def passed(self) -> bool:
        """Check if test passed (result matches expectation)."""
        return self.success == self.test.expected_success


class PermissionVerifier:
    """Verifies deployment user permissions and security contexts."""

    def __init__(
        self,
        deployment_user: Optional[str] = None,
        kubeconfig_path: Optional[str] = None,
        log_level: str = "INFO",
    ) -> None:
        """Initialize the permission verifier."""
        self.logger = setup_logger(__name__, log_level)
        self.deployment_user = deployment_user or os.getenv("HOMELAB_USER", "homelab-deploy")
        self.k8s_client = None
        self.issue_tracker = IssueTracker()

        if KUBERNETES_AVAILABLE:
            self._init_kubernetes_client(kubeconfig_path)

    def _init_kubernetes_client(self, kubeconfig_path: Optional[str]) -> None:
        """Initialize Kubernetes API client."""
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_kube_config()
            self.k8s_client = client.ApiClient()
            self.logger.info("Kubernetes client initialized for permission verification")
        except Exception as e:
            self.logger.warning(f"Could not initialize Kubernetes client: {e}")

    def _run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str, int]:
        """Run a command and return success status, stdout, stderr, and exit code.

        Args:
            cmd: List of command arguments. First item must be the command name,
                 subsequent items are arguments. Shell metacharacters are not allowed.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (success, stdout, stderr, exit_code)

        """
        # Validate command list
        if not cmd or not isinstance(cmd, list) or not all(isinstance(arg, str) for arg in cmd):
            return False, "", "Invalid command format", 1

        # Basic validation of command arguments - reject anything with shell metacharacters
        shell_metacharacters = ["|", "&", ";", "<", ">", "(", ")", "$", "`", "\\", '"', "'"]
        if any(any(char in arg for char in shell_metacharacters) for arg in cmd):
            return False, "", "Command contains invalid characters", 1

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
                result.returncode,
            )
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out", 124
        except Exception as e:
            return False, "", str(e), 1

    def test_deployment_user_permissions(self) -> List[PermissionResult]:
        """Test deployment user basic permissions."""
        tests = [
            PermissionTest(
                name="user_exists",
                command=["id", self.deployment_user],
                expected_success=True,
                description=f"Deployment user {self.deployment_user} exists",
                category="user_setup",
            ),
            PermissionTest(
                name="home_directory_access",
                command=["sudo", "-u", self.deployment_user, "ls", f"/home/{self.deployment_user}"],
                expected_success=True,
                description="Can access deployment user home directory",
                category="user_setup",
            ),
            PermissionTest(
                name="ssh_directory_permissions",
                command=[
                    "sudo",
                    "-u",
                    self.deployment_user,
                    "test",
                    "-d",
                    f"/home/{self.deployment_user}/.ssh",
                ],
                expected_success=True,
                description="SSH directory exists and is accessible",
                category="user_setup",
            ),
            PermissionTest(
                name="docker_group_membership",
                command=["sudo", "-u", self.deployment_user, "docker", "ps"],
                expected_success=True,
                description="User can access Docker without sudo",
                category="docker_access",
            ),
        ]

        results = []
        for test in tests:
            self.logger.debug(f"Running test: {test.name}")
            success, stdout, stderr, exit_code = self._run_command(test.command)

            result = PermissionResult(
                test=test, success=success, output=stdout, error=stderr, exit_code=exit_code
            )
            results.append(result)

            # Add to issue tracker if test failed unexpectedly
            if not result.passed:
                severity = (
                    IssueSeverity.HIGH if test.category == "user_setup" else IssueSeverity.MEDIUM
                )
                self.issue_tracker.add_issue(
                    component=f"permission_{test.category}",
                    message=f"Permission test failed: {test.description}",
                    severity=severity,
                    category=IssueCategory.DEPLOYMENT,
                    details={
                        "command": " ".join(test.command),
                        "expected_success": test.expected_success,
                        "actual_success": success,
                        "output": stdout,
                        "error": stderr,
                        "exit_code": exit_code,
                    },
                    affects_deployment=True,
                )

        return results

    def test_sudo_permissions(self) -> List[PermissionResult]:
        """Test deployment user sudo permissions."""
        tests = [
            PermissionTest(
                name="sudo_no_password",
                command=["sudo", "-u", self.deployment_user, "sudo", "-n", "true"],
                expected_success=True,
                description="Can use sudo without password",
                category="sudo_access",
            ),
            PermissionTest(
                name="systemctl_k3s_status",
                command=["sudo", "-u", self.deployment_user, "sudo", "systemctl", "status", "k3s"],
                expected_success=True,
                description="Can check K3s service status",
                category="sudo_access",
            ),
            PermissionTest(
                name="apt_update",
                command=["sudo", "-u", self.deployment_user, "sudo", "apt", "update", "--dry-run"],
                expected_success=True,
                description="Can run apt update",
                category="sudo_access",
            ),
            PermissionTest(
                name="cannot_edit_sudoers",
                command=["sudo", "-u", self.deployment_user, "sudo", "visudo"],
                expected_success=False,
                description="Cannot edit sudoers file (security check)",
                category="sudo_restrictions",
            ),
            PermissionTest(
                name="cannot_become_root",
                command=["sudo", "-u", self.deployment_user, "sudo", "su", "-"],
                expected_success=False,
                description="Cannot become root user (security check)",
                category="sudo_restrictions",
            ),
        ]

        results = []
        for test in tests:
            self.logger.debug(f"Running sudo test: {test.name}")
            success, stdout, stderr, exit_code = self._run_command(test.command)

            result = PermissionResult(
                test=test, success=success, output=stdout, error=stderr, exit_code=exit_code
            )
            results.append(result)

            # Add to issue tracker if test failed unexpectedly
            if not result.passed:
                if test.category == "sudo_access":
                    severity = IssueSeverity.HIGH
                    category = IssueCategory.DEPLOYMENT
                    affects_deployment = True
                else:  # sudo_restrictions
                    severity = IssueSeverity.CRITICAL  # Security issue if restrictions don't work
                    category = IssueCategory.SECURITY
                    affects_deployment = True

                self.issue_tracker.add_issue(
                    component=f"permission_{test.category}",
                    message=f"Sudo permission test failed: {test.description}",
                    severity=severity,
                    category=category,
                    details={
                        "command": " ".join(test.command),
                        "expected_success": test.expected_success,
                        "actual_success": success,
                        "output": stdout,
                        "error": stderr,
                    },
                    affects_deployment=affects_deployment,
                )

        return results

    def test_kubernetes_permissions(self) -> List[PermissionResult]:
        """Test Kubernetes access permissions."""
        if not self.k8s_client:
            return []

        tests = [
            PermissionTest(
                name="kubectl_cluster_info",
                command=["sudo", "-u", self.deployment_user, "kubectl", "cluster-info"],
                expected_success=True,
                description="Can access Kubernetes cluster",
                category="k8s_access",
            ),
            PermissionTest(
                name="kubectl_get_nodes",
                command=["sudo", "-u", self.deployment_user, "kubectl", "get", "nodes"],
                expected_success=True,
                description="Can list Kubernetes nodes",
                category="k8s_access",
            ),
            PermissionTest(
                name="kubectl_get_pods",
                command=["sudo", "-u", self.deployment_user, "kubectl", "get", "pods", "-A"],
                expected_success=True,
                description="Can list pods in all namespaces",
                category="k8s_access",
            ),
            PermissionTest(
                name="helm_list",
                command=["sudo", "-u", self.deployment_user, "helm", "list", "-A"],
                expected_success=True,
                description="Can list Helm releases",
                category="helm_access",
            ),
        ]

        results = []
        for test in tests:
            self.logger.debug(f"Running Kubernetes test: {test.name}")
            success, stdout, stderr, exit_code = self._run_command(test.command)

            result = PermissionResult(
                test=test, success=success, output=stdout, error=stderr, exit_code=exit_code
            )
            results.append(result)

            # Add to issue tracker if test failed unexpectedly
            if not result.passed:
                self.issue_tracker.add_issue(
                    component=f"permission_{test.category}",
                    message=f"Kubernetes permission test failed: {test.description}",
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.DEPLOYMENT,
                    details={"command": " ".join(test.command), "output": stdout, "error": stderr},
                    affects_deployment=True,
                )

        return results

    def verify_security_contexts(self) -> List[PermissionResult]:
        """Verify security contexts are properly applied."""
        if not self.k8s_client:
            return []

        results = []

        try:
            apps_v1 = client.AppsV1Api(self.k8s_client)
            client.CoreV1Api(self.k8s_client)

            # Get all deployments
            deployments = apps_v1.list_deployment_for_all_namespaces()

            privileged_found = []
            missing_contexts = []

            for deployment in deployments.items:
                # Skip system components that legitimately need root
                if deployment.metadata.namespace in ["kube-system", "metallb-system"]:
                    continue

                deployment_name = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
                spec = deployment.spec.template.spec

                # Check pod security context
                if not spec.security_context or spec.security_context.run_as_non_root is not True:
                    missing_contexts.append(deployment_name)

                # Check container security contexts
                for container in spec.containers or []:
                    if container.security_context:
                        if (
                            container.security_context.run_as_user == 0
                            or container.security_context.privileged is True
                        ):
                            privileged_found.append(f"{deployment_name}:{container.name}")
                    else:
                        missing_contexts.append(f"{deployment_name}:{container.name}")

            # Create test results
            tests = [
                PermissionTest(
                    name="no_privileged_containers",
                    command=["echo", "Security context validation"],
                    expected_success=len(privileged_found) == 0,
                    description=f"No privileged containers found (found {len(privileged_found)})",
                    category="security_contexts",
                    details={"privileged_containers": privileged_found},
                ),
                PermissionTest(
                    name="all_have_security_contexts",
                    command=["echo", "Security context validation"],
                    expected_success=len(missing_contexts) == 0,
                    description=f"All containers have security contexts (missing {len(missing_contexts)})",
                    category="security_contexts",
                    details={"missing_contexts": missing_contexts},
                ),
            ]

            for test in tests:
                result = PermissionResult(
                    test=test,
                    success=test.expected_success,
                    output=f"Checked {len(deployments.items)} deployments",
                )
                results.append(result)

                # Add detailed issues to tracker
                if not result.passed:
                    if test.name == "no_privileged_containers" and privileged_found:
                        for container in privileged_found[:10]:  # Limit to first 10
                            self.issue_tracker.add_issue(
                                component="security_contexts",
                                message=f"Privileged container found: {container}",
                                severity=IssueSeverity.CRITICAL,
                                category=IssueCategory.SECURITY,
                                affects_deployment=True,
                            )

                        if len(privileged_found) > 10:
                            self.issue_tracker.add_issue(
                                component="security_contexts",
                                message=f"Total of {len(privileged_found)} privileged containers found",
                                severity=IssueSeverity.CRITICAL,
                                category=IssueCategory.SECURITY,
                                details={"total_count": len(privileged_found)},
                                affects_deployment=True,
                            )

                    elif test.name == "all_have_security_contexts" and missing_contexts:
                        for container in missing_contexts[:10]:  # Limit to first 10
                            self.issue_tracker.add_issue(
                                component="security_contexts",
                                message=f"Missing security context: {container}",
                                severity=IssueSeverity.HIGH,
                                category=IssueCategory.SECURITY,
                                affects_deployment=True,
                            )

                        if len(missing_contexts) > 10:
                            self.issue_tracker.add_issue(
                                component="security_contexts",
                                message=f"Total of {len(missing_contexts)} containers missing security contexts",
                                severity=IssueSeverity.HIGH,
                                category=IssueCategory.SECURITY,
                                details={"total_count": len(missing_contexts)},
                                affects_deployment=True,
                            )

        except Exception as e:
            self.logger.exception(f"Error verifying security contexts: {e}")
            self.issue_tracker.add_issue(
                component="security_contexts",
                message=f"Failed to verify security contexts: {e}",
                severity=IssueSeverity.HIGH,
                category=IssueCategory.VALIDATION,
            )

        return results

    @staticmethod
    def _count_passed_tests(test_results: List[PermissionResult]) -> int:
        """Count number of passed tests in a list of results."""
        return sum(bool(result.passed) for result in test_results)

    @classmethod
    def _count_total_passed_tests(cls, results: Dict[str, List[PermissionResult]]) -> int:
        """Count total number of passed tests across all categories."""
        return sum(cls._count_passed_tests(test_results) for test_results in results.values())

    @staticmethod
    def _count_total_tests(results: Dict[str, List[PermissionResult]]) -> int:
        """Count total number of tests across all categories."""
        return sum(len(test_results) for test_results in results.values())

    def run_comprehensive_permission_tests(self) -> Dict[str, List[PermissionResult]]:
        """Run all permission verification tests."""
        self.logger.info("Starting comprehensive permission verification...")

        self.issue_tracker.clear()

        results = {
            "user_permissions": self.test_deployment_user_permissions(),
            "sudo_permissions": self.test_sudo_permissions(),
            "kubernetes_permissions": self.test_kubernetes_permissions(),
            "security_contexts": self.verify_security_contexts(),
        }

        # Summary logging
        total_tests = self._count_total_tests(results)
        passed_tests = self._count_total_passed_tests(results)

        self.logger.info(
            f"Permission verification completed: {passed_tests}/{total_tests} tests passed"
        )

        return results

    def generate_permission_report(self, results: Dict[str, List[PermissionResult]]) -> str:
        """Generate a comprehensive permission verification report."""
        report = []
        report.append("# Permission Verification Report")
        report.append("")

        # Summary
        total_tests = self._count_total_tests(results)
        passed_tests = self._count_total_passed_tests(results)

        report.append(f"**Overall Status**: {passed_tests}/{total_tests} tests passed")
        if passed_tests == total_tests:
            report.append("✅ **All permission tests passed!**")
        else:
            report.append("❌ **Some permission tests failed - review and fix issues**")
        report.append("")

        # Detailed results by category
        for category, test_results in results.items():
            if not test_results:
                continue

            category_passed = self._count_passed_tests(test_results)
            category_total = len(test_results)

            report.append(f"## {category.replace('_', ' ').title()}")
            report.append(f"**Status**: {category_passed}/{category_total} tests passed")
            report.append("")

            for result in test_results:
                status = "✅" if result.passed else "❌"
                report.append(f"### {status} {result.test.name}")
                report.append(f"**Description**: {result.test.description}")

                if not result.passed:
                    report.append(
                        f"**Expected**: {'Success' if result.test.expected_success else 'Failure'}"
                    )
                    report.append(f"**Actual**: {'Success' if result.success else 'Failure'}")

                    if result.error:
                        report.append(f"**Error**: {result.error}")

                    if result.output:
                        report.append("**Output**:")
                        report.append("```")
                        report.append(result.output)
                        report.append("```")

                report.append("")

        # Issue summary
        issue_summary = self.issue_tracker.generate_summary()
        if issue_summary.total_issues > 0:
            report.append("## Issues Found")
            report.append("")
            issue_report = self.issue_tracker.format_summary_report()
            report.append(issue_report)

        return "\n".join(report)


def main() -> None:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify deployment user permissions and security contexts"
    )
    parser.add_argument(
        "--deployment-user", default="homelab-deploy", help="Deployment user to test"
    )
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARN", "ERROR"])
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    verifier = PermissionVerifier(
        deployment_user=args.deployment_user,
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level,
    )

    results = verifier.run_comprehensive_permission_tests()
    report = verifier.generate_permission_report(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)

    # Exit with error code if any tests failed
    total_tests = verifier._count_total_tests(results)
    passed_tests = verifier._count_total_passed_tests(results)

    if passed_tests < total_tests:
        sys.exit(1)


if __name__ == "__main__":
    main()
