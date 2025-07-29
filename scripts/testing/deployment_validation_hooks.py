#!/usr/bin/env python3
"""
Deployment Validation Hooks Framework
Provides automated pre-deployment, post-deployment, and continuous validation hooks
for all deployment states in the homelab infrastructure.

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License
"""

import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


try:
    import yaml

    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    print("Warning: Required dependencies not installed. Run: uv add kubernetes pyyaml")
    sys.exit(1)

# Import existing testing modules
try:
    from .infrastructure_health import InfrastructureHealthMonitor
    from .integration_tester import IntegrationConnectivityTester
    from .network_security import NetworkSecurityValidator
    from .service_checker import ServiceDeploymentChecker
    from .test_reporter import HomelabTestReporter, TestSuiteResult
except ImportError:
    try:
        from infrastructure_health import InfrastructureHealthMonitor
        from integration_tester import IntegrationConnectivityTester
        from network_security import NetworkSecurityValidator
        from service_checker import ServiceDeploymentChecker
        from test_reporter import HomelabTestReporter, TestSuiteResult
    except ImportError as e:
        print(f"Warning: Could not import testing modules: {e}")
        print("Some functionality may be limited.")


class DeploymentPhase(Enum):
    """Deployment phases for hook execution."""

    PRE_DEPLOYMENT = "pre-deployment"
    POST_DEPLOYMENT = "post-deployment"
    CONTINUOUS = "continuous"
    ROLLBACK = "rollback"
    UPGRADE = "upgrade"


class HookResult(Enum):
    """Hook execution results."""

    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class ValidationHookConfig:
    """Configuration for validation hooks."""

    enabled: bool = True
    timeout: int = 300
    retry_count: int = 3
    retry_delay: int = 10
    failure_threshold: float = 0.8  # 80% success rate required
    critical: bool = False  # Whether failure should block deployment
    environment_specific: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookExecutionResult:
    """Result of hook execution."""

    hook_name: str
    phase: DeploymentPhase
    result: HookResult
    timestamp: str
    duration: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class DeploymentValidationHook(ABC):
    """Abstract base class for deployment validation hooks."""

    def __init__(
        self,
        name: str,
        config: ValidationHookConfig,
        kubeconfig_path: str | None = None,
        log_level: str = "INFO",
    ) -> None:
        self.name = name
        self.config = config
        self.kubeconfig_path = kubeconfig_path
        self.logger = self._setup_logging(log_level)
        self._setup_kubernetes_client()

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure logging for the hook."""
        logger = logging.getLogger(f"hook.{self.name}")
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"%(asctime)s - [{self.name}] - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _setup_kubernetes_client(self) -> None:
        """Initialize Kubernetes client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                config.load_incluster_config()

            self.k8s_client = client.ApiClient()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()

        except Exception as e:
            self.logger.warning(f"Failed to initialize Kubernetes client: {e}")
            self.k8s_client = None
            self.v1 = None
            self.apps_v1 = None

    @abstractmethod
    def execute(self, phase: DeploymentPhase, context: dict[str, Any]) -> HookExecutionResult:
        """Execute the validation hook."""

    def is_enabled_for_phase(self, phase: DeploymentPhase) -> bool:
        """Check if hook is enabled for specific phase."""
        if not self.config.enabled:
            return False

        # Check phase-specific configuration
        phase_config = self.config.environment_specific.get(phase.value, {})
        return phase_config.get("enabled", True)

    def should_block_on_failure(self) -> bool:
        """Determine if hook failure should block deployment."""
        return self.config.critical


class PreDeploymentValidationHook(DeploymentValidationHook):
    """Pre-deployment validation hook for infrastructure readiness."""

    def execute(self, phase: DeploymentPhase, context: dict[str, Any]) -> HookExecutionResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Executing pre-deployment validation: {self.name}")

        try:
            validation_results = []

            # 1. Cluster connectivity validation
            cluster_result = self._validate_cluster_connectivity()
            validation_results.append(cluster_result)

            # 2. Resource availability validation
            resource_result = self._validate_resource_availability(context)
            validation_results.append(resource_result)

            # 3. Prerequisite services validation
            prereq_result = self._validate_prerequisites(context)
            validation_results.append(prereq_result)

            # 4. Configuration validation
            config_result = self._validate_configurations(context)
            validation_results.append(config_result)

            # 5. Security validation
            security_result = self._validate_security_context(context)
            validation_results.append(security_result)

            # Analyze results
            success_count = sum(1 for r in validation_results if r.get("success", False))
            total_count = len(validation_results)
            success_rate = success_count / total_count if total_count > 0 else 0

            duration = time.time() - start_time

            if success_rate >= self.config.failure_threshold:
                result = HookResult.SUCCESS
                message = f"Pre-deployment validation passed ({success_count}/{total_count} checks)"
            elif success_rate >= 0.5:
                result = HookResult.WARNING
                message = (
                    f"Pre-deployment validation warnings ({success_count}/{total_count} checks)"
                )
            else:
                result = HookResult.FAILURE
                message = f"Pre-deployment validation failed ({success_count}/{total_count} checks)"

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=result,
                timestamp=timestamp,
                duration=duration,
                message=message,
                details={
                    "validation_results": validation_results,
                    "success_rate": success_rate,
                    "total_checks": total_count,
                    "passed_checks": success_count,
                },
                metrics={
                    "success_rate": success_rate,
                    "execution_time": duration,
                    "checks_performed": total_count,
                },
                recommendations=self._generate_recommendations(validation_results),
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.exception(f"Pre-deployment validation failed: {e}")

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=HookResult.FAILURE,
                timestamp=timestamp,
                duration=duration,
                message=f"Pre-deployment validation error: {e!s}",
                details={"error": str(e)},
                recommendations=[
                    "Review pre-deployment validation logs and fix configuration issues",
                ],
            )

    def _validate_cluster_connectivity(self) -> dict[str, Any]:
        """Validate Kubernetes cluster connectivity."""
        try:
            if not self.v1:
                return {
                    "name": "cluster_connectivity",
                    "success": False,
                    "message": "Kubernetes client not available",
                }

            # Test API server connectivity
            self.v1.get_api_resources()

            # Test node connectivity
            nodes = self.v1.list_node()
            ready_nodes = [
                n
                for n in nodes.items
                if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions or [])
            ]

            if len(ready_nodes) == 0:
                return {
                    "name": "cluster_connectivity",
                    "success": False,
                    "message": "No ready nodes found",
                    "details": {"total_nodes": len(nodes.items), "ready_nodes": 0},
                }

            return {
                "name": "cluster_connectivity",
                "success": True,
                "message": f"Cluster connectivity verified ({len(ready_nodes)}/{len(nodes.items)} nodes ready)",
                "details": {"total_nodes": len(nodes.items), "ready_nodes": len(ready_nodes)},
            }

        except Exception as e:
            return {
                "name": "cluster_connectivity",
                "success": False,
                "message": f"Cluster connectivity failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _validate_resource_availability(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate cluster resource availability."""
        try:
            if not self.v1:
                return {
                    "name": "resource_availability",
                    "success": False,
                    "message": "Kubernetes client not available",
                }

            # Get node metrics
            nodes = self.v1.list_node()
            allocatable_cpu = 0
            allocatable_memory = 0

            for node in nodes.items:
                if node.status.allocatable:
                    cpu = node.status.allocatable.get("cpu", "0")
                    memory = node.status.allocatable.get("memory", "0Ki")

                    # Convert CPU (may be in millicores)
                    if "m" in cpu:
                        allocatable_cpu += int(cpu.replace("m", "")) / 1000
                    else:
                        allocatable_cpu += int(cpu)

                    # Convert memory (in Ki, Mi, Gi)
                    if "Ki" in memory:
                        allocatable_memory += int(memory.replace("Ki", "")) / 1024 / 1024
                    elif "Mi" in memory:
                        allocatable_memory += int(memory.replace("Mi", "")) / 1024
                    elif "Gi" in memory:
                        allocatable_memory += int(memory.replace("Gi", ""))

            # Check if we have minimum resources
            min_cpu = context.get("min_cpu_cores", 2)
            min_memory = context.get("min_memory_gb", 4)

            success = allocatable_cpu >= min_cpu and allocatable_memory >= min_memory

            return {
                "name": "resource_availability",
                "success": success,
                "message": f"Resource check: {allocatable_cpu:.1f} CPU cores, {allocatable_memory:.1f}GB RAM available",
                "details": {
                    "allocatable_cpu": allocatable_cpu,
                    "allocatable_memory": allocatable_memory,
                    "required_cpu": min_cpu,
                    "required_memory": min_memory,
                },
            }

        except Exception as e:
            return {
                "name": "resource_availability",
                "success": False,
                "message": f"Resource availability check failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _validate_prerequisites(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate prerequisite services and configurations."""
        try:
            prerequisites = context.get("prerequisites", [])
            if not prerequisites:
                return {
                    "name": "prerequisites",
                    "success": True,
                    "message": "No prerequisites specified",
                    "details": {},
                }

            results = []
            for prereq in prerequisites:
                if prereq["type"] == "namespace":
                    try:
                        self.v1.read_namespace(prereq["name"])
                        results.append({"name": prereq["name"], "success": True})
                    except ApiException:
                        results.append({"name": prereq["name"], "success": False})

                elif prereq["type"] == "storageclass":
                    try:
                        storage_v1 = client.StorageV1Api()
                        storage_v1.read_storage_class(prereq["name"])
                        results.append({"name": prereq["name"], "success": True})
                    except ApiException:
                        results.append({"name": prereq["name"], "success": False})

            success_count = sum(1 for r in results if r["success"])
            success = success_count == len(results)

            return {
                "name": "prerequisites",
                "success": success,
                "message": f"Prerequisites check: {success_count}/{len(results)} satisfied",
                "details": {"results": results},
            }

        except Exception as e:
            return {
                "name": "prerequisites",
                "success": False,
                "message": f"Prerequisites validation failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _validate_configurations(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate deployment configurations."""
        try:
            config_paths = context.get("config_paths", [])
            if not config_paths:
                return {
                    "name": "configurations",
                    "success": True,
                    "message": "No configuration validation specified",
                    "details": {},
                }

            valid_configs = 0
            total_configs = 0

            for config_path in config_paths:
                path = Path(config_path)
                if path.exists():
                    if path.suffix in [".yaml", ".yml"]:
                        try:
                            with open(path) as f:
                                yaml.safe_load(f)
                            valid_configs += 1
                        except yaml.YAMLError:
                            pass
                    elif path.suffix == ".json":
                        try:
                            with open(path) as f:
                                json.load(f)
                            valid_configs += 1
                        except json.JSONDecodeError:
                            pass
                    total_configs += 1

            success = valid_configs == total_configs and total_configs > 0

            return {
                "name": "configurations",
                "success": success,
                "message": f"Configuration validation: {valid_configs}/{total_configs} valid",
                "details": {"valid_configs": valid_configs, "total_configs": total_configs},
            }

        except Exception as e:
            return {
                "name": "configurations",
                "success": False,
                "message": f"Configuration validation failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _validate_security_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate security context and policies."""
        try:
            security_checks = []

            # Check for Pod Security Standards
            try:
                # Check if PSS is enabled
                namespaces = self.v1.list_namespace()
                pss_enabled = any(
                    ns.metadata.labels
                    and any(k.startswith("pod-security.kubernetes.io/") for k in ns.metadata.labels)
                    for ns in namespaces.items
                )
                security_checks.append(
                    {
                        "name": "pod_security_standards",
                        "success": pss_enabled,
                        "message": "Pod Security Standards configured"
                        if pss_enabled
                        else "Pod Security Standards not configured",
                    },
                )
            except Exception:
                security_checks.append(
                    {
                        "name": "pod_security_standards",
                        "success": False,
                        "message": "Failed to check Pod Security Standards",
                    },
                )

            # Check for NetworkPolicies if required
            security_requirements = context.get("security_requirements", {})
            if security_requirements.get("require_network_policies", False):
                try:
                    networking_v1 = client.NetworkingV1Api()
                    policies = networking_v1.list_network_policy_for_all_namespaces()
                    has_policies = len(policies.items) > 0
                    security_checks.append(
                        {
                            "name": "network_policies",
                            "success": has_policies,
                            "message": f"Network policies: {len(policies.items)} found"
                            if has_policies
                            else "No network policies found",
                        },
                    )
                except Exception:
                    security_checks.append(
                        {
                            "name": "network_policies",
                            "success": False,
                            "message": "Failed to check network policies",
                        },
                    )

            success_count = sum(1 for check in security_checks if check["success"])
            success = success_count == len(security_checks) if security_checks else True

            return {
                "name": "security_context",
                "success": success,
                "message": f"Security validation: {success_count}/{len(security_checks)} checks passed",
                "details": {"security_checks": security_checks},
            }

        except Exception as e:
            return {
                "name": "security_context",
                "success": False,
                "message": f"Security validation failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _generate_recommendations(self, validation_results: list[dict[str, Any]]) -> list[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        for result in validation_results:
            if not result.get("success", False):
                name = result.get("name", "unknown")

                if name == "cluster_connectivity":
                    recommendations.append("Verify kubectl configuration and cluster accessibility")
                elif name == "resource_availability":
                    recommendations.append(
                        "Ensure sufficient CPU and memory resources are available",
                    )
                elif name == "prerequisites":
                    recommendations.append("Create required namespaces and storage classes")
                elif name == "configurations":
                    recommendations.append("Validate and fix configuration file syntax errors")
                elif name == "security_context":
                    recommendations.append("Review and configure security policies and contexts")

        return recommendations


class PostDeploymentValidationHook(DeploymentValidationHook):
    """Post-deployment validation hook for deployment verification."""

    def execute(self, phase: DeploymentPhase, context: dict[str, Any]) -> HookExecutionResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Executing post-deployment validation: {self.name}")

        try:
            # Initialize comprehensive testing framework
            test_reporter = HomelabTestReporter(
                kubeconfig_path=self.kubeconfig_path,
                log_level="INFO",
            )

            # Run comprehensive validation
            test_results = test_reporter.run_comprehensive_test_suite(
                config_paths=context.get("config_paths", []),
                include_workstation_tests=context.get("include_workstation_tests", False),
            )

            duration = time.time() - start_time

            # Determine result based on test outcomes
            if test_results.overall_status == "pass":
                result = HookResult.SUCCESS
                message = "Post-deployment validation completed successfully"
            elif test_results.overall_status == "warning":
                result = HookResult.WARNING
                message = "Post-deployment validation completed with warnings"
            else:
                result = HookResult.FAILURE
                message = "Post-deployment validation failed"

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=result,
                timestamp=timestamp,
                duration=duration,
                message=message,
                details={
                    "test_results": asdict(test_results),
                    "summary": test_results.summary,
                },
                metrics=test_results.metrics,
                recommendations=test_results.recommendations,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.exception(f"Post-deployment validation failed: {e}")

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=HookResult.FAILURE,
                timestamp=timestamp,
                duration=duration,
                message=f"Post-deployment validation error: {e!s}",
                details={"error": str(e)},
                recommendations=[
                    "Review post-deployment validation logs and verify service deployments",
                ],
            )


class ContinuousValidationHook(DeploymentValidationHook):
    """Continuous validation hook for ongoing monitoring."""

    def execute(self, phase: DeploymentPhase, context: dict[str, Any]) -> HookExecutionResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Executing continuous validation: {self.name}")

        try:
            validation_results = []

            # 1. Infrastructure health monitoring
            infra_result = self._monitor_infrastructure_health()
            validation_results.append(infra_result)

            # 2. Service availability monitoring
            service_result = self._monitor_service_availability(context)
            validation_results.append(service_result)

            # 3. Security monitoring
            security_result = self._monitor_security_compliance()
            validation_results.append(security_result)

            # 4. Performance monitoring
            performance_result = self._monitor_performance_metrics(context)
            validation_results.append(performance_result)

            # Analyze results
            success_count = sum(1 for r in validation_results if r.get("success", False))
            total_count = len(validation_results)
            success_rate = success_count / total_count if total_count > 0 else 0

            duration = time.time() - start_time

            if success_rate >= self.config.failure_threshold:
                result = HookResult.SUCCESS
                message = f"Continuous validation healthy ({success_count}/{total_count} checks)"
            elif success_rate >= 0.5:
                result = HookResult.WARNING
                message = f"Continuous validation warnings ({success_count}/{total_count} checks)"
            else:
                result = HookResult.FAILURE
                message = (
                    f"Continuous validation issues detected ({success_count}/{total_count} checks)"
                )

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=result,
                timestamp=timestamp,
                duration=duration,
                message=message,
                details={
                    "validation_results": validation_results,
                    "success_rate": success_rate,
                    "total_checks": total_count,
                    "passed_checks": success_count,
                },
                metrics={
                    "success_rate": success_rate,
                    "execution_time": duration,
                    "checks_performed": total_count,
                },
                recommendations=self._generate_continuous_recommendations(validation_results),
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.exception(f"Continuous validation failed: {e}")

            return HookExecutionResult(
                hook_name=self.name,
                phase=phase,
                result=HookResult.FAILURE,
                timestamp=timestamp,
                duration=duration,
                message=f"Continuous validation error: {e!s}",
                details={"error": str(e)},
                recommendations=["Review continuous monitoring configuration and logs"],
            )

    def _monitor_infrastructure_health(self) -> dict[str, Any]:
        """Monitor infrastructure health continuously."""
        try:
            health_monitor = InfrastructureHealthMonitor(
                kubeconfig_path=self.kubeconfig_path,
                log_level="INFO",
            )

            cluster_health = health_monitor.get_cluster_health()

            if cluster_health.overall_status == "healthy":
                return {
                    "name": "infrastructure_health",
                    "success": True,
                    "message": "Infrastructure health is good",
                    "details": asdict(cluster_health),
                }
            return {
                "name": "infrastructure_health",
                "success": False,
                "message": f"Infrastructure health issues: {cluster_health.overall_status}",
                "details": asdict(cluster_health),
            }

        except Exception as e:
            return {
                "name": "infrastructure_health",
                "success": False,
                "message": f"Infrastructure health monitoring failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _monitor_service_availability(self, context: dict[str, Any]) -> dict[str, Any]:
        """Monitor service availability continuously."""
        try:
            service_checker = ServiceDeploymentChecker(
                kubeconfig_path=self.kubeconfig_path,
                log_level="INFO",
            )

            service_results = service_checker.check_all_services()

            healthy_services = sum(
                1
                for service, status in service_results.items()
                if status.overall_status == "healthy"
            )
            total_services = len(service_results)

            success = healthy_services == total_services

            return {
                "name": "service_availability",
                "success": success,
                "message": f"Service availability: {healthy_services}/{total_services} healthy",
                "details": {
                    "service_results": {k: asdict(v) for k, v in service_results.items()},
                    "healthy_services": healthy_services,
                    "total_services": total_services,
                },
            }

        except Exception as e:
            return {
                "name": "service_availability",
                "success": False,
                "message": f"Service availability monitoring failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _monitor_security_compliance(self) -> dict[str, Any]:
        """Monitor security compliance continuously."""
        try:
            security_validator = NetworkSecurityValidator(
                kubeconfig_path=self.kubeconfig_path,
                log_level="INFO",
            )

            security_results = security_validator.run_comprehensive_security_validation()

            successful_checks = sum(1 for result in security_results if result.status == "pass")
            total_checks = len(security_results)

            success = successful_checks == total_checks

            return {
                "name": "security_compliance",
                "success": success,
                "message": f"Security compliance: {successful_checks}/{total_checks} checks passed",
                "details": {
                    "security_results": [asdict(r) for r in security_results],
                    "successful_checks": successful_checks,
                    "total_checks": total_checks,
                },
            }

        except Exception as e:
            return {
                "name": "security_compliance",
                "success": False,
                "message": f"Security compliance monitoring failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _monitor_performance_metrics(self, context: dict[str, Any]) -> dict[str, Any]:
        """Monitor performance metrics continuously."""
        try:
            # Use integration tester for performance validation
            integration_tester = IntegrationConnectivityTester(
                kubeconfig_path=self.kubeconfig_path,
                log_level="INFO",
            )

            # Run basic connectivity tests as performance indicators
            results = integration_tester.run_comprehensive_integration_tests(
                include_workstation_tests=False,
            )

            successful_tests = sum(1 for result in results if result.success)
            total_tests = len(results)

            # Calculate average response time
            response_times = [
                r.response_time for r in results if r.response_time and r.response_time > 0
            ]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            # Performance is good if tests pass and response times are reasonable
            success = successful_tests == total_tests and (
                avg_response_time == 0 or avg_response_time < 5000
            )  # 5 second threshold

            return {
                "name": "performance_metrics",
                "success": success,
                "message": f"Performance: {successful_tests}/{total_tests} tests passed, avg response: {avg_response_time:.0f}ms",
                "details": {
                    "integration_results": [asdict(r) for r in results],
                    "successful_tests": successful_tests,
                    "total_tests": total_tests,
                    "average_response_time": avg_response_time,
                },
            }

        except Exception as e:
            return {
                "name": "performance_metrics",
                "success": False,
                "message": f"Performance monitoring failed: {e!s}",
                "details": {"error": str(e)},
            }

    def _generate_continuous_recommendations(
        self,
        validation_results: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations for continuous monitoring issues."""
        recommendations = []

        for result in validation_results:
            if not result.get("success", False):
                name = result.get("name", "unknown")

                if name == "infrastructure_health":
                    recommendations.append(
                        "Investigate infrastructure health issues and check node resources",
                    )
                elif name == "service_availability":
                    recommendations.append("Review failing services and check pod logs for errors")
                elif name == "security_compliance":
                    recommendations.append(
                        "Address security compliance violations and update policies",
                    )
                elif name == "performance_metrics":
                    recommendations.append(
                        "Investigate performance degradation and optimize resource allocation",
                    )

        return recommendations


class DeploymentValidationHookManager:
    """Manager for deployment validation hooks."""

    def __init__(
        self,
        kubeconfig_path: str | None = None,
        log_level: str = "INFO",
        config_file: str | None = None,
    ) -> None:
        self.kubeconfig_path = kubeconfig_path
        self.logger = self._setup_logging(log_level)
        self.hooks: dict[str, DeploymentValidationHook] = {}
        self.results_dir = Path("test_results/hooks")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        if config_file and Path(config_file).exists():
            self._load_configuration(config_file)
        else:
            self._setup_default_hooks()

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure logging for the hook manager."""
        logger = logging.getLogger("hook_manager")
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - [HookManager] - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_configuration(self, config_file: str) -> None:
        """Load hook configuration from file."""
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)

            for hook_name, hook_config in config.get("hooks", {}).items():
                hook_type = hook_config.get("type", "pre-deployment")
                config_obj = ValidationHookConfig(**hook_config.get("config", {}))

                if hook_type == "pre-deployment":
                    hook = PreDeploymentValidationHook(
                        hook_name,
                        config_obj,
                        self.kubeconfig_path,
                    )
                elif hook_type == "post-deployment":
                    hook = PostDeploymentValidationHook(
                        hook_name,
                        config_obj,
                        self.kubeconfig_path,
                    )
                elif hook_type == "continuous":
                    hook = ContinuousValidationHook(
                        hook_name,
                        config_obj,
                        self.kubeconfig_path,
                    )
                else:
                    self.logger.warning(f"Unknown hook type: {hook_type}")
                    continue

                self.hooks[hook_name] = hook

        except Exception as e:
            self.logger.exception(f"Failed to load configuration: {e}")
            self._setup_default_hooks()

    def _setup_default_hooks(self) -> None:
        """Setup default validation hooks."""
        # Pre-deployment hook
        pre_config = ValidationHookConfig(
            enabled=True,
            timeout=300,
            retry_count=3,
            failure_threshold=0.8,
            critical=True,
        )
        self.hooks["pre-deployment-validation"] = PreDeploymentValidationHook(
            "pre-deployment-validation",
            pre_config,
            self.kubeconfig_path,
        )

        # Post-deployment hook
        post_config = ValidationHookConfig(
            enabled=True,
            timeout=600,
            retry_count=2,
            failure_threshold=0.8,
            critical=True,
        )
        self.hooks["post-deployment-validation"] = PostDeploymentValidationHook(
            "post-deployment-validation",
            post_config,
            self.kubeconfig_path,
        )

        # Continuous monitoring hook
        continuous_config = ValidationHookConfig(
            enabled=True,
            timeout=300,
            retry_count=1,
            failure_threshold=0.7,
            critical=False,
        )
        self.hooks["continuous-monitoring"] = ContinuousValidationHook(
            "continuous-monitoring",
            continuous_config,
            self.kubeconfig_path,
        )

    def execute_hooks_for_phase(
        self,
        phase: DeploymentPhase,
        context: dict[str, Any] | None = None,
    ) -> list[HookExecutionResult]:
        """Execute all enabled hooks for a specific deployment phase."""
        if context is None:
            context = {}

        self.logger.info(f"Executing hooks for phase: {phase.value}")

        results = []
        for hook_name, hook in self.hooks.items():
            if hook.is_enabled_for_phase(phase):
                self.logger.info(f"Executing hook: {hook_name}")

                try:
                    result = hook.execute(phase, context)
                    results.append(result)

                    # Save individual hook result
                    self._save_hook_result(result)

                    # Check if hook failure should block deployment
                    if result.result == HookResult.FAILURE and hook.should_block_on_failure():
                        self.logger.error(f"Critical hook {hook_name} failed, blocking deployment")
                        break

                except Exception as e:
                    self.logger.exception(f"Hook {hook_name} execution failed: {e}")

                    error_result = HookExecutionResult(
                        hook_name=hook_name,
                        phase=phase,
                        result=HookResult.FAILURE,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        duration=0.0,
                        message=f"Hook execution error: {e!s}",
                        details={"error": str(e)},
                    )
                    results.append(error_result)

                    if hook.should_block_on_failure():
                        self.logger.exception(
                            f"Critical hook {hook_name} failed, blocking deployment",
                        )
                        break
            else:
                self.logger.debug(f"Hook {hook_name} disabled for phase {phase.value}")

        # Save phase results summary
        self._save_phase_results(phase, results)

        return results

    def _save_hook_result(self, result: HookExecutionResult) -> None:
        """Save individual hook result to file."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{result.hook_name}_{result.phase.value}_{timestamp_str}.json"
        filepath = self.results_dir / filename

        try:
            with open(filepath, "w") as f:
                json.dump(asdict(result), f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save hook result: {e}")

    def _save_phase_results(
        self,
        phase: DeploymentPhase,
        results: list[HookExecutionResult],
    ) -> None:
        """Save phase results summary."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"phase_{phase.value}_summary_{timestamp_str}.json"
        filepath = self.results_dir / filename

        summary = {
            "phase": phase.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_hooks": len(results),
            "successful_hooks": sum(1 for r in results if r.result == HookResult.SUCCESS),
            "warning_hooks": sum(1 for r in results if r.result == HookResult.WARNING),
            "failed_hooks": sum(1 for r in results if r.result == HookResult.FAILURE),
            "skipped_hooks": sum(1 for r in results if r.result == HookResult.SKIPPED),
            "results": [asdict(r) for r in results],
        }

        try:
            with open(filepath, "w") as f:
                json.dump(summary, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save phase results: {e}")

    def get_hook_status_summary(self) -> dict[str, Any]:
        """Get summary of all hook statuses."""
        summary = {
            "total_hooks": len(self.hooks),
            "enabled_hooks": 0,
            "hooks_by_type": {},
            "hooks": {},
        }

        for hook_name, hook in self.hooks.items():
            hook_type = type(hook).__name__
            summary["hooks_by_type"][hook_type] = summary["hooks_by_type"].get(hook_type, 0) + 1

            if hook.config.enabled:
                summary["enabled_hooks"] += 1

            summary["hooks"][hook_name] = {
                "type": hook_type,
                "enabled": hook.config.enabled,
                "critical": hook.config.critical,
                "timeout": hook.config.timeout,
            }

        return summary


def main() -> int:
    """Main function for running deployment validation hooks."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run deployment validation hooks",
    )
    parser.add_argument(
        "--phase",
        choices=["pre-deployment", "post-deployment", "continuous", "rollback", "upgrade"],
        required=True,
        help="Deployment phase to execute hooks for",
    )
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument("--config-file", help="Path to hook configuration file")
    parser.add_argument("--context", help="JSON context for hook execution")

    args = parser.parse_args()

    # Parse context
    context = {}
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON context: {args.context}")
            return 1

    # Initialize hook manager
    hook_manager = DeploymentValidationHookManager(
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level,
        config_file=args.config_file,
    )

    # Execute hooks for the specified phase
    phase = DeploymentPhase(args.phase)
    results = hook_manager.execute_hooks_for_phase(phase, context)

    # Print summary
    successful = sum(1 for r in results if r.result == HookResult.SUCCESS)
    warnings = sum(1 for r in results if r.result == HookResult.WARNING)
    failures = sum(1 for r in results if r.result == HookResult.FAILURE)

    print(f"\n🎯 Deployment Validation Hook Results for {phase.value}:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ⚠️  Warnings: {warnings}")
    print(f"  ❌ Failures: {failures}")
    print(f"  📊 Total: {len(results)}")

    # Return non-zero exit code if any critical hooks failed
    critical_failures = sum(
        1
        for r in results
        if r.result == HookResult.FAILURE
        and hook_manager.hooks[r.hook_name].should_block_on_failure()
    )

    return 1 if critical_failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
