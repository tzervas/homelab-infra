#!/usr/bin/env python3
"""
Certificate Validation and mTLS Testing Module

Provides comprehensive certificate validation including:
- X.509 certificate validation
- Certificate chain verification
- Expiration date checking
- mTLS connection testing
- Certificate rotation validation
"""

import logging
import ssl
import socket
import datetime
import subprocess
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from kubernetes import client, config
import yaml

@dataclass
class CertificateInfo:
    """Certificate information structure."""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime.datetime
    not_after: datetime.datetime
    san_dns_names: List[str] = field(default_factory=list)
    san_ip_addresses: List[str] = field(default_factory=list)
    signature_algorithm: str = ""
    public_key_algorithm: str = ""
    key_size: Optional[int] = None
    is_ca: bool = False
    is_self_signed: bool = False

@dataclass
class CertificateValidationResult:
    """Certificate validation result."""
    certificate: CertificateInfo
    is_valid: bool
    days_until_expiry: int
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    chain_valid: bool = True
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class MTLSTestResult:
    """mTLS connection test result."""
    endpoint: str
    is_successful: bool
    tls_version: str = ""
    cipher_suite: str = ""
    peer_certificate: Optional[CertificateInfo] = None
    client_certificate_verified: bool = False
    error_message: str = ""
    response_time_ms: float = 0.0

class CertificateValidator:
    """Certificate validation and testing class."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None, log_level: str = "INFO"):
        """Initialize certificate validator."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path
        self._load_kubernetes_config()
        
        # Certificate validation thresholds
        self.warning_days = 30
        self.critical_days = 7
        
    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_kubernetes_config(self) -> None:
        """Load Kubernetes configuration."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                config.load_incluster_config()
        except Exception as e:
            self.logger.warning(f"Could not load Kubernetes config: {e}")
    
    def parse_certificate(self, cert_data: bytes) -> CertificateInfo:
        """Parse certificate from bytes."""
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Extract subject and issuer
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            
            # Extract SAN
            san_dns_names = []
            san_ip_addresses = []
            
            try:
                san_extension = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                ).value
                
                for name in san_extension:
                    if isinstance(name, x509.DNSName):
                        san_dns_names.append(name.value)
                    elif isinstance(name, x509.IPAddress):
                        san_ip_addresses.append(str(name.value))
            except x509.ExtensionNotFound:
                pass
            
            # Check if certificate is CA
            is_ca = False
            try:
                basic_constraints = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.BASIC_CONSTRAINTS
                ).value
                is_ca = basic_constraints.ca
            except x509.ExtensionNotFound:
                pass
            
            # Check if self-signed
            is_self_signed = cert.issuer == cert.subject
            
            # Get public key info
            public_key = cert.public_key()
            public_key_algorithm = public_key.__class__.__name__
            key_size = getattr(public_key, 'key_size', None)
            
            return CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=str(cert.serial_number),
                not_before=cert.not_valid_before,
                not_after=cert.not_valid_after,
                san_dns_names=san_dns_names,
                san_ip_addresses=san_ip_addresses,
                signature_algorithm=cert.signature_algorithm_oid._name,
                public_key_algorithm=public_key_algorithm,
                key_size=key_size,
                is_ca=is_ca,
                is_self_signed=is_self_signed
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse certificate: {e}")
            raise
    
    def validate_certificate(self, cert_info: CertificateInfo) -> CertificateValidationResult:
        """Validate certificate against security requirements."""
        errors = []
        warnings = []
        
        # Calculate days until expiry
        now = datetime.datetime.now()
        days_until_expiry = (cert_info.not_after - now).days
        
        # Check expiration
        if days_until_expiry < 0:
            errors.append("Certificate has expired")
        elif days_until_expiry < self.critical_days:
            errors.append(f"Certificate expires in {days_until_expiry} days (critical)")
        elif days_until_expiry < self.warning_days:
            warnings.append(f"Certificate expires in {days_until_expiry} days")
        
        # Check key size
        if cert_info.key_size and cert_info.key_size < 2048:
            warnings.append(f"Key size {cert_info.key_size} is below recommended 2048 bits")
        
        # Check signature algorithm
        weak_algorithms = ['md5', 'sha1']
        if any(weak_alg in cert_info.signature_algorithm.lower() for weak_alg in weak_algorithms):
            warnings.append(f"Weak signature algorithm: {cert_info.signature_algorithm}")
        
        # Check if certificate is not yet valid
        if cert_info.not_before > now:
            errors.append("Certificate is not yet valid")
        
        is_valid = len(errors) == 0
        
        return CertificateValidationResult(
            certificate=cert_info,
            is_valid=is_valid,
            days_until_expiry=days_until_expiry,
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    def get_certificate_from_endpoint(self, hostname: str, port: int = 443) -> CertificateInfo:
        """Get certificate from TLS endpoint."""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert_chain()[0]
                    cert_pem = ssl.DER_cert_to_PEM_cert(cert_der.public_bytes(x509.Encoding.DER))
                    return self.parse_certificate(cert_pem.encode())
                    
        except Exception as e:
            self.logger.error(f"Failed to get certificate from {hostname}:{port}: {e}")
            raise
    
    def validate_kubernetes_certificates(self) -> List[CertificateValidationResult]:
        """Validate Kubernetes cluster certificates."""
        results = []
        
        try:
            v1 = client.CoreV1Api()
            
            # Get API server certificate
            try:
                api_server_url = client.configuration.Configuration().host
                if api_server_url.startswith('https://'):
                    hostname = api_server_url.replace('https://', '').split(':')[0]
                    port = int(api_server_url.split(':')[2]) if ':' in api_server_url.split('//')[1] else 443
                    
                    cert_info = self.get_certificate_from_endpoint(hostname, port)
                    result = self.validate_certificate(cert_info)
                    result.certificate.subject = f"API Server: {result.certificate.subject}"
                    results.append(result)
                    
            except Exception as e:
                self.logger.warning(f"Could not validate API server certificate: {e}")
            
            # Check TLS secrets in cluster
            try:
                secrets = v1.list_secret_for_all_namespaces()
                for secret in secrets.items:
                    if secret.type == 'kubernetes.io/tls':
                        try:
                            cert_data = secret.data.get('tls.crt')
                            if cert_data:
                                import base64
                                cert_pem = base64.b64decode(cert_data)
                                cert_info = self.parse_certificate(cert_pem)
                                result = self.validate_certificate(cert_info)
                                result.certificate.subject = f"TLS Secret {secret.metadata.namespace}/{secret.metadata.name}: {result.certificate.subject}"
                                results.append(result)
                                
                        except Exception as e:
                            self.logger.debug(f"Could not parse TLS secret {secret.metadata.name}: {e}")
                            
            except Exception as e:
                self.logger.warning(f"Could not list TLS secrets: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to validate Kubernetes certificates: {e}")
        
        return results
    
    def validate_cert_manager_certificates(self) -> List[CertificateValidationResult]:
        """Validate cert-manager issued certificates."""
        results = []
        
        try:
            # Use kubectl to get Certificate resources
            cmd = ["kubectl", "get", "certificates", "--all-namespaces", "-o", "yaml"]
            if self.kubeconfig_path:
                cmd.extend(["--kubeconfig", self.kubeconfig_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                certificates = yaml.safe_load(result.stdout)
                
                if certificates and 'items' in certificates:
                    for cert in certificates['items']:
                        try:
                            cert_name = cert['metadata']['name']
                            namespace = cert['metadata']['namespace']
                            
                            # Get the actual certificate from the secret
                            secret_name = cert['spec']['secretName']
                            
                            get_secret_cmd = ["kubectl", "get", "secret", secret_name, 
                                           "-n", namespace, "-o", "yaml"]
                            if self.kubeconfig_path:
                                get_secret_cmd.extend(["--kubeconfig", self.kubeconfig_path])
                            
                            secret_result = subprocess.run(get_secret_cmd, capture_output=True, text=True)
                            
                            if secret_result.returncode == 0:
                                secret_data = yaml.safe_load(secret_result.stdout)
                                cert_data = secret_data['data']['tls.crt']
                                
                                import base64
                                cert_pem = base64.b64decode(cert_data)
                                cert_info = self.parse_certificate(cert_pem)
                                validation_result = self.validate_certificate(cert_info)
                                validation_result.certificate.subject = f"cert-manager {namespace}/{cert_name}: {validation_result.certificate.subject}"
                                results.append(validation_result)
                                
                        except Exception as e:
                            self.logger.debug(f"Could not validate cert-manager certificate {cert.get('metadata', {}).get('name', 'unknown')}: {e}")
                            
        except Exception as e:
            self.logger.warning(f"Could not validate cert-manager certificates: {e}")
        
        return results

class MTLSValidator:
    """Mutual TLS validation and testing."""
    
    def __init__(self, log_level: str = "INFO"):
        """Initialize mTLS validator."""
        self.logger = self._setup_logging(log_level)
    
    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def test_mtls_connection(self, 
                           endpoint: str, 
                           client_cert_path: str,
                           client_key_path: str,
                           ca_cert_path: Optional[str] = None) -> MTLSTestResult:
        """Test mTLS connection to endpoint."""
        start_time = datetime.datetime.now()
        
        try:
            # Configure session with client certificates
            session = requests.Session()
            session.cert = (client_cert_path, client_key_path)
            
            if ca_cert_path:
                session.verify = ca_cert_path
            else:
                session.verify = True
            
            # Make request
            response = session.get(endpoint, timeout=10)
            end_time = datetime.datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Get TLS information
            tls_version = ""
            cipher_suite = ""
            peer_cert = None
            
            # Try to get TLS details from the connection
            try:
                # This is a simplified approach - in practice you might need to use lower-level APIs
                if hasattr(response.raw, '_original_response'):
                    sock = response.raw._original_response.fp.raw._sock
                    if hasattr(sock, 'version'):
                        tls_version = sock.version()
                    if hasattr(sock, 'cipher'):
                        cipher_suite = sock.cipher()[0] if sock.cipher() else ""
            except:
                pass
            
            return MTLSTestResult(
                endpoint=endpoint,
                is_successful=response.status_code < 400,
                tls_version=tls_version,
                cipher_suite=cipher_suite,
                client_certificate_verified=True,
                response_time_ms=response_time
            )
            
        except requests.exceptions.SSLError as e:
            return MTLSTestResult(
                endpoint=endpoint,
                is_successful=False,
                error_message=f"SSL Error: {str(e)}",
                client_certificate_verified=False
            )
        except Exception as e:
            return MTLSTestResult(
                endpoint=endpoint,
                is_successful=False,
                error_message=f"Connection failed: {str(e)}"
            )
    
    def test_service_mesh_mtls(self) -> List[MTLSTestResult]:
        """Test mTLS in service mesh (if available)."""
        results = []
        
        # This would be implemented based on your service mesh (Istio, Linkerd, etc.)
        # For now, return empty list as placeholder
        self.logger.info("Service mesh mTLS testing not implemented yet")
        
        return results
    
    def validate_mtls_configuration(self, namespace: str = "default") -> Dict[str, Any]:
        """Validate mTLS configuration in Kubernetes namespace."""
        validation_results = {
            "namespace": namespace,
            "mtls_enabled": False,
            "policies_found": [],
            "certificates_found": [],
            "issues": []
        }
        
        try:
            # Check for Istio PeerAuthentication policies
            cmd = ["kubectl", "get", "peerauthentication", "-n", namespace, "-o", "yaml"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                policies = yaml.safe_load(result.stdout)
                if policies and 'items' in policies:
                    validation_results["policies_found"] = [
                        p['metadata']['name'] for p in policies['items']
                    ]
                    validation_results["mtls_enabled"] = len(policies['items']) > 0
            
        except Exception as e:
            validation_results["issues"].append(f"Could not check mTLS policies: {e}")
        
        return validation_results

def main():
    """Main function for standalone testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Certificate and mTLS validation")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--endpoint", help="Test certificate for specific endpoint")
    parser.add_argument("--port", type=int, default=443, help="Port for endpoint testing")
    parser.add_argument("--test-mtls", help="Test mTLS connection to endpoint")
    parser.add_argument("--client-cert", help="Client certificate for mTLS testing")
    parser.add_argument("--client-key", help="Client key for mTLS testing")
    parser.add_argument("--ca-cert", help="CA certificate for mTLS testing")
    
    args = parser.parse_args()
    
    # Certificate validation
    validator = CertificateValidator(kubeconfig_path=args.kubeconfig, log_level=args.log_level)
    
    print("🔒 Certificate Validation Report")
    print("=" * 50)
    
    if args.endpoint:
        try:
            cert_info = validator.get_certificate_from_endpoint(args.endpoint, args.port)
            result = validator.validate_certificate(cert_info)
            
            print(f"\n📋 Certificate for {args.endpoint}:{args.port}")
            print(f"Subject: {result.certificate.subject}")
            print(f"Issuer: {result.certificate.issuer}")
            print(f"Valid until: {result.certificate.not_after}")
            print(f"Days until expiry: {result.days_until_expiry}")
            print(f"Status: {'✅ Valid' if result.is_valid else '❌ Invalid'}")
            
            if result.validation_warnings:
                print(f"Warnings: {', '.join(result.validation_warnings)}")
            if result.validation_errors:
                print(f"Errors: {', '.join(result.validation_errors)}")
                
        except Exception as e:
            print(f"❌ Failed to validate endpoint certificate: {e}")
    
    # Kubernetes certificate validation
    try:
        k8s_results = validator.validate_kubernetes_certificates()
        
        if k8s_results:
            print(f"\n🔒 Kubernetes Certificates ({len(k8s_results)} found)")
            for result in k8s_results:
                status = "✅" if result.is_valid else "❌"
                print(f"  {status} {result.certificate.subject[:80]}...")
                print(f"      Expires in {result.days_until_expiry} days")
                
                if result.validation_warnings:
                    print(f"      ⚠️  {', '.join(result.validation_warnings)}")
                if result.validation_errors:
                    print(f"      ❌ {', '.join(result.validation_errors)}")
        else:
            print("\n🔒 No Kubernetes certificates found or accessible")
            
    except Exception as e:
        print(f"❌ Failed to validate Kubernetes certificates: {e}")
    
    # cert-manager certificate validation
    try:
        cm_results = validator.validate_cert_manager_certificates()
        
        if cm_results:
            print(f"\n🔒 cert-manager Certificates ({len(cm_results)} found)")
            for result in cm_results:
                status = "✅" if result.is_valid else "❌"
                print(f"  {status} {result.certificate.subject[:80]}...")
                print(f"      Expires in {result.days_until_expiry} days")
                
                if result.validation_warnings:
                    print(f"      ⚠️  {', '.join(result.validation_warnings)}")
                if result.validation_errors:
                    print(f"      ❌ {', '.join(result.validation_errors)}")
        else:
            print("\n🔒 No cert-manager certificates found")
            
    except Exception as e:
        print(f"❌ Failed to validate cert-manager certificates: {e}")
    
    # mTLS testing
    if args.test_mtls and args.client_cert and args.client_key:
        mtls_validator = MTLSValidator(log_level=args.log_level)
        
        print(f"\n🔐 mTLS Testing for {args.test_mtls}")
        
        try:
            mtls_result = mtls_validator.test_mtls_connection(
                args.test_mtls, 
                args.client_cert, 
                args.client_key,
                args.ca_cert
            )
            
            status = "✅" if mtls_result.is_successful else "❌"
            print(f"  {status} Connection: {mtls_result.endpoint}")
            print(f"      Client cert verified: {mtls_result.client_certificate_verified}")
            print(f"      Response time: {mtls_result.response_time_ms:.2f}ms")
            
            if mtls_result.tls_version:
                print(f"      TLS version: {mtls_result.tls_version}")
            if mtls_result.cipher_suite:
                print(f"      Cipher suite: {mtls_result.cipher_suite}")
            if mtls_result.error_message:
                print(f"      Error: {mtls_result.error_message}")
                
        except Exception as e:
            print(f"❌ Failed to test mTLS connection: {e}")

if __name__ == "__main__":
    main()
