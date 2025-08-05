#!/usr/bin/env python3
"""Enhanced Configuration Schema Validator for Homelab Infrastructure."""

import logging
import sys
from pathlib import Path

import jsonschema
import yaml


# Schema definitions for different configuration types
HELM_ENVIRONMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["global"],
    "properties": {
        "global": {
            "type": "object",
            "required": ["environment", "domain"],
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "template"],
                },
                "domain": {
                    "type": "string",
                    "pattern": "^([a-zA-Z0-9.-]+|\\${[A-Z_]+})$",
                },
                "tls": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "issuer": {"type": "string"},
                    },
                },
            },
        },
        "resources": {
            "type": "object",
            "properties": {
                "limits": {"$ref": "#/definitions/resourceSpec"},
                "requests": {"$ref": "#/definitions/resourceSpec"},
            },
        },
    },
    "definitions": {
        "resourceSpec": {
            "type": "object",
            "properties": {
                "cpu": {"type": "string"},
                "memory": {"type": "string"},
            },
        },
    },
}

ENVIRONMENT_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["environment"],
    "properties": {
        "environment": {
            "type": "string",
            "enum": ["development", "staging", "production", "template"],
        },
        "global": {"type": "object"},
        "secrets": {"type": "object"},
        "tls": {"type": "object"},
        "metadata": {"type": "object"},
    },
}

ANSIBLE_INVENTORY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "all": {
            "type": "object",
            "properties": {
                "hosts": {"type": "object"},
                "children": {"type": "object"},
                "vars": {"type": "object"},
            },
        },
    },
}


class ConfigValidator:
    def __init__(self, log_level: str = "INFO") -> None:
        self.logger = self._setup_logging(log_level)
        self.errors: list[str] = []

    def _setup_logging(self, level: str) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _handle_validation_error(self, error_msg: str) -> bool:
        """Handle validation error consistently.

        Args:
            error_msg: Error message to log and store

        Returns:
            bool: Always returns False to indicate validation failure
        """
        self.logger.exception(error_msg)
        self.errors.append(error_msg)
        return False

    def _load_and_validate_yaml(
        self,
        config_path: Path,
        schema: dict | None = None,
        allow_empty: bool = True,
        context: str = "",
    ) -> tuple[dict | None, bool]:
        """Load and validate YAML configuration.

        Args:
            config_path: Path to the YAML file
            schema: Optional JSON schema to validate against
            allow_empty: Whether empty configs are acceptable
            context: Context string for error messages

        Returns:
            tuple: (config dict or None, success bool)
        """
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            if not config:
                msg = f"⚠️ {config_path}: Empty configuration file"
                self.logger.warning(msg)
                return None, allow_empty

            if schema:
                jsonschema.validate(config, schema)

            return config, True

        except jsonschema.ValidationError as e:
            return None, self._handle_validation_error(
                f"❌ {config_path}: {context} schema validation failed - {e.message}"
            )
        except Exception as e:
            return None, self._handle_validation_error(
                f"❌ {config_path}: Failed to validate - {e}"
            )

    def validate_helm_environment_config(self, config_path: Path) -> bool:
        """Validate Helm environment configuration file."""
        config, success = self._load_and_validate_yaml(
            config_path,
            HELM_ENVIRONMENT_SCHEMA,
            context="Helm",
        )
        if success and config:
            self.logger.info(f"✅ {config_path}: Valid Helm environment configuration")
        return success

    def validate_environment_config(self, config_path: Path) -> bool:
        """Validate environment-specific configuration file."""
        config, success = self._load_and_validate_yaml(
            config_path,
            ENVIRONMENT_CONFIG_SCHEMA,
            context="Environment",
        )
        if success and config:
            self.logger.info(f"✅ {config_path}: Valid environment configuration")
        return success

    def validate_ansible_inventory(self, config_path: Path) -> bool:
        """Validate Ansible inventory file."""
        config, success = self._load_and_validate_yaml(
            config_path,
            ANSIBLE_INVENTORY_SCHEMA,
            allow_empty=False,
            context="Ansible inventory",
        )

        if not success or not config:
            return False

        # Additional inventory-specific validation
        if "all" not in config:
            self.logger.warning(f"⚠️ {config_path}: No 'all' group in inventory")

        self.logger.info(f"✅ {config_path}: Valid Ansible inventory")
        return True

    def detect_file_type(self, config_path: Path) -> str:
        """Detect configuration file type based on path and content."""
        path_str = str(config_path).lower()

        # Skip Kubernetes manifest files
        if config_path.name.endswith(".k8s.yaml") or config_path.name.endswith(".k8s.yml"):
            return "kubernetes_manifest"

        # Detect by path patterns
        if "helm" in path_str and "environments" in path_str:
            if "values" in config_path.name:
                return "helm_environment"
            if "secrets" in config_path.name:
                return "environment_config"

        if "inventory" in path_str or config_path.name == "hosts.yml":
            return "ansible_inventory"

        if "environments" in path_str or config_path.parent.name == "environments":
            return "environment_config"

        return "generic"

    def validate_file(self, config_path: Path) -> bool:
        """Validate a single configuration file."""
        if not config_path.exists():
            error_msg = f"❌ {config_path}: File does not exist"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False

        file_type = self.detect_file_type(config_path)

        # Skip Kubernetes manifests
        if file_type == "kubernetes_manifest":
            self.logger.info(f"⏭️ {config_path}: Skipping Kubernetes manifest file")
            return True

        # Route to appropriate validator
        if file_type == "helm_environment":
            return self.validate_helm_environment_config(config_path)
        if file_type == "environment_config":
            return self.validate_environment_config(config_path)
        if file_type == "ansible_inventory":
            return self.validate_ansible_inventory(config_path)
        # Generic YAML validation
        try:
            with open(config_path) as f:
                yaml.safe_load(f)
            self.logger.info(f"✅ {config_path}: Valid YAML file")
            return True
        except Exception as e:
            error_msg = f"❌ {config_path}: Invalid YAML - {e}"
            self.logger.exception(error_msg)
            self.errors.append(error_msg)
            return False

    def validate_all_configs(self, config_paths: list[str], environment: str | None = None) -> bool:
        """Validate all configuration files."""
        all_valid = True
        total_files = 0
        valid_files = 0

        for config_path_str in config_paths:
            config_path = Path(config_path_str)

            if config_path.is_dir():
                # Validate all YAML files in directory
                for yaml_file in config_path.glob("**/*.yaml"):
                    total_files += 1
                    if self.validate_file(yaml_file):
                        valid_files += 1
                    else:
                        all_valid = False

                for yml_file in config_path.glob("**/*.yml"):
                    total_files += 1
                    if self.validate_file(yml_file):
                        valid_files += 1
                    else:
                        all_valid = False
            else:
                total_files += 1
                if self.validate_file(config_path):
                    valid_files += 1
                else:
                    all_valid = False

        # Summary
        self.logger.info("\n📊 Validation Summary:")
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Valid files: {valid_files}")
        self.logger.info(f"Invalid files: {total_files - valid_files}")

        if environment:
            self.logger.info(f"Target environment: {environment}")

        return all_valid


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced homelab configuration validator")
    parser.add_argument(
        "--config-paths",
        nargs="+",
        required=True,
        help="Paths to configuration files or directories",
    )
    parser.add_argument("--environment", choices=["development", "staging", "production"])
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first validation error")

    args = parser.parse_args()

    validator = ConfigValidator(args.log_level)

    if validator.validate_all_configs(args.config_paths, args.environment):
        print("\n🎉 All configuration files are valid!")
        sys.exit(0)
    else:
        print(f"\n❌ Validation failed with {len(validator.errors)} errors:")
        for error in validator.errors:
            print(f"  {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
