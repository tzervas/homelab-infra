#!/usr/bin/env python3
"""
Integrated Test Orchestrator for Homelab Infrastructure Testing
Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.

This module provides integration between the Python-based testing framework
in scripts/testing/ and the bash-based K3s validation framework in testing/k3s-validation/.
It serves as a unified entry point for all testing operations.
"""

import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    from .test_reporter import HomelabTestReporter, TestSuiteResult
except ImportError:
    from test_reporter import HomelabTestReporter, TestSuiteResult


def sanitize_categories(categories: list[str] | None) -> list[str]:
    """Sanitize and validate K3s test categories to prevent command injection.
    
    Args:
        categories: List of category names to sanitize
        
    Returns:
        List of sanitized category names
        
    Raises:
        ValueError: If any category contains invalid characters
    """
    if not categories:
        return []
    
    # Define allowed K3s validation categories
    allowed_categories = {
        "core", "k3s-specific", "performance", "security", 
        "failure", "production", "all"
    }
    
    sanitized = []
    for category in categories:
        if not isinstance(category, str):
            raise ValueError(f"Category must be string, got {type(category)}")
        
        # Remove any potentially dangerous characters
        cleaned = re.sub(r'[^a-zA-Z0-9\-_]', '', category.strip())
        
        if not cleaned:
            raise ValueError(f"Invalid category after sanitization: {category}")
        
        if cleaned not in allowed_categories:
            raise ValueError(f"Unknown category: {cleaned}")
            
        sanitized.append(cleaned)
    
    return sanitized


def validate_path(path: str | Path) -> Path:
    """Validate and sanitize file paths to prevent path traversal attacks.
    
    Args:
        path: Path to validate
        
    Returns:
        Validated Path object
        
    Raises:
        ValueError: If path contains dangerous patterns
    """
    if not path:
        raise ValueError("Path cannot be empty")
    
    path_obj = Path(path)
    
    # Check for path traversal attempts
    if '..' in path_obj.parts:
        raise ValueError("Path traversal detected: path contains '..'")
    
    # Convert to absolute path and resolve to prevent symlink attacks
    try:
        resolved_path = path_obj.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")
    
    # Additional security check - ensure path doesn't contain null bytes
    path_str = str(resolved_path)
    if '\x00' in path_str:
        raise ValueError("Path contains null byte")
    
    return resolved_path


@dataclass
class K3sValidationResult:
    """Results from K3s validation framework."""

    timestamp: str
    test_suite: str
    namespace: str
    summary: dict[str, Any]
    cluster_info: dict[str, Any]
    categories_run: list[str] = field(default_factory=list)
    exit_code: int = 0
    duration: float = 0.0
    report_files: list[str] = field(default_factory=list)


@dataclass
class IntegratedTestResults:
    """Combined results from both testing frameworks."""

    timestamp: str
    duration: float
    overall_status: str
    python_framework_results: TestSuiteResult | None = None
    k3s_validation_results: K3sValidationResult | None = None
    integration_summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class IntegratedTestOrchestrator:
    """Master orchestrator for all homelab testing frameworks."""

    def __init__(
        self,
        kubeconfig_path: str | None = None,
        log_level: str = "INFO",
        base_dir: str | None = None,
    ) -> None:
        """Initialize the integrated test orchestrator."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path
        
        # Validate base directory
        try:
            self.base_dir = validate_path(Path(base_dir) if base_dir else Path.cwd())
        except ValueError as e:
            raise ValueError(f"Invalid base directory: {e}")

        # Framework paths - validate during construction to fail fast
        try:
            self.python_framework_dir = validate_path(self.base_dir / "scripts" / "testing")
            self.k3s_validation_dir = validate_path(self.base_dir / "testing" / "k3s-validation")
            self.orchestrator_path = validate_path(self.k3s_validation_dir / "orchestrator.sh")
        except ValueError as e:
            self.logger.warning(f"Framework path validation warning: {e}")
            # Still set the paths but mark as potentially invalid
            self.python_framework_dir = self.base_dir / "scripts" / "testing"
            self.k3s_validation_dir = self.base_dir / "testing" / "k3s-validation"
            self.orchestrator_path = self.k3s_validation_dir / "orchestrator.sh"

        # Results directory
        try:
            self.results_dir = validate_path(self.base_dir / "test_results")
        except ValueError:
            self.results_dir = self.base_dir / "test_results"
        self.results_dir.mkdir(exist_ok=True)

        # Initialize Python framework
        self.python_reporter = HomelabTestReporter(
            kubeconfig_path=kubeconfig_path,
            log_level=log_level,
        )

        self.logger.info("Integrated test orchestrator initialized")

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _validate_framework_availability(self) -> dict[str, bool]:
        """Check availability of both testing frameworks."""
        availability = {
            "python_framework": self.python_framework_dir.exists(),
            "k3s_validation": self.k3s_validation_dir.exists(),
            "orchestrator_script": self.orchestrator_path.exists(),
        }

        self.logger.debug(f"Framework availability: {availability}")
        return availability

    def run_python_framework_tests(
        self,
        config_paths: list[str] | None = None,
        include_workstation: bool = False,
    ) -> TestSuiteResult | None:
        """Run the Python-based testing framework."""
        self.logger.info("🐍 Running Python framework tests...")

        try:
            result = self.python_reporter.run_comprehensive_test_suite(
                config_paths=config_paths,
                include_workstation_tests=include_workstation,
            )

            self.logger.info(
                f"✅ Python framework completed with status: {result.overall_status}",
            )
            return result

        except Exception as e:
            self.logger.exception(f"❌ Python framework tests failed: {e}")
            return None

    def run_k3s_validation_tests(
        self,
        categories: list[str] | None = None,
        parallel: bool = False,
        report_format: str = "json",
    ) -> K3sValidationResult | None:
        """Run the K3s validation framework."""
        self.logger.info("🛠️ Running K3s validation tests...")

        # Validate orchestrator path
        try:
            validated_orchestrator = validate_path(self.orchestrator_path)
            if not validated_orchestrator.exists():
                self.logger.error(f"K3s orchestrator not found: {validated_orchestrator}")
                return None
        except ValueError as e:
            self.logger.error(f"Invalid orchestrator path: {e}")
            return None

        # Sanitize and validate input parameters
        try:
            sanitized_categories = sanitize_categories(categories)
        except ValueError as e:
            self.logger.error(f"Invalid categories: {e}")
            return None

        # Validate report format
        allowed_formats = {"json", "xml", "html"}
        if report_format not in allowed_formats:
            self.logger.error(f"Invalid report format: {report_format}")
            return None

        # Build command arguments securely
        cmd = [str(validated_orchestrator)]

        if sanitized_categories:
            cmd.extend(sanitized_categories)
        else:
            cmd.append("--all")

        cmd.extend([
            "--report-format",
            report_format,
        ])

        if parallel:
            cmd.append("--parallel")

        start_time = time.time()

        try:
            # Validate working directory
            validated_workdir = validate_path(self.k3s_validation_dir)
            
            # Execute the K3s validation framework
            self.logger.debug(f"Executing command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                check=False,
                cwd=validated_workdir,
                capture_output=True,
                text=True,
                timeout=1800,
            )

            duration = time.time() - start_time

            # Parse the JSON report if available
            try:
                validated_reports_dir = validate_path(self.k3s_validation_dir / "reports")
                report_files = list(validated_reports_dir.glob("test-*.json")) if validated_reports_dir.exists() else []
            except ValueError as e:
                self.logger.warning(f"Invalid reports directory path: {e}")
                report_files = []

            # Load the most recent report
            cluster_info = {}
            summary = {}
            test_suite = "K3s Validation"
            namespace = "k3s-test"

            if report_files:
                latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                try:
                    # Validate the report file path
                    validated_report = validate_path(latest_report)
                    with open(validated_report) as f:
                        report_data = json.load(f)
                        # Sanitize loaded data
                        summary = report_data.get("summary", {}) if isinstance(report_data.get("summary"), dict) else {}
                        cluster_info = report_data.get("cluster_info", {}) if isinstance(report_data.get("cluster_info"), dict) else {}
                        test_suite = str(report_data.get("test_suite", test_suite))[:100]  # Limit length
                        namespace = str(report_data.get("namespace", namespace))[:50]  # Limit length
                except (ValueError, json.JSONDecodeError, OSError) as e:
                    self.logger.warning(f"Failed to parse K3s report {latest_report}: {e}")

            k3s_result = K3sValidationResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                test_suite=test_suite,
                namespace=namespace,
                summary=summary,
                cluster_info=cluster_info,
                categories_run=sanitized_categories or ["all"],
                exit_code=result.returncode,
                duration=duration,
                report_files=[str(f) for f in report_files],
            )

            if result.returncode == 0:
                self.logger.info("✅ K3s validation tests completed successfully")
            else:
                self.logger.warning(
                    f"⚠️ K3s validation tests completed with issues (exit code: {result.returncode})",
                )
                if result.stderr:
                    self.logger.warning(f"K3s validation stderr: {result.stderr}")

            return k3s_result

        except subprocess.TimeoutExpired:
            self.logger.exception("❌ K3s validation tests timed out")
            return None
        except Exception as e:
            self.logger.exception(f"❌ K3s validation tests failed: {e}")
            return None

    def generate_integration_recommendations(
        self,
        python_results: TestSuiteResult | None,
        k3s_results: K3sValidationResult | None,
    ) -> list[str]:
        """Generate recommendations based on integrated test results."""
        recommendations = []

        # Python framework recommendations
        if python_results:
            recommendations.extend(python_results.recommendations or [])

        # K3s validation recommendations
        if k3s_results:
            if k3s_results.exit_code != 0:
                recommendations.append(
                    "Review K3s validation test failures for cluster-specific issues",
                )

            # Analyze summary for specific recommendations
            summary = k3s_results.summary
            if summary.get("failed", 0) > 0:
                recommendations.append(
                    f"Address {summary['failed']} failed K3s validation tests",
                )

            if summary.get("warnings", 0) > 0:
                recommendations.append(
                    f"Review {summary['warnings']} K3s validation warnings",
                )

        # Integration-specific recommendations
        if python_results and k3s_results:
            # Check for consistency between frameworks
            if python_results.overall_status == "fail" and k3s_results.exit_code == 0:
                recommendations.append(
                    "Investigate discrepancy between Python framework failures and K3s validation success",
                )
            elif python_results.overall_status == "pass" and k3s_results.exit_code != 0:
                recommendations.append(
                    "Investigate discrepancy between Python framework success and K3s validation failures",
                )

        # Framework availability recommendations
        availability = self._validate_framework_availability()
        if not availability["k3s_validation"]:
            recommendations.append(
                "Install K3s validation framework for comprehensive cluster testing",
            )

        return recommendations

    def run_integrated_test_suite(
        self,
        python_config_paths: list[str] | None = None,
        include_workstation: bool = False,
        k3s_categories: list[str] | None = None,
        parallel_k3s: bool = False,
        skip_python: bool = False,
        skip_k3s: bool = False,
    ) -> IntegratedTestResults:
        """Run the complete integrated test suite."""
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info("🚀 Starting integrated homelab test suite...")

        # Validate framework availability
        availability = self._validate_framework_availability()

        # Run Python framework tests
        python_results = None
        if not skip_python and availability["python_framework"]:
            python_results = self.run_python_framework_tests(
                config_paths=python_config_paths,
                include_workstation=include_workstation,
            )
        elif skip_python:
            self.logger.info("🐍 Skipping Python framework tests as requested")
        else:
            self.logger.warning("🐍 Python framework not available, skipping")

        # Run K3s validation tests
        k3s_results = None
        if not skip_k3s and availability["k3s_validation"] and availability["orchestrator_script"]:
            k3s_results = self.run_k3s_validation_tests(
                categories=k3s_categories,
                parallel=parallel_k3s,
            )
        elif skip_k3s:
            self.logger.info("🛠️ Skipping K3s validation tests as requested")
        else:
            self.logger.warning("🛠️ K3s validation framework not available, skipping")

        duration = time.time() - start_time

        # Determine overall status
        overall_status = "pass"

        if (python_results and python_results.overall_status == "fail") or (
            k3s_results and k3s_results.exit_code != 0
        ):
            overall_status = "fail"
        elif (python_results and python_results.overall_status == "warning") or (
            k3s_results and k3s_results.summary.get("warnings", 0) > 0
        ):
            overall_status = "warning"

        # Generate recommendations
        recommendations = self.generate_integration_recommendations(
            python_results,
            k3s_results,
        )

        # Create integration summary
        integration_summary = {
            "frameworks_run": [],
            "total_duration": duration,
            "python_framework_status": python_results.overall_status
            if python_results
            else "skipped",
            "k3s_validation_status": "pass"
            if k3s_results and k3s_results.exit_code == 0
            else "fail"
            if k3s_results
            else "skipped",
        }

        if python_results:
            integration_summary["frameworks_run"].append("python")
        if k3s_results:
            integration_summary["frameworks_run"].append("k3s_validation")

        # Create integrated results
        integrated_results = IntegratedTestResults(
            timestamp=timestamp,
            duration=duration,
            overall_status=overall_status,
            python_framework_results=python_results,
            k3s_validation_results=k3s_results,
            integration_summary=integration_summary,
            recommendations=recommendations,
        )

        self.logger.info(
            f"✅ Integrated test suite completed in {duration:.2f}s with status: {overall_status.upper()}",
        )

        return integrated_results

    def export_integrated_report(
        self,
        results: IntegratedTestResults,
        format_type: str = "json",
        filename: str | None = None,
    ) -> str:
        """Export integrated test results to file."""
        if not filename:
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"integrated_test_report_{timestamp_str}"

        if format_type == "json":
            filepath = self.results_dir / f"{filename}.json"

            # Convert dataclasses to dict for JSON serialization
            json_data = asdict(results)

            with open(filepath, "w") as f:
                json.dump(json_data, f, indent=2, default=str)

            self.logger.info(f"📄 Integrated JSON report exported to: {filepath}")
            return str(filepath)

        if format_type == "markdown":
            filepath = self.results_dir / f"{filename}.md"

            with open(filepath, "w") as f:
                f.write("# Integrated Homelab Infrastructure Test Report\\n\\n")
                f.write(f"**Generated:** {results.timestamp}\\n")
                f.write(f"**Duration:** {results.duration:.2f} seconds\\n")
                f.write(f"**Overall Status:** {results.overall_status.upper()}\\n\\n")

                # Integration summary
                f.write("## Integration Summary\\n\\n")
                f.writelines(
                    f"- **{key.replace('_', ' ').title()}:** {value}\\n"
                    for key, value in results.integration_summary.items()
                )
                f.write("\\n")

                # Python framework results
                if results.python_framework_results:
                    f.write("## Python Framework Results\\n\\n")
                    f.write(
                        f"**Status:** {results.python_framework_results.overall_status.upper()}\\n",
                    )
                    if results.python_framework_results.summary:
                        f.writelines(
                            f"- **{key.replace('_', ' ').title()}:** {value}\\n"
                            for key, value in results.python_framework_results.summary.items()
                        )
                    f.write("\\n")

                # K3s validation results
                if results.k3s_validation_results:
                    f.write("## K3s Validation Results\\n\\n")
                    f.write(f"**Exit Code:** {results.k3s_validation_results.exit_code}\\n")
                    if results.k3s_validation_results.summary:
                        f.writelines(
                            f"- **{key.replace('_', ' ').title()}:** {value}\\n"
                            for key, value in results.k3s_validation_results.summary.items()
                        )
                    f.write("\\n")

                # Recommendations
                if results.recommendations:
                    f.write("## Recommendations\\n\\n")
                    f.writelines(
                        f"{i}. {rec}\\n" for i, rec in enumerate(results.recommendations, 1)
                    )

            self.logger.info(f"📄 Integrated Markdown report exported to: {filepath}")
            return str(filepath)

        msg = f"Unsupported format type: {format_type}"
        raise ValueError(msg)

    def print_integrated_summary(self, results: IntegratedTestResults) -> None:
        """Print a comprehensive console summary of integrated results."""
        print("\\n🏠 INTEGRATED HOMELAB INFRASTRUCTURE TEST REPORT")
        print(f"{'=' * 60}")
        print(f"Timestamp: {results.timestamp}")
        print(f"Duration: {results.duration:.2f}s")
        print(f"Overall Status: {results.overall_status.upper()}")
        print(f"{'=' * 60}\\n")

        # Integration summary
        print("🔗 INTEGRATION SUMMARY:")
        for key, value in results.integration_summary.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

        # Python framework summary
        if results.python_framework_results:
            print("\\n🐍 PYTHON FRAMEWORK RESULTS:")
            print(f"  Status: {results.python_framework_results.overall_status.upper()}")
            if results.python_framework_results.summary:
                for key, value in results.python_framework_results.summary.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")

        # K3s validation summary
        if results.k3s_validation_results:
            print("\\n🛠️ K3S VALIDATION RESULTS:")
            print(f"  Exit Code: {results.k3s_validation_results.exit_code}")
            print(f"  Test Suite: {results.k3s_validation_results.test_suite}")
            if results.k3s_validation_results.summary:
                for key, value in results.k3s_validation_results.summary.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")

        # Recommendations
        if results.recommendations:
            print(f"\\n💡 RECOMMENDATIONS ({len(results.recommendations)}):")
            for i, rec in enumerate(results.recommendations, 1):
                print(f"  {i}. {rec}")

        print(f"\\n{'=' * 60}")


def main() -> int:
    """Main function for integrated testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run integrated homelab test suite (Python + K3s validation)",
    )
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--python-config-paths",
        nargs="+",
        help="Configuration paths for Python framework validation",
    )
    parser.add_argument(
        "--include-workstation",
        action="store_true",
        help="Include workstation perspective tests in Python framework",
    )
    parser.add_argument(
        "--k3s-categories",
        nargs="+",
        choices=["core", "k3s-specific", "performance", "security", "failure", "production"],
        help="K3s validation categories to run",
    )
    parser.add_argument(
        "--parallel-k3s",
        action="store_true",
        help="Run K3s validation tests in parallel",
    )
    parser.add_argument(
        "--skip-python",
        action="store_true",
        help="Skip Python framework tests",
    )
    parser.add_argument(
        "--skip-k3s",
        action="store_true",
        help="Skip K3s validation tests",
    )
    parser.add_argument(
        "--output-format",
        choices=["console", "json", "markdown", "all"],
        default="console",
        help="Output format for results",
    )
    parser.add_argument("--output-file", help="Custom output filename (without extension)")

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = IntegratedTestOrchestrator(
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level,
    )

    # Run integrated test suite
    results = orchestrator.run_integrated_test_suite(
        python_config_paths=args.python_config_paths,
        include_workstation=args.include_workstation,
        k3s_categories=args.k3s_categories,
        parallel_k3s=args.parallel_k3s,
        skip_python=args.skip_python,
        skip_k3s=args.skip_k3s,
    )

    # Output results
    if args.output_format in ["console", "all"]:
        orchestrator.print_integrated_summary(results)

    if args.output_format in ["json", "all"]:
        orchestrator.export_integrated_report(results, "json", args.output_file)

    if args.output_format in ["markdown", "all"]:
        orchestrator.export_integrated_report(results, "markdown", args.output_file)

    return 0 if results.overall_status != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
