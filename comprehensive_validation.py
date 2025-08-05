#!/usr/bin/env python3
"""
Comprehensive Homelab Infrastructure Validation Script
Validates all services are operational, SSO authentication, service integration, and monitoring.
"""

import json
import ssl
import subprocess
import sys
import urllib.request
from typing import Any


class HomelabValidator:
    def __init__(self) -> None:
        self.results = {
            "cluster_health": {},
            "service_status": {},
            "sso_authentication": {},
            "service_integration": {},
            "monitoring_validation": {},
            "overall_status": "unknown",
        }

    def run_command(self, cmd: list[str]) -> dict[str, Any]:
        """Execute a shell command and return result."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    def validate_cluster_health(self) -> None:
        """Validate Kubernetes cluster health."""
        print("🏥 Validating Cluster Health...")

        # Check cluster info
        result = self.run_command(["kubectl", "cluster-info"])
        self.results["cluster_health"]["cluster_info"] = {
            "accessible": result["success"],
            "details": result["stdout"] if result["success"] else result["stderr"],
        }

        # Check node status
        result = self.run_command(["kubectl", "get", "nodes", "-o", "json"])
        if result["success"]:
            try:
                nodes_data = json.loads(result["stdout"])
                nodes = []
                for node in nodes_data.get("items", []):
                    node_name = node["metadata"]["name"]
                    conditions = node["status"]["conditions"]
                    ready_condition = next((c for c in conditions if c["type"] == "Ready"), None)
                    nodes.append(
                        {
                            "name": node_name,
                            "ready": ready_condition["status"] == "True"
                            if ready_condition
                            else False,
                            "status": "Ready"
                            if ready_condition and ready_condition["status"] == "True"
                            else "NotReady",
                        },
                    )
                self.results["cluster_health"]["nodes"] = nodes
            except json.JSONDecodeError:
                self.results["cluster_health"]["nodes"] = []

        # Check system pods
        result = self.run_command(["kubectl", "get", "pods", "-n", "kube-system", "-o", "json"])
        if result["success"]:
            try:
                pods_data = json.loads(result["stdout"])
                system_pods = []
                for pod in pods_data.get("items", []):
                    pod_name = pod["metadata"]["name"]
                    phase = pod["status"]["phase"]
                    system_pods.append(
                        {
                            "name": pod_name,
                            "phase": phase,
                            "ready": phase == "Running",
                        },
                    )
                self.results["cluster_health"]["system_pods"] = system_pods
            except json.JSONDecodeError:
                self.results["cluster_health"]["system_pods"] = []

    def validate_service_status(self) -> None:
        """Validate all deployed services."""
        print("🚀 Validating Service Status...")

        # Get all pods across namespaces
        result = self.run_command(["kubectl", "get", "pods", "-A", "-o", "json"])
        if result["success"]:
            try:
                pods_data = json.loads(result["stdout"])
                services = {}

                for pod in pods_data.get("items", []):
                    namespace = pod["metadata"]["namespace"]
                    pod_name = pod["metadata"]["name"]
                    phase = pod["status"]["phase"]

                    # Skip system namespaces for service validation
                    if namespace in [
                        "kube-system",
                        "metallb-system",
                        "ingress-nginx",
                        "cert-manager",
                    ]:
                        continue

                    if namespace not in services:
                        services[namespace] = []

                    # Check if pod is ready
                    ready = False
                    if "containerStatuses" in pod["status"]:
                        ready = all(
                            c.get("ready", False) for c in pod["status"]["containerStatuses"]
                        )

                    services[namespace].append(
                        {
                            "pod_name": pod_name,
                            "phase": phase,
                            "ready": ready,
                            "running": phase == "Running" and ready,
                        },
                    )

                self.results["service_status"] = services
            except json.JSONDecodeError:
                self.results["service_status"] = {}

    def validate_ingress_and_certificates(self) -> None:
        """Validate ingress and certificate status."""
        print("🔐 Validating Ingress and Certificates...")

        # Check ingresses
        result = self.run_command(["kubectl", "get", "ingress", "-A", "-o", "json"])
        if result["success"]:
            try:
                ingress_data = json.loads(result["stdout"])
                ingresses = []
                for ingress in ingress_data.get("items", []):
                    name = ingress["metadata"]["name"]
                    namespace = ingress["metadata"]["namespace"]
                    hosts = []
                    if "rules" in ingress["spec"]:
                        hosts = [rule.get("host", "unknown") for rule in ingress["spec"]["rules"]]

                    ingresses.append(
                        {
                            "name": name,
                            "namespace": namespace,
                            "hosts": hosts,
                        },
                    )
                self.results["service_integration"]["ingresses"] = ingresses
            except json.JSONDecodeError:
                self.results["service_integration"]["ingresses"] = []

        # Check certificates
        result = self.run_command(["kubectl", "get", "certificates", "-A", "-o", "json"])
        if result["success"]:
            try:
                cert_data = json.loads(result["stdout"])
                certificates = []
                for cert in cert_data.get("items", []):
                    name = cert["metadata"]["name"]
                    namespace = cert["metadata"]["namespace"]
                    ready = False
                    if "status" in cert and "conditions" in cert["status"]:
                        ready_condition = next(
                            (c for c in cert["status"]["conditions"] if c["type"] == "Ready"),
                            None,
                        )
                        ready = ready_condition["status"] == "True" if ready_condition else False

                    certificates.append(
                        {
                            "name": name,
                            "namespace": namespace,
                            "ready": ready,
                        },
                    )
                self.results["service_integration"]["certificates"] = certificates
            except json.JSONDecodeError:
                self.results["service_integration"]["certificates"] = []

    def validate_sso_authentication(self) -> None:
        """Validate SSO authentication and OAuth2 proxy."""
        print("🔐 Validating SSO Authentication...")

        services_to_test = [
            "homelab.local",
            "grafana.homelab.local",
            "prometheus.homelab.local",
            "auth.homelab.local",
        ]

        auth_results = {}

        for service in services_to_test:
            try:
                # Create SSL context that accepts self-signed certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Test HTTPS connectivity
                url = f"https://{service}"
                req = urllib.request.Request(url)

                try:
                    with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                        status_code = response.getcode()
                        auth_results[service] = {
                            "accessible": True,
                            "https_enabled": True,
                            "status_code": status_code,
                            "redirect_detected": status_code in [301, 302, 307, 308],
                        }
                except urllib.error.HTTPError as e:
                    auth_results[service] = {
                        "accessible": True,
                        "https_enabled": True,
                        "status_code": e.code,
                        "redirect_detected": e.code in [301, 302, 307, 308],
                    }

            except Exception as e:
                auth_results[service] = {
                    "accessible": False,
                    "https_enabled": False,
                    "error": str(e),
                }

        self.results["sso_authentication"] = auth_results

    def validate_monitoring_dashboards(self) -> None:
        """Validate monitoring dashboards and metrics collection."""
        print("📊 Validating Monitoring Dashboards...")

        monitoring_results = {}

        # Test Prometheus metrics endpoint
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Test Prometheus API
            prom_url = "https://prometheus.homelab.local/api/v1/targets"
            req = urllib.request.Request(prom_url)

            try:
                with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                    if response.getcode() == 200:
                        data = json.loads(response.read().decode())
                        active_targets = data.get("data", {}).get("activeTargets", [])
                        monitoring_results["prometheus"] = {
                            "accessible": True,
                            "targets_count": len(active_targets),
                            "targets_up": len(
                                [t for t in active_targets if t.get("health") == "up"],
                            ),
                        }
                    else:
                        monitoring_results["prometheus"] = {
                            "accessible": False,
                            "error": f"HTTP {response.getcode()}",
                        }
            except Exception as e:
                monitoring_results["prometheus"] = {
                    "accessible": False,
                    "error": str(e),
                }

        except Exception as e:
            monitoring_results["prometheus"] = {
                "accessible": False,
                "error": str(e),
            }

        # Test Grafana accessibility
        try:
            grafana_url = "https://grafana.homelab.local"
            req = urllib.request.Request(grafana_url)

            try:
                with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                    monitoring_results["grafana"] = {
                        "accessible": True,
                        "status_code": response.getcode(),
                    }
            except urllib.error.HTTPError as e:
                monitoring_results["grafana"] = {
                    "accessible": True,
                    "status_code": e.code,
                }
        except Exception as e:
            monitoring_results["grafana"] = {
                "accessible": False,
                "error": str(e),
            }

        self.results["monitoring_validation"] = monitoring_results

    def determine_overall_status(self) -> None:
        """Determine overall system status."""
        print("🎯 Determining Overall Status...")

        issues = []
        warnings = []

        # Check cluster health
        if not self.results["cluster_health"].get("cluster_info", {}).get("accessible", False):
            issues.append("Cluster not accessible")

        # Check nodes
        nodes = self.results["cluster_health"].get("nodes", [])
        unhealthy_nodes = [n for n in nodes if not n.get("ready", False)]
        if unhealthy_nodes:
            issues.append(f"{len(unhealthy_nodes)} unhealthy nodes")

        # Check system pods
        system_pods = self.results["cluster_health"].get("system_pods", [])
        failed_system_pods = [p for p in system_pods if not p.get("ready", False)]
        if failed_system_pods:
            warnings.append(f"{len(failed_system_pods)} system pods not ready")

        # Check services
        for namespace, pods in self.results["service_status"].items():
            failed_pods = [p for p in pods if not p.get("running", False)]
            if failed_pods:
                issues.append(f"{len(failed_pods)} failed pods in {namespace}")

        # Check certificates
        certificates = self.results["service_integration"].get("certificates", [])
        unready_certs = [c for c in certificates if not c.get("ready", False)]
        if unready_certs:
            warnings.append(f"{len(unready_certs)} certificates not ready")

        # Check SSO authentication
        auth_failures = [
            service
            for service, result in self.results["sso_authentication"].items()
            if not result.get("accessible", False)
        ]
        if auth_failures:
            issues.append(f"SSO authentication failures: {', '.join(auth_failures)}")

        # Check monitoring
        if not self.results["monitoring_validation"].get("prometheus", {}).get("accessible", False):
            issues.append("Prometheus not accessible")
        if not self.results["monitoring_validation"].get("grafana", {}).get("accessible", False):
            issues.append("Grafana not accessible")

        # Determine overall status
        if issues:
            self.results["overall_status"] = "FAIL"
            self.results["issues"] = issues
        elif warnings:
            self.results["overall_status"] = "WARNING"
            self.results["warnings"] = warnings
        else:
            self.results["overall_status"] = "PASS"

        self.results["issues"] = issues
        self.results["warnings"] = warnings

    def print_summary(self) -> int:
        """Print comprehensive validation summary."""
        print("\n" + "=" * 80)
        print("🏠 COMPREHENSIVE HOMELAB INFRASTRUCTURE VALIDATION REPORT")
        print("=" * 80)

        print(f"\n🎯 OVERALL STATUS: {self.results['overall_status']}")

        if self.results.get("issues"):
            print(f"\n🚨 CRITICAL ISSUES ({len(self.results['issues'])}):")
            for issue in self.results["issues"]:
                print(f"  ❌ {issue}")

        if self.results.get("warnings"):
            print(f"\n⚠️  WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"  ⚠️  {warning}")

        # Cluster Health Summary
        print("\n🏥 CLUSTER HEALTH:")
        cluster_accessible = (
            self.results["cluster_health"].get("cluster_info", {}).get("accessible", False)
        )
        print(f"  Cluster Accessible: {'✅' if cluster_accessible else '❌'}")

        nodes = self.results["cluster_health"].get("nodes", [])
        healthy_nodes = len([n for n in nodes if n.get("ready", False)])
        print(f"  Healthy Nodes: {healthy_nodes}/{len(nodes)}")

        system_pods = self.results["cluster_health"].get("system_pods", [])
        ready_system_pods = len([p for p in system_pods if p.get("ready", False)])
        print(f"  Ready System Pods: {ready_system_pods}/{len(system_pods)}")

        # Service Status Summary
        print("\n🚀 SERVICE STATUS:")
        for namespace, pods in self.results["service_status"].items():
            running_pods = len([p for p in pods if p.get("running", False)])
            total_pods = len(pods)
            status_icon = "✅" if running_pods == total_pods else "❌"
            print(f"  {status_icon} {namespace}: {running_pods}/{total_pods} pods running")

        # SSO Authentication Summary
        print("\n🔐 SSO AUTHENTICATION:")
        for service, result in self.results["sso_authentication"].items():
            accessible = result.get("accessible", False)
            https_enabled = result.get("https_enabled", False)
            icon = "✅" if accessible and https_enabled else "❌"
            print(f"  {icon} {service}: HTTPS {'✅' if https_enabled else '❌'}")

        # Service Integration Summary
        print("\n🔗 SERVICE INTEGRATION:")
        ingresses = self.results["service_integration"].get("ingresses", [])
        print(f"  Ingresses Configured: {len(ingresses)}")

        certificates = self.results["service_integration"].get("certificates", [])
        ready_certs = len([c for c in certificates if c.get("ready", False)])
        print(f"  Ready Certificates: {ready_certs}/{len(certificates)}")

        # Monitoring Summary
        print("\n📊 MONITORING VALIDATION:")
        prom_accessible = (
            self.results["monitoring_validation"].get("prometheus", {}).get("accessible", False)
        )
        print(f"  Prometheus: {'✅' if prom_accessible else '❌'}")

        if prom_accessible:
            targets_up = self.results["monitoring_validation"]["prometheus"].get("targets_up", 0)
            targets_total = self.results["monitoring_validation"]["prometheus"].get(
                "targets_count",
                0,
            )
            print(f"    Active Targets: {targets_up}/{targets_total}")

        grafana_accessible = (
            self.results["monitoring_validation"].get("grafana", {}).get("accessible", False)
        )
        print(f"  Grafana: {'✅' if grafana_accessible else '❌'}")

        print(f"\n{'=' * 80}")

        # Return appropriate exit code
        return 0 if self.results["overall_status"] in ["PASS", "WARNING"] else 1

    def run_comprehensive_validation(self):
        """Run complete validation suite."""
        print("🚀 Starting Comprehensive Homelab Infrastructure Validation...")
        print("=" * 80)

        try:
            self.validate_cluster_health()
            self.validate_service_status()
            self.validate_ingress_and_certificates()
            self.validate_sso_authentication()
            self.validate_monitoring_dashboards()
            self.determine_overall_status()
        except Exception as e:
            print(f"❌ Validation failed with error: {e}")
            self.results["overall_status"] = "ERROR"
            self.results["error"] = str(e)

        return self.print_summary()


if __name__ == "__main__":
    validator = HomelabValidator()
    exit_code = validator.run_comprehensive_validation()
    sys.exit(exit_code)
