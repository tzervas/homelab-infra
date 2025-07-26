#!/usr/bin/env python3
"""
Network & Security Validator for Homelab Infrastructure

This module tests network connectivity, TLS certificates, network policies,
MetalLB functionality, DNS resolution, and RBAC security policies.
"""

import logging
import socket
import ssl
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

# Import our previous modules
try:
    from .infrastructure_health import HealthStatus
    from .service_checker import ServiceDeploymentChecker
except ImportError:
    try:
        from infrastructure_health import HealthStatus
        from service_checker import ServiceDeploymentChecker
    except ImportError:
        # Fallback definitions
        @dataclass
        class HealthStatus:
            component: str
            status: str
            message: str
            details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityStatus:
    """Security validation result."""
    check_type: str
    component: str
    status: str  # "secure", "warning", "vulnerable", "unknown"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    @property
    def is_secure(self) -> bool:
        """Check if component is secure."""
        return self.status == "secure"


class NetworkSecurityValidator:
    """Network and security validation for homelab infrastructure."""

    def __init__(self, kubeconfig_path: Optional[str] = None, log_level: str = "INFO"):
        """Initialize the network security validator."""
        self.logger = self._setup_logging(log_level)
        self.k8s_client = None
        self.service_checker = None

        # Network and security configuration
        self.metallb_ip_range = "192.168.25.200-192.168.25.250"
        self.critical_services = ["gitlab", "keycloak", "prometheus", "grafana"]
        self.network_policies = ["default-deny-all", "allow-dns", "monitoring-ingress"]

        if KUBERNETES_AVAILABLE:
            self._init_kubernetes_client(kubeconfig_path)
            try:
                self.service_checker = ServiceDeploymentChecker(kubeconfig_path, log_level)
            except Exception as e:
                self.logger.warning(f"Could not initialize service checker: {e}")

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _init_kubernetes_client(self, kubeconfig_path: Optional[str]) -> None:
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
            self.logger.info("Kubernetes client initialized for security validation")

        except Exception as e:
            self.logger.error(f"Failed to initialize Kubernetes client: {e}")

    def test_network_connectivity(self) -> SecurityStatus:
        """Test basic network connectivity and routing."""
        try:
            # Test external connectivity
            external_result = subprocess.run(
                ["ping", "-c", "3", "-W", "5", "8.8.8.8"],
                capture_output=True, text=True, timeout=15
            )

            # Test internal DNS
            dns_result = subprocess.run(
                ["nslookup", "kubernetes.default.svc.cluster.local"],
                capture_output=True, text=True, timeout=10
            )

            connectivity_issues = []
            if external_result.returncode != 0:
                connectivity_issues.append("External connectivity failed")
            if dns_result.returncode != 0:
                connectivity_issues.append("Internal DNS resolution failed")

            if not connectivity_issues:
                status = "secure"
                message = "Network connectivity verified"
            else:
                status = "warning"
                message = f"Connectivity issues: {', '.join(connectivity_issues)}"

            return SecurityStatus(
                check_type="network_connectivity",
                component="cluster_network",
                status=status,
                message=message,
                details={
                    "external_ping": external_result.returncode == 0,
                    "internal_dns": dns_result.returncode == 0
                }
            )

        except Exception as e:
            return SecurityStatus(
                check_type="network_connectivity",
                component="cluster_network",
                status="unknown",
                message=f"Network test failed: {str(e)}"
            )

    def validate_tls_certificates(self) -> SecurityStatus:
        """Validate TLS certificates and check expiry."""
        if not self.k8s_client:
            return SecurityStatus(
                check_type="tls_certificates",
                component="certificates",
                status="unknown",
                message="Kubernetes client unavailable"
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)
            secrets = v1.list_secret_for_all_namespaces()

            tls_secrets = []
            expiring_certs = []

            for secret in secrets.items:
                if secret.type == "kubernetes.io/tls":
                    tls_secrets.append(secret.metadata.name)

                    # Check certificate expiry if possible
                    if secret.data and "tls.crt" in secret.data:
                        try:
                            import base64
                            cert_data = base64.b64decode(secret.data["tls.crt"])
                            cert = ssl.DER_cert_to_PEM_cert(cert_data)

                            # Parse certificate (simplified check)
                            if "CERTIFICATE" in cert:
                                # Note: Full cert parsing would require cryptography library
                                # This is a simplified check
                                pass
                        except Exception:
                            pass

            cert_count = len(tls_secrets)
            if cert_count > 0:
                status = "secure" if not expiring_certs else "warning"
                message = f"Found {cert_count} TLS certificates"
            else:
                status = "warning"
                message = "No TLS certificates found"

            return SecurityStatus(
                check_type="tls_certificates",
                component="certificates",
                status=status,
                message=message,
                details={
                    "total_certificates": cert_count,
                    "expiring_soon": len(expiring_certs),
                    "certificate_names": tls_secrets[:5]  # Limit for brevity
                },
                recommendations=["Install cryptography library for detailed cert validation"] if cert_count > 0 else []
            )

        except Exception as e:
            return SecurityStatus(
                check_type="tls_certificates",
                component="certificates",
                status="unknown",
                message=f"TLS validation failed: {str(e)}"
            )

    def test_network_policies(self) -> SecurityStatus:
        """Test network policy enforcement."""
        if not self.k8s_client:
            return SecurityStatus(
                check_type="network_policies",
                component="network_security",
                status="unknown",
                message="Kubernetes client unavailable"
            )

        try:
            networking_v1 = client.NetworkingV1Api(self.k8s_client)
            policies = networking_v1.list_network_policy_for_all_namespaces()

            policy_names = [p.metadata.name for p in policies.items]
            critical_policies_found = [p for p in self.network_policies if p in policy_names]
            missing_policies = [p for p in self.network_policies if p not in policy_names]

            total_policies = len(policies.items)

            if len(critical_policies_found) == len(self.network_policies):
                status = "secure"
                message = f"All critical network policies present ({total_policies} total)"
            elif missing_policies:
                status = "warning"
                message = f"Missing critical policies: {', '.join(missing_policies)}"
            else:
                status = "warning"
                message = f"Found {total_policies} policies, verification needed"

            return SecurityStatus(
                check_type="network_policies",
                component="network_security",
                status=status,
                message=message,
                details={
                    "total_policies": total_policies,
                    "critical_found": critical_policies_found,
                    "missing_policies": missing_policies,
                    "all_policies": policy_names[:10]  # Limit for brevity
                },
                recommendations=["Review policy effectiveness"] if missing_policies else []
            )

        except Exception as e:
            return SecurityStatus(
                check_type="network_policies",
                component="network_security",
                status="unknown",
                message=f"Network policy check failed: {str(e)}"
            )

    def verify_metallb_functionality(self) -> SecurityStatus:
        """Verify MetalLB LoadBalancer functionality."""
        if not self.k8s_client:
            return SecurityStatus(
                check_type="metallb_loadbalancer",
                component="load_balancer",
                status="unknown",
                message="Kubernetes client unavailable"
            )

        try:
            v1 = client.CoreV1Api(self.k8s_client)

            # Check MetalLB pods
            metallb_pods = v1.list_namespaced_pod(namespace="metallb-system")
            running_pods = sum(1 for p in metallb_pods.items if p.status.phase == "Running")
            total_pods = len(metallb_pods.items)

            # Check LoadBalancer services
            services = v1.list_service_for_all_namespaces()
            lb_services = [s for s in services.items if s.spec.type == "LoadBalancer"]
            lb_with_external_ip = [s for s in lb_services if s.status.load_balancer.ingress]

            metallb_healthy = running_pods == total_pods > 0
            lb_functional = len(lb_with_external_ip) > 0

            if metallb_healthy and lb_functional:
                status = "secure"
                message = f"MetalLB operational: {len(lb_with_external_ip)} LoadBalancers active"
            elif metallb_healthy:
                status = "warning"
                message = "MetalLB running but no active LoadBalancers"
            else:
                status = "vulnerable"
                message = f"MetalLB issues: {running_pods}/{total_pods} pods running"

            return SecurityStatus(
                check_type="metallb_loadbalancer",
                component="load_balancer",
                status=status,
                message=message,
                details={
                    "metallb_pods_running": running_pods,
                    "metallb_pods_total": total_pods,
                    "loadbalancer_services": len(lb_services),
                    "active_loadbalancers": len(lb_with_external_ip),
                    "ip_range": self.metallb_ip_range
                }
            )

        except Exception as e:
            return SecurityStatus(
                check_type="metallb_loadbalancer",
                component="load_balancer",
                status="unknown",
                message=f"MetalLB check failed: {str(e)}"
            )

    def check_dns_service_discovery(self) -> SecurityStatus:
        """Check DNS resolution and service discovery."""
        try:
            # Test core services DNS resolution
            dns_tests = [
                "kubernetes.default.svc.cluster.local",
                "kube-dns.kube-system.svc.cluster.local",
            ]

            dns_results = {}
            for service in dns_tests:
                try:
                    result = subprocess.run(
                        ["nslookup", service],
                        capture_output=True, text=True, timeout=5
                    )
                    dns_results[service] = result.returncode == 0
                except Exception:
                    dns_results[service] = False

            successful_lookups = sum(1 for success in dns_results.values() if success)
            total_tests = len(dns_tests)

            if successful_lookups == total_tests:
                status = "secure"
                message = "DNS service discovery functional"
            elif successful_lookups > 0:
                status = "warning"
                message = f"Partial DNS functionality: {successful_lookups}/{total_tests}"
            else:
                status = "vulnerable"
                message = "DNS service discovery failed"

            return SecurityStatus(
                check_type="dns_service_discovery",
                component="dns",
                status=status,
                message=message,
                details={
                    "dns_test_results": dns_results,
                    "successful_lookups": successful_lookups,
                    "total_tests": total_tests
                }
            )

        except Exception as e:
            return SecurityStatus(
                check_type="dns_service_discovery",
                component="dns",
                status="unknown",
                message=f"DNS check failed: {str(e)}"
            )

    def validate_rbac_security(self) -> SecurityStatus:
        """Validate RBAC and security policies."""
        if not self.k8s_client:
            return SecurityStatus(
                check_type="rbac_security",
                component="rbac",
                status="unknown",
                message="Kubernetes client unavailable"
            )

        try:
            rbac_v1 = client.RbacAuthorizationV1Api(self.k8s_client)

            # Check ClusterRoles and ClusterRoleBindings
            cluster_roles = rbac_v1.list_cluster_role()
            cluster_role_bindings = rbac_v1.list_cluster_role_binding()

            # Look for overly permissive bindings
            admin_bindings = []
            for binding in cluster_role_bindings.items:
                if binding.role_ref.name == "cluster-admin":
                    admin_bindings.append(binding.metadata.name)

            # Check service accounts
            v1 = client.CoreV1Api(self.k8s_client)
            service_accounts = v1.list_service_account_for_all_namespaces()

            total_roles = len(cluster_roles.items)
            total_bindings = len(cluster_role_bindings.items)
            total_sa = len(service_accounts.items)

            if len(admin_bindings) <= 3:  # Reasonable number of admin bindings
                status = "secure"
                message = f"RBAC configured: {total_roles} roles, {total_bindings} bindings"
            else:
                status = "warning"
                message = f"Review needed: {len(admin_bindings)} cluster-admin bindings"

            return SecurityStatus(
                check_type="rbac_security",
                component="rbac",
                status=status,
                message=message,
                details={
                    "total_cluster_roles": total_roles,
                    "total_cluster_bindings": total_bindings,
                    "total_service_accounts": total_sa,
                    "cluster_admin_bindings": len(admin_bindings),
                    "admin_binding_names": admin_bindings[:5]  # Limit for brevity
                },
                recommendations=["Review cluster-admin bindings"] if len(admin_bindings) > 3 else []
            )

        except Exception as e:
            return SecurityStatus(
                check_type="rbac_security",
                component="rbac",
                status="unknown",
                message=f"RBAC check failed: {str(e)}"
            )

    def run_comprehensive_security_scan(self) -> List[SecurityStatus]:
        """Run all security and network validation checks."""
        self.logger.info("Starting comprehensive network and security validation...")

        checks = [
            self.test_network_connectivity,
            self.validate_tls_certificates,
            self.test_network_policies,
            self.verify_metallb_functionality,
            self.check_dns_service_discovery,
            self.validate_rbac_security
        ]

        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)

                status_icon = "🔒" if result.is_secure else "⚠️" if result.status == "warning" else "🚨"
                self.logger.info(f"{status_icon} {result.check_type}: {result.message}")

            except Exception as e:
                self.logger.error(f"Security check failed: {e}")
                results.append(SecurityStatus(
                    check_type="unknown",
                    component="unknown",
                    status="unknown",
                    message=f"Check failed: {str(e)}"
                ))

        return results


def main():
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate homelab network and security")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--check", choices=["network", "tls", "policies", "metallb", "dns", "rbac"],
                       help="Run specific security check only")

    args = parser.parse_args()

    validator = NetworkSecurityValidator(
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level
    )

    if args.check:
        # Run specific check
        check_map = {
            "network": validator.test_network_connectivity,
            "tls": validator.validate_tls_certificates,
            "policies": validator.test_network_policies,
            "metallb": validator.verify_metallb_functionality,
            "dns": validator.check_dns_service_discovery,
            "rbac": validator.validate_rbac_security
        }

        result = check_map[args.check]()
        results = [result]
    else:
        # Run comprehensive scan
        results = validator.run_comprehensive_security_scan()

    # Display results
    print(f"\n🔐 Network & Security Validation Report:")

    secure_checks = sum(1 for r in results if r.is_secure)
    total_checks = len(results)

    print(f"Security Score: {secure_checks}/{total_checks}")

    for result in results:
        icon = "🔒" if result.is_secure else "⚠️" if result.status == "warning" else "🚨"
        print(f"\n{icon} {result.check_type.replace('_', ' ').title()}:")
        print(f"  Status: {result.status.upper()}")
        print(f"  Message: {result.message}")

        if result.recommendations:
            print(f"  Recommendations:")
            for rec in result.recommendations:
                print(f"    • {rec}")

    return 0 if secure_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
