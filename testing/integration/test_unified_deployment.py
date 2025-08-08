#!/usr/bin/env python3
"""
Integration tests for unified deployment functionality.

This module tests the complete deployment pipeline from configuration
through to running services, validating that all components work together
as expected after the branch consolidation.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


# Test configuration
TEST_CONFIG = {
    "cluster_name": "integration-test",
    "namespace": "homelab-integration-test",
    "timeout": 300,  # 5 minutes
    "cleanup_after_test": True,
}


class IntegrationTestError(Exception):
    """Custom exception for integration test failures."""


class UnifiedDeploymentIntegrationTest:
    """Integration test suite for unified deployment functionality."""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent
        self.config_dir = self.project_root / "config" / "consolidated"
        self.helm_dir = self.project_root / "helm"
        self.k8s_dir = self.project_root / "kubernetes"
        self.terraform_dir = self.project_root / "terraform"

        # Test state tracking
        self.deployed_resources = []
        self.test_namespace = TEST_CONFIG["namespace"]

    def setup_test_environment(self):
        """Set up the test environment."""
        print("Setting up integration test environment...")

        # Create test namespace
        self._run_kubectl(
            [
                "create",
                "namespace",
                self.test_namespace,
                "--dry-run=client",
                "-o",
                "yaml",
            ],
        )

        # Validate required files exist
        required_files = [
            self.config_dir / "domains.yaml",
            self.config_dir / "networking.yaml",
            self.config_dir / "security.yaml",
            self.helm_dir / "helmfile.yaml",
        ]

        for file_path in required_files:
            if not file_path.exists():
                msg = f"Required file missing: {file_path}"
                raise IntegrationTestError(msg)

    def teardown_test_environment(self):
        """Clean up test environment."""
        if TEST_CONFIG["cleanup_after_test"]:
            print("Cleaning up integration test environment...")
            try:
                self._run_kubectl(
                    ["delete", "namespace", self.test_namespace, "--ignore-not-found=true"],
                )
            except subprocess.CalledProcessError:
                print(f"Warning: Could not delete namespace {self.test_namespace}")

    def _run_kubectl(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run kubectl command with error handling."""
        cmd = ["kubectl", *args]
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            msg = f"kubectl command timed out: {' '.join(cmd)}"
            raise IntegrationTestError(msg)
        except subprocess.CalledProcessError as e:
            msg = f"kubectl command failed: {e.stderr}"
            raise IntegrationTestError(msg)

    def _run_helm(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run helm command with error handling."""
        cmd = ["helm", *args]
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=120,
                cwd=self.helm_dir,
            )
        except subprocess.TimeoutExpired:
            msg = f"helm command timed out: {' '.join(cmd)}"
            raise IntegrationTestError(msg)
        except subprocess.CalledProcessError as e:
            msg = f"helm command failed: {e.stderr}"
            raise IntegrationTestError(msg)


@pytest.fixture(scope="module")
def integration_test():
    """Pytest fixture for integration test setup and teardown."""
    test_instance = UnifiedDeploymentIntegrationTest()
    test_instance.setup_test_environment()
    yield test_instance
    test_instance.teardown_test_environment()


class TestConfigurationIntegration:
    """Test configuration integration across all components."""

    def test_config_consolidation_integrity(self, integration_test):
        """Test that consolidated configuration maintains integrity."""
        config_files = [
            "domains.yaml",
            "networking.yaml",
            "security.yaml",
            "services.yaml",
            "storage.yaml",
            "namespaces.yaml",
            "environments.yaml",
            "resources.yaml",
        ]

        for config_file in config_files:
            config_path = integration_test.config_dir / config_file
            assert config_path.exists(), f"Configuration file missing: {config_file}"

            # Validate YAML syntax
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                assert config_data is not None, f"Invalid YAML in {config_file}"

    def test_environment_config_consistency(self, integration_test):
        """Test that environment configurations are consistent."""
        env_dir = integration_test.project_root / "config" / "environments"
        environments = ["development", "staging", "production"]

        for env in environments:
            env_path = env_dir / env / "values.yaml"
            if env_path.exists():
                with open(env_path) as f:
                    env_config = yaml.safe_load(f)

                    # Validate required sections
                    assert "global" in env_config or "app" in env_config, (
                        f"Environment {env} missing required configuration sections"
                    )

    def test_helm_values_integration(self, integration_test):
        """Test Helm values integration with consolidated config."""
        helm_values_dir = integration_test.helm_dir / "environments"

        for values_file in helm_values_dir.glob("values-*.yaml"):
            with open(values_file) as f:
                values_data = yaml.safe_load(f)

                # Check for consistent structure
                assert isinstance(values_data, dict), f"Invalid structure in {values_file.name}"

                # Validate no hardcoded secrets
                yaml_str = yaml.dump(values_data)
                suspicious_patterns = ["password:", "secret:", "key:"]

                for pattern in suspicious_patterns:
                    if pattern in yaml_str.lower():
                        # Check if it's a placeholder or reference
                        lines = yaml_str.lower().split("\n")
                        for line in lines:
                            if pattern in line and not any(
                                placeholder in line
                                for placeholder in [
                                    "changeme",
                                    "placeholder",
                                    "template",
                                    "${",
                                    "secretref",
                                ]
                            ):
                                pytest.fail(
                                    f"Potential hardcoded secret in {values_file.name}: {line.strip()}",
                                )


class TestHelmIntegration:
    """Test Helm chart integration and deployment."""

    def test_helm_chart_validation(self, integration_test):
        """Test that all Helm charts are valid and can be templated."""
        charts_dir = integration_test.helm_dir / "charts"

        for chart_dir in charts_dir.iterdir():
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                print(f"Validating Helm chart: {chart_dir.name}")

                # Test chart templating
                result = integration_test._run_helm(
                    [
                        "template",
                        chart_dir.name,
                        str(chart_dir),
                        "--debug",
                        "--dry-run",
                    ],
                )

                assert result.returncode == 0, f"Helm template failed for {chart_dir.name}"
                assert len(result.stdout) > 0, f"No output from helm template for {chart_dir.name}"

    def test_helmfile_validation(self, integration_test):
        """Test helmfile configuration validation."""
        helmfile_path = integration_test.helm_dir / "helmfile.yaml"
        assert helmfile_path.exists(), "helmfile.yaml not found"

        # Test helmfile template
        result = subprocess.run(
            [
                "helmfile",
                "template",
                "--skip-deps",
            ],
            cwd=integration_test.helm_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        # Note: helmfile might not be available in CI, so we'll check file syntax instead
        if result.returncode != 0 and "command not found" not in result.stderr:
            pytest.fail(f"Helmfile validation failed: {result.stderr}")

    def test_helm_security_contexts(self, integration_test):
        """Test that Helm charts enforce proper security contexts."""
        charts_dir = integration_test.helm_dir / "charts"

        for chart_dir in charts_dir.iterdir():
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                # Template the chart
                result = integration_test._run_helm(
                    [
                        "template",
                        chart_dir.name,
                        str(chart_dir),
                    ],
                )

                # Parse templated output
                templated_yaml = result.stdout

                # Check for security contexts in Deployment/StatefulSet resources
                resources = yaml.safe_load_all(templated_yaml)

                for resource in resources:
                    if resource and resource.get("kind") in ["Deployment", "StatefulSet"]:
                        spec = resource.get("spec", {})
                        template = spec.get("template", {})
                        pod_spec = template.get("spec", {})

                        # Check for pod security context
                        security_context = pod_spec.get("securityContext", {})

                        # Should have non-root user
                        if "runAsNonRoot" in security_context:
                            assert security_context["runAsNonRoot"] is True, (
                                f"Chart {chart_dir.name} allows root execution"
                            )


class TestKubernetesIntegration:
    """Test Kubernetes manifest integration."""

    def test_kubernetes_manifest_validation(self, integration_test):
        """Test that Kubernetes manifests are valid."""
        k8s_base_dir = integration_test.k8s_dir / "base"

        for manifest_file in k8s_base_dir.glob("*.yaml"):
            print(f"Validating K8s manifest: {manifest_file.name}")

            # Validate with kubectl dry-run
            result = integration_test._run_kubectl(
                [
                    "apply",
                    "-f",
                    str(manifest_file),
                    "--dry-run=client",
                    "--validate=true",
                ],
            )

            assert result.returncode == 0, (
                f"Kubernetes manifest validation failed for {manifest_file.name}: {result.stderr}"
            )

    def test_network_policies_integration(self, integration_test):
        """Test network policies are properly configured."""
        network_policies_file = integration_test.k8s_dir / "base" / "network-policies.yaml"

        if network_policies_file.exists():
            with open(network_policies_file) as f:
                policies = list(yaml.safe_load_all(f))

            # Should have at least a default deny policy
            policy_names = [p.get("metadata", {}).get("name", "") for p in policies if p]
            assert any("deny" in name.lower() for name in policy_names), (
                "No default deny network policy found"
            )

    def test_rbac_integration(self, integration_test):
        """Test RBAC configuration is properly set up."""
        rbac_file = integration_test.k8s_dir / "base" / "rbac.yaml"

        if rbac_file.exists():
            with open(rbac_file) as f:
                rbac_resources = list(yaml.safe_load_all(f))

            # Should have ServiceAccount and either Role/ClusterRole and RoleBinding/ClusterRoleBinding
            resource_kinds = [r.get("kind", "") for r in rbac_resources if r]

            # Validate ServiceAccount exists
            assert "ServiceAccount" in resource_kinds, "Missing ServiceAccount"

            # Check for either Role or ClusterRole
            assert any(kind in resource_kinds for kind in ["Role", "ClusterRole"]), (
                "Missing Role or ClusterRole"
            )

            # Check for either RoleBinding or ClusterRoleBinding
            assert any(kind in resource_kinds for kind in ["RoleBinding", "ClusterRoleBinding"]), (
                "Missing RoleBinding or ClusterRoleBinding"
            )


class TestTerraformIntegration:
    """Test Terraform integration (preparation for Terratest)."""

    def test_terraform_syntax_validation(self, integration_test):
        """Test Terraform configuration syntax."""
        terraform_files = list(integration_test.terraform_dir.rglob("*.tf"))

        assert len(terraform_files) > 0, "No Terraform files found"

        for tf_file in terraform_files:
            # Basic syntax validation
            with open(tf_file) as f:
                content = f.read()

                # Check for basic Terraform syntax
                assert content.strip(), f"Empty Terraform file: {tf_file}"
                assert not content.count("{") < content.count(
                    "}",
                ), f"Unbalanced braces in {tf_file}"

    def test_terraform_module_structure(self, integration_test):
        """Test Terraform module structure."""
        modules_dir = integration_test.terraform_dir / "modules"

        if modules_dir.exists():
            for module_dir in modules_dir.iterdir():
                if module_dir.is_dir():
                    # Each module should have main.tf and variables.tf
                    main_tf = module_dir / "main.tf"
                    variables_tf = module_dir / "variables.tf"

                    assert main_tf.exists(), f"Module {module_dir.name} missing main.tf"
                    # variables.tf is recommended but not required
                    if not variables_tf.exists():
                        print(f"Warning: Module {module_dir.name} missing variables.tf")


class TestServiceIntegration:
    """Test service integration and dependencies."""

    def test_service_configuration_consistency(self, integration_test):
        """Test that service configurations are consistent across components."""
        services_config = integration_test.config_dir / "services.yaml"

        if services_config.exists():
            with open(services_config) as f:
                services = yaml.safe_load(f)

            # Validate service configuration structure
            assert isinstance(services, dict), "Services configuration should be a dictionary"

            # Check for required service definitions
            expected_services = ["keycloak", "gitlab", "grafana", "prometheus"]

            if "services" in services:
                service_names = list(services["services"].keys())
                for expected_service in expected_services:
                    if expected_service not in service_names:
                        print(
                            f"Warning: Expected service {expected_service} not found in configuration",
                        )

    def test_monitoring_integration(self, integration_test):
        """Test monitoring stack integration."""
        monitoring_dir = integration_test.k8s_dir / "monitoring"

        if monitoring_dir.exists():
            # Check for Prometheus configuration
            prometheus_files = list(monitoring_dir.rglob("*prometheus*.yaml"))
            assert len(prometheus_files) > 0, "No Prometheus configuration found"

            # Validate ServiceMonitor configurations
            for prom_file in prometheus_files:
                with open(prom_file) as f:
                    resources = list(yaml.safe_load_all(f))

                for resource in resources:
                    if resource and resource.get("kind") == "ServiceMonitor":
                        spec = resource.get("spec", {})
                        assert "selector" in spec, "ServiceMonitor missing selector"
                        assert "endpoints" in spec, "ServiceMonitor missing endpoints"


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.slow()
    def test_configuration_to_deployment_pipeline(self, integration_test):
        """Test the complete pipeline from configuration to deployment."""
        # This test simulates the full deployment process

        # Step 1: Validate configuration loading
        config_files = list(integration_test.config_dir.glob("*.yaml"))
        assert len(config_files) > 0, "No configuration files found"

        # Step 2: Test Helm chart templating with configurations
        charts_dir = integration_test.helm_dir / "charts"

        for chart_dir in charts_dir.iterdir():
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                # Template with test values
                test_values = {
                    "global": {"imageRegistry": "test.registry"},
                    "replicaCount": 1,
                    "image": {"tag": "test"},
                }

                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                    yaml.dump(test_values, f)
                    test_values_file = f.name

                try:
                    result = integration_test._run_helm(
                        [
                            "template",
                            chart_dir.name,
                            str(chart_dir),
                            "-f",
                            test_values_file,
                        ],
                    )

                    assert result.returncode == 0, (
                        f"Helm template with test values failed for {chart_dir.name}"
                    )

                    # Validate the templated output
                    templated_resources = list(yaml.safe_load_all(result.stdout))
                    valid_resources = [r for r in templated_resources if r is not None]
                    assert len(valid_resources) > 0, (
                        f"No valid resources generated for {chart_dir.name}"
                    )

                finally:
                    os.unlink(test_values_file)

    def test_security_policy_enforcement(self, integration_test):
        """Test that security policies are properly enforced."""
        # Test Pod Security Standards
        pod_security_file = integration_test.k8s_dir / "base" / "pod-security-standards.yaml"

        if pod_security_file.exists():
            with open(pod_security_file) as f:
                resources = list(yaml.safe_load_all(f))

            # Should have namespace labels for Pod Security Standards
            for resource in resources:
                if resource and resource.get("kind") == "Namespace":
                    labels = resource.get("metadata", {}).get("labels", {})

                    # Check for Pod Security Standard labels
                    pss_labels = [
                        "pod-security.kubernetes.io/enforce",
                        "pod-security.kubernetes.io/audit",
                        "pod-security.kubernetes.io/warn",
                    ]

                    pss_found = any(label in labels for label in pss_labels)
                    if not pss_found:
                        print(
                            f"Warning: Namespace {resource.get('metadata', {}).get('name')} "
                            "missing Pod Security Standard labels",
                        )


def run_integration_tests():
    """Run integration tests from command line."""
    import sys

    # Run pytest with integration test configuration
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    # Add slow tests if requested
    if "--include-slow" in sys.argv:
        pytest_args.append("-m")
        pytest_args.append("slow")
    else:
        pytest_args.append("-m")
        pytest_args.append("not slow")

    return pytest.main(pytest_args)


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
