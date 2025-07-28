#!/usr/bin/env python3
"""Terraform State Validation Module for Homelab Infrastructure Testing Framework.

This module provides comprehensive validation of Terraform state to ensure
infrastructure matches the desired configuration and is properly deployed.
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TerraformResource:
    """Represents a Terraform resource in the state."""

    address: str
    type: str
    name: str
    provider: str
    instances: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if resource has valid instances."""
        return len(self.instances) > 0 and all(
            instance.get("attributes", {}) is not None for instance in self.instances
        )


@dataclass
class TerraformValidationResult:
    """Result of Terraform state validation."""

    component: str
    is_valid: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    resources_checked: int = 0
    resources_valid: int = 0

    @property
    def validation_percentage(self) -> float:
        """Calculate validation success percentage."""
        if self.resources_checked == 0:
            return 0.0
        return (self.resources_valid / self.resources_checked) * 100


class TerraformStateValidator:
    """Validates Terraform state and infrastructure compliance."""

    def __init__(self, terraform_dir: str = "terraform", log_level: str = "INFO") -> None:
        """Initialize the Terraform validator."""
        self.logger = self._setup_logging(log_level)
        self.terraform_dir = Path(terraform_dir)
        self.state_data: dict[str, Any] | None = None

        # Expected resource types for homelab infrastructure
        self.expected_resources = {
            "kubernetes_namespace": ["metallb-system", "cert-manager", "ingress-nginx"],
            "helm_release": ["metallb", "cert-manager", "ingress-nginx"],
            "kubernetes_secret": [],  # Will be populated dynamically
            "kubernetes_config_map": [],  # Will be populated dynamically
        }

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

    def _run_terraform_command(self, command: list[str]) -> str | None:
        """Run a Terraform command and return output."""
        try:
            # Change to terraform directory
            original_cwd = Path.cwd()
            self.terraform_dir.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["terraform", *command],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode != 0:
                self.logger.error(f"Terraform command failed: {' '.join(command)}")
                self.logger.error(f"Error: {result.stderr}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            self.logger.exception(f"Terraform command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            self.logger.exception(f"Failed to run terraform command: {e}")
            return None
        finally:
            # Return to original directory
            try:
                original_cwd.resolve()  # Test if the directory still exists
            except (OSError, FileNotFoundError):
                pass  # Directory might have been deleted

    def load_terraform_state(self) -> bool:
        """Load and parse Terraform state."""
        self.logger.info("Loading Terraform state...")

        # Check if terraform is initialized
        if not (self.terraform_dir / ".terraform").exists():
            self.logger.error("Terraform not initialized. Run 'terraform init' first.")
            return False

        # Get state in JSON format
        state_output = self._run_terraform_command(["show", "-json"])
        if not state_output:
            self.logger.error("Failed to retrieve Terraform state")
            return False

        try:
            self.state_data = json.loads(state_output)
            self.logger.info("Terraform state loaded successfully")
            return True
        except json.JSONDecodeError as e:
            self.logger.exception(f"Failed to parse Terraform state JSON: {e}")
            return False

    def extract_resources(self) -> list[TerraformResource]:
        """Extract resources from Terraform state."""
        if not self.state_data:
            return []

        resources = []

        # Extract resources from state
        values = self.state_data.get("values", {})
        root_module = values.get("root_module", {})

        # Process root module resources
        for resource_data in root_module.get("resources", []):
            resource = TerraformResource(
                address=resource_data.get("address", ""),
                type=resource_data.get("type", ""),
                name=resource_data.get("name", ""),
                provider=resource_data.get("provider_name", ""),
                instances=[
                    {
                        "attributes": resource_data.get("values", {}),
                        "schema_version": resource_data.get("schema_version", 0),
                    }
                ],
            )
            resources.append(resource)

        # Process child modules if any
        for child_module in root_module.get("child_modules", []):
            for resource_data in child_module.get("resources", []):
                resource = TerraformResource(
                    address=resource_data.get("address", ""),
                    type=resource_data.get("type", ""),
                    name=resource_data.get("name", ""),
                    provider=resource_data.get("provider_name", ""),
                    instances=[
                        {
                            "attributes": resource_data.get("values", {}),
                            "schema_version": resource_data.get("schema_version", 0),
                        }
                    ],
                )
                resources.append(resource)

        self.logger.info(f"Extracted {len(resources)} resources from Terraform state")
        return resources

    def validate_kubernetes_resources(self) -> TerraformValidationResult:
        """Validate Kubernetes resources in Terraform state."""
        resources = self.extract_resources()
        k8s_resources = [r for r in resources if r.provider in ["kubernetes", "helm"]]

        if not k8s_resources:
            return TerraformValidationResult(
                component="kubernetes_resources",
                is_valid=False,
                message="No Kubernetes resources found in Terraform state",
                resources_checked=0,
                resources_valid=0,
            )

        valid_resources = [r for r in k8s_resources if r.is_valid]

        # Check for expected namespaces
        namespace_resources = [r for r in k8s_resources if r.type == "kubernetes_namespace"]
        expected_namespaces = self.expected_resources.get("kubernetes_namespace", [])

        missing_namespaces = []
        for expected_ns in expected_namespaces:
            found = any(
                expected_ns
                in r.instances[0].get("attributes", {}).get("metadata", [{}])[0].get("name", "")
                for r in namespace_resources
                if r.instances
            )
            if not found:
                missing_namespaces.append(expected_ns)

        validation_percentage = (len(valid_resources) / len(k8s_resources)) * 100

        if missing_namespaces:
            message = f"Missing expected namespaces: {', '.join(missing_namespaces)}"
            is_valid = False
        elif validation_percentage < 90:
            message = f"Only {validation_percentage:.1f}% of Kubernetes resources are valid"
            is_valid = False
        else:
            message = f"All {len(valid_resources)} Kubernetes resources are valid"
            is_valid = True

        return TerraformValidationResult(
            component="kubernetes_resources",
            is_valid=is_valid,
            message=message,
            details={
                "total_k8s_resources": len(k8s_resources),
                "valid_k8s_resources": len(valid_resources),
                "namespace_resources": len(namespace_resources),
                "missing_namespaces": missing_namespaces,
                "resource_types": list({r.type for r in k8s_resources}),
            },
            resources_checked=len(k8s_resources),
            resources_valid=len(valid_resources),
        )

    def validate_helm_releases(self) -> TerraformValidationResult:
        """Validate Helm releases in Terraform state."""
        resources = self.extract_resources()
        helm_resources = [r for r in resources if r.type == "helm_release"]

        if not helm_resources:
            return TerraformValidationResult(
                component="helm_releases",
                is_valid=False,
                message="No Helm releases found in Terraform state",
                resources_checked=0,
                resources_valid=0,
            )

        valid_releases = []
        release_details = []

        for resource in helm_resources:
            if not resource.instances:
                continue

            attributes = resource.instances[0].get("attributes", {})
            release_name = attributes.get("name", "")
            namespace = attributes.get("namespace", "")
            chart = attributes.get("chart", "")
            status = attributes.get("status", "")

            is_valid = all([release_name, namespace, chart, status == "deployed"])

            if is_valid:
                valid_releases.append(resource)

            release_details.append(
                {
                    "name": release_name,
                    "namespace": namespace,
                    "chart": chart,
                    "status": status,
                    "valid": is_valid,
                }
            )

        validation_percentage = (len(valid_releases) / len(helm_resources)) * 100

        if validation_percentage < 90:
            message = f"Only {len(valid_releases)}/{len(helm_resources)} Helm releases are valid"
            is_valid = False
        else:
            message = f"All {len(valid_releases)} Helm releases are valid"
            is_valid = True

        return TerraformValidationResult(
            component="helm_releases",
            is_valid=is_valid,
            message=message,
            details={
                "total_releases": len(helm_resources),
                "valid_releases": len(valid_releases),
                "releases": release_details,
            },
            resources_checked=len(helm_resources),
            resources_valid=len(valid_releases),
        )

    def validate_infrastructure_state(self) -> TerraformValidationResult:
        """Validate overall infrastructure state."""
        if not self.load_terraform_state():
            return TerraformValidationResult(
                component="infrastructure_state",
                is_valid=False,
                message="Failed to load Terraform state",
                resources_checked=0,
                resources_valid=0,
            )

        resources = self.extract_resources()

        if not resources:
            return TerraformValidationResult(
                component="infrastructure_state",
                is_valid=False,
                message="No resources found in Terraform state",
                resources_checked=0,
                resources_valid=0,
            )

        valid_resources = [r for r in resources if r.is_valid]
        validation_percentage = (len(valid_resources) / len(resources)) * 100

        # Analyze resource distribution
        resource_types = {}
        for resource in resources:
            resource_types[resource.type] = resource_types.get(resource.type, 0) + 1

        if validation_percentage < 95:
            message = f"Infrastructure state validation: {validation_percentage:.1f}% valid"
            is_valid = False
        else:
            message = f"Infrastructure state is healthy: {len(valid_resources)}/{len(resources)} resources valid"
            is_valid = True

        return TerraformValidationResult(
            component="infrastructure_state",
            is_valid=is_valid,
            message=message,
            details={
                "total_resources": len(resources),
                "valid_resources": len(valid_resources),
                "resource_types": resource_types,
                "validation_percentage": validation_percentage,
            },
            resources_checked=len(resources),
            resources_valid=len(valid_resources),
        )

    def run_comprehensive_validation(self) -> list[TerraformValidationResult]:
        """Run comprehensive Terraform state validation."""
        self.logger.info("Starting comprehensive Terraform state validation...")

        results = []

        # Validate overall infrastructure state
        results.append(self.validate_infrastructure_state())

        # Only proceed with detailed validation if state is loaded
        if self.state_data:
            results.append(self.validate_kubernetes_resources())
            results.append(self.validate_helm_releases())

        self.logger.info(f"Terraform validation completed with {len(results)} checks")
        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Terraform state for homelab infrastructure"
    )
    parser.add_argument("--terraform-dir", default="terraform", help="Path to Terraform directory")
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    parser.add_argument(
        "--component",
        choices=["state", "kubernetes", "helm"],
        help="Validate specific component only",
    )

    args = parser.parse_args()

    validator = TerraformStateValidator(terraform_dir=args.terraform_dir, log_level=args.log_level)

    if args.component:
        # Run specific validation
        if args.component == "state":
            result = validator.validate_infrastructure_state()
        elif args.component == "kubernetes":
            validator.load_terraform_state()
            result = validator.validate_kubernetes_resources()
        elif args.component == "helm":
            validator.load_terraform_state()
            result = validator.validate_helm_releases()

        print(f"\n🔍 {result.component.title()} Validation:")
        print(f"Status: {'✅ PASS' if result.is_valid else '❌ FAIL'}")
        print(f"Message: {result.message}")

        if result.details:
            print(f"Details: {result.details}")

        return 0 if result.is_valid else 1

    # Run comprehensive validation
    results = validator.run_comprehensive_validation()

    print("\n🏗️  Terraform State Validation Report:")
    print("=" * 50)

    total_checks = len(results)
    passed_checks = sum(1 for r in results if r.is_valid)

    for result in results:
        icon = "✅" if result.is_valid else "❌"
        print(f"  {icon} {result.component}: {result.message}")

        if result.resources_checked > 0:
            percentage = result.validation_percentage
            print(
                f"    📊 Resources: {result.resources_valid}/{result.resources_checked} ({percentage:.1f}%)"
            )

    print(f"\nOverall: {passed_checks}/{total_checks} validations passed")

    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
