#!/usr/bin/env python3
"""Service Deployment Checker for Homelab Infrastructure.

This module validates deployed services (GitLab, Keycloak, monitoring stack)
and performs comprehensive health checks with intelligent retry logic.
"""

import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import requests

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

# Import our previous modules
try:
    from .config_validator import ConfigValidator
    from .infrastructure_health import HealthStatus, InfrastructureHealthMonitor
except ImportError:
    try:
        from config_validator import ConfigValidator
        from infrastructure_health import HealthStatus, InfrastructureHealthMonitor
    except ImportError:
        # Fallback definitions if modules aren't available
        @dataclass
        class HealthStatus:
            component: str
            status: str
            message: str
            details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceStatus:
    """Extended service status with deployment-specific information."""

    service_name: str
    namespace: str
    status: str  # "ready", "pending", "failed", "unknown"
    message: str
    pod_count: int = 0
    ready_pods: int = 0
    endpoints_healthy: bool = False
    resource_usage: dict[str, Any] = field(default_factory=dict)
    health_checks: dict[str, bool] = field(default_factory=dict)
    retry_count: int = 0

    @property
    def is_ready(self) -> bool:
        """Check if service is fully ready."""
        return self.status == "ready" and self.ready_pods == self.pod_count > 0


class ServiceDeploymentChecker:
    """Main checker for homelab service deployments."""

    def __init__(self, kubeconfig_path: str | None = None, log_level: str = "INFO") -> None:
        """Initialize the service checker."""
        self.logger = self._setup_logging(log_level)
        self.k8s_client = None
        self.infra_monitor = None
        self.config_validator = None

        # Service definitions for homelab
        self.services = {
            "gitlab": {
                "namespace": "gitlab-system",
                "ports": [80, 443],
                "health_path": "/-/health",
            },
            "keycloak": {
                "namespace": "keycloak",
                "ports": [8080],
                "health_path": "/auth/health/ready",
            },
            "prometheus": {"namespace": "monitoring", "ports": [9090], "health_path": "/-/healthy"},
            "grafana": {"namespace": "monitoring", "ports": [3000], "health_path": "/api/health"},
            "nginx-ingress": {
                "namespace": "ingress-nginx",
                "ports": [80, 443],
                "health_path": "/healthz",
            },
            "cert-manager": {"namespace": "cert-manager", "ports": [], "health_path": None},
            "metallb": {"namespace": "metallb-system", "ports": [], "health_path": None},
        }

        if KUBERNETES_AVAILABLE:
            self._init_kubernetes_client(kubeconfig_path)
            try:
                self.infra_monitor = InfrastructureHealthMonitor(kubeconfig_path, log_level)
                self.config_validator = ConfigValidator(log_level)
            except Exception as e:
                self.logger.warning(f"Could not initialize helper modules: {e}")

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _init_kubernetes_client(self, kubeconfig_path: str | None) -> None:
        """Initialize Kubernetes API client."""
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()

            self.k8s_client = client.ApiClient()
            self.logger.info("Kubernetes client initialized for service checking")

        except Exception as e:
            self.logger.exception(f"Failed to initialize Kubernetes client: {e}")

    def check_pod_status_with_retry(
        self,
        namespace: str,
        label_selector: str | None = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> tuple[int, int, list[dict]]:
        """Check pod status with intelligent retry logic."""
        if not self.k8s_client:
            self.logger.warning("Kubernetes client not initialized - cannot check pod status")
            return 0, 0, []

        for attempt in range(max_retries):
            try:
                v1 = client.CoreV1Api(self.k8s_client)
                pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

                total_pods = len(pods.items)
                ready_pods = 0
                pod_details = []

                for pod in pods.items:
                    pod_ready = pod.status.phase == "Running" and (
                        not pod.status.container_statuses
                        or all(cs.ready for cs in pod.status.container_statuses)
                    )

                    if pod_ready:
                        ready_pods += 1

                    # Calculate resource usage
                    resource_usage = {}
                    if pod.spec.containers:
                        for container in pod.spec.containers:
                            if container.resources:
                                resource_usage[container.name] = {
                                    "requests": container.resources.requests or {},
                                    "limits": container.resources.limits or {},
                                }

                    pod_details.append(
                        {
                            "name": pod.metadata.name,
                            "ready": pod_ready,
                            "phase": pod.status.phase,
                            "restarts": sum(
                                cs.restart_count for cs in (pod.status.container_statuses or [])
                            ),
                            "resource_usage": resource_usage,
                        },
                    )

                return total_pods, ready_pods, pod_details

            except Exception as e:
                self.logger.warning(f"Pod status check attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(
                        retry_delay,
                    )  # Wait before retry to avoid overwhelming the API server
                else:
                    return 0, 0, []

        return 0, 0, []

    def check_service_endpoints(self, service_name: str, namespace: str) -> bool:
        """Validate service endpoints and basic connectivity."""
        if not self.k8s_client:
            return False

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            services = v1.list_namespaced_service(namespace=namespace)

            for svc in services.items:
                if service_name.lower() in svc.metadata.name.lower():
                    # Check if service has endpoints
                    try:
                        endpoints = v1.read_namespaced_endpoints(
                            name=svc.metadata.name,
                            namespace=namespace,
                        )

                        if endpoints.subsets:
                            for subset in endpoints.subsets:
                                if subset.addresses:
                                    return True
                        return False

                    except ApiException:
                        return False

            return False

        except Exception as e:
            self.logger.exception(f"Failed to check endpoints for {service_name}: {e}")
            return False

    def perform_health_check(
        self,
        service_name: str,
        namespace: str,
        health_path: str | None = None,
    ) -> dict[str, bool]:
        """Perform application-specific health checks."""
        health_results = {}

        if not health_path or not self.k8s_client:
            return health_results

        try:
            # Get service IP/endpoint
            v1 = client.CoreV1Api(self.k8s_client)
            services = v1.list_namespaced_service(namespace=namespace)

            for svc in services.items:
                if service_name.lower() in svc.metadata.name.lower():
                    if svc.spec.cluster_ip and svc.spec.cluster_ip != "None":
                        for port in svc.spec.ports or []:
                            port_num = port.port

                            # Attempt HTTP health check
                            for protocol in ["http", "https"]:
                                try:
                                    url = f"{protocol}://{svc.spec.cluster_ip}:{port_num}{health_path}"
                                    # Add instance variable for internal SSL verification
                                    verify_internal = getattr(self, "verify_internal_ssl", False)

                                    response = requests.get(url, timeout=10, verify=verify_internal)
                                    health_results[f"{protocol}_{port_num}"] = (
                                        response.status_code < 400
                                    )
                                    break  # If successful, don't try other protocol
                                except:
                                    health_results[f"{protocol}_{port_num}"] = False

        except Exception as e:
            self.logger.debug(f"Health check for {service_name} failed: {e}")

        return health_results

    def check_service(self, service_name: str) -> ServiceStatus:
        """Comprehensive service check with all validations."""
        if service_name not in self.services:
            return ServiceStatus(
                service_name=service_name,
                namespace="unknown",
                status="unknown",
                message="Service not defined in checker",
            )

        service_config = self.services[service_name]
        namespace = service_config["namespace"]

        self.logger.info(f"Checking service: {service_name} in namespace: {namespace}")

        # Check pod status with retry
        total_pods, ready_pods, pod_details = self.check_pod_status_with_retry(namespace)

        # Check service endpoints
        endpoints_healthy = self.check_service_endpoints(service_name, namespace)

        # Perform health checks
        health_checks = self.perform_health_check(
            service_name,
            namespace,
            service_config.get("health_path"),
        )

        # Calculate resource usage summary
        resource_usage = {}
        if pod_details:
            total_cpu_requests = 0
            total_memory_requests = 0
            for pod in pod_details:
                for resources in pod.get("resource_usage", {}).values():
                    requests = resources.get("requests", {})
                    if "cpu" in requests:
                        total_cpu_requests += self._parse_cpu(requests["cpu"])
                    if "memory" in requests:
                        total_memory_requests += self._parse_memory(requests["memory"])

            resource_usage = {
                "total_cpu_requests": f"{total_cpu_requests}m",
                "total_memory_requests": f"{total_memory_requests}Mi",
                "pod_details": pod_details,
            }

        # Determine overall status
        if total_pods == 0:
            status = "failed"
            message = "No pods found"
        elif ready_pods == total_pods and endpoints_healthy:
            status = "ready"
            message = f"All {total_pods} pods ready, endpoints healthy"
        elif ready_pods > 0:
            status = "pending"
            message = f"{ready_pods}/{total_pods} pods ready"
        else:
            status = "failed"
            message = "No pods ready"

        return ServiceStatus(
            service_name=service_name,
            namespace=namespace,
            status=status,
            message=message,
            pod_count=total_pods,
            ready_pods=ready_pods,
            endpoints_healthy=endpoints_healthy,
            resource_usage=resource_usage,
            health_checks=health_checks,
        )

    def _parse_cpu(self, cpu_str: str) -> int:
        """Parse CPU string to millicores.

        Supports Kubernetes CPU formats:
        - '100m' (millicores)
        - '0.5', '1.5' (cores as float)
        - '1e3m', '1e-3' (scientific notation)
        - '250u' (250 microcores = 0.25m)
        - '500n' (500 nanocores = 0.0005m)
        """
        try:
            from kubernetes.utils.quantity import parse_quantity

            # parse_quantity returns the value in base units
            # For CPU, base unit is "core" so we convert to millicores
            cores = parse_quantity(cpu_str)
            return int(cores * 1000)
        except ImportError:
            # Fallback implementation
            cpu_str = cpu_str.strip()
            try:
                # Handle scientific notation
                if "e" in cpu_str.lower():
                    if cpu_str.endswith("m"):
                        return int(float(cpu_str[:-1]))
                    return int(float(cpu_str) * 1000)

                # Handle units
                if cpu_str.endswith("m"):
                    return int(float(cpu_str[:-1]))
                if cpu_str.endswith("u"):  # microcores
                    return int(float(cpu_str[:-1]) / 1000)
                if cpu_str.endswith("n"):  # nanocores
                    return int(float(cpu_str[:-1]) / 1_000_000)
                # Assume cores (can be float)
                return int(float(cpu_str) * 1000)
            except (ValueError, TypeError) as e:
                msg = f"Invalid CPU string format: '{cpu_str}'"
                raise ValueError(msg) from e

    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to Mi (Mebibytes).

        Supports all Kubernetes memory formats including:
        - Binary: Ki, Mi, Gi, Ti, Pi, Ei
        - Decimal: K, M, G, T, P, E
        - Plain bytes
        """
        try:
            from kubernetes.utils.quantity import parse_quantity

            # parse_quantity returns bytes
            bytes_value = parse_quantity(memory_str)
            return int(bytes_value / (1024 * 1024))  # Convert to MiB
        except ImportError:
            # Enhanced fallback implementation
            memory_str = memory_str.strip()

            # Binary units
            if memory_str.endswith("Mi"):
                return int(memory_str[:-2])
            if memory_str.endswith("Gi"):
                return int(memory_str[:-2]) * 1024
            if memory_str.endswith("Ki"):
                return int(memory_str[:-2]) // 1024
            if memory_str.endswith("Ti"):
                return int(memory_str[:-2]) * 1024 * 1024
            if memory_str.endswith("Pi"):
                return int(memory_str[:-2]) * 1024 * 1024 * 1024
            if memory_str.endswith("Ei"):
                return int(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024

            # Decimal units
            if memory_str.endswith("M"):
                return int(float(memory_str[:-1]) * 1000**2 / (1024**2))  # MB to MiB
            if memory_str.endswith("G"):
                return int(float(memory_str[:-1]) * 1000**3 / (1024**2))  # GB to MiB
            if memory_str.endswith("T"):
                return int(float(memory_str[:-1]) * 1000**4 / (1024**2))  # TB to MiB
            if memory_str.endswith("P"):
                return int(float(memory_str[:-1]) * 1000**5 / (1024**2))  # PB to MiB
            if memory_str.endswith("E"):
                return int(float(memory_str[:-1]) * 1000**6 / (1024**2))  # EB to MiB
            if memory_str.endswith("K"):
                return int(float(memory_str[:-1]) * 1000 / (1024**2))  # KB to MiB
            if memory_str.endswith("k"):
                return int(float(memory_str[:-1]) * 1000 / (1024**2))  # kB to MiB

            # Assume bytes if no unit
            return int(float(memory_str) / (1024**2))

    def check_all_services(self) -> dict[str, ServiceStatus]:
        """Check all defined services."""
        results = {}

        # Optionally run infrastructure health check first
        if self.infra_monitor:
            self.logger.info("Running infrastructure health check first...")
            cluster_health = self.infra_monitor.get_cluster_health()
            if cluster_health.cluster_status == "critical":
                self.logger.warning(
                    "Infrastructure health is critical, service checks may be unreliable",
                )

        for service_name in self.services:
            try:
                result = self.check_service(service_name)
                results[service_name] = result

                status_icon = (
                    "✅" if result.is_ready else "⚠️" if result.status == "pending" else "❌"
                )
                self.logger.info(f"{status_icon} {service_name}: {result.message}")

            except Exception as e:
                self.logger.exception(f"Failed to check {service_name}: {e}")
                results[service_name] = ServiceStatus(
                    service_name=service_name,
                    namespace=self.services[service_name]["namespace"],
                    status="failed",
                    message=f"Check failed: {e!s}",
                )

        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Check homelab service deployments")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--service",
        choices=list(ServiceDeploymentChecker({}).services.keys()),
        help="Check specific service only",
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Include detailed resource usage and health check results",
    )

    args = parser.parse_args()

    checker = ServiceDeploymentChecker(kubeconfig_path=args.kubeconfig, log_level=args.log_level)

    if args.service:
        # Check specific service
        result = checker.check_service(args.service)
        results = {args.service: result}
    else:
        # Check all services
        results = checker.check_all_services()

    # Display results
    print("\n🚀 Service Deployment Status:")

    ready_services = sum(1 for r in results.values() if r.is_ready)
    total_services = len(results)

    print(f"Ready Services: {ready_services}/{total_services}")

    for service_name, result in results.items():
        icon = "✅" if result.is_ready else "⚠️" if result.status == "pending" else "❌"
        print(f"\n{icon} {service_name.upper()}:")
        print(f"  Status: {result.status}")
        print(f"  Message: {result.message}")
        print(f"  Pods: {result.ready_pods}/{result.pod_count}")
        print(f"  Endpoints: {'✅' if result.endpoints_healthy else '❌'}")

        if args.include_details and result.resource_usage:
            print(
                f"  Resources: CPU={result.resource_usage.get('total_cpu_requests', 'N/A')}, "
                f"Memory={result.resource_usage.get('total_memory_requests', 'N/A')}",
            )

        if result.health_checks:
            healthy_checks = sum(1 for v in result.health_checks.values() if v)
            total_checks = len(result.health_checks)
            print(f"  Health Checks: {healthy_checks}/{total_checks} passing")

    return 0 if ready_services == total_services else 1


if __name__ == "__main__":
    sys.exit(main())
