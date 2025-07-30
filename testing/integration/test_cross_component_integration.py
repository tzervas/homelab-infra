#!/usr/bin/env python3
"""
Cross-component integration tests for homelab infrastructure.

This module tests the integration between different components
(Helm, Kubernetes, Terraform, Ansible) to ensure they work together
seamlessly after the branch consolidation.
"""

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml


class CrossComponentIntegrationTest:
    """Test suite for cross-component integration."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "config" / "consolidated"
        self.helm_dir = self.project_root / "helm"
        self.k8s_dir = self.project_root / "kubernetes"
        self.terraform_dir = self.project_root / "terraform"
        self.ansible_dir = self.project_root / "ansible"

    def get_configuration_references(self) -> dict[str, set[str]]:
        """Extract configuration references across all components."""
        references = {
            "domains": set(),
            "services": set(),
            "namespaces": set(),
            "storage_classes": set(),
            "networks": set(),
        }

        # Extract from consolidated config
        config_files = {
            "domains": self.config_dir / "domains.yaml",
            "services": self.config_dir / "services.yaml",
            "namespaces": self.config_dir / "namespaces.yaml",
            "networking": self.config_dir / "networking.yaml",
            "storage": self.config_dir / "storage.yaml",
        }

        for config_type, config_file in config_files.items():
            if config_file.exists():
                with open(config_file) as f:
                    config_data = yaml.safe_load(f)

                    if config_type == "domains" and config_data:
                        if "domains" in config_data:
                            references["domains"].update(config_data["domains"].keys())

                    elif config_type == "services" and config_data:
                        if "services" in config_data:
                            references["services"].update(config_data["services"].keys())

                    elif config_type == "namespaces" and config_data:
                        if "namespaces" in config_data:
                            references["namespaces"].update(config_data["namespaces"].keys())

                    elif config_type == "networking" and config_data:
                        if "networks" in config_data:
                            references["networks"].update(config_data["networks"].keys())

                    elif config_type == "storage" and config_data:
                        if "storage_classes" in config_data:
                            references["storage_classes"].update(
                                config_data["storage_classes"].keys()
                            )

        return references


@pytest.fixture(scope="module")
def cross_component_test():
    """Pytest fixture for cross-component test setup."""
    return CrossComponentIntegrationTest()


class TestHelmKubernetesIntegration:
    """Test integration between Helm charts and Kubernetes manifests."""

    def test_namespace_consistency(self, cross_component_test):
        """Test that namespaces are consistent between Helm and K8s manifests."""
        # Get namespaces from consolidated config
        namespaces_config = cross_component_test.config_dir / "namespaces.yaml"
        config_namespaces = set()

        if namespaces_config.exists():
            with open(namespaces_config) as f:
                ns_data = yaml.safe_load(f)
                if ns_data and "namespaces" in ns_data:
                    config_namespaces = set(ns_data["namespaces"].keys())

        # Get namespaces from Kubernetes manifests
        k8s_namespaces = set()
        namespace_file = cross_component_test.k8s_dir / "base" / "namespaces.yaml"

        if namespace_file.exists():
            with open(namespace_file) as f:
                resources = list(yaml.safe_load_all(f))
                for resource in resources:
                    if resource and resource.get("kind") == "Namespace":
                        name = resource.get("metadata", {}).get("name")
                        if name:
                            k8s_namespaces.add(name)

        # Get namespaces from Helm values
        helm_namespaces = set()
        helm_values_dir = cross_component_test.helm_dir / "environments"

        for values_file in helm_values_dir.glob("values-*.yaml"):
            with open(values_file) as f:
                values_data = yaml.safe_load(f)
                if values_data:
                    # Look for namespace references
                    self._extract_namespaces_from_dict(values_data, helm_namespaces)

        # Verify consistency (allowing for some differences like system namespaces)
        common_namespaces = {"homelab", "monitoring", "gitlab", "keycloak"}

        for ns in common_namespaces:
            if ns in config_namespaces:
                assert (
                    ns in k8s_namespaces or len(k8s_namespaces) == 0
                ), f"Namespace {ns} in config but not in K8s manifests"

    def _extract_namespaces_from_dict(self, data: Any, namespaces: set[str]) -> None:
        """Recursively extract namespace references from data structure."""
        if isinstance(data, dict):
            if "namespace" in data and isinstance(data["namespace"], str):
                namespaces.add(data["namespace"])
            for value in data.values():
                self._extract_namespaces_from_dict(value, namespaces)
        elif isinstance(data, list):
            for item in data:
                self._extract_namespaces_from_dict(item, namespaces)

    def test_service_name_consistency(self, cross_component_test):
        """Test that service names are consistent across components."""
        # Get services from consolidated config
        services_config = cross_component_test.config_dir / "services.yaml"
        config_services = set()

        if services_config.exists():
            with open(services_config) as f:
                services_data = yaml.safe_load(f)
                if services_data and "services" in services_data:
                    config_services = set(services_data["services"].keys())

        # Get services from Kubernetes manifests
        k8s_services = set()
        k8s_base_dir = cross_component_test.k8s_dir / "base"

        for manifest_file in k8s_base_dir.glob("*.yaml"):
            with open(manifest_file) as f:
                resources = list(yaml.safe_load_all(f))
                for resource in resources:
                    if resource and resource.get("kind") == "Service":
                        name = resource.get("metadata", {}).get("name")
                        if name:
                            k8s_services.add(name)

        # Check for reasonable overlap
        if config_services and k8s_services:
            overlap = config_services.intersection(k8s_services)
            assert len(overlap) > 0, "No service name overlap between config and K8s manifests"

    def test_ingress_domain_consistency(self, cross_component_test):
        """Test that ingress domains are consistent with domain configuration."""
        # Get domains from consolidated config
        domains_config = cross_component_test.config_dir / "domains.yaml"
        config_domains = set()

        if domains_config.exists():
            with open(domains_config) as f:
                domains_data = yaml.safe_load(f)
                if domains_data:
                    if "domains" in domains_data:
                        config_domains = set(domains_data["domains"].keys())
                    elif "base_domain" in domains_data:
                        # Extract base domain
                        base_domain = domains_data["base_domain"]
                        config_domains.add(base_domain)

        # Get domains from Kubernetes ingress
        ingress_domains = set()
        k8s_base_dir = cross_component_test.k8s_dir / "base"

        for manifest_file in k8s_base_dir.glob("*.yaml"):
            with open(manifest_file) as f:
                resources = list(yaml.safe_load_all(f))
                for resource in resources:
                    if resource and resource.get("kind") == "Ingress":
                        spec = resource.get("spec", {})
                        rules = spec.get("rules", [])
                        for rule in rules:
                            if "host" in rule:
                                host = rule["host"]
                                # Extract domain from host
                                if "." in host:
                                    domain = ".".join(host.split(".")[1:])
                                    ingress_domains.add(domain)

        # Check for consistency (if both exist)
        if config_domains and ingress_domains:
            # Allow for flexible matching
            domain_match = False
            for config_domain in config_domains:
                for ingress_domain in ingress_domains:
                    if config_domain in ingress_domain or ingress_domain in config_domain:
                        domain_match = True
                        break

            assert (
                domain_match
            ), f"No domain match between config {config_domains} and ingress {ingress_domains}"


class TestTerraformHelmIntegration:
    """Test integration between Terraform and Helm."""

    def test_terraform_output_helm_input_consistency(self, cross_component_test):
        """Test that Terraform outputs match expected Helm inputs."""
        # Look for Terraform outputs
        terraform_outputs = set()

        for tf_file in cross_component_test.terraform_dir.rglob("outputs.tf"):
            with open(tf_file) as f:
                content = f.read()

                # Basic extraction of output names
                import re

                output_matches = re.findall(r'output\s+"([^"]+)"', content)
                terraform_outputs.update(output_matches)

        # Look for common integration points
        expected_outputs = {
            "cluster_endpoint",
            "cluster_ca_certificate",
            "kubeconfig",
            "load_balancer_ip",
            "storage_class_name",
        }

        # Check if we have relevant Terraform outputs (if Terraform is used)
        if terraform_outputs:
            common_outputs = terraform_outputs.intersection(expected_outputs)
            # We expect at least some common integration outputs
            assert (
                len(common_outputs) > 0 or len(terraform_outputs) == 0
            ), f"Terraform outputs {terraform_outputs} don't include expected integration points"

    def test_terraform_variable_configuration_consistency(self, cross_component_test):
        """Test that Terraform variables align with configuration."""
        # Get Terraform variables
        terraform_vars = set()

        for tf_file in cross_component_test.terraform_dir.rglob("variables.tf"):
            with open(tf_file) as f:
                content = f.read()

                # Basic extraction of variable names
                import re

                var_matches = re.findall(r'variable\s+"([^"]+)"', content)
                terraform_vars.update(var_matches)

        # Check for configuration alignment
        expected_vars = {
            "cluster_name",
            "node_count",
            "namespace",
            "domain_name",
            "environment",
        }

        if terraform_vars:
            # Should have some expected infrastructure variables
            common_vars = terraform_vars.intersection(expected_vars)
            assert (
                len(common_vars) > 0
            ), f"Terraform variables {terraform_vars} don't include expected configuration variables"


class TestAnsibleIntegration:
    """Test Ansible integration with other components."""

    def test_ansible_inventory_consistency(self, cross_component_test):
        """Test that Ansible inventory is consistent with infrastructure config."""
        inventory_files = [
            cross_component_test.ansible_dir / "inventory" / "hosts.yml",
            cross_component_test.ansible_dir / "inventory" / "vm-test-inventory.yml",
        ]

        for inventory_file in inventory_files:
            if inventory_file.exists():
                with open(inventory_file) as f:
                    inventory_data = yaml.safe_load(f)

                assert inventory_data is not None, f"Invalid inventory file: {inventory_file}"

                # Check for reasonable inventory structure
                if "all" in inventory_data:
                    all_group = inventory_data["all"]
                    assert (
                        "children" in all_group or "hosts" in all_group
                    ), f"Inventory {inventory_file} missing hosts or children"

    def test_ansible_playbook_integration(self, cross_component_test):
        """Test that Ansible playbooks integrate with configuration."""
        site_yml = cross_component_test.ansible_dir / "site.yml"

        if site_yml.exists():
            with open(site_yml) as f:
                playbook_data = yaml.safe_load(f)

            assert isinstance(playbook_data, list), "site.yml should contain a list of plays"

            # Check for integration with configuration
            for play in playbook_data:
                if isinstance(play, dict):
                    # Should have hosts defined
                    assert "hosts" in play, "Play missing hosts specification"

                    # Check for variable integration
                    vars_files = play.get("vars_files", [])
                    if vars_files:
                        # Verify vars files exist
                        for vars_file in vars_files:
                            vars_path = cross_component_test.ansible_dir / vars_file
                            if not vars_path.exists():
                                # Try relative to project root
                                vars_path = cross_component_test.project_root / vars_file

                            # Don't fail if external vars files don't exist
                            if not vars_path.exists() and not vars_file.startswith("config/"):
                                print(f"Warning: Ansible vars file not found: {vars_file}")


class TestConfigurationPropagation:
    """Test that configuration changes propagate correctly across components."""

    def test_domain_configuration_propagation(self, cross_component_test):
        """Test that domain configuration propagates to all components."""
        domains_config = cross_component_test.config_dir / "domains.yaml"

        if not domains_config.exists():
            pytest.skip("Domain configuration not found")

        with open(domains_config) as f:
            domains_data = yaml.safe_load(f)

        if not domains_data or "domains" not in domains_data:
            pytest.skip("No domains configuration found")

        domains = domains_data["domains"]

        # Check Helm values reference domains
        helm_values_dir = cross_component_test.helm_dir / "environments"
        domain_references_found = False

        for values_file in helm_values_dir.glob("values-*.yaml"):
            with open(values_file) as f:
                values_content = f.read()

                # Look for domain references
                for domain_key in domains:
                    if domain_key in values_content:
                        domain_references_found = True
                        break

        # Check Kubernetes manifests reference domains
        k8s_base_dir = cross_component_test.k8s_dir / "base"

        for manifest_file in k8s_base_dir.glob("*.yaml"):
            with open(manifest_file) as f:
                manifest_content = f.read()

                # Look for domain references in ingress or config
                for domain_key in domains:
                    if domain_key in manifest_content:
                        domain_references_found = True
                        break

        # We expect domains to be referenced somewhere
        if len(domains) > 0:
            assert (
                domain_references_found
            ), "Domain configuration not referenced in deployment files"

    def test_security_configuration_propagation(self, cross_component_test):
        """Test that security configuration propagates correctly."""
        security_config = cross_component_test.config_dir / "security.yaml"

        if not security_config.exists():
            pytest.skip("Security configuration not found")

        with open(security_config) as f:
            security_data = yaml.safe_load(f)

        if not security_data:
            pytest.skip("No security configuration found")

        # Check for security context enforcement in Helm charts
        charts_dir = cross_component_test.helm_dir / "charts"
        security_contexts_found = False

        for chart_dir in charts_dir.iterdir():
            if chart_dir.is_dir():
                values_file = chart_dir / "values.yaml"
                if values_file.exists():
                    with open(values_file) as f:
                        values_data = yaml.safe_load(f)

                        if values_data and "securityContext" in str(values_data):
                            security_contexts_found = True
                            break

        # Check Kubernetes manifests for security contexts
        k8s_base_dir = cross_component_test.k8s_dir / "base"
        security_contexts_file = k8s_base_dir / "security-contexts.yaml"

        if security_contexts_file.exists():
            security_contexts_found = True

        # We expect security configuration to be applied
        assert security_contexts_found, "Security configuration not applied in deployment files"


class TestDependencyChain:
    """Test dependency chains between components."""

    def test_deployment_order_dependencies(self, cross_component_test):
        """Test that deployment order respects dependencies."""
        # Check Helm chart dependencies
        charts_dir = cross_component_test.helm_dir / "charts"
        chart_dependencies = {}

        for chart_dir in charts_dir.iterdir():
            if chart_dir.is_dir():
                chart_yaml = chart_dir / "Chart.yaml"
                if chart_yaml.exists():
                    with open(chart_yaml) as f:
                        chart_data = yaml.safe_load(f)

                        chart_name = chart_data.get("name", chart_dir.name)
                        dependencies = chart_data.get("dependencies", [])
                        chart_dependencies[chart_name] = [dep["name"] for dep in dependencies]

        # Verify dependency chain is acyclic (simplified check)
        for chart, deps in chart_dependencies.items():
            for dep in deps:
                # Dependency should not depend back on the chart (circular dependency)
                if dep in chart_dependencies:
                    dep_deps = chart_dependencies[dep]
                    assert chart not in dep_deps, f"Circular dependency between {chart} and {dep}"

    def test_service_startup_dependencies(self, cross_component_test):
        """Test that service startup dependencies are properly configured."""
        # Check for init containers or dependency management
        k8s_base_dir = cross_component_test.k8s_dir / "base"

        dependency_patterns_found = False

        for manifest_file in k8s_base_dir.glob("*.yaml"):
            with open(manifest_file) as f:
                resources = list(yaml.safe_load_all(f))

                for resource in resources:
                    if resource and resource.get("kind") in ["Deployment", "StatefulSet"]:
                        spec = resource.get("spec", {})
                        template = spec.get("template", {})
                        pod_spec = template.get("spec", {})

                        # Check for init containers (dependency management)
                        if "initContainers" in pod_spec:
                            dependency_patterns_found = True

                        # Check for readiness/liveness probes (proper startup)
                        containers = pod_spec.get("containers", [])
                        for container in containers:
                            if "readinessProbe" in container or "livenessProbe" in container:
                                dependency_patterns_found = True

        # We expect some form of dependency management
        assert dependency_patterns_found, "No dependency management patterns found in deployments"


def run_cross_component_tests():
    """Run cross-component integration tests from command line."""
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    return pytest.main(pytest_args)


if __name__ == "__main__":
    exit_code = run_cross_component_tests()
    sys.exit(exit_code)
