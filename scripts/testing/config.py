"""Configuration settings for the homelab testing framework.

This module centralizes all configuration settings including service endpoints,
timeouts, service definitions, and other configurable parameters.
"""

from dataclasses import dataclass, field
import os
from typing import Any, Dict, List, Optional

# Import environment variables early to make them available throughout the module
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""

    name: str
    internal_url: str
    external_url: str
    health_path: str
    api_paths: List[str] = field(default_factory=list)
    requires_auth: bool = False
    sso_enabled: bool = False


@dataclass
class ServiceDefinition:
    """Service definition for deployment checking."""

    namespace: str
    ports: List[int] = field(default_factory=list)
    health_path: Optional[str] = None


@dataclass
class TestingConfig:
    """Main configuration class for testing framework."""

    # Timeout settings
    # Timeout settings [from environment variables]
    short_timeout: int = int(os.getenv("SHORT_TIMEOUT", "10"))
    long_timeout: int = int(os.getenv("LONG_TIMEOUT", "30"))
    retry_delay: int = int(os.getenv("RETRY_DELAY", "5"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    # SSL verification settings [from environment variables]
    verify_external_ssl: bool = os.getenv("VERIFY_EXTERNAL_SSL", "True").lower() == "true"
    verify_internal_ssl: bool = os.getenv("VERIFY_INTERNAL_SSL", "False").lower() == "false"

    # Network settings [from environment variables]
    metallb_ip_range: str = os.getenv("METALLB_IP_RANGE")
    homelab_domain: str = os.getenv("HOMELAB_DOMAIN")
    dev_domain: str = os.getenv("HOMELAB_DEV_DOMAIN")

    # Critical namespaces for health checking [from environment variables]
    critical_namespaces: List[str] = field(
        default_factory=lambda: [
            namespace.strip()
            for namespace in os.getenv(
                "CRITICAL_NAMESPACES",
                "kube-system,metallb-system,cert-manager,ingress-nginx,longhorn-system,monitoring",
            ).split(",")
        ]
    )

    # Network policies to validate
    network_policies: List[str] = field(
        default_factory=lambda: ["default-deny-all", "allow-dns", "monitoring-ingress"]
    )

    # Service endpoints for integration testing
    service_endpoints: Dict[str, ServiceEndpoint] = field(
        default_factory=lambda: {
            "gitlab": ServiceEndpoint(
                name="GitLab",
                internal_url=f"http://{os.getenv('GITLAB_IP', '192.168.1.201')}",
                external_url=f"https://gitlab.{os.getenv('HOMELAB_DOMAIN', 'homelab.example.com')}",
                health_path="/-/health",
                api_paths=["/api/v4/projects", "/api/v4/user"],
                requires_auth=True,
                sso_enabled=True,
            ),
            "keycloak": ServiceEndpoint(
                name="Keycloak",
                internal_url=f"http://{os.getenv('KEYCLOAK_IP', '192.168.1.202')}:8080",
                external_url=f"https://keycloak.{os.getenv('HOMELAB_DOMAIN', 'homelab.example.com')}",
                health_path="/auth/health/ready",
                api_paths=["/auth/realms/homelab", "/auth/admin/master/console"],
                requires_auth=True,
                sso_enabled=False,  # Keycloak is the SSO provider
            ),
            "prometheus": ServiceEndpoint(
                name="Prometheus",
                internal_url=f"http://{os.getenv('PROMETHEUS_IP', '192.168.1.203')}:9090",
                external_url=f"https://prometheus.{os.getenv('HOMELAB_DOMAIN', 'homelab.example.com')}",
                health_path="/-/healthy",
                api_paths=["/api/v1/query", "/api/v1/targets"],
                requires_auth=False,
                sso_enabled=True,
            ),
            "grafana": ServiceEndpoint(
                name="Grafana",
                internal_url=f"http://{os.getenv('GRAFANA_IP', '192.168.1.204')}:3000",
                external_url=f"https://grafana.{os.getenv('HOMELAB_DOMAIN', 'homelab.example.com')}",
                health_path="/api/health",
                api_paths=["/api/datasources", "/api/dashboards/home"],
                requires_auth=True,
                sso_enabled=True,
            ),
        }
    )

    # Service definitions for deployment checking
    service_definitions: Dict[str, ServiceDefinition] = field(
        default_factory=lambda: {
            "gitlab": ServiceDefinition(
                namespace=os.getenv("GITLAB_NAMESPACE", "gitlab-system"),
                ports=[80, 443],
                health_path="/-/health",
            ),
            "keycloak": ServiceDefinition(
                namespace=os.getenv("KEYCLOAK_NAMESPACE", "keycloak"),
                ports=[8080],
                health_path="/auth/health/ready",
            ),
            "prometheus": ServiceDefinition(
                namespace=os.getenv("MONITORING_NAMESPACE", "monitoring"),
                ports=[9090],
                health_path="/-/healthy",
            ),
            "grafana": ServiceDefinition(
                namespace=os.getenv("MONITORING_NAMESPACE", "monitoring"),
                ports=[3000],
                health_path="/api/health",
            ),
            "nginx-ingress": ServiceDefinition(
                namespace=os.getenv("INGRESS_NGINX_NAMESPACE", "ingress-nginx"),
                ports=[80, 443],
                health_path="/healthz",
            ),
            "cert-manager": ServiceDefinition(
                namespace=os.getenv("CERT_MANAGER_NAMESPACE", "cert-manager"),
                ports=[],
                health_path=None,
            ),
            "metallb": ServiceDefinition(
                namespace=os.getenv("METALLB_NAMESPACE", "metallb-system"),
                ports=[],
                health_path=None,
            ),
        }
    )

    # Configuration validation schemas
    validation_schemas: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
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
                    }
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
    )

    # Default configuration paths for validation
    default_config_paths: List[str] = field(
        default_factory=lambda: [
            "ansible/inventory",
            "helm/environments",
            "examples/private-config-template",
        ]
    )

    # Service communication test patterns
    service_communication_tests: List[tuple] = field(
        default_factory=lambda: [
            ("prometheus", "grafana", "Prometheus -> Grafana data source"),
            ("keycloak", "gitlab", "Keycloak -> GitLab SSO"),
            ("keycloak", "grafana", "Keycloak -\x1b[0;000m -> Grafana SSO"),
        ]
    )


def __post_init__(self) -> None:
    """Initialize and validate configuration after instantiation."""
    print(f"Using METALLB_IP_RANGE: {self.metallb_ip_range}")
    print(f"Using HOMELAB_DOMAIN: {self.homelab_domain}")
    print(f"Using CRITICAL_NAMESPACES: {self.critical_namespaces}")


# Default configuration instance
DEFAULT_CONFIG = TestingConfig()


def get_config(overrides: Optional[Dict[str, Any]] = None) -> TestingConfig:
    """Get configuration with optional overrides.

    Args:
        overrides: Dictionary of configuration overrides

    Returns:
        TestingConfig instance with overrides applied

    """
    if not overrides:
        return DEFAULT_CONFIG

    import os

    # Create a copy of the default config
    config = TestingConfig()

    # Load from environment
    config.metallb_ip_range = os.getenv("METALLB_IP_RANGE", config.metallb_ip_range)
    config.homelab_domain = os.getenv("HOMELAB_DOMAIN", config.homelab_domain)
    config.dev_domain = os.getenv("HOMELAB_DEV_DOMAIN", config.dev_domain)

    # Apply overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


def load_config_from_file(file_path: str) -> TestingConfig:
    """Load configuration from YAML file.

    Args:
        file_path: Path to YAML configuration file

    Returns:
        TestingConfig instance loaded from file

    """
    try:
        import yaml

        with open(file_path) as f:
            config_data = yaml.safe_load(f)
        return get_config(config_data)
    except Exception as e:
        import warnings

        warnings.warn(f"Failed to load config from {file_path}: {e}", RuntimeWarning)
        return DEFAULT_CONFIG


def get_service_endpoint_names() -> List[str]:
    """Get list of available service endpoint names.

    Returns:
        List of service endpoint names

    """
    return list(DEFAULT_CONFIG.service_endpoints.keys())


def get_service_definition_names() -> List[str]:
    """Get list of available service definition names.

    Returns:
        List of service definition names

    """
    return list(DEFAULT_CONFIG.service_definitions.keys())


def update_service_endpoints_from_env() -> Dict[str, ServiceEndpoint]:
    """Update service endpoints from environment variables.

    Returns:
        Updated service endpoints dictionary

    """
    import os

    endpoints = DEFAULT_CONFIG.service_endpoints.copy()

    # Update URLs from environment variables
    env_mappings = {
        "gitlab": {"internal_url": "GITLAB_INTERNAL_URL", "external_url": "GITLAB_EXTERNAL_URL"},
        "keycloak": {
            "internal_url": "KEYCLOAK_INTERNAL_URL",
            "external_url": "KEYCLOAK_EXTERNAL_URL",
        },
        "prometheus": {
            "internal_url": "PROMETHEUS_INTERNAL_URL",
            "external_url": "PROMETHEUS_EXTERNAL_URL",
        },
        "grafana": {"internal_url": "GRAFANA_INTERNAL_URL", "external_url": "GRAFANA_EXTERNAL_URL"},
    }

    for service_name, env_vars in env_mappings.items():
        if service_name in endpoints:
            endpoint = endpoints[service_name]
            for attr, env_var in env_vars.items():
                env_value = os.getenv(env_var)
                if env_value:
                    setattr(endpoint, attr, env_value)

    return endpoints
