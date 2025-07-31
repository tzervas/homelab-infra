#!/usr/bin/env python3
"""
Generate domains.yaml configuration dynamically from base settings.
This script reads from .env files and base configurations to create
a unified domain configuration without hardcoding.
"""

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class DomainConfigGenerator:
    """Generate domain configuration from base settings."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.env_vars = self._load_env_vars()
        self.services = self._get_service_list()

    def _load_env_vars(self) -> dict[str, str]:
        """Load environment variables from .env files."""
        env_vars = {}

        # Load from system environment
        env_vars.update(os.environ)

        # Load from .env files
        env_files = [
            self.base_dir / "helm" / "environments" / ".env",
            self.base_dir / ".env",
        ]

        for env_file in env_files:
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip()

        return env_vars

    def _get_service_list(self) -> list[str]:
        """Get list of services from the services configuration."""
        services_file = self.base_dir / "config" / "consolidated" / "services.yaml"
        services = []

        if services_file.exists():
            with open(services_file) as f:
                config = yaml.safe_load(f)
                if config and "services" in config:
                    # Extract service names from nested structure
                    for category_services in config["services"].values():
                        if isinstance(category_services, dict):
                            for service_name in category_services:
                                if service_name not in services:
                                    services.append(service_name)

        # Default services if file doesn't exist
        if not services:
            services = [
                "auth",
                "homelab",
                "grafana",
                "prometheus",
                "ollama",
                "jupyter",
                "gitlab",
                "keycloak",
                "longhorn",
                "argocd",
                "oauth2-proxy",
            ]

        return services

    def _get_base_domain(self, environment: str = "production") -> str:
        """Get base domain for the given environment."""
        # Check environment-specific domain first
        env_domain_key = f"HOMELAB_{environment.upper()}_DOMAIN"
        if env_domain_key in self.env_vars:
            return self.env_vars[env_domain_key]

        # Fall back to main domain
        if "HOMELAB_DOMAIN" in self.env_vars:
            base_domain = self.env_vars["HOMELAB_DOMAIN"]
            if environment != "production":
                # Add environment prefix for non-prod
                return f"{environment}.{base_domain}"
            return base_domain

        # Default fallback
        return f"{environment}.homelab.local" if environment != "production" else "homelab.local"

    def generate_config(self) -> dict[str, Any]:
        """Generate the complete domain configuration."""
        config = {
            "domains": {
                "base": {
                    "primary": self._get_base_domain(),
                    "tld": self._get_base_domain().split(".")[-1],
                },
            },
            "global": {
                "domain": {
                    "base": self._get_base_domain(),
                    "tld": self._get_base_domain().split(".")[-1],
                },
                "labels": {
                    "app.kubernetes.io/managed-by": "homelab-infra",
                    "app.kubernetes.io/part-of": "homelab",
                    "homelab.local/environment": "{{ .Values.environment }}",
                    "homelab.local/component": "{{ .Values.component }}",
                },
                "services": {},
                "environments": {},
            },
            "dns": {
                "cluster_dns": self.env_vars.get("CLUSTER_DNS", "10.43.0.10"),
                "search_domains": [],
            },
            "certificates": {
                "issuer": {
                    "email": self.env_vars.get("TLS_EMAIL", "admin@homelab.local"),
                    "staging_server": "https://acme-staging-v02.api.letsencrypt.org/directory",
                    "production_server": "https://acme-v02.api.letsencrypt.org/directory",
                },
                "defaults": {
                    "duration": "2160h",
                    "renewBefore": "360h",
                    "algorithm": "RSA",
                    "size": 2048,
                },
                "ca": {
                    "common_name": "Homelab CA",
                    "organization": "Homelab",
                    "organizational_unit": "Homelab Infrastructure",
                    "country": "US",
                    "province": "Home",
                    "locality": "Lab",
                },
            },
            "registry": {
                "default": self.env_vars.get("REGISTRY_DEFAULT", "docker.io"),
                "pullPolicy": self.env_vars.get("REGISTRY_PULL_POLICY", "IfNotPresent"),
                "pullSecrets": [],
            },
            "annotations": {
                "deployment.kubernetes.io/revision": '{{ .Values.revision | default "1" }}',
                "homelab.local/managed-by": "centralized-config",
                "homelab.local/last-updated": '{{ now | date "2006-01-02T15:04:05Z" }}',
            },
        }

        # Generate service subdomains dynamically
        base_domain = self._get_base_domain()
        for service in self.services:
            # Special case for the main homelab service
            if service == "homelab":
                config["global"]["services"][service] = base_domain
            else:
                config["global"]["services"][service] = f"{service}.{base_domain}"

        # Generate environment-specific configurations
        environments = ["development", "staging", "production"]
        for env in environments:
            env_domain = self._get_base_domain(env)
            config["global"]["environments"][env] = {
                "suffix": "" if env == "production" else env,
                "base": env_domain,
            }

        # Generate search domains
        config["dns"]["search_domains"] = [
            base_domain,
            "svc.cluster.local",
            "cluster.local",
        ]

        return config

    def write_config(self, output_path: Path) -> None:
        """Write the generated configuration to a file."""
        config = self.generate_config()

        # Add header comment
        header = f"""# Unified Domain Configuration
# Single source of truth for all domain-related settings
#
# THIS FILE IS AUTOMATICALLY GENERATED - DO NOT EDIT DIRECTLY
# Generated at: {datetime.utcnow().isoformat()}Z
#
# To modify domain settings, update:
#   - .env file for environment-specific domains
#   - config/consolidated/services.yaml for service list
#   - Then run: scripts/generate-domains-config.py
"""

        with open(output_path, "w") as f:
            f.write(header)
            f.write("\n")
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Generated domain configuration: {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate dynamic domain configuration from base settings",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output path for generated domains.yaml",
    )
    parser.add_argument(
        "--base-dir",
        "-b",
        type=Path,
        default=Path.cwd(),
        help="Base directory of the project (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print configuration without writing to file",
    )

    args = parser.parse_args()

    # Find project root if not specified
    if not (args.base_dir / "config").exists():
        # Try to find project root
        current = Path.cwd()
        while current != current.parent:
            if (current / "config" / "consolidated").exists():
                args.base_dir = current
                break
            current = current.parent

    # Default output path
    if not args.output:
        args.output = args.base_dir / "config" / "consolidated" / "domains.yaml"

    generator = DomainConfigGenerator(args.base_dir)

    if args.dry_run:
        config = generator.generate_config()
        print(yaml.dump(config, default_flow_style=False, sort_keys=False))
    else:
        generator.write_config(args.output)


if __name__ == "__main__":
    main()
