#!/usr/bin/env python3
"""
Production Health Check Script
Comprehensive validation of homelab infrastructure after production deployment.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from typing import Any


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProductionHealthChecker:
    """Comprehensive production health validation."""

    def __init__(self, output_format: str = "console") -> None:
        self.output_format = output_format
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": "production",
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "warning_checks": 0,
            },
        }

    def run_kubectl_command(self, cmd: list[str]) -> tuple[bool, str]:
        """Execute kubectl command and return result."""
        try:
            result = subprocess.run(
                ["kubectl", *cmd],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            return result.returncode == 0, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_cluster_connectivity(self) -> dict[str, Any]:
        """Verify Kubernetes cluster connectivity."""
        logger.info("Checking cluster connectivity...")

        success, output = self.run_kubectl_command(["cluster-info"])

        return {
            "name": "cluster_connectivity",
            "status": "PASS" if success else "FAIL",
            "message": "Kubernetes cluster is accessible"
            if success
            else f"Cluster not accessible: {output}",
            "details": output,
        }

    def check_node_health(self) -> dict[str, Any]:
        """Check all nodes are healthy."""
        logger.info("Checking node health...")

        success, output = self.run_kubectl_command(["get", "nodes", "-o", "json"])
        if not success:
            return {
                "name": "node_health",
                "status": "FAIL",
                "message": f"Failed to get node status: {output}",
                "details": {},
            }

        try:
            nodes_data = json.loads(output)
            nodes = nodes_data.get("items", [])

            healthy_nodes = 0
            total_nodes = len(nodes)
            node_details = {}

            for node in nodes:
                node_name = node["metadata"]["name"]
                conditions = node["status"].get("conditions", [])

                # Check if node is Ready
                ready_condition = next(
                    (c for c in conditions if c["type"] == "Ready"),
                    None,
                )

                is_ready = ready_condition and ready_condition["status"] == "True"
                node_details[node_name] = {
                    "ready": is_ready,
                    "version": node["status"]["nodeInfo"]["kubeletVersion"],
                    "os": node["status"]["nodeInfo"]["osImage"],
                }

                if is_ready:
                    healthy_nodes += 1

            all_healthy = healthy_nodes == total_nodes

            return {
                "name": "node_health",
                "status": "PASS" if all_healthy else "FAIL",
                "message": f"{healthy_nodes}/{total_nodes} nodes are healthy",
                "details": {
                    "total_nodes": total_nodes,
                    "healthy_nodes": healthy_nodes,
                    "nodes": node_details,
                },
            }

        except json.JSONDecodeError as e:
            return {
                "name": "node_health",
                "status": "FAIL",
                "message": f"Failed to parse node data: {e}",
                "details": {},
            }

    def check_critical_namespaces(self) -> dict[str, Any]:
        """Check critical namespaces exist and are active."""
        logger.info("Checking critical namespaces...")

        critical_namespaces = [
            "kube-system",
            "monitoring",
            "ingress-nginx",
            "cert-manager",
            "metallb-system",
        ]

        success, output = self.run_kubectl_command(["get", "namespaces", "-o", "json"])
        if not success:
            return {
                "name": "critical_namespaces",
                "status": "FAIL",
                "message": f"Failed to get namespaces: {output}",
                "details": {},
            }

        try:
            namespaces_data = json.loads(output)
            existing_namespaces = {
                ns["metadata"]["name"]: ns["status"]["phase"]
                for ns in namespaces_data.get("items", [])
            }

            missing_namespaces = []
            inactive_namespaces = []

            for ns in critical_namespaces:
                if ns not in existing_namespaces:
                    missing_namespaces.append(ns)
                elif existing_namespaces[ns] != "Active":
                    inactive_namespaces.append(ns)

            issues = missing_namespaces + inactive_namespaces

            return {
                "name": "critical_namespaces",
                "status": "PASS" if not issues else "FAIL",
                "message": "All critical namespaces are active"
                if not issues
                else f'Issues with namespaces: {", ".join(issues)}',
                "details": {
                    "expected": critical_namespaces,
                    "found": list(existing_namespaces.keys()),
                    "missing": missing_namespaces,
                    "inactive": inactive_namespaces,
                },
            }

        except json.JSONDecodeError as e:
            return {
                "name": "critical_namespaces",
                "status": "FAIL",
                "message": f"Failed to parse namespace data: {e}",
                "details": {},
            }

    def check_deployment_health(self) -> dict[str, Any]:
        """Check all deployments are healthy."""
        logger.info("Checking deployment health...")

        success, output = self.run_kubectl_command(
            ["get", "deployments", "--all-namespaces", "-o", "json"],
        )
        if not success:
            return {
                "name": "deployment_health",
                "status": "FAIL",
                "message": f"Failed to get deployments: {output}",
                "details": {},
            }

        try:
            deployments_data = json.loads(output)
            deployments = deployments_data.get("items", [])

            unhealthy_deployments = []
            deployment_summary = {
                "total": len(deployments),
                "healthy": 0,
                "unhealthy": 0,
            }

            for deployment in deployments:
                name = deployment["metadata"]["name"]
                namespace = deployment["metadata"]["namespace"]
                spec = deployment["spec"]
                status = deployment["status"]

                desired_replicas = spec.get("replicas", 1)
                ready_replicas = status.get("readyReplicas", 0)

                is_healthy = ready_replicas == desired_replicas

                if is_healthy:
                    deployment_summary["healthy"] += 1
                else:
                    deployment_summary["unhealthy"] += 1
                    unhealthy_deployments.append(
                        {
                            "name": name,
                            "namespace": namespace,
                            "desired": desired_replicas,
                            "ready": ready_replicas,
                        },
                    )

            all_healthy = deployment_summary["unhealthy"] == 0

            return {
                "name": "deployment_health",
                "status": "PASS" if all_healthy else "FAIL",
                "message": f'{deployment_summary["healthy"]}/{deployment_summary["total"]} deployments are healthy',
                "details": {
                    "summary": deployment_summary,
                    "unhealthy_deployments": unhealthy_deployments,
                },
            }

        except json.JSONDecodeError as e:
            return {
                "name": "deployment_health",
                "status": "FAIL",
                "message": f"Failed to parse deployment data: {e}",
                "details": {},
            }

    def check_service_endpoints(self) -> dict[str, Any]:
        """Check critical services have endpoints."""
        logger.info("Checking service endpoints...")

        critical_services = {
            "monitoring": ["prometheus", "grafana", "alertmanager"],
            "ingress-nginx": ["ingress-nginx-controller"],
            "kube-system": ["kube-dns"],
        }

        endpoint_issues = []

        for namespace, services in critical_services.items():
            for service in services:
                success, output = self.run_kubectl_command(
                    [
                        "get",
                        "endpoints",
                        service,
                        "-n",
                        namespace,
                        "-o",
                        "json",
                    ],
                )

                if not success:
                    endpoint_issues.append(f"{namespace}/{service}: not found")
                    continue

                try:
                    endpoint_data = json.loads(output)
                    subsets = endpoint_data.get("subsets", [])

                    has_endpoints = any(subset.get("addresses", []) for subset in subsets)

                    if not has_endpoints:
                        endpoint_issues.append(f"{namespace}/{service}: no endpoints")

                except json.JSONDecodeError:
                    endpoint_issues.append(f"{namespace}/{service}: parse error")

        return {
            "name": "service_endpoints",
            "status": "PASS" if not endpoint_issues else "FAIL",
            "message": "All critical services have endpoints"
            if not endpoint_issues
            else f'Endpoint issues: {", ".join(endpoint_issues)}',
            "details": {
                "checked_services": critical_services,
                "issues": endpoint_issues,
            },
        }

    def check_ingress_connectivity(self) -> dict[str, Any]:
        """Check ingress controller is responding."""
        logger.info("Checking ingress connectivity...")

        # Get ingress controller service
        success, output = self.run_kubectl_command(
            [
                "get",
                "svc",
                "ingress-nginx-controller",
                "-n",
                "ingress-nginx",
                "-o",
                "json",
            ],
        )

        if not success:
            return {
                "name": "ingress_connectivity",
                "status": "FAIL",
                "message": "Ingress controller service not found",
                "details": {},
            }

        try:
            # For production health check, we verify the service exists and has external IPs
            service_data = json.loads(output)
            status = service_data.get("status", {})
            load_balancer = status.get("loadBalancer", {})
            ingress_ips = load_balancer.get("ingress", [])

            has_external_access = len(ingress_ips) > 0

            return {
                "name": "ingress_connectivity",
                "status": "PASS" if has_external_access else "WARN",
                "message": "Ingress has external IPs"
                if has_external_access
                else "Ingress service exists but no external IPs",
                "details": {
                    "service_type": service_data["spec"]["type"],
                    "external_ips": [
                        ip.get("ip", ip.get("hostname", "unknown")) for ip in ingress_ips
                    ],
                },
            }

        except json.JSONDecodeError as e:
            return {
                "name": "ingress_connectivity",
                "status": "FAIL",
                "message": f"Failed to parse ingress service data: {e}",
                "details": {},
            }

    def check_certificate_health(self) -> dict[str, Any]:
        """Check cert-manager certificates are ready."""
        logger.info("Checking certificate health...")

        success, output = self.run_kubectl_command(
            [
                "get",
                "certificates",
                "--all-namespaces",
                "-o",
                "json",
            ],
        )

        if not success:
            return {
                "name": "certificate_health",
                "status": "WARN",
                "message": "No certificates found or cert-manager not installed",
                "details": {},
            }

        try:
            certificates_data = json.loads(output)
            certificates = certificates_data.get("items", [])

            if not certificates:
                return {
                    "name": "certificate_health",
                    "status": "WARN",
                    "message": "No certificates found",
                    "details": {"total_certificates": 0},
                }

            certificate_status = {
                "total": len(certificates),
                "ready": 0,
                "not_ready": 0,
                "issues": [],
            }

            for cert in certificates:
                name = cert["metadata"]["name"]
                namespace = cert["metadata"]["namespace"]
                status = cert.get("status", {})
                conditions = status.get("conditions", [])

                ready_condition = next(
                    (c for c in conditions if c["type"] == "Ready"),
                    None,
                )

                is_ready = ready_condition and ready_condition["status"] == "True"

                if is_ready:
                    certificate_status["ready"] += 1
                else:
                    certificate_status["not_ready"] += 1
                    reason = (
                        ready_condition.get("reason", "Unknown")
                        if ready_condition
                        else "No Ready condition"
                    )
                    certificate_status["issues"].append(f"{namespace}/{name}: {reason}")

            all_ready = certificate_status["not_ready"] == 0

            return {
                "name": "certificate_health",
                "status": "PASS" if all_ready else "WARN",
                "message": f'{certificate_status["ready"]}/{certificate_status["total"]} certificates are ready',
                "details": certificate_status,
            }

        except json.JSONDecodeError as e:
            return {
                "name": "certificate_health",
                "status": "FAIL",
                "message": f"Failed to parse certificate data: {e}",
                "details": {},
            }

    def check_monitoring_stack(self) -> dict[str, Any]:
        """Check monitoring stack is operational."""
        logger.info("Checking monitoring stack...")

        monitoring_components = ["prometheus", "grafana", "alertmanager"]
        component_status = {}

        for component in monitoring_components:
            success, output = self.run_kubectl_command(
                [
                    "get",
                    "deployment",
                    component,
                    "-n",
                    "monitoring",
                    "-o",
                    "json",
                ],
            )

            if not success:
                component_status[component] = {
                    "status": "MISSING",
                    "message": "Deployment not found",
                }
                continue

            try:
                deployment_data = json.loads(output)
                status = deployment_data["status"]
                spec = deployment_data["spec"]

                desired = spec.get("replicas", 1)
                ready = status.get("readyReplicas", 0)

                is_healthy = ready == desired

                component_status[component] = {
                    "status": "HEALTHY" if is_healthy else "UNHEALTHY",
                    "replicas": f"{ready}/{desired}",
                    "message": "Running normally"
                    if is_healthy
                    else f"Only {ready}/{desired} replicas ready",
                }

            except json.JSONDecodeError:
                component_status[component] = {
                    "status": "ERROR",
                    "message": "Failed to parse deployment data",
                }

        healthy_components = sum(
            1 for status in component_status.values() if status["status"] == "HEALTHY"
        )
        total_components = len(monitoring_components)

        return {
            "name": "monitoring_stack",
            "status": "PASS" if healthy_components == total_components else "WARN",
            "message": f"{healthy_components}/{total_components} monitoring components are healthy",
            "details": component_status,
        }

    def run_all_checks(self) -> dict[str, Any]:
        """Run all production health checks."""
        logger.info("Starting production health checks...")

        checks = [
            self.check_cluster_connectivity,
            self.check_node_health,
            self.check_critical_namespaces,
            self.check_deployment_health,
            self.check_service_endpoints,
            self.check_ingress_connectivity,
            self.check_certificate_health,
            self.check_monitoring_stack,
        ]

        for check_func in checks:
            check_result = check_func()
            check_name = check_result["name"]
            self.results["checks"][check_name] = check_result

            # Update summary
            self.results["summary"]["total_checks"] += 1
            if check_result["status"] == "PASS":
                self.results["summary"]["passed_checks"] += 1
            elif check_result["status"] == "WARN":
                self.results["summary"]["warning_checks"] += 1
            else:
                self.results["summary"]["failed_checks"] += 1

        # Overall health assessment
        failed = self.results["summary"]["failed_checks"]
        warnings = self.results["summary"]["warning_checks"]

        if failed == 0 and warnings == 0:
            self.results["overall_status"] = "HEALTHY"
            self.results["overall_message"] = "All production health checks passed"
        elif failed == 0:
            self.results["overall_status"] = "HEALTHY_WITH_WARNINGS"
            self.results["overall_message"] = f"Production is healthy but has {warnings} warnings"
        else:
            self.results["overall_status"] = "UNHEALTHY"
            self.results["overall_message"] = (
                f"Production health check failed: {failed} failed checks, {warnings} warnings"
            )

        return self.results

    def output_results(self) -> None:
        """Output results in the specified format."""
        if self.output_format == "json":
            print(json.dumps(self.results, indent=2))
        elif self.output_format == "junit":
            self._output_junit()
        else:
            self._output_console()

    def _output_console(self) -> None:
        """Output results to console."""
        print("\n🏥 Production Health Check Report")
        print(f"{'=' * 50}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Environment: {self.results['environment']}")
        print(f"Overall Status: {self.results['overall_status']}")
        print(f"Message: {self.results['overall_message']}")

        print("\n📊 Summary:")
        summary = self.results["summary"]
        print(f"  Total Checks: {summary['total_checks']}")
        print(f"  ✅ Passed: {summary['passed_checks']}")
        print(f"  ⚠️  Warnings: {summary['warning_checks']}")
        print(f"  ❌ Failed: {summary['failed_checks']}")

        print("\n🔍 Detailed Results:")
        for check_name, check_result in self.results["checks"].items():
            status_icon = {
                "PASS": "✅",
                "WARN": "⚠️",
                "FAIL": "❌",
            }.get(check_result["status"], "❓")

            print(f"  {status_icon} {check_name}: {check_result['message']}")

            # Show details for failed checks
            if check_result["status"] == "FAIL" and check_result.get("details"):
                details = check_result["details"]
                if isinstance(details, dict):
                    for key, value in details.items():
                        if isinstance(value, list | dict) and value:
                            print(f"    {key}: {json.dumps(value, indent=6)}")
                        else:
                            print(f"    {key}: {value}")

    def _output_junit(self) -> None:
        """Output results in JUnit XML format."""
        # Basic JUnit XML output for CI integration
        print('<?xml version="1.0" encoding="UTF-8"?>')
        print("<testsuites>")
        print(
            f'<testsuite name="ProductionHealthCheck" tests="{self.results["summary"]["total_checks"]}" '
            f'failures="{self.results["summary"]["failed_checks"]}" '
            f'errors="0" skipped="{self.results["summary"]["warning_checks"]}">',
        )

        for check_name, check_result in self.results["checks"].items():
            if check_result["status"] == "PASS":
                print(f'<testcase name="{check_name}" classname="ProductionHealthCheck"/>')
            elif check_result["status"] == "WARN":
                print(f'<testcase name="{check_name}" classname="ProductionHealthCheck">')
                print(f'<skipped message="{check_result["message"]}"/>')
                print("</testcase>")
            else:
                print(f'<testcase name="{check_name}" classname="ProductionHealthCheck">')
                print(f'<failure message="{check_result["message"]}">')
                print(f'Details: {json.dumps(check_result.get("details", {}), indent=2)}')
                print("</failure>")
                print("</testcase>")

        print("</testsuite>")
        print("</testsuites>")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Production Health Check for Homelab Infrastructure",
    )
    parser.add_argument(
        "--output-format",
        choices=["console", "json", "junit"],
        default="console",
        help="Output format for results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        health_checker = ProductionHealthChecker(output_format=args.output_format)
        results = health_checker.run_all_checks()
        health_checker.output_results()

        # Exit with appropriate code
        if results["overall_status"] == "UNHEALTHY":
            sys.exit(1)
        elif results["overall_status"] == "HEALTHY_WITH_WARNINGS":
            sys.exit(2)  # Warning exit code
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Health check interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error during health check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
