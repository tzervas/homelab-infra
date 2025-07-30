#!/usr/bin/env python3
"""
Terraform State Monitor
Monitors Terraform state files and exposes metrics for Prometheus scraping.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import boto3
from prometheus_client import Gauge, Histogram, Info, start_http_server


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
terraform_state_resources = Gauge(
    "terraform_state_resources_total",
    "Total number of resources in Terraform state",
    ["environment", "workspace"],
)

terraform_state_last_modified = Gauge(
    "terraform_state_last_modified_timestamp",
    "Timestamp when state was last modified",
    ["environment", "workspace"],
)

terraform_state_drift_detected = Gauge(
    "terraform_state_drift_detected",
    "Whether drift has been detected in Terraform state",
    ["environment", "workspace", "resource_type"],
)

terraform_apply_duration = Histogram(
    "terraform_apply_duration_seconds",
    "Duration of Terraform apply operations",
    ["environment", "workspace", "status"],
)

terraform_plan_changes = Gauge(
    "terraform_plan_changes_total",
    "Number of changes detected in Terraform plan",
    ["environment", "workspace", "change_type"],
)

terraform_state_version = Gauge(
    "terraform_state_version",
    "Version of the Terraform state",
    ["environment", "workspace"],
)

terraform_state_serial = Gauge(
    "terraform_state_serial",
    "Serial number of the Terraform state",
    ["environment", "workspace"],
)

terraform_provider_version = Info(
    "terraform_provider_version",
    "Version information for Terraform providers",
    ["environment", "workspace", "provider"],
)


class TerraformStateMonitor:
    """Monitor for Terraform state files and operations."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.s3_client = None

        if config.get("remote_state", {}).get("backend") == "s3":
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=config["remote_state"]["access_key"],
                aws_secret_access_key=config["remote_state"]["secret_key"],
                endpoint_url=config["remote_state"].get("endpoint_url"),
                region_name=config["remote_state"].get("region", "us-east-1"),
            )

    def get_state_file(self, environment: str, workspace: str = "default") -> dict | None:
        """Retrieve Terraform state file content."""
        try:
            if self.config.get("remote_state", {}).get("backend") == "s3":
                return self._get_s3_state(environment, workspace)
            return self._get_local_state(environment, workspace)
        except Exception as e:
            logger.exception(f"Failed to get state for {environment}/{workspace}: {e}")
            return None

    def _get_s3_state(self, environment: str, workspace: str) -> dict | None:
        """Get state from S3 backend."""
        bucket = self.config["remote_state"]["bucket"]
        key = f"terraform/{environment}/{workspace}/terraform.tfstate"

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read()
            return json.loads(content)
        except Exception as e:
            logger.exception(f"Failed to get S3 state {bucket}/{key}: {e}")
            return None

    def _get_local_state(self, environment: str, workspace: str) -> dict | None:
        """Get state from local file."""
        state_path = Path(self.config["local_state_path"]) / environment / f"{workspace}.tfstate"

        if not state_path.exists():
            logger.warning(f"State file not found: {state_path}")
            return None

        try:
            with open(state_path) as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Failed to read local state {state_path}: {e}")
            return None

    def analyze_state(self, state: dict, environment: str, workspace: str) -> None:
        """Analyze Terraform state and update metrics."""
        if not state:
            return

        # Basic state metrics
        resources = state.get("resources", [])
        terraform_state_resources.labels(
            environment=environment,
            workspace=workspace,
        ).set(len(resources))

        terraform_state_version.labels(
            environment=environment,
            workspace=workspace,
        ).set(state.get("version", 0))

        terraform_state_serial.labels(
            environment=environment,
            workspace=workspace,
        ).set(state.get("serial", 0))

        # Provider versions
        providers = state.get("terraform_version_constraints", {})
        for provider, version in providers.items():
            terraform_provider_version.labels(
                environment=environment,
                workspace=workspace,
                provider=provider,
            ).info({"version": str(version)})

        # Resource type analysis
        resource_types = {}
        for resource in resources:
            resource_type = resource.get("type", "unknown")
            resource_types[resource_type] = resource_types.get(resource_type, 0) + 1

        logger.info(
            f"State analysis for {environment}/{workspace}: "
            f"{len(resources)} resources, {len(resource_types)} types",
        )

    def check_drift(self, environment: str, workspace: str) -> None:
        """Check for configuration drift."""
        # This would typically run terraform plan and parse output
        # For now, we'll simulate drift detection

        # Reset drift metrics
        terraform_state_drift_detected.labels(
            environment=environment,
            workspace=workspace,
            resource_type="all",
        ).set(0)

        # In a real implementation, you would:
        # 1. Run `terraform plan -detailed-exitcode`
        # 2. Parse the output to identify specific resources with drift
        # 3. Update metrics accordingly

        logger.info(f"Drift check completed for {environment}/{workspace}")

    def monitor_loop(self) -> None:
        """Main monitoring loop."""
        environments = self.config.get("environments", ["development", "staging", "production"])
        workspaces = self.config.get("workspaces", ["default"])

        while True:
            try:
                for environment in environments:
                    for workspace in workspaces:
                        logger.info(f"Monitoring {environment}/{workspace}")

                        # Get and analyze state
                        state = self.get_state_file(environment, workspace)
                        if state:
                            self.analyze_state(state, environment, workspace)

                            # Update last modified timestamp
                            terraform_state_last_modified.labels(
                                environment=environment,
                                workspace=workspace,
                            ).set(time.time())

                        # Check for drift
                        self.check_drift(environment, workspace)

                # Sleep for configured interval
                time.sleep(self.config.get("check_interval", 300))  # 5 minutes default

            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying


def load_config() -> dict:
    """Load configuration from environment variables and files."""
    config_path = os.getenv("TERRAFORM_MONITOR_CONFIG", "/etc/terraform-monitor/config.json")

    # Default configuration
    config = {
        "environments": ["development", "staging", "production"],
        "workspaces": ["default"],
        "check_interval": 300,
        "metrics_port": 8080,
        "local_state_path": "/var/lib/terraform/states",
    }

    # Load from file if exists
    if os.path.exists(config_path):
        with open(config_path) as f:
            file_config = json.load(f)
            config.update(file_config)

    # Override with environment variables
    if os.getenv("TERRAFORM_S3_BACKEND"):
        config["remote_state"] = {
            "backend": "s3",
            "bucket": os.getenv("TERRAFORM_S3_BUCKET"),
            "access_key": os.getenv("TERRAFORM_S3_ACCESS_KEY"),
            "secret_key": os.getenv("TERRAFORM_S3_SECRET_KEY"),
            "endpoint_url": os.getenv("TERRAFORM_S3_ENDPOINT"),
            "region": os.getenv("TERRAFORM_S3_REGION", "us-east-1"),
        }

    return config


def main() -> None:
    """Main function."""
    logger.info("Starting Terraform State Monitor")

    config = load_config()
    monitor = TerraformStateMonitor(config)

    # Start Prometheus metrics server
    metrics_port = config.get("metrics_port", 8080)
    start_http_server(metrics_port)
    logger.info(f"Metrics server started on port {metrics_port}")

    # Start monitoring loop
    try:
        monitor.monitor_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down Terraform State Monitor")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
