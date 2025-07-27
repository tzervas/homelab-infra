#!/usr/bin/env python3
"""Integration & Connectivity Tester for Homelab Infrastructure.

This module performs comprehensive end-to-end testing of service connectivity,
SSO integration, ingress routing, and validates the complete system integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import socket
import sys
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

# Import our testing modules
try:
    from .config_validator import ConfigValidator
    from .infrastructure_health import InfrastructureHealthMonitor
    from .network_security import NetworkSecurityValidator
    from .service_checker import ServiceDeploymentChecker
except ImportError:
    try:
        from config_validator import ConfigValidator
        from infrastructure_health import InfrastructureHealthMonitor
        from network_security import NetworkSecurityValidator
        from service_checker import ServiceDeploymentChecker
    except ImportError:
        # Fallback for standalone usage
        print("Warning: Some testing modules not available. Running with limited functionality.")
        ConfigValidator = None
        InfrastructureHealthMonitor = None
        ServiceDeploymentChecker = None
        NetworkSecurityValidator = None


@dataclass
class IntegrationTestResult:
    """Result of an integration test."""

    test_name: str
    status: str  # "pass", "fail", "warning", "skip"
    message: str
    duration: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    from_perspective: str = "server"  # "server" or "workstation"

    @property
    def passed(self) -> bool:
        """Check if test passed."""
        return self.status == "pass"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""

    name: str
    internal_url: str
    external_url: str
    health_path: str
    api_paths: list[str] = field(default_factory=list)
    requires_auth: bool = False
    sso_enabled: bool = False


class IntegrationConnectivityTester:
    """Comprehensive integration and connectivity testing."""

    def __init__(self, kubeconfig_path: str | None = None, log_level: str = "INFO") -> None:
        """Initialize the integration tester."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path

        # Initialize testing modules
        self.config_validator = ConfigValidator(log_level) if ConfigValidator else None
        self.infra_monitor = (
            InfrastructureHealthMonitor(kubeconfig_path, log_level)
            if InfrastructureHealthMonitor
            else None
        )
        self.service_checker = (
            ServiceDeploymentChecker(kubeconfig_path, log_level)
            if ServiceDeploymentChecker
            else None
        )
        self.security_validator = (
            NetworkSecurityValidator(kubeconfig_path, log_level)
            if NetworkSecurityValidator
            else None
        )

        # Service endpoint configuration for homelab
        self.service_endpoints = {
            "gitlab": ServiceEndpoint(
                name="GitLab",
                internal_url="http://192.168.16.201",
                external_url="https://gitlab.homelab.local",
                health_path="/-/health",
                api_paths=["/api/v4/projects", "/api/v4/user"],
                requires_auth=True,
                sso_enabled=True,
            ),
            "keycloak": ServiceEndpoint(
                name="Keycloak",
                internal_url="http://192.168.16.202:8080",
                external_url="https://keycloak.homelab.local",
                health_path="/auth/health/ready",
                api_paths=["/auth/realms/homelab", "/auth/admin/master/console"],
                requires_auth=True,
                sso_enabled=False,  # Keycloak is the SSO provider
            ),
            "prometheus": ServiceEndpoint(
                name="Prometheus",
                internal_url="http://192.168.16.204:9090",
                external_url="https://prometheus.homelab.local",
                health_path="/-/healthy",
                api_paths=["/api/v1/query", "/api/v1/targets"],
                requires_auth=False,
                sso_enabled=True,
            ),
            "grafana": ServiceEndpoint(
                name="Grafana",
                internal_url="http://192.168.16.205:3000",
                external_url="https://grafana.homelab.local",
                health_path="/api/health",
                api_paths=["/api/datasources", "/api/dashboards/home"],
                requires_auth=True,
                sso_enabled=True,
            ),
        }

        # Test timeouts
        self.short_timeout = 10
        self.long_timeout = 30

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

    def test_service_connectivity(
        self,
        endpoint: ServiceEndpoint,
        perspective: str = "server",
        verify_ssl: bool | None = None,
    ) -> IntegrationTestResult:
        """Test basic connectivity to a service endpoint."""
        start_time = time.time()

        # Choose URL based on perspective
        test_url = endpoint.internal_url if perspective == "server" else endpoint.external_url

        # Determine SSL verification default if not explicitly set
        if verify_ssl is None:
            verify_ssl = perspective != "server"

        # Warn if connecting to external URL with SSL verification disabled
        if perspective != "server" and not verify_ssl:
            self.logger.warning(
                f"SSL verification is disabled for external URL '{test_url}'. "
                "This may hide certificate issues in production."
            )

        try:
            # Test basic connectivity
            response = requests.get(
                urljoin(test_url, endpoint.health_path),
                timeout=self.short_timeout,
                verify=verify_ssl,
                allow_redirects=True,
            )

            duration = time.time() - start_time

            if response.status_code < 400:
                return IntegrationTestResult(
                    test_name=f"{endpoint.name}_connectivity",
                    status="pass",
                    message=f"{endpoint.name} accessible via {perspective}",
                    duration=duration,
                    from_perspective=perspective,
                    details={
                        "url": test_url,
                        "status_code": response.status_code,
                        "response_time": duration,
                    },
                )
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_connectivity",
                status="fail",
                message=f"{endpoint.name} returned {response.status_code}",
                duration=duration,
                from_perspective=perspective,
                details={"url": test_url, "status_code": response.status_code},
            )

        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_connectivity",
                status="fail",
                message=f"{endpoint.name} connection timeout",
                duration=duration,
                from_perspective=perspective,
                details={"url": test_url, "error": "timeout"},
            )
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_connectivity",
                status="fail",
                message=f"{endpoint.name} connection failed: {e!s}",
                duration=duration,
                from_perspective=perspective,
                details={"url": test_url, "error": str(e)},
            )

    def test_api_endpoints(
        self, endpoint: ServiceEndpoint, perspective: str = "server"
    ) -> IntegrationTestResult:
        """Test API endpoint accessibility."""
        start_time = time.time()
        base_url = endpoint.internal_url if perspective == "server" else endpoint.external_url

        api_results = {}
        successful_apis = 0

        for api_path in endpoint.api_paths:
            try:
                url = urljoin(base_url, api_path)
                request_kwargs = {
                    "timeout": self.short_timeout,
                    "verify": False,
                    "allow_redirects": True,
                }

                # Add authentication if required
                if getattr(endpoint, "requires_auth", False):
                    auth_token = self.get_auth_token(endpoint)
                    if auth_token:
                        request_kwargs["headers"] = {"Authorization": f"Bearer {auth_token}"}

                response = requests.get(url, **request_kwargs)

                # Consider 200-299, 401 (auth required), and 403 (forbidden) as "reachable"
                reachable = response.status_code < 500 and response.status_code != 404
                api_results[api_path] = {
                    "status_code": response.status_code,
                    "reachable": reachable,
                }

                if reachable:
                    successful_apis += 1

            except Exception as e:
                api_results[api_path] = {"status_code": None, "reachable": False, "error": str(e)}

        duration = time.time() - start_time
        total_apis = len(endpoint.api_paths)

        if successful_apis == total_apis:
            status = "pass"
            message = f"All {total_apis} {endpoint.name} APIs reachable"
        elif successful_apis > 0:
            status = "warning"
            message = f"{successful_apis}/{total_apis} {endpoint.name} APIs reachable"
        else:
            status = "fail"
            message = f"No {endpoint.name} APIs reachable"

        return IntegrationTestResult(
            test_name=f"{endpoint.name}_api_endpoints",
            status=status,
            message=message,
            duration=duration,
            from_perspective=perspective,
            details={
                "api_results": api_results,
                "successful_apis": successful_apis,
                "total_apis": total_apis,
            },
        )

    def test_sso_integration_flow(self, endpoint: ServiceEndpoint) -> IntegrationTestResult:
        """Test SSO integration flow between services."""
        start_time = time.time()

        if not endpoint.sso_enabled:
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_sso_flow",
                status="skip",
                message=f"{endpoint.name} does not use SSO",
                duration=0.0,
            )

        try:
            # Test SSO discovery
            keycloak_endpoint = self.service_endpoints.get("keycloak")
            if not keycloak_endpoint:
                return IntegrationTestResult(
                    test_name=f"{endpoint.name}_sso_flow",
                    status="fail",
                    message="Keycloak endpoint not configured",
                    duration=time.time() - start_time,
                )

            # Check if service redirects to Keycloak for authentication
            protected_url = urljoin(endpoint.external_url, "/")

            session = requests.Session()
            response = session.get(
                protected_url, timeout=self.long_timeout, verify=False, allow_redirects=False
            )

            # Refined SSO detection logic to reduce false positives
            location = response.headers.get("location", "").lower()
            www_authenticate = response.headers.get("www-authenticate", "").lower()
            sso_location_keywords = ["keycloak", "sso", "login", "oauth", "openid"]
            is_sso_redirect = response.status_code in {302, 303, 307} and any(
                keyword in location for keyword in sso_location_keywords
            )
            is_sso_401 = response.status_code == 401 and any(
                keyword in www_authenticate for keyword in ["bearer", "keycloak", "oauth", "openid"]
            )
            sso_indicators = [is_sso_redirect, is_sso_401]

            duration = time.time() - start_time

            if any(sso_indicators):
                return IntegrationTestResult(
                    test_name=f"{endpoint.name}_sso_flow",
                    status="pass",
                    message=f"{endpoint.name} SSO integration working",
                    duration=duration,
                    details={
                        "status_code": response.status_code,
                        "location_header": response.headers.get("location", ""),
                        "sso_detected": True,
                    },
                )
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_sso_flow",
                status="warning",
                message=f"{endpoint.name} SSO flow unclear",
                duration=duration,
                details={
                    "status_code": response.status_code,
                    "location_header": response.headers.get("location", ""),
                    "sso_detected": False,
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(
                test_name=f"{endpoint.name}_sso_flow",
                status="fail",
                message=f"{endpoint.name} SSO test failed: {e!s}",
                duration=duration,
                details={"error": str(e)},
            )

    def test_ingress_routing(self) -> IntegrationTestResult:
        """Test ingress routing and external accessibility."""
        start_time = time.time()

        routing_results = {}
        successful_routes = 0

        for service_name, endpoint in self.service_endpoints.items():
            try:
                # Test external domain resolution
                domain = urlparse(endpoint.external_url).netloc

                # DNS resolution test
                try:
                    socket.gethostbyname(domain)
                    dns_ok = True
                except:
                    dns_ok = False

                # HTTP connectivity test
                try:
                    # Add a parameter to the method or use instance variable
                    verify_ssl = getattr(self, "verify_external_ssl", True)

                    response = requests.head(
                        endpoint.external_url,
                        timeout=self.short_timeout,
                        verify=verify_ssl,
                        allow_redirects=True,
                    )
                    http_ok = response.status_code < 500
                except:
                    http_ok = False

                routing_results[service_name] = {
                    "domain": domain,
                    "dns_resolution": dns_ok,
                    "http_reachable": http_ok,
                    "overall_ok": dns_ok and http_ok,
                }

                if dns_ok and http_ok:
                    successful_routes += 1

            except Exception as e:
                routing_results[service_name] = {
                    "domain": urlparse(endpoint.external_url).netloc,
                    "dns_resolution": False,
                    "http_reachable": False,
                    "overall_ok": False,
                    "error": str(e),
                }

        duration = time.time() - start_time
        total_services = len(self.service_endpoints)

        if successful_routes == total_services:
            status = "pass"
            message = f"All {total_services} ingress routes functional"
        elif successful_routes > 0:
            status = "warning"
            message = f"{successful_routes}/{total_services} ingress routes functional"
        else:
            status = "fail"
            message = "No ingress routes functional"

        return IntegrationTestResult(
            test_name="ingress_routing",
            status=status,
            message=message,
            duration=duration,
            details={
                "routing_results": routing_results,
                "successful_routes": successful_routes,
                "total_services": total_services,
            },
        )

    def test_service_to_service_communication(self) -> IntegrationTestResult:
        """Test internal service-to-service communication."""
        start_time = time.time()

        # Test communication patterns specific to homelab
        communication_tests = [
            ("prometheus", "grafana", "Prometheus -> Grafana data source"),
            ("keycloak", "gitlab", "Keycloak -> GitLab SSO"),
            ("keycloak", "grafana", "Keycloak -> Grafana SSO"),
        ]

        comm_results = {}
        successful_comms = 0

        for source, target, description in communication_tests:
            try:
                source_endpoint = self.service_endpoints.get(source)
                target_endpoint = self.service_endpoints.get(target)

                if not source_endpoint or not target_endpoint:
                    comm_results[description] = {
                        "status": "skip",
                        "reason": "Endpoint not configured",
                    }
                    continue

                # Simple connectivity test from source to target
                target_url = target_endpoint.internal_url

                # Use ping test as a proxy for network connectivity
                parsed_url = urlparse(target_url)
                target_host = parsed_url.netloc.split(":")[0]
                target_port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    tcp_result = sock.connect_ex((target_host, target_port))
                    sock.close()
                except Exception:
                    tcp_result = 1

                connectivity_ok = tcp_result == 0

                comm_results[description] = {
                    "status": "pass" if connectivity_ok else "fail",
                    "target_host": target_host,
                    "target_port": target_port,
                    "tcp_connection_success": connectivity_ok,
                }

                if connectivity_ok:
                    successful_comms += 1

            except Exception as e:
                comm_results[description] = {"status": "fail", "error": str(e)}

        duration = time.time() - start_time
        total_tests = len(communication_tests)

        if successful_comms == total_tests:
            status = "pass"
            message = f"All {total_tests} service communications working"
        elif successful_comms > 0:
            status = "warning"
            message = f"{successful_comms}/{total_tests} service communications working"
        else:
            status = "fail"
            message = "Service-to-service communication issues"

        return IntegrationTestResult(
            test_name="service_to_service_communication",
            status=status,
            message=message,
            duration=duration,
            details={
                "communication_results": comm_results,
                "successful_communications": successful_comms,
                "total_tests": total_tests,
            },
        )

    def get_auth_token(self, endpoint: ServiceEndpoint) -> str | None:
        """Get authentication token for the endpoint.

        Override this method to provide actual authentication logic.
        """
        msg = (
            "Authentication required but get_auth_token() not implemented. "
            "Override this method or set auth tokens via environment variables."
        )
        raise NotImplementedError(msg)

    @classmethod
    def get_service_names(cls) -> list[str]:
        """Get list of available service names."""
        return ["gitlab", "keycloak", "prometheus", "grafana"]

    def run_comprehensive_integration_tests(
        self, include_workstation_tests: bool = False
    ) -> list[IntegrationTestResult]:
        """Run all integration tests."""
        self.logger.info("Starting comprehensive integration testing...")

        results = []

        # Run foundational checks first if modules available
        if self.infra_monitor:
            self.logger.info("Running infrastructure health check...")
            cluster_health = self.infra_monitor.get_cluster_health()
            if cluster_health.cluster_status == "critical":
                self.logger.warning("Infrastructure health critical - some tests may fail")

        # Test service connectivity from server perspective
        for endpoint in self.service_endpoints.values():
            # Gather all tests for current endpoint
            endpoint_tests = [
                self.test_service_connectivity(endpoint, "server"),
                self.test_api_endpoints(endpoint, "server"),
            ]

            # Add workstation perspective tests if requested
            if include_workstation_tests:
                endpoint_tests.extend(
                    [
                        self.test_service_connectivity(endpoint, "workstation"),
                        self.test_api_endpoints(endpoint, "workstation"),
                    ]
                )

            # Add SSO test for this endpoint
            endpoint_tests.append(self.test_sso_integration_flow(endpoint))

            # Add all endpoint tests
            results.extend(endpoint_tests)

        # Add infrastructure-level tests
        results.extend([self.test_ingress_routing(), self.test_service_to_service_communication()])

        # Log summary
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)

        self.logger.info(f"Integration testing complete: {passed_tests}/{total_tests} tests passed")

        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Run comprehensive integration tests")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    parser.add_argument(
        "--include-workstation", action="store_true", help="Include workstation perspective tests"
    )
    parser.add_argument(
        "--service",
        choices=IntegrationConnectivityTester.get_service_names(),
        help="Test specific service only",
    )

    args = parser.parse_args()

    tester = IntegrationConnectivityTester(
        kubeconfig_path=args.kubeconfig, log_level=args.log_level
    )

    if args.service:
        # Test specific service
        endpoint = tester.service_endpoints[args.service]
        results = [
            tester.test_service_connectivity(endpoint, "server"),
            tester.test_api_endpoints(endpoint, "server"),
            tester.test_sso_integration_flow(endpoint),
        ]
    else:
        # Run comprehensive tests
        results = tester.run_comprehensive_integration_tests(args.include_workstation)

    # Display results
    print("\n🔗 Integration & Connectivity Test Results:")

    passed_tests = sum(1 for r in results if r.passed)
    failed_tests = sum(1 for r in results if r.status == "fail")
    warning_tests = sum(1 for r in results if r.status == "warning")
    skipped_tests = sum(1 for r in results if r.status == "skip")
    len(results)

    print(f"Results: {passed_tests}✅ {failed_tests}❌ {warning_tests}⚠️ {skipped_tests}⏭️")

    for result in results:
        icon = (
            "✅"
            if result.passed
            else "❌"
            if result.status == "fail"
            else "⚠️"
            if result.status == "warning"
            else "⏭️"
        )
        perspective_info = (
            f" ({result.from_perspective})"
            if hasattr(result, "from_perspective") and result.from_perspective != "server"
            else ""
        )
        print(f"\n{icon} {result.test_name.replace('_', ' ').title()}{perspective_info}:")
        print(f"  {result.message}")
        if result.duration > 0:
            print(f"  Duration: {result.duration:.2f}s")

    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
