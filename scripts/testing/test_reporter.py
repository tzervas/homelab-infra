#!/usr/bin/env python3
"""Test Reporter & Aggregator for Homelab Infrastructure Testing Framework.

This module orchestrates all testing modules, aggregates results, and provides
comprehensive reporting in multiple formats with trend analysis and metrics.
"""

import json
import logging
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Import all testing modules
try:
    from .config_validator import ConfigValidator, ValidationResult
    from .infrastructure_health import ClusterHealth, InfrastructureHealthMonitor
    from .integration_tester import IntegrationConnectivityTester, IntegrationTestResult
    from .issue_tracker import (
        IssueCategory,
        IssueSeverity,
        IssueTracker,
        create_missing_items_issues,
        create_security_context_issues,
    )
    from .network_security import NetworkSecurityValidator, SecurityStatus
    from .service_checker import ServiceDeploymentChecker, ServiceStatus
except ImportError:
    try:
        from config_validator import ConfigValidator, ValidationResult
        from infrastructure_health import ClusterHealth, InfrastructureHealthMonitor
        from integration_tester import IntegrationConnectivityTester, IntegrationTestResult
        from issue_tracker import (
            IssueCategory,
            IssueSeverity,
            IssueTracker,
            create_missing_items_issues,
            create_security_context_issues,
        )
        from network_security import NetworkSecurityValidator, SecurityStatus
        from service_checker import ServiceDeploymentChecker, ServiceStatus
    except ImportError as e:
        print(f"Warning: Could not import some testing modules: {e}")
        print("Some functionality may be limited.")

        # Create mock classes if issue tracker is not available
        class IssueTracker:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def add_issue(self, *args, **kwargs) -> None:
                pass

            def format_summary_report(self) -> str:
                return "Issue tracking not available"


@dataclass
class TestSuiteResult:
    """Comprehensive test suite results."""

    timestamp: str
    duration: float
    overall_status: str  # "pass", "fail", "warning"
    summary: dict[str, Any] = field(default_factory=dict)
    config_validation: list[ValidationResult] | None = None
    infrastructure_health: ClusterHealth | None = None
    service_deployment: dict[str, ServiceStatus] | None = None
    network_security: list[SecurityStatus] | None = None
    integration_tests: list[IntegrationTestResult] | None = None
    recommendations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class HomelabTestReporter:
    """Comprehensive test reporter and aggregator."""

    def __init__(self, kubeconfig_path: str | None = None, log_level: str = "INFO") -> None:
        """Initialize the test reporter."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)

        # Initialize testing modules
        self.config_validator = None
        self.infra_monitor = None
        self.service_checker = None
        self.security_validator = None
        self.integration_tester = None

        # Initialize issue tracker
        self.issue_tracker = IssueTracker(max_issues_per_component=10, max_total_display=50)

        try:
            if "ConfigValidator" in globals():
                self.config_validator = ConfigValidator(log_level)
            if "InfrastructureHealthMonitor" in globals():
                self.infra_monitor = InfrastructureHealthMonitor(kubeconfig_path, log_level)
            if "ServiceDeploymentChecker" in globals():
                self.service_checker = ServiceDeploymentChecker(kubeconfig_path, log_level)
            if "NetworkSecurityValidator" in globals():
                self.security_validator = NetworkSecurityValidator(kubeconfig_path, log_level)
            if "IntegrationConnectivityTester" in globals():
                self.integration_tester = IntegrationConnectivityTester(kubeconfig_path, log_level)
        except Exception as e:
            self.logger.exception(f"Failed to initialize testing modules: {e}")

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run_config_validation(
        self,
        config_paths: list[str] | None = None,
    ) -> list[ValidationResult] | None:
        """Run configuration validation tests."""
        if not self.config_validator:
            self.logger.warning("Config validator not available")
            return None

        try:
            self.logger.info("Running configuration validation...")

            if config_paths:
                results = []
                for path in config_paths:
                    if Path(path).is_dir():
                        results.extend(self.config_validator.validate_directory(path))
                    else:
                        results.append(self.config_validator.validate_file(path))
            else:
                # Default configuration paths for homelab
                default_paths = [
                    "ansible/inventory",
                    "helm/environments",
                    "examples/private-config-template",
                ]
                results = []
                for path in default_paths:
                    if Path(path).exists():
                        results.extend(self.config_validator.validate_directory(path))

            return results

        except Exception as e:
            self.logger.exception(f"Configuration validation failed: {e}")
            return None

    def run_infrastructure_health_check(self) -> ClusterHealth | None:
        """Run infrastructure health monitoring."""
        if not self.infra_monitor:
            self.logger.warning("Infrastructure monitor not available")
            return None

        try:
            self.logger.info("Running infrastructure health check...")
            return self.infra_monitor.get_cluster_health()
        except Exception as e:
            self.logger.exception(f"Infrastructure health check failed: {e}")
            return None

    def run_service_deployment_check(self) -> dict[str, ServiceStatus] | None:
        """Run service deployment validation."""
        if not self.service_checker:
            self.logger.warning("Service checker not available")
            return None

        try:
            self.logger.info("Running service deployment check...")
            return self.service_checker.check_all_services()
        except Exception as e:
            self.logger.exception(f"Service deployment check failed: {e}")
            return None

    def run_network_security_validation(self) -> list[SecurityStatus] | None:
        """Run network and security validation."""
        if not self.security_validator:
            self.logger.warning("Security validator not available")
            return None

        try:
            self.logger.info("Running network and security validation...")
            return self.security_validator.run_comprehensive_security_scan()
        except Exception as e:
            self.logger.exception(f"Network security validation failed: {e}")
            return None

    def run_integration_tests(
        self,
        include_workstation: bool = False,
    ) -> list[IntegrationTestResult] | None:
        """Run integration and connectivity tests."""
        if not self.integration_tester:
            self.logger.warning("Integration tester not available")
            return None

        try:
            self.logger.info("Running integration tests...")
            return self.integration_tester.run_comprehensive_integration_tests(include_workstation)
        except Exception as e:
            self.logger.exception(f"Integration tests failed: {e}")
            return None

    def calculate_metrics(self, result: TestSuiteResult) -> dict[str, Any]:
        """Calculate test metrics and statistics."""
        metrics = {"total_test_duration": result.duration, "timestamp": result.timestamp}

        # Config validation metrics
        if result.config_validation:
            valid_configs = sum(1 for r in result.config_validation if r.is_valid)
            total_configs = len(result.config_validation)
            metrics["config_validation"] = {
                "total_files": total_configs,
                "valid_files": valid_configs,
                "validation_rate": (valid_configs / total_configs * 100)
                if total_configs > 0
                else 0,
            }

        # Infrastructure health metrics
        if result.infrastructure_health:
            metrics["infrastructure_health"] = {
                "health_percentage": result.infrastructure_health.health_percentage,
                "total_checks": result.infrastructure_health.total_checks,
                "healthy_checks": result.infrastructure_health.healthy_checks,
            }

        # Service deployment metrics
        if result.service_deployment:
            ready_services = sum(1 for s in result.service_deployment.values() if s.is_ready)
            total_services = len(result.service_deployment)
            metrics["service_deployment"] = {
                "total_services": total_services,
                "ready_services": ready_services,
                "readiness_rate": (ready_services / total_services * 100)
                if total_services > 0
                else 0,
            }

        # Security metrics
        if result.network_security:
            secure_checks = sum(1 for s in result.network_security if s.is_secure)
            total_security_checks = len(result.network_security)
            metrics["network_security"] = {
                "total_checks": total_security_checks,
                "secure_checks": secure_checks,
                "security_score": (secure_checks / total_security_checks * 100)
                if total_security_checks > 0
                else 0,
            }

        # Integration test metrics
        if result.integration_tests:
            passed_tests = sum(1 for t in result.integration_tests if t.passed)
            total_tests = len(result.integration_tests)
            avg_duration = (
                sum(t.duration for t in result.integration_tests) / total_tests
                if total_tests > 0
                else 0
            )
            metrics["integration_tests"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_test_duration": avg_duration,
            }

        return metrics

    def generate_recommendations(self, result: TestSuiteResult) -> list[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        # Config validation recommendations
        if result.config_validation:
            invalid_configs = [r for r in result.config_validation if not r.is_valid]
            if invalid_configs:
                recommendations.append(f"Fix {len(invalid_configs)} invalid configuration files")

        # Infrastructure health recommendations
        if (
            result.infrastructure_health
            and result.infrastructure_health.cluster_status != "healthy"
        ):
            recommendations.append("Address infrastructure health issues before proceeding")

        # Service deployment recommendations
        if result.service_deployment:
            unready_services = [
                name for name, status in result.service_deployment.items() if not status.is_ready
            ]
            if unready_services:
                recommendations.append(
                    f"Investigate unready services: {', '.join(unready_services)}",
                )

        # Security recommendations
        if result.network_security:
            security_issues = [
                s for s in result.network_security if s.status in ["warning", "vulnerable"]
            ]
            if security_issues:
                recommendations.append("Review and address security warnings")
                for issue in security_issues:
                    recommendations.extend(issue.recommendations)

        # Integration test recommendations
        if result.integration_tests:
            failed_tests = [t for t in result.integration_tests if t.status == "fail"]
            if failed_tests:
                recommendations.append(
                    "Fix failing integration tests for complete system validation",
                )

        return recommendations

    def run_comprehensive_test_suite(
        self,
        config_paths: list[str] | None = None,
        include_workstation_tests: bool = False,
    ) -> TestSuiteResult:
        """Run the complete test suite and aggregate results."""
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info("🚀 Starting comprehensive homelab testing suite...")

        # Clear previous issues
        self.issue_tracker.clear()

        # Run all test modules and collect issues
        config_results = self.run_config_validation(config_paths)
        self._process_config_issues(config_results)

        infra_health = self.run_infrastructure_health_check()
        self._process_infrastructure_issues(infra_health)

        service_status = self.run_service_deployment_check()
        self._process_service_issues(service_status)

        security_results = self.run_network_security_validation()
        self._process_security_issues(security_results)

        integration_results = self.run_integration_tests(include_workstation_tests)
        self._process_integration_issues(integration_results)

        duration = time.time() - start_time

        # Determine overall status
        overall_status = "pass"

        if config_results and any(not r.is_valid for r in config_results):
            overall_status = "warning"

        if infra_health and infra_health.cluster_status == "critical":
            overall_status = "fail"

        if service_status and any(not s.is_ready for s in service_status.values()):
            if overall_status == "pass":
                overall_status = "warning"

        if integration_results and any(t.status == "fail" for t in integration_results):
            overall_status = "fail"

        # Create comprehensive result
        result = TestSuiteResult(
            timestamp=timestamp,
            duration=duration,
            overall_status=overall_status,
            config_validation=config_results,
            infrastructure_health=infra_health,
            service_deployment=service_status,
            network_security=security_results,
            integration_tests=integration_results,
        )

        # Calculate metrics and recommendations
        result.metrics = self.calculate_metrics(result)
        result.recommendations = self.generate_recommendations(result)

        # Create summary
        result.summary = {
            "overall_status": overall_status,
            "test_duration": duration,
            "modules_run": sum(
                bool(r is not None)
                for r in [
                    config_results,
                    infra_health,
                    service_status,
                    security_results,
                    integration_results,
                ]
            ),
            "total_recommendations": len(result.recommendations),
        }

        self.logger.info(
            f"✅ Test suite completed in {duration:.2f}s with status: {overall_status.upper()}",
        )

        return result

    def _process_config_issues(self, config_results: list[ValidationResult] | None) -> None:
        """Process configuration validation results and add to issue tracker."""
        if not config_results:
            return

        for result in config_results:
            if not result.is_valid:
                severity = (
                    IssueSeverity.HIGH
                    if "critical" in result.message.lower()
                    else IssueSeverity.MEDIUM
                )
                self.issue_tracker.add_issue(
                    component=f"config_{result.file_type}",
                    message=result.message,
                    severity=severity,
                    category=IssueCategory.CONFIGURATION,
                    details={"file_path": result.file_path, "errors": result.errors},
                    affects_deployment=severity == IssueSeverity.HIGH,
                )

    def _process_infrastructure_issues(self, infra_health: ClusterHealth | None) -> None:
        """Process infrastructure health results and add to issue tracker."""
        if not infra_health:
            return

        # Process cluster status
        if infra_health.cluster_status == "critical":
            self.issue_tracker.add_issue(
                component="kubernetes_cluster",
                message="Cluster is in critical state",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.DEPLOYMENT,
                affects_deployment=True,
            )
        elif infra_health.cluster_status == "warning":
            self.issue_tracker.add_issue(
                component="kubernetes_cluster",
                message="Cluster has warning conditions",
                severity=IssueSeverity.HIGH,
                category=IssueCategory.DEPLOYMENT,
                affects_deployment=True,
            )

        # Process node issues
        if hasattr(infra_health, "node_statuses") and infra_health.node_statuses:
            unhealthy_nodes = [
                node for node, status in infra_health.node_statuses.items() if status != "ready"
            ]
            if unhealthy_nodes:
                create_missing_items_issues(
                    tracker=self.issue_tracker,
                    component="kubernetes_nodes",
                    missing_items=unhealthy_nodes,
                    item_type="unhealthy node",
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.DEPLOYMENT,
                )

    def _process_service_issues(self, service_status: dict[str, ServiceStatus] | None) -> None:
        """Process service deployment results and add to issue tracker."""
        if not service_status:
            return

        for service_name, status in service_status.items():
            if not status.is_ready:
                severity = (
                    IssueSeverity.CRITICAL if status.status == "failed" else IssueSeverity.HIGH
                )
                self.issue_tracker.add_issue(
                    component=f"service_{service_name}",
                    message=f"Service not ready: {status.message}",
                    severity=severity,
                    category=IssueCategory.DEPLOYMENT,
                    details={
                        "pod_count": status.pod_count,
                        "ready_pods": status.ready_pods,
                        "namespace": status.namespace,
                    },
                    affects_deployment=True,
                )

    def _process_security_issues(self, security_results: list[SecurityStatus] | None) -> None:
        """Process security validation results and add to issue tracker."""
        if not security_results:
            return

        for security_status in security_results:
            if not security_status.is_secure:
                # Map security status to issue severity
                if security_status.status == "vulnerable":
                    severity = IssueSeverity.CRITICAL
                elif security_status.status == "warning":
                    severity = IssueSeverity.HIGH
                else:
                    severity = IssueSeverity.MEDIUM

                # Extract detailed counts from security status
                details = security_status.details
                message = security_status.message

                # Handle specific security issues with counts
                if "privileged_containers_shown" in details:
                    total_privileged = details.get("total_privileged_containers", 0)
                    total_missing = details.get("total_missing_contexts", 0)

                    if total_privileged > 0:
                        privileged_containers = details.get("privileged_containers_shown", [])
                        create_security_context_issues(
                            tracker=self.issue_tracker,
                            component="kubernetes_security_contexts",
                            privileged_containers=privileged_containers,
                            missing_contexts=[],
                        )

                        # Add summary issue with total count
                        if total_privileged > len(privileged_containers):
                            self.issue_tracker.add_issue(
                                component="kubernetes_security_contexts",
                                message=f"Total of {total_privileged} privileged containers found (showing {len(privileged_containers)})",
                                severity=IssueSeverity.CRITICAL,
                                category=IssueCategory.SECURITY,
                                details={"total_count": total_privileged},
                                affects_deployment=True,
                            )

                    if total_missing > 0:
                        missing_contexts = details.get("missing_contexts_shown", [])
                        create_security_context_issues(
                            tracker=self.issue_tracker,
                            component="kubernetes_security_contexts",
                            privileged_containers=[],
                            missing_contexts=missing_contexts,
                        )

                        # Add summary issue with total count
                        if total_missing > len(missing_contexts):
                            self.issue_tracker.add_issue(
                                component="kubernetes_security_contexts",
                                message=f"Total of {total_missing} missing security contexts (showing {len(missing_contexts)})",
                                severity=IssueSeverity.HIGH,
                                category=IssueCategory.SECURITY,
                                details={"total_count": total_missing},
                                affects_deployment=True,
                            )
                else:
                    # Generic security issue
                    self.issue_tracker.add_issue(
                        component=f"security_{security_status.component}",
                        message=message,
                        severity=severity,
                        category=IssueCategory.SECURITY,
                        details=details,
                        recommendations=security_status.recommendations,
                        affects_deployment=severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH],
                    )

    def _process_integration_issues(
        self,
        integration_results: list[IntegrationTestResult] | None,
    ) -> None:
        """Process integration test results and add to issue tracker."""
        if not integration_results:
            return

        for test_result in integration_results:
            if test_result.status == "fail":
                self.issue_tracker.add_issue(
                    component=f"integration_{test_result.test_name}",
                    message=f"Integration test failed: {test_result.message}",
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.CONNECTIVITY,
                    details=test_result.details,
                    affects_deployment=True,
                )
            elif test_result.status == "warning":
                self.issue_tracker.add_issue(
                    component=f"integration_{test_result.test_name}",
                    message=f"Integration test warning: {test_result.message}",
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.CONNECTIVITY,
                    details=test_result.details,
                )

    def export_json_report(self, result: TestSuiteResult, filename: str | None = None) -> str:
        """Export results to JSON format."""
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"homelab_test_report_{timestamp}.json"

        filepath = self.results_dir / filename

        # Convert dataclasses to dict for JSON serialization
        json_data = asdict(result)

        with open(filepath, "w") as f:
            json.dump(json_data, f, indent=2, default=str)

        self.logger.info(f"JSON report exported to: {filepath}")
        return str(filepath)

    def export_markdown_report(
        self,
        result: TestSuiteResult,
        filename: str | None = None,
    ) -> str:
        """Export results to Markdown format."""
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"homelab_test_report_{timestamp}.md"

        filepath = self.results_dir / filename

        with open(filepath, "w") as f:
            f.write("# Homelab Infrastructure Test Report\n\n")
            f.write(f"**Generated:** {result.timestamp}\n")
            f.write(f"**Duration:** {result.duration:.2f} seconds\n")
            f.write(f"**Overall Status:** {result.overall_status.upper()}\n\n")

            # Summary section
            f.write("## Summary\n\n")
            f.writelines(
                f"- **{key.replace('_', ' ').title()}:** {value}\n"
                for key, value in result.summary.items()
            )
            f.write("\n")

            # Issue Summary section (prioritized issues with counts)
            issue_summary = self.issue_tracker.generate_summary()
            if issue_summary.total_issues > 0:
                f.write("## Issue Summary\n\n")
                f.write(f"**Total Issues**: {issue_summary.total_issues}\n")
                f.write(f"**Deployment Blocking**: {issue_summary.deployment_blocking}\n\n")

                # Critical issues (always show all)
                critical_issues = self.issue_tracker.get_critical_issues()
                if critical_issues:
                    f.write("### 🚨 Critical Issues (Must Fix)\n\n")
                    f.writelines(
                        f"- **{issue.component}**: {issue.message}\n" for issue in critical_issues
                    )
                    f.write("\n")

                # Issue breakdown by severity
                f.write("### Issues by Severity\n\n")
                for severity in IssueSeverity:
                    count = issue_summary.by_severity[severity]
                    if count > 0:
                        icon = {
                            "critical": "🚨",
                            "high": "⚠️",
                            "medium": "⚡",
                            "low": "ℹ️",
                            "info": "📝",
                        }[severity.value]
                        f.write(f"- {icon} **{severity.value.title()}**: {count}\n")
                f.write("\n")

                # Top issues by component
                f.write("### Top Issues by Component\n\n")
                component_counts = Counter(issue.component for issue in self.issue_tracker.issues)
                for component, count in component_counts.most_common(10):
                    component_issues = [
                        i for i in issue_summary.top_issues if i.component == component
                    ]
                    if component_issues:
                        highest_severity = min(
                            component_issues,
                            key=lambda x: list(IssueSeverity).index(x.severity),
                        )
                        severity_icon = {
                            "critical": "🚨",
                            "high": "⚠️",
                            "medium": "⚡",
                            "low": "ℹ️",
                            "info": "📝",
                        }[highest_severity.severity.value]
                        f.write(f"**{severity_icon} {component}** ({count} issues)\n")

                        # Show sample issues for this component
                        f.writelines(f"  - {issue.message}\n" for issue in component_issues[:2])

                        if count > 2:
                            f.write(f"  - ... and {count - 2} more issues\n")
                        f.write("\n")

            # Metrics section
            if result.metrics:
                f.write("## Metrics\n\n")
                for category, metrics in result.metrics.items():
                    if isinstance(metrics, dict):
                        f.write(f"### {category.replace('_', ' ').title()}\n\n")
                        f.writelines(
                            f"- **{key.replace('_', ' ').title()}:** {value}\n"
                            for key, value in metrics.items()
                        )
                        f.write("\n")

            # Recommendations section
            if result.recommendations:
                f.write("## Recommendations\n\n")
                f.writelines(f"{i}. {rec}\n" for i, rec in enumerate(result.recommendations, 1))
                f.write("\n")

            # Detailed results sections
            if result.config_validation:
                f.write("## Configuration Validation\n\n")
                valid_count = sum(1 for r in result.config_validation if r.is_valid)
                total_count = len(result.config_validation)
                f.write(f"**Status:** {valid_count}/{total_count} files valid\n\n")

            if result.infrastructure_health:
                f.write("## Infrastructure Health\n\n")
                f.write(
                    f"**Overall Status:** {result.infrastructure_health.cluster_status.upper()}\n",
                )
                f.write(
                    f"**Health Score:** {result.infrastructure_health.health_percentage:.1f}%\n\n",
                )

            if result.service_deployment:
                f.write("## Service Deployment\n\n")
                for service_name, status in result.service_deployment.items():
                    icon = "✅" if status.is_ready else "❌"
                    f.write(f"- {icon} **{service_name}:** {status.message}\n")
                f.write("\n")

            if result.network_security:
                f.write("## Network & Security\n\n")
                for security in result.network_security:
                    icon = (
                        "🔒"
                        if security.is_secure
                        else "⚠️"
                        if security.status == "warning"
                        else "🚨"
                    )
                    f.write(
                        f"- {icon} **{security.check_type.replace('_', ' ').title()}:** {security.message}\n",
                    )
                f.write("\n")

            if result.integration_tests:
                f.write("## Integration Tests\n\n")
                for test in result.integration_tests:
                    icon = "✅" if test.passed else "❌" if test.status == "fail" else "⚠️"
                    f.write(
                        f"- {icon} **{test.test_name.replace('_', ' ').title()}:** {test.message}\n",
                    )

        self.logger.info(f"Markdown report exported to: {filepath}")
        return str(filepath)

    def export_issue_report(self, filename: str | None = None) -> str:
        """Export a dedicated issue report with comprehensive counting and prioritization."""
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"homelab_issues_report_{timestamp}.md"

        filepath = self.results_dir / filename

        with open(filepath, "w") as f:
            # Generate comprehensive issue report
            issue_report = self.issue_tracker.format_summary_report()
            f.write(issue_report)

        self.logger.info(f"Issue report exported to: {filepath}")
        return str(filepath)

    def print_console_summary(self, result: TestSuiteResult) -> None:
        """Print a comprehensive console summary."""
        print("\n🏠 HOMELAB INFRASTRUCTURE TEST REPORT")
        print(f"{'='*60}")
        print(f"Timestamp: {result.timestamp}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Overall Status: {result.overall_status.upper()}")
        print(f"{'='*60}\n")

        # Issue Summary with counts
        issue_summary = self.issue_tracker.generate_summary()
        if issue_summary.total_issues > 0:
            print("🚨 ISSUE SUMMARY:")
            print(f"  Total Issues: {issue_summary.total_issues}")
            print(f"  Deployment Blocking: {issue_summary.deployment_blocking}")

            # Critical issues (always show)
            critical_issues = self.issue_tracker.get_critical_issues()
            if critical_issues:
                print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
                for issue in critical_issues[:5]:  # Show top 5 critical
                    print(f"  - {issue.component}: {issue.message}")
                if len(critical_issues) > 5:
                    print(f"  ... and {len(critical_issues) - 5} more critical issues")

            # Issue breakdown by severity
            print("\n📊 Issues by Severity:")
            for severity in IssueSeverity:
                count = issue_summary.by_severity[severity]
                if count > 0:
                    icon = {
                        "critical": "🚨",
                        "high": "⚠️",
                        "medium": "⚡",
                        "low": "ℹ️",
                        "info": "📝",
                    }[severity.value]
                    print(f"  {icon} {severity.value.title()}: {count}")

            # Top problematic components
            component_counts = Counter(issue.component for issue in self.issue_tracker.issues)
            if component_counts:
                print("\n🔧 Most Problematic Components:")
                for component, count in component_counts.most_common(5):
                    print(f"  - {component}: {count} issues")
        else:
            print("✅ NO ISSUES FOUND - SYSTEM IS HEALTHY!")

        # Summary metrics
        if result.metrics:
            print("\n📊 METRICS SUMMARY:")
            for category, metrics in result.metrics.items():
                if isinstance(metrics, dict):
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for key, value in metrics.items():
                        if isinstance(value, float):
                            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
                        else:
                            print(f"  {key.replace('_', ' ').title()}: {value}")

        # Recommendations (enhanced with issue tracker recommendations)
        all_recommendations = result.recommendations or []

        # Add top recommendations from issue tracker
        if issue_summary.total_issues > 0:
            critical_recommendations = []
            for issue in self.issue_tracker.get_critical_issues():
                critical_recommendations.extend(
                    issue.recommendations[:2],
                )  # Top 2 per critical issue

            # Remove duplicates and add to recommendations
            unique_critical_recs = []
            for rec in critical_recommendations:
                if rec not in all_recommendations and rec not in unique_critical_recs:
                    unique_critical_recs.append(rec)

            all_recommendations.extend(
                unique_critical_recs[:5],
            )  # Add top 5 unique critical recommendations

        if all_recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(all_recommendations)}):")
            for i, rec in enumerate(all_recommendations, 1):
                print(f"  {i}. {rec}")

        print(f"\n{'='*60}")


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run comprehensive homelab test suite")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--config-paths",
        nargs="+",
        help="Specific configuration paths to validate",
    )
    parser.add_argument(
        "--include-workstation",
        action="store_true",
        help="Include workstation perspective tests",
    )
    parser.add_argument(
        "--output-format",
        choices=["console", "json", "markdown", "issues", "all"],
        default="console",
        help="Output format for results",
    )
    parser.add_argument("--output-file", help="Custom output filename (without extension)")
    parser.add_argument(
        "--export-issues",
        action="store_true",
        help="Export a detailed issue report",
    )

    args = parser.parse_args()

    reporter = HomelabTestReporter(kubeconfig_path=args.kubeconfig, log_level=args.log_level)

    # Run comprehensive test suite
    result = reporter.run_comprehensive_test_suite(
        config_paths=args.config_paths,
        include_workstation_tests=args.include_workstation,
    )

    # Output results
    if args.output_format in ["console", "all"]:
        reporter.print_console_summary(result)

    if args.output_format in ["json", "all"]:
        reporter.export_json_report(result, args.output_file)

    if args.output_format in ["markdown", "all"]:
        reporter.export_markdown_report(result, args.output_file)

    if args.output_format in ["issues", "all"] or args.export_issues:
        reporter.export_issue_report(args.output_file)

    return 0 if result.overall_status != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
