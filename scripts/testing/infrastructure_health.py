#!/usr/bin/env python3
"""Infrastructure Health Monitor for Homelab Kubernetes Cluster.

This module provides comprehensive health monitoring for K3s clusters including
connectivity checks, node status, core components, and network validation.
"""

import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False


@dataclass
class HealthStatus:
    """Structured health status for infrastructure components."""

    component: str
    status: str  # "healthy", "warning", "critical", "unknown"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        """Check if component is in healthy state."""
        return self.status == "healthy"


@dataclass
class ClusterHealth:
    """Overall cluster health summary."""

    cluster_status: str
    total_checks: int
    healthy_checks: int
    warning_checks: int
    critical_checks: int
    component_statuses: list[HealthStatus] = field(default_factory=list)

    @property
    def health_percentage(self) -> float:
        """Calculate overall health percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.healthy_checks / self.total_checks) * 100


class InfrastructureHealthMonitor:
    """Main health monitoring class for homelab infrastructure."""

    def __init__(self, kubeconfig_path: str | None = None, log_level: str = "INFO") -> None:
        """Initialize the health monitor."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path
        self.k8s_client = None
        self.critical_namespaces = [
            "kube-system",
            "metallb-system",
            "cert-manager",
            "ingress-nginx",
            "longhorn-system",
            "monitoring",
        ]

        if KUBERNETES_AVAILABLE:
            self._init_kubernetes_client()
        else:
            self.logger.warning(
                "Kubernetes client not available. Install with: pip install kubernetes",
            )

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

    def _init_kubernetes_client(self) -> None:
        """Initialize Kubernetes API client."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                try:
                    config.load_incluster_config()
                except:
                    config.load_kube_config()

            self.k8s_client = client.ApiClient()
            self.logger.info("Kubernetes client initialized successfully")

        except Exception as e:
            self.logger.exception(f"Failed to initialize Kubernetes client: {e}")
            self.k8s_client = None

    def check_cluster_connectivity(self) -> HealthStatus:
        """Check basic Kubernetes API connectivity."""
        if not KUBERNETES_AVAILABLE or not self.k8s_client:
            return HealthStatus(
                component="cluster_connectivity",
                status="critical",
                message="Kubernetes client not available",
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            version = v1.get_api_resources()

            return HealthStatus(
                component="cluster_connectivity",
                status="healthy",
                message="Cluster API accessible",
                details={"api_resources_count": len(version.resources)},
            )

        except ApiException as e:
            return HealthStatus(
                component="cluster_connectivity",
                status="critical",
                message=f"API connection failed: {e.reason}",
                details={"status_code": e.status},
            )
        except Exception as e:
            return HealthStatus(
                component="cluster_connectivity",
                status="critical",
                message=f"Unexpected error: {e!s}",
            )

    def check_node_status(self) -> HealthStatus:
        """Check node status and resource availability."""
        if not self.k8s_client:
            return HealthStatus(
                component="node_status",
                status="unknown",
                message="Kubernetes client unavailable",
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            nodes = v1.list_node()

            node_details = {}
            unhealthy_nodes = []

            for node in nodes.items:
                node_name = node.metadata.name
                node_ready = False

                # Check node conditions
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            node_ready = condition.status == "True"
                            break

                if not node_ready:
                    unhealthy_nodes.append(node_name)

                # Get resource capacity
                capacity = node.status.capacity or {}
                allocatable = node.status.allocatable or {}

                node_details[node_name] = {
                    "ready": node_ready,
                    "cpu_capacity": capacity.get("cpu", "unknown"),
                    "memory_capacity": capacity.get("memory", "unknown"),
                    "cpu_allocatable": allocatable.get("cpu", "unknown"),
                    "memory_allocatable": allocatable.get("memory", "unknown"),
                }

            total_nodes = len(nodes.items)
            healthy_nodes = total_nodes - len(unhealthy_nodes)

            if unhealthy_nodes:
                status = "critical" if len(unhealthy_nodes) == total_nodes else "warning"
                message = f"{len(unhealthy_nodes)}/{total_nodes} nodes unhealthy"
            else:
                status = "healthy"
                message = f"All {total_nodes} nodes ready"

            return HealthStatus(
                component="node_status",
                status=status,
                message=message,
                details={
                    "total_nodes": total_nodes,
                    "healthy_nodes": healthy_nodes,
                    "unhealthy_nodes": unhealthy_nodes,
                    "node_details": node_details,
                },
            )

        except Exception as e:
            return HealthStatus(
                component="node_status",
                status="critical",
                message=f"Failed to check nodes: {e!s}",
            )

    def check_core_components(self) -> HealthStatus:
        """Check core Kubernetes components in kube-system namespace."""
        if not self.k8s_client:
            return HealthStatus(
                component="core_components",
                status="unknown",
                message="Kubernetes client unavailable",
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            pods = v1.list_namespaced_pod(namespace="kube-system")

            core_components = ["kube-apiserver", "etcd", "kube-controller", "kube-scheduler"]
            component_status = {}
            unhealthy_components = []

            for pod in pods.items:
                pod_name = pod.metadata.name

                # Check if this is a core component
                component_type = None
                for component in core_components:
                    if component in pod_name:
                        component_type = component
                        break

                if component_type:
                    is_ready = pod.status.phase == "Running"
                    if pod.status.container_statuses:
                        is_ready = all(cs.ready for cs in pod.status.container_statuses)

                    component_status[pod_name] = {
                        "type": component_type,
                        "ready": is_ready,
                        "phase": pod.status.phase,
                        "restarts": sum(
                            cs.restart_count for cs in (pod.status.container_statuses or [])
                        ),
                    }

                    if not is_ready:
                        unhealthy_components.append(pod_name)

            if unhealthy_components:
                status = "critical"
                message = f"{len(unhealthy_components)} core components unhealthy"
            else:
                status = "healthy"
                message = "All core components healthy"

            return HealthStatus(
                component="core_components",
                status=status,
                message=message,
                details={"components": component_status, "unhealthy": unhealthy_components},
            )

        except Exception as e:
            return HealthStatus(
                component="core_components",
                status="critical",
                message=f"Failed to check core components: {e!s}",
            )

    def check_namespace_status(self) -> HealthStatus:
        """Check critical namespace status and resource quotas."""
        if not self.k8s_client:
            return HealthStatus(
                component="namespace_status",
                status="unknown",
                message="Kubernetes client unavailable",
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            namespaces = v1.list_namespace()

            namespace_details = {}
            missing_namespaces = []

            existing_ns = [ns.metadata.name for ns in namespaces.items]

            for ns_name in self.critical_namespaces:
                if ns_name in existing_ns:
                    # Get namespace details
                    try:
                        pods = v1.list_namespaced_pod(namespace=ns_name)
                        running_pods = sum(1 for p in pods.items if p.status.phase == "Running")
                        total_pods = len(pods.items)

                        namespace_details[ns_name] = {
                            "exists": True,
                            "total_pods": total_pods,
                            "running_pods": running_pods,
                            "pod_health": running_pods / total_pods if total_pods > 0 else 1.0,
                        }
                    except Exception:
                        namespace_details[ns_name] = {"exists": True, "error": "Failed to get pods"}
                else:
                    missing_namespaces.append(ns_name)
                    namespace_details[ns_name] = {"exists": False}

            if missing_namespaces:
                status = "warning"
                message = f"{len(missing_namespaces)} critical namespaces missing"
            else:
                status = "healthy"
                message = "All critical namespaces present"

            return HealthStatus(
                component="namespace_status",
                status=status,
                message=message,
                details={
                    "namespace_details": namespace_details,
                    "missing_namespaces": missing_namespaces,
                },
            )

        except Exception as e:
            return HealthStatus(
                component="namespace_status",
                status="critical",
                message=f"Failed to check namespaces: {e!s}",
            )

    def check_network_connectivity(self) -> HealthStatus:
        """Check basic network connectivity between cluster components."""
        try:
            # Simple DNS resolution test
            dns_result = subprocess.run(
                ["nslookup", "kubernetes.default.svc.cluster.local"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            dns_healthy = dns_result.returncode == 0

            # Simple ping test to cluster service
            ping_result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", "kubernetes.default"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            ping_healthy = ping_result.returncode == 0

            if dns_healthy and ping_healthy:
                status = "healthy"
                message = "Network connectivity verified"
            elif dns_healthy or ping_healthy:
                status = "warning"
                message = "Partial network connectivity"
            else:
                status = "critical"
                message = "Network connectivity issues detected"

            return HealthStatus(
                component="network_connectivity",
                status=status,
                message=message,
                details={"dns_resolution": dns_healthy, "ping_test": ping_healthy},
            )

        except Exception as e:
            return HealthStatus(
                component="network_connectivity",
                status="warning",
                message=f"Network check failed: {e!s}",
            )

    def get_cluster_health(self) -> ClusterHealth:
        """Get comprehensive cluster health status."""
        self.logger.info("Starting comprehensive cluster health check...")

        checks = [
            self.check_cluster_connectivity,
            self.check_node_status,
            self.check_core_components,
            self.check_namespace_status,
            self.check_network_connectivity,
        ]

        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
                self.logger.info(f"{result.component}: {result.status} - {result.message}")
            except Exception as e:
                self.logger.exception(f"Health check failed: {e}")
                results.append(
                    HealthStatus(
                        component="unknown",
                        status="critical",
                        message=f"Check failed: {e!s}",
                    ),
                )

        # Calculate overall health
        total_checks = len(results)
        healthy_checks = sum(1 for r in results if r.status == "healthy")
        warning_checks = sum(1 for r in results if r.status == "warning")
        critical_checks = sum(1 for r in results if r.status == "critical")

        if critical_checks > 0:
            cluster_status = "critical"
        elif warning_checks > 0:
            cluster_status = "warning"
        else:
            cluster_status = "healthy"

        return ClusterHealth(
            cluster_status=cluster_status,
            total_checks=total_checks,
            healthy_checks=healthy_checks,
            warning_checks=warning_checks,
            critical_checks=critical_checks,
            component_statuses=results,
        )


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor homelab infrastructure health")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--component",
        choices=["connectivity", "nodes", "components", "namespaces", "network"],
        help="Check specific component only",
    )

    args = parser.parse_args()

    monitor = InfrastructureHealthMonitor(kubeconfig_path=args.kubeconfig, log_level=args.log_level)

    if args.component:
        # Run specific check
        check_map = {
            "connectivity": monitor.check_cluster_connectivity,
            "nodes": monitor.check_node_status,
            "components": monitor.check_core_components,
            "namespaces": monitor.check_namespace_status,
            "network": monitor.check_network_connectivity,
        }

        result = check_map[args.component]()
        print(f"\n🔍 {result.component.title()} Health Check:")
        print(f"Status: {result.status.upper()}")
        print(f"Message: {result.message}")

        if result.details:
            print(f"Details: {result.details}")

        return 0 if result.is_healthy else 1

    # Run comprehensive health check
    health = monitor.get_cluster_health()

    print("\n🏥 Cluster Health Report:")
    print(f"Overall Status: {health.cluster_status.upper()}")
    print(f"Health Score: {health.health_percentage:.1f}%")
    print(f"Checks: {health.healthy_checks}✅ {health.warning_checks}⚠️ {health.critical_checks}❌")

    print("\n📊 Component Details:")
    for status in health.component_statuses:
        icon = "✅" if status.status == "healthy" else "⚠️" if status.status == "warning" else "❌"
        print(f"  {icon} {status.component}: {status.message}")

    return 0 if health.cluster_status in ["healthy", "warning"] else 1


if __name__ == "__main__":
    sys.exit(main())
