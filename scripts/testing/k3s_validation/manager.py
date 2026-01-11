#!/usr/bin/env python3
"""
K3s Validation Manager for orchestrating validation process.

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .parser import K3sReportParser
from .process import K3sProcessExecutor


@dataclass
class K3sValidationResult:
    """Results from K3s validation framework."""

    timestamp: str
    test_suite: str
    namespace: str
    summary: dict[str, Any]
    cluster_info: dict[str, Any]
    categories_run: list[str]
    exit_code: int = 0
    duration: float = 0.0
    report_files: list[str] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.report_files is None:
            self.report_files = []


class K3sValidationManager:
    """Manages K3s validation test execution and reporting."""

    def __init__(self, base_dir: Path, timeout_config=None):
        """Initialize the validation manager.

        Args:
            base_dir: Base directory for the project.
            timeout_config: Optional configuration for operation timeouts.
        """
        self.logger = logging.getLogger(__name__)
        self.base_dir = base_dir
        self.k3s_validation_dir = base_dir / "testing" / "k3s-validation"
        self.orchestrator_path = self.k3s_validation_dir / "orchestrator.sh"
        self.reports_dir = self.k3s_validation_dir / "reports"

        # Initialize helper components
        self.process_executor = K3sProcessExecutor(timeout_config)
        self.report_parser = K3sReportParser()

    def validate_k3s_config(self, categories: list[str], report_format: str = "json", parallel: bool = False) -> K3sValidationResult:
        """Run K3s validation with specified configuration.

        Args:
            categories: List of test categories to run.
            report_format: Format for test reports (json, xml, html).
            parallel: Whether to run tests in parallel.

        Returns:
            K3sValidationResult containing test results.

        Raises:
            ValueError: If input parameters are invalid.
            Exception: For execution or validation failures.
        """
        # Validate report format
        allowed_formats = {"json", "xml", "html"}
        if report_format not in allowed_formats:
            raise ValueError(f"Invalid report format: {report_format}")

        # Build command
        cmd = [str(self.orchestrator_path)]
        if categories:
            cmd.extend(categories)
        else:
            cmd.append("--all")

        cmd.extend(["--report-format", report_format])
        if parallel:
            cmd.append("--parallel")

        # Record start time for duration calculation
        start_time = time.time()

        try:
            # Execute validation
            result = self.process_executor.execute_k3s_validation(cmd, self.k3s_validation_dir)
            
            # Parse reports
            report_data = self.report_parser.parse_validation_report(self.reports_dir)
            
            # Calculate duration
            duration = time.time() - start_time

            # Create validation result
            validation_result = K3sValidationResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                test_suite=report_data["test_suite"],
                namespace=report_data["namespace"],
                summary=report_data["summary"],
                cluster_info=report_data["cluster_info"],
                categories_run=categories or ["all"],
                exit_code=result.returncode,
                duration=duration,
                report_files=report_data.get("report_files", [])
            )

            # Log results
            if result.returncode == 0:
                self.logger.info("✅ K3s validation tests completed successfully")
            else:
                self.logger.warning(
                    f"⚠️ K3s validation tests completed with issues (exit code: {result.returncode})"
                )
                if result.stderr:
                    self.logger.warning(f"K3s validation stderr: {result.stderr}")

            return validation_result

        except Exception as e:
            self.logger.error(f"❌ K3s validation failed: {e}")
            raise
