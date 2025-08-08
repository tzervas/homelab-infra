#!/usr/bin/env python3
"""
K3s Report Parser for handling test reports.

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class K3sReportParser:
    """Parses and validates K3s validation test reports."""

    def __init__(self):
        """Initialize the report parser."""
        self.logger = logging.getLogger(__name__)

    def parse_validation_report(self, reports_dir: Path) -> dict[str, Any]:
        """Parse and validate the most recent K3s validation report.

        Args:
            reports_dir: Directory containing the test reports.

        Returns:
            Dictionary containing parsed and sanitized report data.
        """
        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cluster_info": {},
            "summary": {},
            "test_suite": "K3s Validation",
            "namespace": "k3s-test",
        }

        try:
            report_files = (
                list(reports_dir.glob("test-*.json"))
                if reports_dir.exists()
                else []
            )

            if report_files:
                latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
                try:
                    with open(latest_report) as f:
                        loaded_data = json.load(f)
                        
                        # Sanitize and validate loaded data
                        report_data["summary"] = (
                            loaded_data.get("summary", {})
                            if isinstance(loaded_data.get("summary"), dict)
                            else {}
                        )
                        report_data["cluster_info"] = (
                            loaded_data.get("cluster_info", {})
                            if isinstance(loaded_data.get("cluster_info"), dict)
                            else {}
                        )
                        # Limit string lengths to prevent potential issues
                        report_data["test_suite"] = str(loaded_data.get("test_suite", report_data["test_suite"]))[:100]
                        report_data["namespace"] = str(loaded_data.get("namespace", report_data["namespace"]))[:50]
                        report_data["report_files"] = [str(f) for f in report_files]

                except (json.JSONDecodeError, OSError) as e:
                    self.logger.warning(f"Failed to parse K3s report {latest_report}: {e}")
            else:
                self.logger.warning("No report files found in the reports directory")

        except Exception as e:
            self.logger.error(f"Error during report parsing: {e}")

        return report_data
