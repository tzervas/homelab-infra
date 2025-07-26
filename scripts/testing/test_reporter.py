#!/usr/bin/env python3
"""
Test Reporter & Aggregator for Homelab Infrastructure Testing Framework

This module orchestrates all testing modules, aggregates results, and provides
comprehensive reporting in multiple formats with trend analysis and metrics.
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import all testing modules
try:
    from .config_validator import ConfigValidator, ValidationResult
    from .infrastructure_health import InfrastructureHealthMonitor, ClusterHealth
    from .service_checker import ServiceDeploymentChecker, ServiceStatus
    from .network_security import NetworkSecurityValidator, SecurityStatus
    from .integration_tester import IntegrationConnectivityTester, IntegrationTestResult
except ImportError:
    try:
        from config_validator import ConfigValidator, ValidationResult
        from infrastructure_health import InfrastructureHealthMonitor, ClusterHealth
        from service_checker import ServiceDeploymentChecker, ServiceStatus
        from network_security import NetworkSecurityValidator, SecurityStatus
        from integration_tester import IntegrationConnectivityTester, IntegrationTestResult
    except ImportError as e:
        print(f"Warning: Could not import some testing modules: {e}")
        print("Some functionality may be limited.")


@dataclass
class TestSuiteResult:
    """Comprehensive test suite results."""
    timestamp: str
    duration: float
    overall_status: str  # "pass", "fail", "warning"
    summary: Dict[str, Any] = field(default_factory=dict)
    config_validation: Optional[List[ValidationResult]] = None
    infrastructure_health: Optional[ClusterHealth] = None
    service_deployment: Optional[Dict[str, ServiceStatus]] = None
    network_security: Optional[List[SecurityStatus]] = None
    integration_tests: Optional[List[IntegrationTestResult]] = None
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class HomelabTestReporter:
    """Comprehensive test reporter and aggregator."""

    def __init__(self, kubeconfig_path: Optional[str] = None, log_level: str = "INFO"):
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

        try:
            if 'ConfigValidator' in globals():
                self.config_validator = ConfigValidator(log_level)
            if 'InfrastructureHealthMonitor' in globals():
                self.infra_monitor = InfrastructureHealthMonitor(kubeconfig_path, log_level)
            if 'ServiceDeploymentChecker' in globals():
                self.service_checker = ServiceDeploymentChecker(kubeconfig_path, log_level)
            if 'NetworkSecurityValidator' in globals():
                self.security_validator = NetworkSecurityValidator(kubeconfig_path, log_level)
            if 'IntegrationConnectivityTester' in globals():
                self.integration_tester = IntegrationConnectivityTester(kubeconfig_path, log_level)
        except Exception as e:
            self.logger.error(f"Failed to initialize testing modules: {e}")

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run_config_validation(self, config_paths: List[str] = None) -> Optional[List[ValidationResult]]:
        """Run configuration validation tests."""
        if not self.config_validator:
            self.logger.warning("Config validator not available")
            return None

        try:
            self.logger.info("Running configuration validation...")

            if config_paths:
                results = []
                for path in config_paths:
                    if os.path.isdir(path):
                        results.extend(self.config_validator.validate_directory(path))
                    else:
                        results.append(self.config_validator.validate_file(path))
            else:
                # Default configuration paths for homelab
                default_paths = [
                    "ansible/inventory",
                    "helm/environments",
                    "examples/private-config-template"
                ]
                results = []
                for path in default_paths:
                    if os.path.exists(path):
                        results.extend(self.config_validator.validate_directory(path))

            return results

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return None

    def run_infrastructure_health_check(self) -> Optional[ClusterHealth]:
        """Run infrastructure health monitoring."""
        if not self.infra_monitor:
            self.logger.warning("Infrastructure monitor not available")
            return None

        try:
            self.logger.info("Running infrastructure health check...")
            return self.infra_monitor.get_cluster_health()
        except Exception as e:
            self.logger.error(f"Infrastructure health check failed: {e}")
            return None

    def run_service_deployment_check(self) -> Optional[Dict[str, ServiceStatus]]:
        """Run service deployment validation."""
        if not self.service_checker:
            self.logger.warning("Service checker not available")
            return None

        try:
            self.logger.info("Running service deployment check...")
            return self.service_checker.check_all_services()
        except Exception as e:
            self.logger.error(f"Service deployment check failed: {e}")
            return None

    def run_network_security_validation(self) -> Optional[List[SecurityStatus]]:
        """Run network and security validation."""
        if not self.security_validator:
            self.logger.warning("Security validator not available")
            return None

        try:
            self.logger.info("Running network and security validation...")
            return self.security_validator.run_comprehensive_security_scan()
        except Exception as e:
            self.logger.error(f"Network security validation failed: {e}")
            return None

    def run_integration_tests(self, include_workstation: bool = False) -> Optional[List[IntegrationTestResult]]:
        """Run integration and connectivity tests."""
        if not self.integration_tester:
            self.logger.warning("Integration tester not available")
            return None

        try:
            self.logger.info("Running integration tests...")
            return self.integration_tester.run_comprehensive_integration_tests(include_workstation)
        except Exception as e:
            self.logger.error(f"Integration tests failed: {e}")
            return None

    def calculate_metrics(self, result: TestSuiteResult) -> Dict[str, Any]:
        """Calculate test metrics and statistics."""
        metrics = {
            "total_test_duration": result.duration,
            "timestamp": result.timestamp
        }

        # Config validation metrics
        if result.config_validation:
            valid_configs = sum(1 for r in result.config_validation if r.is_valid)
            total_configs = len(result.config_validation)
            metrics["config_validation"] = {
                "total_files": total_configs,
                "valid_files": valid_configs,
                "validation_rate": (valid_configs / total_configs * 100) if total_configs > 0 else 0
            }

        # Infrastructure health metrics
        if result.infrastructure_health:
            metrics["infrastructure_health"] = {
                "health_percentage": result.infrastructure_health.health_percentage,
                "total_checks": result.infrastructure_health.total_checks,
                "healthy_checks": result.infrastructure_health.healthy_checks
            }

        # Service deployment metrics
        if result.service_deployment:
            ready_services = sum(1 for s in result.service_deployment.values() if s.is_ready)
            total_services = len(result.service_deployment)
            metrics["service_deployment"] = {
                "total_services": total_services,
                "ready_services": ready_services,
                "readiness_rate": (ready_services / total_services * 100) if total_services > 0 else 0
            }

        # Security metrics
        if result.network_security:
            secure_checks = sum(1 for s in result.network_security if s.is_secure)
            total_security_checks = len(result.network_security)
            metrics["network_security"] = {
                "total_checks": total_security_checks,
                "secure_checks": secure_checks,
                "security_score": (secure_checks / total_security_checks * 100) if total_security_checks > 0 else 0
            }

        # Integration test metrics
        if result.integration_tests:
            passed_tests = sum(1 for t in result.integration_tests if t.passed)
            total_tests = len(result.integration_tests)
            avg_duration = sum(t.duration for t in result.integration_tests) / total_tests if total_tests > 0 else 0
            metrics["integration_tests"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_test_duration": avg_duration
            }

        return metrics

    def generate_recommendations(self, result: TestSuiteResult) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        # Config validation recommendations
        if result.config_validation:
            invalid_configs = [r for r in result.config_validation if not r.is_valid]
            if invalid_configs:
                recommendations.append(f"Fix {len(invalid_configs)} invalid configuration files")

        # Infrastructure health recommendations
        if result.infrastructure_health and result.infrastructure_health.cluster_status != "healthy":
            recommendations.append("Address infrastructure health issues before proceeding")

        # Service deployment recommendations
        if result.service_deployment:
            unready_services = [name for name, status in result.service_deployment.items() if not status.is_ready]
            if unready_services:
                recommendations.append(f"Investigate unready services: {', '.join(unready_services)}")

        # Security recommendations
        if result.network_security:
            security_issues = [s for s in result.network_security if s.status in ["warning", "vulnerable"]]
            if security_issues:
                recommendations.append("Review and address security warnings")
                for issue in security_issues:
                    recommendations.extend(issue.recommendations)

        # Integration test recommendations
        if result.integration_tests:
            failed_tests = [t for t in result.integration_tests if t.status == "fail"]
            if failed_tests:
                recommendations.append("Fix failing integration tests for complete system validation")

        return recommendations

    def run_comprehensive_test_suite(self, config_paths: List[str] = None,
                                   include_workstation_tests: bool = False) -> TestSuiteResult:
        """Run the complete test suite and aggregate results."""
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        self.logger.info("🚀 Starting comprehensive homelab testing suite...")

        # Run all test modules
        config_results = self.run_config_validation(config_paths)
        infra_health = self.run_infrastructure_health_check()
        service_status = self.run_service_deployment_check()
        security_results = self.run_network_security_validation()
        integration_results = self.run_integration_tests(include_workstation_tests)

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
            integration_tests=integration_results
        )

        # Calculate metrics and recommendations
        result.metrics = self.calculate_metrics(result)
        result.recommendations = self.generate_recommendations(result)

        # Create summary
        result.summary = {
            "overall_status": overall_status,
            "test_duration": duration,
            "modules_run": sum(1 for r in [config_results, infra_health, service_status, security_results, integration_results] if r is not None),
            "total_recommendations": len(result.recommendations)
        }

        self.logger.info(f"✅ Test suite completed in {duration:.2f}s with status: {overall_status.upper()}")

        return result

    def export_json_report(self, result: TestSuiteResult, filename: Optional[str] = None) -> str:
        """Export results to JSON format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"homelab_test_report_{timestamp}.json"

        filepath = self.results_dir / filename

        # Convert dataclasses to dict for JSON serialization
        json_data = asdict(result)

        with open(filepath, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)

        self.logger.info(f"JSON report exported to: {filepath}")
        return str(filepath)

    def export_markdown_report(self, result: TestSuiteResult, filename: Optional[str] = None) -> str:
        """Export results to Markdown format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"homelab_test_report_{timestamp}.md"

        filepath = self.results_dir / filename

        with open(filepath, 'w') as f:
            f.write(f"# Homelab Infrastructure Test Report\n\n")
            f.write(f"**Generated:** {result.timestamp}\n")
            f.write(f"**Duration:** {result.duration:.2f} seconds\n")
            f.write(f"**Overall Status:** {result.overall_status.upper()}\n\n")

            # Summary section
            f.write("## Summary\n\n")
            for key, value in result.summary.items():
                f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            f.write("\n")

            # Metrics section
            if result.metrics:
                f.write("## Metrics\n\n")
                for category, metrics in result.metrics.items():
                    if isinstance(metrics, dict):
                        f.write(f"### {category.replace('_', ' ').title()}\n\n")
                        for key, value in metrics.items():
                            f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
                        f.write("\n")

            # Recommendations section
            if result.recommendations:
                f.write("## Recommendations\n\n")
                for i, rec in enumerate(result.recommendations, 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")

            # Detailed results sections
            if result.config_validation:
                f.write("## Configuration Validation\n\n")
                valid_count = sum(1 for r in result.config_validation if r.is_valid)
                total_count = len(result.config_validation)
                f.write(f"**Status:** {valid_count}/{total_count} files valid\n\n")

            if result.infrastructure_health:
                f.write("## Infrastructure Health\n\n")
                f.write(f"**Overall Status:** {result.infrastructure_health.cluster_status.upper()}\n")
                f.write(f"**Health Score:** {result.infrastructure_health.health_percentage:.1f}%\n\n")

            if result.service_deployment:
                f.write("## Service Deployment\n\n")
                for service_name, status in result.service_deployment.items():
                    icon = "✅" if status.is_ready else "❌"
                    f.write(f"- {icon} **{service_name}:** {status.message}\n")
                f.write("\n")

            if result.network_security:
                f.write("## Network & Security\n\n")
                for security in result.network_security:
                    icon = "🔒" if security.is_secure else "⚠️" if security.status == "warning" else "🚨"
                    f.write(f"- {icon} **{security.check_type.replace('_', ' ').title()}:** {security.message}\n")
                f.write("\n")

            if result.integration_tests:
                f.write("## Integration Tests\n\n")
                for test in result.integration_tests:
                    icon = "✅" if test.passed else "❌" if test.status == "fail" else "⚠️"
                    f.write(f"- {icon} **{test.test_name.replace('_', ' ').title()}:** {test.message}\n")

        self.logger.info(f"Markdown report exported to: {filepath}")
        return str(filepath)

    def print_console_summary(self, result: TestSuiteResult) -> None:
        """Print a comprehensive console summary."""
        print(f"\n🏠 HOMELAB INFRASTRUCTURE TEST REPORT")
        print(f"{'='*60}")
        print(f"Timestamp: {result.timestamp}")
        print(f"Duration: {result.duration:.2f}s")
        print(f"Overall Status: {result.overall_status.upper()}")
        print(f"{'='*60}\n")

        # Summary metrics
        if result.metrics:
            print("📊 METRICS SUMMARY:")
            for category, metrics in result.metrics.items():
                if isinstance(metrics, dict):
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for key, value in metrics.items():
                        if isinstance(value, float):
                            print(f"  {key.replace('_', ' ').title()}: {value:.1f}")
                        else:
                            print(f"  {key.replace('_', ' ').title()}: {value}")

        # Recommendations
        if result.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(result.recommendations)}):")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"  {i}. {rec}")

        print(f"\n{'='*60}")


def main():
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run comprehensive homelab test suite")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--config-paths", nargs="+", help="Specific configuration paths to validate")
    parser.add_argument("--include-workstation", action="store_true",
                       help="Include workstation perspective tests")
    parser.add_argument("--output-format", choices=["console", "json", "markdown", "all"],
                       default="console", help="Output format for results")
    parser.add_argument("--output-file", help="Custom output filename (without extension)")

    args = parser.parse_args()

    reporter = HomelabTestReporter(
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level
    )

    # Run comprehensive test suite
    result = reporter.run_comprehensive_test_suite(
        config_paths=args.config_paths,
        include_workstation_tests=args.include_workstation
    )

    # Output results
    if args.output_format in ["console", "all"]:
        reporter.print_console_summary(result)

    if args.output_format in ["json", "all"]:
        reporter.export_json_report(result, args.output_file)

    if args.output_format in ["markdown", "all"]:
        reporter.export_markdown_report(result, args.output_file)

    return 0 if result.overall_status != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
