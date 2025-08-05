"""Certificate Manager - TLS certificate management and validation.

Supports Let's Encrypt, custom CA, and self-signed certificates through cert-manager.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from functools import wraps
from shlex import quote, split
from typing import TYPE_CHECKING, Any, TypeVar, Callable

import aiohttp
from dateutil import parser as dateutil_parser

from kubernetes import client, config
from kubernetes.client.rest import ApiException


T = TypeVar('T')


def handle_cert_errors(f: Callable[..., T]) -> Callable[..., T]:
    """Decorator for handling certificate operation errors."""
    @wraps(f)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await f(*args, **kwargs)
        except ApiException as e:
            logging.error(f"Kubernetes API error: {e}")
            return {"status": "failed", "error": f"API error: {e.reason}"}
        except Exception as e:
            logging.exception(f"Certificate operation failed: {e}")
            return {"status": "failed", "error": str(e)}
    return wrapper


# Default configuration for certificate issuers
ISSUER_DEFAULTS = {
    "readiness_timeout": 300,
    "polling_interval": 10
}


if TYPE_CHECKING:
    from .config_manager import ConfigManager


class CertificateManager:
    """Comprehensive certificate management and validation."""

    def _sanitize_command(self, command: str, **kwargs: str) -> str:
        """Safely format command with quoted arguments."""
        return command.format(**{k: quote(v) for k, v in kwargs.items()})

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

    @handle_cert_errors
    async def deploy_cert_manager(self) -> dict[str, Any]:
        """Deploy cert-manager with issuers."""
        self.logger.info("Deploying cert-manager")
        
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), transient=True) as progress:
            task = progress.add_task("Deploying cert-manager...", total=None)

            try:
                # Deploy cert-manager CRDs and controller
                cert_manager_urls = [
                    "https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.crds.yaml",
                    "https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml",
                ]
                
                # Create namespace first
                progress.update(task, description="Creating cert-manager namespace...")
                result = await asyncio.create_subprocess_exec(
                    *split("kubectl create namespace cert-manager --dry-run=client -o yaml"),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    result = await asyncio.create_subprocess_exec(
                        "kubectl", "apply", "-f", "-",
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await result.communicate(input=stdout)
                
                if result.returncode != 0:
                    progress.update(task, description="[red]Failed to create namespace[/red]")
                    return {
                        "status": "failed",
                        "error": "Failed to create namespace",
                        "stderr": stderr.decode(),
                    }
                
                # Apply cert-manager manifests
                for url in cert_manager_urls:
                    progress.update(task, description=f"Applying manifest from {url}...")
                    result = await asyncio.create_subprocess_exec(
                        "kubectl", "apply", "-f", url,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await result.communicate()

                    if result.returncode != 0:
                        self.logger.error(f"Cert-manager deployment failed: {stderr.decode()}")
                        progress.update(task, description="[red]Deployment failed")
                        return {
                            "status": "failed",
                            "error": f"Command failed: {command}",
                            "stderr": stderr.decode(),
                        }

                # Wait for cert-manager to be ready
                progress.update(task, description="Waiting for cert-manager to be ready...")
                await self._wait_for_cert_manager_ready()

                # Deploy issuers
                progress.update(task, description="Deploying issuers...")
                issuer_result = await self._deploy_issuers()
                if issuer_result["status"] != "success":
                    return issuer_result

                progress.update(task, description="cert-manager deployed successfully")
                return {
                    "status": "success",
                    "message": "cert-manager deployed successfully",
                    "issuers": issuer_result.get("issuers", []),
                }

            except Exception as e:
                progress.update(task, description=f"[red]Error: {str(e)}")
                self.logger.exception(f"cert-manager deployment failed: {e}")
                return {
                    "status": "failed",
                    "error": str(e),
                }

    async def _wait_for_cert_manager_ready(self, timeout: int = 300) -> bool:
        """Wait for cert-manager to be ready."""
        try:
            config.load_kube_config()
            v1 = client.CoreV1Api()
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    pods = v1.list_namespaced_pod(
                        namespace="cert-manager",
                        label_selector="app.kubernetes.io/name=cert-manager",
                    )

                    if not pods.items:
                        await asyncio.sleep(5)
                        continue

                    all_ready = True
                    for pod in pods.items:
                        if not pod.status.container_statuses:
                            all_ready = False
                            break

                        for container in pod.status.container_statuses:
                            if not container.ready:
                                all_ready = False
                                break

                    if all_ready:
                        self.logger.info("cert-manager is ready")
                        return True

                except ApiException as e:
                    self.logger.warning(f"Error checking cert-manager status: {e}")

                await asyncio.sleep(5)

            msg = f"cert-manager not ready after {timeout} seconds"
            raise TimeoutError(msg)

        except Exception as e:
            self.logger.exception(f"Failed to check cert-manager readiness: {e}")
            raise

    async def _deploy_issuers(self) -> dict[str, Any]:
        """Deploy certificate issuers."""
        self.logger.info("Deploying certificate issuers")

        try:
            # Apply issuer configuration
            result = await asyncio.create_subprocess_exec(
                "kubectl", "apply", "-f", "kubernetes/base/cert-manager-issuers.yaml",
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
            issuers = ["letsencrypt-prod", "letsencrypt-staging", "selfsigned-issuer", "ca-issuer"]
            for issuer in issuers:
                if not await self._wait_for_issuer_ready(issuer):
                    return {
                        "status": "failed",
                        "error": f"Issuer {issuer} failed to become ready"
                    }

            return {
                "status": "success",
                "message": "Certificate issuers deployed successfully",
                "issuers": [
                    "letsencrypt-prod",
                    "letsencrypt-staging",
                    "selfsigned-issuer",
                    "ca-issuer",
                ],
            }

        except Exception as e:
            self.logger.exception(f"Issuer deployment failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    @handle_cert_errors
    async def validate_certificates(self) -> dict[str, Any]:
        """Validate all certificates and their endpoints."""
        self.logger.info("Validating certificates")

        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

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

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), transient=True) as progress:
            task = progress.add_task("Validating endpoints...", total=len(endpoints))

            results = []
            for endpoint in endpoints:
                progress.update(task, description=f"Validating: {endpoint}...", advance=1)
                result = await self._validate_endpoint(endpoint)
                results.append(result)

            endpoint_results = dict(zip(endpoints, results, strict=False))
            successful = sum(1 for result in endpoint_results.values() if result["status"] == "success")
            total = len(endpoint_results)

            return {
                "status": "success" if successful == total else "partial",
                "endpoints": endpoint_results,
                "summary": {
                    "total": total,
                    "successful": successful,
                    "failed": total - successful,
                },
            }

    async def _validate_endpoint(self, endpoint: str) -> dict[str, Any]:
        """Validate a single endpoint's certificate."""
        try:
            async with self.http_session.get(endpoint) as response:
                return {
                    "status": "success" if response.status < 400 else "failed",
                    "status_code": response.status,
                    "ssl_verified": True,
                }
        except aiohttp.ClientSSLError as e:
            return {
                "status": "ssl_error",
                "error": str(e),
                "ssl_verified": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "ssl_verified": None,
            }

    async def check_certificate_expiry(self) -> dict[str, Any]:
        """Check certificate expiry dates."""
        self.logger.info("Checking certificate expiry")

        try:
            # Get all certificates
            result = await asyncio.create_subprocess_exec(
                "kubectl", "get", "certificates", "-A", "-o", "json",
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
            renewal_threshold = self.cert_config.get("validation", {}).get(
                "renewal_threshold_days",
                30,
            )
            threshold_date = datetime.now() + timedelta(days=renewal_threshold)

            for cert in certificates_data.get("items", []):
                cert_name = cert["metadata"]["name"]
                namespace = cert["metadata"]["namespace"]

                # Check certificate status
                status = cert.get("status", {})
                not_after = status.get("notAfter")

                if not_after:
                    try:
                        expiry_date = dateutil_parser.isoparse(not_after)
                        days_until_expiry = (expiry_date - datetime.now()).days

                        cert_info = {
                            "name": cert_name,
                            "namespace": namespace,
                            "expiry_date": not_after,
                            "days_until_expiry": days_until_expiry,
                            "needs_renewal": expiry_date < threshold_date,
                            "status": self._get_certificate_status(cert)
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
            self.logger.exception(f"Certificate expiry check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    async def renew_certificate(self, cert_name: str, namespace: str = "default") -> dict[str, Any]:
        """Force renewal of a specific certificate."""
        self.logger.info(f"Renewing certificate: {cert_name} in namespace: {namespace}")

        try:
            # Force certificate renewal by deleting the secret
            annotate_cmd = [
                "kubectl", "annotate", "certificate",
                cert_name, "-n", namespace,
                "cert-manager.io/issue-temporary-certificate=true", "--overwrite"
            ]
            
            delete_secret_cmd = [
                "kubectl", "delete", "secret",
                f"$(kubectl get certificate {quote(cert_name)} -n {quote(namespace)} -o jsonpath='{{.spec.secretName}}')",
                "-n", namespace
            ]
            
            for cmd in [annotate_cmd, split(delete_secret_cmd)]:
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
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
            self.logger.exception(f"Certificate renewal failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }

    def _get_certificate_status(self, cert: dict[str, Any]) -> str:
        conditions = cert.get("status", {}).get("conditions", [])
        # Check all conditions for Ready status
        ready_conditions = [
            cond for cond in conditions 
            if cond.get("type") == "Ready"
        ]
        # Get most recent Ready condition
        if ready_conditions:
            latest_ready = max(
                ready_conditions,
                key=lambda x: dateutil_parser.isoparse(x.get("lastTransitionTime", ""))
            )
            return "ready" if latest_ready.get("status") == "True" else "not_ready"
        return "unknown"

    def get_certificate_config(self) -> dict[str, Any]:
        """Get certificate configuration."""
        return self.cert_config

    def get_supported_issuers(self) -> list[str]:
        """Get list of supported certificate issuers."""
        issuers = self.cert_config.get("issuers", {})
        return [name for name, config in issuers.items() if config.get("enabled", False)]

    async def _wait_for_issuer_ready(self, issuer_name: str, namespace: str = "default") -> bool:
        """Wait for a certificate issuer to be ready.

        Args:
            issuer_name: Name of the issuer to check
            namespace: Kubernetes namespace where the issuer is deployed

        Returns:
            bool: True if issuer becomes ready within timeout, False otherwise
        """
        config.load_kube_config()
        custom_api = client.CustomObjectsApi()
        timeout = self.cert_config.get("issuer_readiness_timeout", ISSUER_DEFAULTS["readiness_timeout"])
        interval = self.cert_config.get("issuer_polling_interval", ISSUER_DEFAULTS["polling_interval"])
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                issuer = custom_api.get_namespaced_custom_object(
                    group="cert-manager.io",
                    version="v1",
                    namespace=namespace,
                    plural="issuers",
                    name=issuer_name
                )
                if any(cond.get("type") == "Ready" and cond.get("status") == "True" 
                       for cond in issuer.get("status", {}).get("conditions", [])):
                    return True
            except ApiException as e:
                self.logger.warning(f"Error checking issuer status: {e}")
            await asyncio.sleep(interval)
        return False
