"""Configuration settings for Homelab Portal."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = "Homelab Portal"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Kubernetes settings
    kubernetes_namespace: str = "default"
    in_cluster: bool = True

    # Service discovery
    prometheus_url: str = "http://prometheus.monitoring.svc.cluster.local:9090"
    keycloak_url: str = "http://keycloak.keycloak.svc.cluster.local:8080"

    # Security settings
    cors_origins: list[str] = ["https://homelab.local"]

    # Feature flags
    enable_metrics: bool = True
    enable_health_checks: bool = True
    enable_security_dashboard: bool = True

    # Cache settings
    cache_ttl: int = 60  # seconds

    # Services to monitor
    monitored_services: list[dict[str, str]] = [
        {
            "name": "Grafana",
            "namespace": "monitoring",
            "service": "grafana",
            "url": "https://grafana.homelab.local",
            "icon": "📊",
            "description": "Data visualization and monitoring dashboards",
        },
        {
            "name": "Prometheus",
            "namespace": "monitoring",
            "service": "prometheus",
            "url": "https://prometheus.homelab.local",
            "icon": "🔍",
            "description": "Metrics collection and monitoring system",
        },
        {
            "name": "GitLab",
            "namespace": "gitlab",
            "service": "gitlab-webservice",
            "url": "https://gitlab.homelab.local",
            "icon": "🚀",
            "description": "Self-hosted Git repository with CI/CD",
        },
        {
            "name": "Keycloak",
            "namespace": "keycloak",
            "service": "keycloak",
            "url": "https://keycloak.homelab.local",
            "icon": "🔐",
            "description": "Identity and access management",
        },
        {
            "name": "JupyterLab",
            "namespace": "jupyter",
            "service": "jupyter",
            "url": "https://jupyter.homelab.local",
            "icon": "📓",
            "description": "Interactive development environment",
        },
        {
            "name": "Ollama",
            "namespace": "ai-ml",
            "service": "ollama",
            "url": "https://ollama.homelab.local",
            "icon": "🤖",
            "description": "Local LLM hosting with web interface",
        },
        {
            "name": "Longhorn",
            "namespace": "longhorn-system",
            "service": "longhorn-frontend",
            "url": "https://longhorn.homelab.local",
            "icon": "💾",
            "description": "Distributed storage management",
        },
    ]
