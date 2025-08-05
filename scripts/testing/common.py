"""Common utilities for the homelab testing framework.

This module provides shared logging configuration and import fallback logic
to reduce boilerplate across all testing modules.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any


def setup_logging(module_name: str, log_level: str = "INFO") -> logging.Logger:
    """Configure structured logging for testing modules.

    Args:
        module_name: Name of the module requesting the logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance

    """
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Only add handler if no handlers exist
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def safe_import_kubernetes() -> tuple[bool, Any | None, Any | None]:
    """Safely import Kubernetes client with fallback handling.

    Returns:
        Tuple of (available, client_module, config_module)

    """
    try:
        from kubernetes import client, config

        return True, client, config
    except ImportError as e:
        warnings.warn(f"Kubernetes client not available: {e}", ImportWarning)
        return False, None, None


def safe_import_requests() -> tuple[bool, Any | None]:
    """Safely import requests with fallback handling.

    Returns:
        Tuple of (available, requests_module)

    """
    try:
        import requests

        return True, requests
    except ImportError as e:
        warnings.warn(f"Requests library not available: {e}", ImportWarning)
        return False, None


def safe_import_yaml() -> tuple[bool, Any | None]:
    """Safely import YAML with fallback handling.

    Returns:
        Tuple of (available, yaml_module)

    """
    try:
        import yaml

        return True, yaml
    except ImportError as e:
        warnings.warn(f"YAML library not available: {e}", ImportWarning)
        return False, None


def safe_import_jsonschema() -> tuple[bool, type | None, type | None]:
    """Safely import jsonschema with fallback handling.

    Returns:
        Tuple of (available, Draft7Validator, ValidationError)

    """
    try:
        from jsonschema import Draft7Validator, ValidationError

        return True, Draft7Validator, ValidationError
    except ImportError as e:
        warnings.warn(f"JSONSchema library not available: {e}", ImportWarning)
        return False, None, None


def get_kubernetes_client(kubeconfig_path: str | None = None) -> Any | None:
    """Get initialized Kubernetes API client.

    Args:
        kubeconfig_path: Optional path to kubeconfig file

    Returns:
        Kubernetes API client or None if unavailable

    """
    k8s_available, client, config = safe_import_kubernetes()
    if not k8s_available:
        return None

    try:
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

        return client.ApiClient()
    except Exception as e:
        warnings.warn(f"Failed to initialize Kubernetes client: {e}", RuntimeWarning)
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m{secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h{minutes}m"


def get_status_icon(status: str) -> str:
    """Get appropriate icon for status.

    Args:
        status: Status string (pass, fail, warning, etc.)

    Returns:
        Unicode icon for the status

    """
    status_icons = {
        "pass": "✅",
        "fail": "❌",
        "warning": "⚠️",
        "skip": "⏭️",
        "pending": "🔄",
        "unknown": "❓",
        "healthy": "✅",
        "critical": "🚨",
        "secure": "🔒",
        "vulnerable": "🚨",
        "ready": "✅",
        "in_progress": "🔄",
    }
    return status_icons.get(status.lower(), "❓")


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string with ellipsis if too long.

    Args:
        text: Input text
        max_length: Maximum length before truncation

    Returns:
        Truncated string with ellipsis if needed

    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def merge_configs(base_config: dict[str, Any], override_config: dict[str, Any]) -> dict[str, Any]:
    """Merge configuration dictionaries with override support.

    Args:
        base_config: Base configuration
        override_config: Configuration overrides

    Returns:
        Merged configuration dictionary

    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged
