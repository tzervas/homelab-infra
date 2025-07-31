#!/usr/bin/env python3
"""
TLS Configuration Validation Script
Validates TLS configurations across the homelab infrastructure for security compliance.
"""

import json
import logging
import socket
import ssl
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import requests
import urllib3
import yaml


# Configure logging with user rule compliance
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/tls-validation.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Disable SSL warnings for testing purposes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TLSCompliance(Enum):
    """TLS compliance levels."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAIL = "fail"


@dataclass
class TLSConfig:
    """TLS configuration data class."""

    host: str
    port: int
    protocol_version: str
    cipher_suite: str
    key_exchange: str
    certificate_valid: bool
    certificate_chain_valid: bool
    hsts_enabled: bool
    compression_disabled: bool
    session_resumption: str
    forward_secrecy: bool
    compliance_level: TLSCompliance
    vulnerabilities: list[str]
    recommendations: list[str]


@dataclass
class ValidationResult:
    """Validation result data class."""

    target: str
    passed: bool
    compliance_level: TLSCompliance
    issues: list[str]
    recommendations: list[str]
    raw_data: dict[str, Any]


class TLSValidator:
    """TLS configuration validator class."""

    def __init__(self, config_file: str = "/etc/security/tls-validation-config.yaml") -> None:
        """Initialize the TLS validator."""
        self.config = self._load_config(config_file)
        self.validation_results: list[ValidationResult] = []

        # TLS security requirements
        self.min_tls_version = self.config.get("min_tls_version", "TLSv1.2")
        self.allowed_cipher_suites = self.config.get(
            "allowed_cipher_suites",
            [
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-RSA-CHACHA20-POLY1305",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256",
            ],
        )
        self.weak_cipher_suites = self.config.get(
            "weak_cipher_suites",
            [
                "DES",
                "RC4",
                "MD5",
                "SHA1",
                "NULL",
                "anon",
                "EXPORT",
            ],
        )

    def _load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {
                "min_tls_version": "TLSv1.2",
                "require_forward_secrecy": True,
                "require_hsts": True,
                "max_certificate_age_days": 365,
                "targets": {
                    "kubernetes_services": True,
                    "ingress_endpoints": True,
                    "external_services": True,
                },
            }

    def run_kubectl_command(self, args: list[str]) -> tuple[str, int]:
        """Run kubectl command and return output and exit code."""
        try:
            cmd = ["kubectl", *args]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return result.stdout, result.returncode
        except subprocess.TimeoutExpired:
            logger.exception(f"kubectl command timed out: {' '.join(args)}")
            return "", 1
        except Exception as e:
            logger.exception(f"Error running kubectl command: {e}")
            return "", 1

    def validate_kubernetes_tls(self) -> list[ValidationResult]:
        """Validate TLS configurations in Kubernetes."""
        results = []

        # Get all ingresses
        output, exit_code = self.run_kubectl_command(
            [
                "get",
                "ingress",
                "-A",
                "-o",
                "json",
            ],
        )

        if exit_code == 0:
            try:
                ingress_data = json.loads(output)
                for item in ingress_data.get("items", []):
                    ingress_results = self._validate_ingress_tls(item)
                    results.extend(ingress_results)
            except json.JSONDecodeError as e:
                logger.exception(f"Failed to parse ingress JSON: {e}")

        # Get all services with LoadBalancer type
        output, exit_code = self.run_kubectl_command(
            [
                "get",
                "services",
                "-A",
                "-o",
                "json",
            ],
        )

        if exit_code == 0:
            try:
                service_data = json.loads(output)
                for item in service_data.get("items", []):
                    if item.get("spec", {}).get("type") == "LoadBalancer":
                        service_results = self._validate_service_tls(item)
                        results.extend(service_results)
            except json.JSONDecodeError as e:
                logger.exception(f"Failed to parse service JSON: {e}")

        return results

    def _validate_ingress_tls(self, ingress_data: dict) -> list[ValidationResult]:
        """Validate TLS configuration for an ingress."""
        results = []

        metadata = ingress_data.get("metadata", {})
        spec = ingress_data.get("spec", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")

        # Check TLS configuration
        tls_configs = spec.get("tls", [])
        spec.get("rules", [])

        if not tls_configs:
            results.append(
                ValidationResult(
                    target=f"ingress/{namespace}/{name}",
                    passed=False,
                    compliance_level=TLSCompliance.FAIL,
                    issues=["No TLS configuration found"],
                    recommendations=["Configure TLS for all ingress rules"],
                    raw_data=ingress_data,
                ),
            )
            return results

        # Validate each TLS configuration
        for tls_config in tls_configs:
            hosts = tls_config.get("hosts", [])
            tls_config.get("secretName", "")

            for host in hosts:
                if host:
                    result = self._validate_endpoint_tls(host, 443)
                    result.target = f"ingress/{namespace}/{name}/{host}"
                    results.append(result)

        return results

    def _validate_service_tls(self, service_data: dict) -> list[ValidationResult]:
        """Validate TLS configuration for a LoadBalancer service."""
        results = []

        metadata = service_data.get("metadata", {})
        spec = service_data.get("spec", {})
        status = service_data.get("status", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")

        # Get external IP/hostname
        load_balancer = status.get("loadBalancer", {})
        ingress_list = load_balancer.get("ingress", [])

        if not ingress_list:
            return results

        ports = spec.get("ports", [])
        tls_ports = [p for p in ports if p.get("port") in [443, 8443, 9443]]

        for ingress_info in ingress_list:
            ip = ingress_info.get("ip")
            hostname = ingress_info.get("hostname")
            target_host = hostname or ip

            if target_host:
                for port_info in tls_ports:
                    port = port_info.get("port", 443)
                    result = self._validate_endpoint_tls(target_host, port)
                    result.target = f"service/{namespace}/{name}/{target_host}:{port}"
                    results.append(result)

        return results

    def _validate_endpoint_tls(self, hostname: str, port: int = 443) -> ValidationResult:
        """Validate TLS configuration for a specific endpoint."""
        issues = []
        recommendations = []
        vulnerabilities = []

        try:
            # Test TLS connection
            tls_info = self._get_tls_info(hostname, port)

            if not tls_info:
                return ValidationResult(
                    target=f"{hostname}:{port}",
                    passed=False,
                    compliance_level=TLSCompliance.FAIL,
                    issues=["Failed to establish TLS connection"],
                    recommendations=["Check TLS configuration and certificate validity"],
                    raw_data={},
                )

            # Validate TLS version
            tls_version = tls_info.get("version", "")
            if not self._is_tls_version_acceptable(tls_version):
                issues.append(f"Weak TLS version: {tls_version}")
                recommendations.append(f"Upgrade to {self.min_tls_version} or higher")

            # Validate cipher suite
            cipher_suite = tls_info.get("cipher", "")
            if not self._is_cipher_suite_secure(cipher_suite):
                issues.append(f"Weak cipher suite: {cipher_suite}")
                recommendations.append("Use strong cipher suites with forward secrecy")
                vulnerabilities.append("WEAK_CIPHER")

            # Check for forward secrecy
            if not self._has_forward_secrecy(cipher_suite):
                issues.append("No forward secrecy")
                recommendations.append("Configure ECDHE or DHE key exchange")
                vulnerabilities.append("NO_FORWARD_SECRECY")

            # Validate certificate
            cert_issues = self._validate_certificate(tls_info.get("certificate"))
            issues.extend(cert_issues)

            # Test for common vulnerabilities
            vuln_results = self._test_vulnerabilities(hostname, port)
            vulnerabilities.extend(vuln_results)

            # Check HTTP security headers
            if port in [80, 443, 8080, 8443]:
                header_issues = self._check_security_headers(hostname, port)
                issues.extend(header_issues)

            # Determine compliance level
            compliance_level = self._calculate_compliance_level(issues, vulnerabilities)

            return ValidationResult(
                target=f"{hostname}:{port}",
                passed=len(issues) == 0,
                compliance_level=compliance_level,
                issues=issues,
                recommendations=recommendations,
                raw_data=tls_info,
            )

        except Exception as e:
            logger.exception(f"Error validating {hostname}:{port}: {e}")
            return ValidationResult(
                target=f"{hostname}:{port}",
                passed=False,
                compliance_level=TLSCompliance.FAIL,
                issues=[f"Validation error: {e!s}"],
                recommendations=["Check connectivity and TLS configuration"],
                raw_data={},
            )

    def _get_tls_info(self, hostname: str, port: int) -> dict[str, Any] | None:
        """Get TLS information for a host."""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    cipher = ssock.cipher()
                    version = ssock.version()

                    return {
                        "version": version,
                        "cipher": cipher[0] if cipher else "",
                        "cipher_suite": cipher,
                        "certificate": cert,
                        "protocol": ssock.version(),
                        "server_hostname": hostname,
                        "port": port,
                    }
        except Exception as e:
            logger.exception(f"Failed to get TLS info for {hostname}:{port}: {e}")
            return None

    def _is_tls_version_acceptable(self, version: str) -> bool:
        """Check if TLS version meets minimum requirements."""
        version_priority = {
            "TLSv1.3": 4,
            "TLSv1.2": 3,
            "TLSv1.1": 2,
            "TLSv1": 1,
            "SSLv3": 0,
            "SSLv2": 0,
        }

        min_priority = version_priority.get(self.min_tls_version, 3)
        current_priority = version_priority.get(version, 0)

        return current_priority >= min_priority

    def _is_cipher_suite_secure(self, cipher_suite: str) -> bool:
        """Check if cipher suite is secure."""
        if not cipher_suite:
            return False

        # Check for weak ciphers
        for weak_cipher in self.weak_cipher_suites:
            if weak_cipher.upper() in cipher_suite.upper():
                return False

        # Prefer AEAD ciphers
        secure_patterns = ["GCM", "CHACHA20", "POLY1305"]
        return any(pattern in cipher_suite.upper() for pattern in secure_patterns)

    def _has_forward_secrecy(self, cipher_suite: str) -> bool:
        """Check if cipher suite provides forward secrecy."""
        if not cipher_suite:
            return False

        fs_patterns = ["ECDHE", "DHE"]
        return any(pattern in cipher_suite.upper() for pattern in fs_patterns)

    def _validate_certificate(self, cert_data: bytes) -> list[str]:
        """Validate certificate."""
        issues = []

        if not cert_data:
            issues.append("No certificate data available")
            return issues

        try:
            from datetime import datetime, timedelta

            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            cert = x509.load_der_x509_certificate(cert_data, default_backend())

            # Check expiration
            now = datetime.now()
            if cert.not_valid_after < now:
                issues.append("Certificate has expired")
            elif cert.not_valid_after < now + timedelta(days=30):
                issues.append("Certificate expires within 30 days")

            # Check if not yet valid
            if cert.not_valid_before > now:
                issues.append("Certificate is not yet valid")

            # Check key size
            public_key = cert.public_key()
            if hasattr(public_key, "key_size"):
                if public_key.key_size < 2048:
                    issues.append(f"Weak RSA key size: {public_key.key_size} bits")

            # Check signature algorithm
            sig_algo = cert.signature_algorithm_oid._name
            if "sha1" in sig_algo.lower() or "md5" in sig_algo.lower():
                issues.append(f"Weak signature algorithm: {sig_algo}")

        except Exception as e:
            issues.append(f"Certificate validation error: {e!s}")

        return issues

    def _test_vulnerabilities(self, hostname: str, port: int) -> list[str]:
        """Test for common TLS vulnerabilities."""
        vulnerabilities = []

        try:
            # Test for weak protocol support
            weak_protocols = ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]
            for protocol in weak_protocols:
                if self._test_protocol_support(hostname, port, protocol):
                    vulnerabilities.append(f"WEAK_PROTOCOL_{protocol}")

            # Test for compression support (CRIME vulnerability)
            if self._test_compression_support(hostname, port):
                vulnerabilities.append("TLS_COMPRESSION_ENABLED")

            # Test for heartbleed (if OpenSSL)
            if self._test_heartbleed(hostname, port):
                vulnerabilities.append("HEARTBLEED")

        except Exception as e:
            logger.exception(f"Error testing vulnerabilities for {hostname}:{port}: {e}")

        return vulnerabilities

    def _test_protocol_support(self, hostname: str, port: int, protocol: str) -> bool:
        """Test if a specific protocol is supported."""
        try:
            context = ssl.SSLContext()

            # Set protocol version
            if protocol == "SSLv2":
                return False  # SSLv2 not supported in Python
            if protocol == "SSLv3":
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
            elif protocol == "TLSv1":
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            elif protocol == "TLSv1.1":
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
            else:
                return False

            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock) as ssock:
                    return ssock.version() == protocol

        except Exception:
            return False

    def _test_compression_support(self, hostname: str, port: int) -> bool:
        """Test if TLS compression is enabled."""
        try:
            # Use openssl command to test compression
            cmd = [
                "openssl",
                "s_client",
                "-connect",
                f"{hostname}:{port}",
                "-compression",
                "-brief",
            ]
            result = subprocess.run(
                cmd,
                input="",
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            return "Compression: " in result.stdout and "NONE" not in result.stdout

        except Exception:
            return False

    def _test_heartbleed(self, hostname: str, port: int) -> bool:
        """Test for Heartbleed vulnerability."""
        # This is a simplified test - in practice, you'd use specialized tools
        try:
            # Use openssl to check for heartbeat extension
            cmd = [
                "openssl",
                "s_client",
                "-connect",
                f"{hostname}:{port}",
                "-tlsextdebug",
                "-msg",
            ]
            result = subprocess.run(
                cmd,
                input="",
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            # Look for heartbeat extension in output
            return "heartbeat" in result.stderr.lower()

        except Exception:
            return False

    def _check_security_headers(self, hostname: str, port: int) -> list[str]:
        """Check HTTP security headers."""
        issues = []

        try:
            # Test HTTPS connection
            url = f"https://{hostname}:{port}" if port != 443 else f"https://{hostname}"
            response = requests.get(url, timeout=10, verify=False)

            headers = response.headers

            # Check HSTS
            if "strict-transport-security" not in headers:
                issues.append("Missing HSTS header")
            else:
                hsts = headers["strict-transport-security"]
                if "max-age" not in hsts:
                    issues.append("HSTS header missing max-age")
                elif "includeSubDomains" not in hsts:
                    issues.append("HSTS header should include subdomains")

            # Check other security headers
            security_headers = {
                "x-frame-options": "Missing X-Frame-Options header",
                "x-content-type-options": "Missing X-Content-Type-Options header",
                "x-xss-protection": "Missing X-XSS-Protection header",
                "content-security-policy": "Missing Content-Security-Policy header",
            }

            for header, message in security_headers.items():
                if header not in headers:
                    issues.append(message)

        except Exception as e:
            logger.exception(f"Error checking security headers for {hostname}:{port}: {e}")

        return issues

    def _calculate_compliance_level(
        self,
        issues: list[str],
        vulnerabilities: list[str],
    ) -> TLSCompliance:
        """Calculate overall compliance level."""
        if len(vulnerabilities) > 0:
            return TLSCompliance.FAIL

        if len(issues) == 0:
            return TLSCompliance.EXCELLENT
        if len(issues) <= 2:
            return TLSCompliance.GOOD
        if len(issues) <= 4:
            return TLSCompliance.ACCEPTABLE
        return TLSCompliance.POOR

    def validate_external_endpoints(self) -> list[ValidationResult]:
        """Validate TLS for external endpoints."""
        results = []

        external_endpoints = self.config.get("external_endpoints", [])

        for endpoint in external_endpoints:
            if isinstance(endpoint, str):
                # Parse URL
                parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
                hostname = parsed.hostname
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
            elif isinstance(endpoint, dict):
                hostname = endpoint.get("hostname")
                port = endpoint.get("port", 443)
            else:
                continue

            if hostname:
                result = self._validate_endpoint_tls(hostname, port)
                results.append(result)

        return results

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive TLS validation report."""
        total_tests = len(self.validation_results)
        passed_tests = len([r for r in self.validation_results if r.passed])

        compliance_counts = {}
        for level in TLSCompliance:
            compliance_counts[level.value] = len(
                [r for r in self.validation_results if r.compliance_level == level],
            )

        # Group issues by type
        issue_counts = {}
        all_issues = []
        for result in self.validation_results:
            all_issues.extend(result.issues)

        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            },
            "compliance_distribution": compliance_counts,
            "common_issues": dict(
                sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            ),
            "detailed_results": [
                {
                    "target": result.target,
                    "passed": result.passed,
                    "compliance_level": result.compliance_level.value,
                    "issues": result.issues,
                    "recommendations": result.recommendations,
                }
                for result in self.validation_results
            ],
        }

    def run_validation(self) -> None:
        """Run comprehensive TLS validation."""
        logger.info("Starting TLS configuration validation")

        # Validate Kubernetes TLS configurations
        if self.config.get("targets", {}).get("kubernetes_services", True):
            k8s_results = self.validate_kubernetes_tls()
            self.validation_results.extend(k8s_results)
            logger.info(f"Validated {len(k8s_results)} Kubernetes TLS configurations")

        # Validate external endpoints
        if self.config.get("targets", {}).get("external_services", True):
            external_results = self.validate_external_endpoints()
            self.validation_results.extend(external_results)
            logger.info(f"Validated {len(external_results)} external TLS endpoints")

        # Generate and log report
        report = self.generate_report()

        logger.info("TLS Validation Summary:")
        logger.info(f"  Total tests: {report['summary']['total_tests']}")
        logger.info(f"  Passed: {report['summary']['passed_tests']}")
        logger.info(f"  Failed: {report['summary']['failed_tests']}")
        logger.info(f"  Pass rate: {report['summary']['pass_rate']:.1f}%")

        # Log compliance distribution
        for level, count in report["compliance_distribution"].items():
            if count > 0:
                logger.info(f"  {level.upper()}: {count}")

        # Log failed validations
        failed_results = [r for r in self.validation_results if not r.passed]
        if failed_results:
            logger.warning("Failed TLS validations:")
            for result in failed_results:
                logger.warning(f"  {result.target}: {', '.join(result.issues)}")

        logger.info("TLS configuration validation completed")


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="TLS Configuration Validation")
    parser.add_argument(
        "--config",
        default="/etc/security/tls-validation-config.yaml",
        help="Configuration file path",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output", "-o", help="Output file for JSON report")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        validator = TLSValidator(args.config)
        validator.run_validation()

        if args.output:
            report = validator.generate_report()
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {args.output}")

    except Exception as e:
        logger.exception(f"TLS validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
