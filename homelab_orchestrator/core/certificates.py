"""Certificate Manager - TLS certificate management and validation.

Supports Let's Encrypt, custom CA, and self-signed certificates through cert-manager.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp


if TYPE_CHECKING:
    from .config_manager import ConfigManager


class CertificateManager:
    """Comprehensive certificate management and validation."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize certificate manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Certificate configuration
        self.cert_config = config_manager.get_config("certificates", "certificates", {})
        
        # HTTP session for certificate validation
        self.http_session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Start certificate manager services."""
        self.logger.info("Starting certificate manager")
        
        # Initialize HTTP session for certificate validation
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context(),
            limit=10,
            limit_per_host=3,
        )
        self.http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def stop(self) -> None:
        """Stop certificate manager services."""
        self.logger.info("Stopping certificate manager")
        
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

    async def deploy_cert_manager(self) -> dict[str, Any]:
        """Deploy cert-manager with issuers."""
        self.logger.info("Deploying cert-manager")
        
        try:
            # Deploy cert-manager CRDs and controller
            cert_manager_commands = [
                "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.crds.yaml",
                "kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -",
                "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml",
            ]
            
            for command in cert_manager_commands:
                result = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    self.logger.error(f"Cert-manager deployment failed: {stderr.decode()}")
                    return {
                        "status": "failed",
                        "error": f"Command failed: {command}",
                        "stderr": stderr.decode(),
                    }
            
            # Wait for cert-manager to be ready
            await self._wait_for_cert_manager_ready()
            
            # Deploy issuers
            issuer_result = await self._deploy_issuers()
            if issuer_result["status"] != "success":
                return issuer_result
            
            return {
                "status": "success",
                "message": "cert-manager deployed successfully",
                "issuers": issuer_result.get("issuers", []),
            }
            
        except Exception as e:
            self.logger.error(f"cert-manager deployment failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _wait_for_cert_manager_ready(self, timeout: int = 300) -> bool:
        """Wait for cert-manager to be ready."""
        self.logger.info("Waiting for cert-manager to be ready")
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Check if cert-manager pods are running
                result = await asyncio.create_subprocess_shell(
                    "kubectl get pods -n cert-manager -l app.kubernetes.io/name=cert-manager --no-headers",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    pods = stdout.decode().strip().split("\n")
                    if pods and pods[0]:  # Check if we have non-empty output
                        all_ready = True
                        for pod_line in pods:
                            if not pod_line.strip():
                                continue
                            parts = pod_line.split()
                            if len(parts) >= 3 and parts[2] != "Running":
                                all_ready = False
                                break
                        
                        if all_ready:
                            self.logger.info("cert-manager is ready")
                            return True
                
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.warning(f"Error checking cert-manager status: {e}")
                await asyncio.sleep(10)
        
        self.logger.warning("Timeout waiting for cert-manager to be ready")
        return False

    async def _deploy_issuers(self) -> dict[str, Any]:
        """Deploy certificate issuers."""
        self.logger.info("Deploying certificate issuers")
        
        try:
            # Apply issuer configuration
            result = await asyncio.create_subprocess_shell(
                "kubectl apply -f kubernetes/base/cert-manager-issuers.yaml",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {
                    "status": "failed",
                    "error": "Failed to deploy issuers",
                    "stderr": stderr.decode(),
                }
            
            # Wait for issuers to be ready
            await asyncio.sleep(30)  # Give issuers time to initialize
            
            return {
                "status": "success",
                "message": "Certificate issuers deployed successfully",
                "issuers": ["letsencrypt-prod", "letsencrypt-staging", "selfsigned-issuer", "ca-issuer"],
            }
            
        except Exception as e:
            self.logger.error(f"Issuer deployment failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    async def validate_certificates(self) -> dict[str, Any]:
        """Validate all certificates and their endpoints."""
        self.logger.info("Validating certificates")
        
        if not self.http_session:
            return {
                "status": "failed",
                "error": "Certificate manager not started",
            }
        
        validation_config = self.cert_config.get("validation", {})
        health_checks = validation_config.get("health_checks", {})
        
        if not health_checks.get("enabled", False):
            return {
                "status": "skipped",
                "message": "Certificate validation disabled",
            }
        
        endpoints = health_checks.get("endpoints", [])
        results = {}
        
        for endpoint in endpoints:
            try:
                async with self.http_session.get(endpoint) as response:
                    results[endpoint] = {
                        "status": "success" if response.status < 400 else "failed",
                        "status_code": response.status,
                        "ssl_verified": True,
                    }
            except aiohttp.ClientSSLError as e:
                results[endpoint] = {
                    "status": "ssl_error",
                    "error": str(e),
                    "ssl_verified": False,
                }
            except Exception as e:
                results[endpoint] = {
                    "status": "error",
                    "error": str(e),
                    "ssl_verified": None,
                }
        
        # Count successful validations
        successful = sum(1 for result in results.values() if result["status"] == "success")
        total = len(results)
        
        return {
            "status": "success" if successful == total else "partial",
            "endpoints": results,
            "summary": {
                "total": total,
                "successful": successful,
                "failed": total - successful,
            },
        }

    async def check_certificate_expiry(self) -> dict[str, Any]:
        """Check certificate expiry dates."""
        self.logger.info("Checking certificate expiry")
        
        try:
            # Get all certificates
            result = await asyncio.create_subprocess_shell(
                "kubectl get certificates -A -o json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {
                    "status": "failed",
                    "error": "Failed to get certificates",
                    "stderr": stderr.decode(),
                }
            
            import json
            certificates_data = json.loads(stdout.decode())
            
            expiry_info = []
            renewal_threshold = self.cert_config.get("validation", {}).get("renewal_threshold_days", 30)
            threshold_date = datetime.now() + timedelta(days=renewal_threshold)
            
            for cert in certificates_data.get("items", []):
                cert_name = cert["metadata"]["name"]
                namespace = cert["metadata"]["namespace"]
                
                # Check certificate status
                status = cert.get("status", {})
                not_after = status.get("notAfter")
                
                if not_after:
                    try:
                        expiry_date = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
                        days_until_expiry = (expiry_date - datetime.now()).days
                        
                        cert_info = {
                            "name": cert_name,
                            "namespace": namespace,
                            "expiry_date": not_after,
                            "days_until_expiry": days_until_expiry,
                            "needs_renewal": expiry_date < threshold_date,
                            "status": "ready" if status.get("conditions", [{}])[-1].get("type") == "Ready" else "not_ready",
                        }
                        expiry_info.append(cert_info)
                        
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Failed to parse expiry date for {cert_name}: {e}")
            
            # Count certificates needing renewal
            needs_renewal = [cert for cert in expiry_info if cert["needs_renewal"]]
            
            return {
                "status": "success",
                "certificates": expiry_info,
                "summary": {
                    "total": len(expiry_info),
                    "needs_renewal": len(needs_renewal),
                    "renewal_threshold_days": renewal_threshold,
                },
                "needs_renewal": needs_renewal,
            }
            
        except Exception as e:
            self.logger.error(f"Certificate expiry check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    async def renew_certificate(self, cert_name: str, namespace: str = "default") -> dict[str, Any]:
        """Force renewal of a specific certificate."""
        self.logger.info(f"Renewing certificate: {cert_name} in namespace: {namespace}")
        
        try:
            # Force certificate renewal by deleting the secret
            commands = [
                f"kubectl annotate certificate {cert_name} -n {namespace} cert-manager.io/issue-temporary-certificate=true --overwrite",
                f"kubectl delete secret $(kubectl get certificate {cert_name} -n {namespace} -o jsonpath='{{.spec.secretName}}') -n {namespace} || true",
            ]
            
            for command in commands:
                result = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0 and "not found" not in stderr.decode().lower():
                    return {
                        "status": "failed",
                        "error": f"Failed to renew certificate: {stderr.decode()}",
                    }
            
            return {
                "status": "success",
                "message": f"Certificate renewal initiated for {cert_name}",
            }
            
        except Exception as e:
            self.logger.error(f"Certificate renewal failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    def get_certificate_config(self) -> dict[str, Any]:
        """Get certificate configuration."""
        return self.cert_config
        
    def get_supported_issuers(self) -> list[str]:
        """Get list of supported certificate issuers."""
        issuers = self.cert_config.get("issuers", {})
        return [name for name, config in issuers.items() if config.get("enabled", False)]