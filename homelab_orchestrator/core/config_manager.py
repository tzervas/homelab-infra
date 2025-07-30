"""
Configuration Manager - Unified configuration loading and management.

Integrates with the consolidated config system and provides runtime configuration
management with environment-specific overrides, validation, and caching.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ConfigContext:
    """Configuration context for environment and deployment settings."""

    environment: str = "development"
    cluster_type: str = "local"  # local, remote, hybrid
    gpu_enabled: bool = False
    sso_enabled: bool = True
    monitoring_enabled: bool = True

    # Runtime overrides
    overrides: dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Unified configuration management integrating with consolidated config system."""

    def __init__(
        self,
        project_root: Path | None = None,
        config_context: ConfigContext | None = None,
    ) -> None:
        """Initialize configuration manager.

        Args:
            project_root: Path to project root directory
            config_context: Configuration context for environment settings
        """
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root or Path.cwd()
        self.context = config_context or ConfigContext()

        # Configuration paths
        self.consolidated_config_dir = self.project_root / "config" / "consolidated"
        self.env_config_dir = self.project_root / "config" / "environments"

        # Loaded configurations cache
        self._config_cache: dict[str, Any] = {}
        self._load_consolidated_configs()

    @classmethod
    def from_environment(cls, environment: str = "development") -> "ConfigManager":
        """Create ConfigManager from environment variables and defaults.

        Args:
            environment: Environment name to use

        Returns:
            Configured ConfigManager instance
        """
        project_root = Path(os.environ.get("HOMELAB_PROJECT_ROOT", Path.cwd()))
        context = ConfigContext(
            environment=environment,
            cluster_type=os.environ.get("HOMELAB_CLUSTER_TYPE", "local"),
            gpu_enabled=os.environ.get("HOMELAB_GPU_ENABLED", "false").lower() == "true",
            sso_enabled=os.environ.get("HOMELAB_SSO_ENABLED", "true").lower() == "true",
            monitoring_enabled=os.environ.get("HOMELAB_MONITORING_ENABLED", "true").lower()
            == "true",
        )
        return cls(project_root=project_root, config_context=context)

    def _load_consolidated_configs(self) -> None:
        """Load all consolidated configuration files."""
        config_files = [
            "domains.yaml",
            "networking.yaml",
            "storage.yaml",
            "security.yaml",
            "resources.yaml",
            "namespaces.yaml",
            "environments.yaml",
            "services.yaml",
        ]

        for config_file in config_files:
            config_path = self.consolidated_config_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config_name = config_file.replace(".yaml", "")
                        self._config_cache[config_name] = yaml.safe_load(f)
                        self.logger.debug(f"Loaded {config_name} configuration")
                except Exception as e:
                    self.logger.exception(f"Failed to load {config_file}: {e}")
            else:
                self.logger.warning(f"Configuration file not found: {config_path}")

    def get_config(self, config_type: str, key_path: str | None = None, default: Any = None) -> Any:
        """Get configuration value with caching.

        Args:
            config_type: Type of configuration (domains, networking, etc.)
            key_path: Dot-separated path to specific configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if config_type not in self._config_cache:
            self.logger.warning(f"Configuration type '{config_type}' not found")
            return default

        config = self._config_cache[config_type]

        if not key_path:
            return config

        # Navigate through nested configuration using key path
        current = config
        for key in key_path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def get_environment_config(self, environment: str | None = None) -> dict[str, Any]:
        """Get environment-specific configuration.

        Args:
            environment: Environment name (defaults to context environment)

        Returns:
            Environment configuration dictionary
        """
        env = environment or self.context.environment
        return self.get_config("environments", f"environments.{env}", {})

    def get_service_config(self, service_name: str) -> dict[str, Any]:
        """Get service-specific configuration.

        Args:
            service_name: Name of the service

        Returns:
            Service configuration dictionary
        """
        return self.get_config("services", f"services.discovery.{service_name}", {})

    def get_domain_config(self) -> dict[str, Any]:
        """Get domain configuration with environment-specific overrides."""
        base_domains = self.get_config("domains", "domains", {})
        env_config = self.get_environment_config()

        # Apply environment-specific domain overrides
        if env_config and "domain_suffix" in env_config:
            suffix = env_config["domain_suffix"]
            if suffix and suffix != "":
                # Modify service domains for environment
                if "services" in base_domains:
                    for service, url in base_domains["services"].items():
                        if url.endswith(".homelab.local"):
                            base_domains["services"][service] = url.replace(
                                ".homelab.local",
                                f".{suffix}.homelab.local",
                            )

        return base_domains

    def get_networking_config(self) -> dict[str, Any]:
        """Get networking configuration with environment overrides."""
        networking = self.get_config("networking", "networking", {})
        env_config = self.get_environment_config()

        # Apply environment-specific networking overrides
        if env_config and "networking" in env_config:
            env_networking = env_config["networking"]
            if "metallb_pool" in env_networking:
                if "metallb" in networking and "ip_pools" in networking["metallb"]:
                    # Override the IP pool for this environment
                    pool_name = f"{self.context.environment}_pool"
                    networking["metallb"]["ip_pools"][pool_name] = {
                        "addresses": env_networking["metallb_pool"],
                        "name": pool_name,
                    }

        return networking

    def get_security_config(self) -> dict[str, Any]:
        """Get security configuration with environment and context overrides."""
        # Get the full security configuration, not just the nested 'security' key
        full_security_config = self.get_config("security")

        # Extract the nested security context if it exists
        security_context = full_security_config.get("security", {})

        # Build the complete security configuration
        security = {
            "default_security_context": security_context.get("default_security_context", {}),
            "service_contexts": security_context.get("service_contexts", {}),
            "pod_security_standards": full_security_config.get("pod_security_standards", {}),
            "rbac": full_security_config.get("rbac", {}),
            "network_policies": full_security_config.get("network_policies", {}),
            "image_security": full_security_config.get("image_security", {}),
            "secrets": full_security_config.get("secrets", {}),
        }

        env_config = self.get_environment_config()

        # Apply environment-specific security settings
        if env_config and "security" in env_config:
            env_security = env_config["security"]
            # Override pod security standards if specified
            if "pod_security_standard" in env_security:
                if "pod_security_standards" in security:
                    security["pod_security_standards"]["default"]["enforce"] = env_security[
                        "pod_security_standard"
                    ]

        # Apply context-based security overrides
        if not self.context.sso_enabled:
            # Disable SSO-related security features
            if "rbac" in security:
                security["rbac"]["sso_integration"] = False

        return security

    def get_resource_config(self) -> dict[str, Any]:
        """Get resource configuration with environment scaling."""
        resources = self.get_config("resources", "resources", {})
        env_config = self.get_environment_config()

        # Apply environment-specific resource scaling
        if env_config and "resource_scaling" in env_config:
            scaling_factor = env_config["resource_scaling"]

            # Scale default resource limits
            if "defaults" in resources:
                defaults = resources["defaults"]
                if "limits" in defaults:
                    for resource, value in defaults["limits"].items():
                        if resource == "cpu" and value.endswith("m"):
                            # Scale CPU (millicores)
                            cpu_value = int(value.replace("m", ""))
                            scaled_cpu = int(cpu_value * scaling_factor)
                            defaults["limits"][resource] = f"{scaled_cpu}m"
                        elif resource == "memory" and value.endswith("Gi"):
                            # Scale memory (Gigabytes)
                            mem_value = float(value.replace("Gi", ""))
                            scaled_mem = mem_value * scaling_factor
                            defaults["limits"][resource] = f"{scaled_mem:.1f}Gi"

        return resources

    def get_gpu_config(self) -> dict[str, Any]:
        """Get GPU configuration based on context and environment."""
        # GPU configuration derived from resource and environment settings
        gpu_config = {
            "enabled": self.context.gpu_enabled,
            "discovery": {
                "auto_detect": True,
                "local_gpus": True,
                "remote_gpus": self.context.cluster_type in ["remote", "hybrid"],
            },
            "resource_allocation": {
                "default_memory_fraction": 0.8,
                "allow_memory_growth": True,
            },
        }

        # Environment-specific GPU settings
        env_config = self.get_environment_config()
        if env_config and "features" in env_config:
            features = env_config["features"]
            if "gpu_enabled" in features:
                gpu_config["enabled"] = features["gpu_enabled"]

        return gpu_config

    def get_deployment_config(self) -> dict[str, Any]:
        """Get deployment configuration combining multiple config sources."""
        return {
            "environment": self.context.environment,
            "cluster_type": self.context.cluster_type,
            "domains": self.get_domain_config(),
            "networking": self.get_networking_config(),
            "security": self.get_security_config(),
            "resources": self.get_resource_config(),
            "gpu": self.get_gpu_config(),
            "services": self.get_config("services", "services", {}),
            "namespaces": self.get_config("namespaces", "namespaces", {}),
            "storage": self.get_config("storage", "storage", {}),
        }

    def validate_configuration(self) -> dict[str, Any]:
        """Validate loaded configuration for consistency and completeness.

        Returns:
            Validation results with status and issues
        """
        issues = []
        warnings = []

        # Check required configuration files
        required_configs = ["domains", "networking", "security", "resources"]
        for config_type in required_configs:
            if config_type not in self._config_cache:
                issues.append(f"Missing required configuration: {config_type}")

        # Validate domain configuration
        domains = self.get_domain_config()
        if not domains.get("base", {}).get("primary"):
            issues.append("Primary domain not configured")

        # Validate networking configuration
        networking = self.get_networking_config()
        if not networking.get("metallb", {}).get("default_pool"):
            issues.append("MetalLB default pool not configured")

        # Validate environment configuration
        env_config = self.get_environment_config()
        if not env_config:
            warnings.append(f"No configuration found for environment: {self.context.environment}")

        # Check for context consistency
        if self.context.gpu_enabled:
            gpu_config = self.get_gpu_config()
            if not gpu_config.get("enabled"):
                warnings.append("GPU enabled in context but not in configuration")

        return {
            "status": "valid" if not issues else "invalid",
            "issues": issues,
            "warnings": warnings,
            "config_files_loaded": len(self._config_cache),
            "environment": self.context.environment,
            "cluster_type": self.context.cluster_type,
        }

    def reload_configuration(self) -> None:
        """Reload all configuration files and clear cache."""
        self._config_cache.clear()
        self._load_consolidated_configs()
        self.logger.info("Configuration reloaded")

    def export_runtime_config(self, output_path: Path) -> None:
        """Export runtime configuration to file for debugging.

        Args:
            output_path: Path to export configuration file
        """
        runtime_config = {
            "context": {
                "environment": self.context.environment,
                "cluster_type": self.context.cluster_type,
                "gpu_enabled": self.context.gpu_enabled,
                "sso_enabled": self.context.sso_enabled,
                "monitoring_enabled": self.context.monitoring_enabled,
            },
            "deployment_config": self.get_deployment_config(),
            "validation": self.validate_configuration(),
        }

        with open(output_path, "w") as f:
            yaml.dump(runtime_config, f, default_flow_style=False, indent=2)

        self.logger.info(f"Runtime configuration exported to: {output_path}")

    @staticmethod
    def from_environment() -> "ConfigManager":
        """Create ConfigManager from environment variables.

        Returns:
            ConfigManager instance configured from environment
        """
        context = ConfigContext(
            environment=os.getenv("HOMELAB_ENVIRONMENT", "development"),
            cluster_type=os.getenv("HOMELAB_CLUSTER_TYPE", "local"),
            gpu_enabled=os.getenv("HOMELAB_GPU_ENABLED", "false").lower() == "true",
            sso_enabled=os.getenv("HOMELAB_SSO_ENABLED", "true").lower() == "true",
            monitoring_enabled=os.getenv("HOMELAB_MONITORING_ENABLED", "true").lower() == "true",
        )

        project_root = Path(os.getenv("HOMELAB_PROJECT_ROOT", Path.cwd()))

        return ConfigManager(project_root=project_root, config_context=context)
