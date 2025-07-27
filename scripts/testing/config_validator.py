#!/usr/bin/env python3
"""Configuration Validator for Homelab Infrastructure.

This module provides validation capabilities for YAML/JSON configuration files,
Ansible inventory files, Helm values files, and environment-specific configurations.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator


@dataclass
class ValidationResult:
    """Structured validation result for configuration files."""

    file_path: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_type: str = ""

    def add_error(self, message: str) -> None:
        """Add an error message to the result."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(message)


class ConfigValidator:
    """Main validator class for homelab configuration files."""

    def __init__(self, log_level: str = "INFO") -> None:
        """Initialize the validator with logging configuration."""
        self.logger = self._setup_logging(log_level)
        self.schemas = self._load_schemas()

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        # Only add handler if no handlers exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_schemas(self) -> dict[str, dict[str, Any]]:
        """Load validation schemas for different configuration types."""
        return {
            "ansible_inventory": {
                "type": "object",
                "required": ["all"],
                "properties": {
                    "all": {
                        "type": "object",
                        "properties": {
                            "children": {"type": "object"},
                            "vars": {"type": "object"},
                            "hosts": {"type": "object"},
                        },
                    },
                },
            },
            "helm_values": {
                "type": "object",
                "properties": {
                    "global": {"type": "object"},
                    "resources": {"type": "object"},
                    "image": {"type": "object"},
                },
            },
            "environment_config": {
                "type": "object",
                "required": ["environment"],
                "properties": {"environment": {"type": "string"}, "global": {"type": "object"}},
            },
        }

    def _load_file(self, file_path: str) -> dict[str, Any] | None:
        """Safely load YAML or JSON file."""
        try:
            path = Path(file_path)
            if not path.exists():
                msg = f"File not found: {file_path}"
                raise FileNotFoundError(msg)

            with open(path, encoding="utf-8") as f:
                if path.suffix.lower() == ".json":
                    return json.load(f)
                return yaml.safe_load(f)

        except Exception as e:
            self.logger.exception(f"Failed to load {file_path}: {e}")
            return None

    def validate_schema(self, data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
        """Validate data against JSON schema."""
        validator = Draft7Validator(schema)
        errors = []

        for error in validator.iter_errors(data):
            errors.append(f"Schema validation error: {error.message}")

        return errors

    def validate_ansible_inventory(self, file_path: str) -> ValidationResult:
        """Validate Ansible inventory file structure."""
        result = ValidationResult(file_path=file_path, is_valid=True, file_type="ansible_inventory")

        data = self._load_file(file_path)
        if data is None:
            result.add_error("Failed to load file")
            return result

        # Schema validation
        schema_errors = self.validate_schema(data, self.schemas["ansible_inventory"])
        for error in schema_errors:
            result.add_error(error)

        # Ansible-specific validations
        if "all" in data:
            all_section = data["all"]

            # Check for required host variables
            required_vars = ["ansible_host", "ansible_user"]
            if "children" in all_section:
                for group_data in all_section["children"].values():
                    if "hosts" in group_data:
                        for host_name, host_vars in group_data["hosts"].items():
                            for var in required_vars:
                                if var not in host_vars:
                                    result.add_warning(f"Host {host_name} missing {var}")

            # Validate IP addresses in metallb_range
            if "vars" in all_section and "homelab_network" in all_section["vars"]:
                network = all_section["vars"]["homelab_network"]
                if "metallb_range" in network:
                    if not self._validate_ip_range(network["metallb_range"]):
                        result.add_error("Invalid MetalLB IP range format")

        return result

    def validate_helm_values(self, file_path: str) -> ValidationResult:
        """Validate Helm values file for common issues."""
        result = ValidationResult(file_path=file_path, is_valid=True, file_type="helm_values")

        data = self._load_file(file_path)
        if data is None:
            result.add_error("Failed to load file")
            return result

        # Check for resource specifications
        if "resources" in data:
            resources = data["resources"]
            if "requests" not in resources and "limits" not in resources:
                result.add_warning("No resource requests or limits specified")

            # Validate resource formats
            for resource_type in ["requests", "limits"]:
                if resource_type in resources:
                    for key, value in resources[resource_type].items():
                        if key in ["cpu", "memory"] and not self._validate_resource_value(value):
                            result.add_error(f"Invalid {key} resource format: {value}")

        # Check for sensitive data patterns
        sensitive_patterns = ["password", "secret", "key", "token"]
        self._check_sensitive_data(data, sensitive_patterns, result)

        return result

    def validate_environment_config(self, file_path: str) -> ValidationResult:
        """Validate environment-specific configuration files."""
        result = ValidationResult(
            file_path=file_path,
            is_valid=True,
            file_type="environment_config",
        )

        data = self._load_file(file_path)
        if data is None:
            result.add_error("Failed to load file")
            return result

        # Schema validation
        schema_errors = self.validate_schema(data, self.schemas["environment_config"])
        for error in schema_errors:
            result.add_error(error)

        # Environment-specific validations
        if "environment" in data:
            env = data["environment"]
            valid_envs = ["development", "staging", "production"]
            if env not in valid_envs:
                result.add_warning(f"Non-standard environment: {env}")

        # Check for proper resource scaling by environment
        if "resources" in data and "environment" in data:
            env = data["environment"]
            resources = data["resources"]

            if env == "production" and "limits" not in resources:
                result.add_error("Production environment should have resource limits")

        return result

    def _validate_ip_range(self, ip_range: str) -> bool:
        """Validate IP range format (e.g., 192.168.1.100-192.168.1.200)."""
        import re

        pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        return bool(re.fullmatch(pattern, ip_range))

    def _validate_resource_value(self, value: str) -> bool:
        """Validate Kubernetes resource value format."""
        import re

        # CPU: number (int or float) with optional 'm' suffix, or with units u/n
        # Also support scientific notation like 1e3m or 1.5e-3
        cpu_pattern = r"([0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?)(m|u|n)?"

        # Memory: number with optional valid binary or decimal suffix
        # Ki, Mi, Gi, Ti, Pi, Ei (binary) or k, K, M, G, T, P, E (decimal)
        memory_pattern = r"([0-9]+(\.[0-9]+)?)(Ki|Mi|Gi|Ti|Pi|Ei|k|K|M|G|T|P|E)?"

        value_str = str(value).strip()

        # Check if it matches CPU pattern
        if re.fullmatch(cpu_pattern, value_str):
            return True

        # Check if it matches memory pattern
        if re.fullmatch(memory_pattern, value_str):
            return True

        # Check if it's a plain number (bytes or cores)
        return bool(re.fullmatch("[0-9]+(\\.[0-9]+)?", value_str))

    def _check_sensitive_data(
        self,
        data: dict[str, Any],
        patterns: list[str],
        result: ValidationResult,
    ) -> None:
        """Recursively check for potential sensitive data exposure."""

        def _check_recursive(obj, path="") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(pattern in key.lower() for pattern in patterns):
                        if isinstance(value, str) and not value.startswith("${"):
                            result.add_warning(f"Potential sensitive data at {current_path}")
                    _check_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _check_recursive(item, f"{path}[{i}]")

        _check_recursive(data)

    def validate_file(self, file_path: str, file_type: str | None = None) -> ValidationResult:
        """Validate a configuration file based on its type or path."""
        path = Path(file_path)

        # Auto-detect file type if not specified
        if file_type is None:
            if "inventory" in str(path) or path.name == "hosts.yml":
                file_type = "ansible_inventory"
            elif "values" in str(path) or path.name.startswith("values"):
                file_type = "helm_values"
            elif "environment" in str(path) or path.parent.name == "environments":
                file_type = "environment_config"
            else:
                file_type = "generic"

        # Route to appropriate validator
        if file_type == "ansible_inventory":
            return self.validate_ansible_inventory(file_path)
        if file_type == "helm_values":
            return self.validate_helm_values(file_path)
        if file_type == "environment_config":
            return self.validate_environment_config(file_path)
        # Generic YAML/JSON validation
        result = ValidationResult(file_path=file_path, is_valid=True, file_type="generic")
        data = self._load_file(file_path)
        if data is None:
            result.add_error("Failed to load file")
        return result

    def validate_directory(
        self,
        directory: str,
        patterns: list[str] | None = None,
    ) -> list[ValidationResult]:
        """Validate all configuration files in a directory."""
        if patterns is None:
            patterns = ["*.yml", "*.yaml", "*.json"]

        results = []
        dir_path = Path(directory)

        for pattern in patterns:
            for file_path in dir_path.rglob(pattern):
                if file_path.is_file():
                    result = self.validate_file(str(file_path))
                    results.append(result)

                    # Log results
                    if result.is_valid:
                        self.logger.info(f"✅ {file_path}: Valid")
                    else:
                        self.logger.error(f"❌ {file_path}: {len(result.errors)} errors")

        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate homelab configuration files")
    parser.add_argument("paths", nargs="+", help="File or directory paths to validate")
    parser.add_argument(
        "--type",
        choices=["ansible_inventory", "helm_values", "environment_config"],
        help="Specify configuration type",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level",
    )

    args = parser.parse_args()

    validator = ConfigValidator(log_level=args.log_level)
    results = []

    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            result = validator.validate_file(str(path), args.type)
            results.append(result)
        else:
            results.extend(validator.validate_directory(str(path)))

    # Summary
    total_files = len(results)
    valid_files = sum(1 for r in results if r.is_valid)

    print("\n📊 Validation Summary:")
    print(f"Total files: {total_files}")
    print(f"Valid files: {valid_files}")
    print(f"Invalid files: {total_files - valid_files}")

    # Detail errors
    for result in results:
        if not result.is_valid:
            print(f"\n❌ {result.file_path}:")
            for error in result.errors:
                print(f"  • {error}")
        if result.warnings:
            print(f"\n⚠️  {result.file_path} warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")

    return 0 if all(r.is_valid for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
