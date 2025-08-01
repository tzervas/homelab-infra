#!/usr/bin/env python3
"""
YAML Configuration Validator.

This script validates YAML files in specified directories against schema definitions
and performs additional security and best practice checks.
"""

import json
import logging
import os
import sys

import yaml
from jsonschema import ValidationError, validate


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_schema(schema_path: str) -> dict:
    """Load JSON schema from file."""
    try:
        with open(schema_path) as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"Failed to load schema from {schema_path}: {e}")
        return None


def validate_yaml_file(file_path: str, schema: dict | None = None) -> tuple[bool, list[str]]:
    """Validate a YAML file against schema and perform additional checks."""
    errors = []
    try:
        with open(file_path) as f:
            content = yaml.safe_load(f)

        if schema:
            try:
                validate(instance=content, schema=schema)
            except ValidationError as e:
                errors.append(f"Schema validation error: {e.message}")

        # Additional security checks
        if isinstance(content, dict):
            # Check for potential secrets
            for key in content:
                if any(
                    secret_word in key.lower()
                    for secret_word in ["password", "secret", "token", "key"]
                ):
                    errors.append(f"Warning: Potential secret found in key '{key}'")

            # Check for unencrypted sensitive data
            # pragma: allowlist secret
            sensitive_patterns = ["BEGIN CERTIFICATE"]
            content_str = str(content)
            for pattern in sensitive_patterns:
                if pattern in content_str:
                    errors.append(f"Warning: Found sensitive data pattern: {pattern}")

        return len(errors) == 0, errors
    except Exception as e:
        return False, [f"Failed to validate {file_path}: {e!s}"]


def validate_directory(directory: str, schema_path: str | None = None) -> tuple[int, int]:
    """Validate all YAML files in a directory."""
    if not os.path.exists(directory):
        logger.error(f"Directory not found: {directory}")
        return 0, 0

    schema = load_schema(schema_path) if schema_path else None
    valid_count = 0
    invalid_count = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith((".yml", ".yaml")):
                file_path = os.path.join(root, file)
                is_valid, errors = validate_yaml_file(file_path, schema)

                if is_valid:
                    logger.info(f"✅ {file_path}: Valid")
                    valid_count += 1
                else:
                    logger.error(f"❌ {file_path}: {len(errors)} errors")
                    for error in errors:
                        logger.error(f"  - {error}")
                    invalid_count += 1

    return valid_count, invalid_count


def main() -> int:
    """Main execution function."""
    config_path = os.getenv("CONFIG_PATH", "./config")
    helm_path = os.getenv("HELM_PATH", "./helm")
    kubernetes_path = os.getenv("KUBERNETES_PATH", "./kubernetes")

    total_valid = 0
    total_invalid = 0

    # Validate configuration files
    logger.info("Validating configuration files...")
    valid, invalid = validate_directory(config_path)
    total_valid += valid
    total_invalid += invalid

    # Validate Helm charts
    logger.info("Validating Helm charts...")
    valid, invalid = validate_directory(helm_path)
    total_valid += valid
    total_invalid += invalid

    # Validate Kubernetes manifests
    logger.info("Validating Kubernetes manifests...")
    valid, invalid = validate_directory(kubernetes_path)
    total_valid += valid
    total_invalid += invalid

    # Print summary
    logger.info(f"""
Validation Summary:
-----------------
Total files validated: {total_valid + total_invalid}
✅ Valid: {total_valid}
❌ Invalid: {total_invalid}
    """)

    return 0 if total_invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
