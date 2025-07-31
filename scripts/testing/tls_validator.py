#!/usr/bin/env python3
"""TLS/mTLS Security Validation Module for Homelab Infrastructure Testing Framework.

This module provides comprehensive validation of TLS/mTLS configurations
including certificate validation, cipher suite analysis, and protocol security.
"""

import logging
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


try:
    import requests
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


@dataclass
class CertificateInfo:
    """Information about a TLS certificate."""

    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    signature_algorithm: str
    key_size: int
    san_names: list[str] = field(default_factory=list)
    is_self_signed: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        return datetime.now(timezone.utc) > self.not_after

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until certificate expires."""
        delta = self.not_after - datetime.now(timezone.utc)
        return max(0, delta.days)

    @property
    def is_valid_key_size(self) -> bool:
        """Check if key size meets security standards."""
        return self.key_size >= 2048


@dataclass
class TLSValidationResult:
    """Result of TLS/mTLS validation."""

    endpoint: str
    component: str
    is_secure: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    certificate_info: CertificateInfo | None = None
    timestamp: float = field(default_factory=time.time)

    @property
    def security_level(self) -> str:
        """Determine security level based on validation results."""
        if not self.is_secure:
            return "insecure"

        if self.certificate_info:
            if self.certificate_info.days_until_expiry < 30:
                return "warning"
            if not self.certificate_info.is_valid_key_size:
                return "warning"

        return "secure"


class TLSSecurityValidator:
    """Validates TLS/mTLS configurations and certificate security."""

    def __init__(self, log_level: str = "INFO") -> None:
        """Initialize the TLS validator."""
        self.logger = self._setup_logging(log_level)

        # Common homelab endpoints to test
        self.default_endpoints = {
            "grafana": "https://grafana.homelab.local",
            "prometheus": "https://prometheus.homelab.local",
            "longhorn": "https://longhorn.homelab.local",
            "kubernetes-api": "https://kubernetes.default.svc.cluster.local:443",
        }

        # Security requirements
        self.min_tls_version = ssl.TLSVersion.TLSv1_2
        self.forbidden_ciphers = [
            "DES",
            "3DES",
            "RC4",
            "MD5",
            "SHA1",
        ]
        self.required_cipher_suites = [
            "ECDHE",
            "AES",
            "GCM",
        ]

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

    def _parse_certificate(self, cert_der: bytes) -> CertificateInfo | None:
        """Parse a DER-encoded certificate."""
        if not CRYPTO_AVAILABLE:
            self.logger.warning(
                "Cryptography library not available for detailed certificate parsing",
            )
            return None

        try:
            cert = x509.load_der_x509_certificate(cert_der, default_backend())

            # Extract subject and issuer
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()

            # Extract SAN names
            san_names = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
                )
                san_names = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass

            # Determine key size
            public_key = cert.public_key()
            if hasattr(public_key, "key_size"):
                key_size = public_key.key_size
            else:
                key_size = 0  # Unknown key size

            return CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=str(cert.serial_number),
                not_before=cert.not_valid_before.replace(tzinfo=timezone.utc),
                not_after=cert.not_valid_after.replace(tzinfo=timezone.utc),
                signature_algorithm=cert.signature_algorithm_oid._name,
                key_size=key_size,
                san_names=san_names,
                is_self_signed=(subject == issuer),
            )

        except Exception as e:
            self.logger.exception(f"Failed to parse certificate: {e}")
            return None

    def _get_ssl_info(
        self,
        hostname: str,
        port: int,
        timeout: int = 10,
    ) -> tuple[ssl.SSLSocket | None, CertificateInfo | None]:
        """Get SSL information for a hostname and port."""
        try:
            # Create SSL context with security settings
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # We'll validate manually

            # Connect to the server
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # Get certificate
                    cert_der = ssock.getpeercert_chain()[0].to_bytes()
                    cert_info = self._parse_certificate(cert_der)

                    return ssock, cert_info

        except Exception as e:
            self.logger.exception(f"Failed to get SSL info for {hostname}:{port} - {e}")
            return None, None

    def validate_endpoint_tls(self, endpoint: str) -> TLSValidationResult:
        """Validate TLS configuration for a specific endpoint."""
        parsed_url = urlparse(endpoint)
        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)

        if parsed_url.scheme != "https":
            return TLSValidationResult(
                endpoint=endpoint,
                component="tls_endpoint",
                is_secure=False,
                message="Endpoint is not using HTTPS",
                details={"scheme": parsed_url.scheme},
            )

        self.logger.info(f"Validating TLS for {hostname}:{port}")

        ssock, cert_info = self._get_ssl_info(hostname, port)

        if not ssock or not cert_info:
            return TLSValidationResult(
                endpoint=endpoint,
                component="tls_endpoint",
                is_secure=False,
                message="Failed to establish TLS connection or retrieve certificate",
            )

        # Analyze TLS configuration
        issues = []
        warnings = []

        # Check certificate validity
        if cert_info.is_expired:
            issues.append("Certificate is expired")
        elif cert_info.days_until_expiry < 30:
            warnings.append(f"Certificate expires in {cert_info.days_until_expiry} days")

        # Check key size
        if not cert_info.is_valid_key_size:
            issues.append(f"Key size {cert_info.key_size} is below minimum 2048 bits")

        # Check if self-signed
        if cert_info.is_self_signed:
            warnings.append("Certificate is self-signed")

        # Check cipher suite
        cipher = ssock.cipher()
        if cipher:
            cipher_name = cipher[0]
            # Check for forbidden ciphers
            for forbidden in self.forbidden_ciphers:
                if forbidden in cipher_name:
                    issues.append(f"Using forbidden cipher: {cipher_name}")

            # Check for required cipher components
            missing_components = []
            for required in self.required_cipher_suites:
                if required not in cipher_name:
                    missing_components.append(required)

            if missing_components:
                warnings.append(
                    f"Cipher missing recommended components: {', '.join(missing_components)}",
                )

        # Check TLS version
        tls_version = ssock.version()
        if tls_version and tls_version < "TLSv1.2":
            issues.append(f"Using outdated TLS version: {tls_version}")

        # Determine overall security status
        is_secure = len(issues) == 0

        if issues:
            message = f"TLS security issues: {'; '.join(issues)}"
        elif warnings:
            message = f"TLS configuration has warnings: {'; '.join(warnings)}"
        else:
            message = "TLS configuration is secure"

        return TLSValidationResult(
            endpoint=endpoint,
            component="tls_endpoint",
            is_secure=is_secure,
            message=message,
            certificate_info=cert_info,
            details={
                "tls_version": tls_version,
                "cipher": cipher,
                "issues": issues,
                "warnings": warnings,
                "hostname": hostname,
                "port": port,
            },
        )

    def validate_kubernetes_tls(self) -> list[TLSValidationResult]:
        """Validate TLS configuration for Kubernetes components."""
        results = []

        # Test Kubernetes API server
        try:
            # Try to get cluster info to test TLS
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                # Extract API server URL from cluster info
                lines = result.stdout.split("\n")
                api_url = None
                for line in lines:
                    if "Kubernetes control plane" in line or "Kubernetes master" in line:
                        parts = line.split()
                        for part in parts:
                            if part.startswith("https://"):
                                api_url = part
                                break
                        break

                if api_url:
                    result = self.validate_endpoint_tls(api_url)
                    result.component = "kubernetes_api"
                    results.append(result)
                else:
                    results.append(
                        TLSValidationResult(
                            endpoint="kubernetes-api",
                            component="kubernetes_api",
                            is_secure=False,
                            message="Could not extract Kubernetes API URL",
                        ),
                    )
            else:
                results.append(
                    TLSValidationResult(
                        endpoint="kubernetes-api",
                        component="kubernetes_api",
                        is_secure=False,
                        message="Cannot access Kubernetes cluster",
                        details={"error": result.stderr},
                    ),
                )

        except Exception as e:
            results.append(
                TLSValidationResult(
                    endpoint="kubernetes-api",
                    component="kubernetes_api",
                    is_secure=False,
                    message=f"Failed to validate Kubernetes TLS: {e}",
                ),
            )

        return results

    def validate_ingress_tls(self) -> list[TLSValidationResult]:
        """Validate TLS configuration for ingress endpoints."""
        results = []

        try:
            # Get ingress resources
            result = subprocess.run(
                ["kubectl", "get", "ingress", "-A", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                results.append(
                    TLSValidationResult(
                        endpoint="ingress",
                        component="ingress_tls",
                        is_secure=False,
                        message="Failed to retrieve ingress resources",
                        details={"error": result.stderr},
                    ),
                )
                return results

            import json

            ingress_data = json.loads(result.stdout)

            for ingress in ingress_data.get("items", []):
                name = ingress.get("metadata", {}).get("name", "unknown")
                namespace = ingress.get("metadata", {}).get("namespace", "default")

                # Check for TLS configuration
                spec = ingress.get("spec", {})
                tls_configs = spec.get("tls", [])

                if not tls_configs:
                    results.append(
                        TLSValidationResult(
                            endpoint=f"{namespace}/{name}",
                            component="ingress_tls",
                            is_secure=False,
                            message="Ingress has no TLS configuration",
                            details={"ingress": name, "namespace": namespace},
                        ),
                    )
                    continue

                # Validate each TLS host
                for tls_config in tls_configs:
                    hosts = tls_config.get("hosts", [])
                    secret_name = tls_config.get("secretName", "")

                    for host in hosts:
                        # Try to validate the host if accessible
                        endpoint = f"https://{host}"
                        validation_result = self.validate_endpoint_tls(endpoint)
                        validation_result.component = "ingress_tls"
                        validation_result.details.update(
                            {
                                "ingress": name,
                                "namespace": namespace,
                                "secret_name": secret_name,
                            },
                        )
                        results.append(validation_result)

        except Exception as e:
            results.append(
                TLSValidationResult(
                    endpoint="ingress",
                    component="ingress_tls",
                    is_secure=False,
                    message=f"Failed to validate ingress TLS: {e}",
                ),
            )

        return results

    def run_comprehensive_tls_validation(self) -> list[TLSValidationResult]:
        """Run comprehensive TLS/mTLS validation."""
        self.logger.info("Starting comprehensive TLS/mTLS validation...")

        results = []

        # Validate default endpoints
        for name, endpoint in self.default_endpoints.items():
            try:
                result = self.validate_endpoint_tls(endpoint)
                result.component = f"tls_{name}"
                results.append(result)
            except Exception as e:
                results.append(
                    TLSValidationResult(
                        endpoint=endpoint,
                        component=f"tls_{name}",
                        is_secure=False,
                        message=f"Failed to validate {name}: {e}",
                    ),
                )

        # Validate Kubernetes TLS
        results.extend(self.validate_kubernetes_tls())

        # Validate Ingress TLS
        results.extend(self.validate_ingress_tls())

        self.logger.info(f"TLS validation completed with {len(results)} checks")
        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate TLS/mTLS security for homelab infrastructure",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--endpoint", help="Specific endpoint to validate")
    parser.add_argument(
        "--component",
        choices=["kubernetes", "ingress"],
        help="Validate specific component only",
    )

    args = parser.parse_args()

    if not CRYPTO_AVAILABLE:
        print(
            "Warning: cryptography library not available. Install with: pip install cryptography requests",
        )
        print("Some functionality may be limited.")

    validator = TLSSecurityValidator(log_level=args.log_level)

    if args.endpoint:
        # Validate specific endpoint
        result = validator.validate_endpoint_tls(args.endpoint)

        print(f"\n🔐 TLS Validation for {args.endpoint}:")
        print(f"Status: {'✅ SECURE' if result.is_secure else '❌ INSECURE'}")
        print(f"Message: {result.message}")

        if result.certificate_info:
            cert = result.certificate_info
            print("\n📜 Certificate Details:")
            print(f"  Subject: {cert.subject}")
            print(f"  Issuer: {cert.issuer}")
            print(f"  Valid until: {cert.not_after}")
            print(f"  Days until expiry: {cert.days_until_expiry}")
            print(f"  Key size: {cert.key_size} bits")
            print(f"  Self-signed: {cert.is_self_signed}")

            if cert.san_names:
                print(f"  SAN names: {', '.join(cert.san_names)}")

        return 0 if result.is_secure else 1

    if args.component:
        # Validate specific component
        if args.component == "kubernetes":
            results = validator.validate_kubernetes_tls()
        elif args.component == "ingress":
            results = validator.validate_ingress_tls()
    else:
        # Run comprehensive validation
        results = validator.run_comprehensive_tls_validation()

    print("\n🔐 TLS/mTLS Security Validation Report:")
    print("=" * 50)

    total_checks = len(results)
    secure_checks = sum(1 for r in results if r.is_secure)

    for result in results:
        security_level = result.security_level
        if security_level == "secure":
            icon = "✅"
        elif security_level == "warning":
            icon = "⚠️"
        else:
            icon = "❌"

        print(f"  {icon} {result.component} ({result.endpoint}): {result.message}")

        if result.certificate_info and result.certificate_info.days_until_expiry < 90:
            print(f"    📅 Certificate expires in {result.certificate_info.days_until_expiry} days")

    print(f"\nOverall: {secure_checks}/{total_checks} endpoints secure")

    return 0 if secure_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
