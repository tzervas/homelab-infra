"""Security Manager - Unified security and SSO management.

Consolidates security validation, SSO integration, and certificate management
into a comprehensive security orchestration system.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from datetime import datetime
from typing import TYPE_CHECKING, Any

import aiohttp


if TYPE_CHECKING:
    from .config_manager import ConfigManager


class SecurityManager:
    """Comprehensive security management and validation."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize security manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Security configuration
        self.security_config = config_manager.get_security_config()
        self.deployment_config = config_manager.get_deployment_config()

        # HTTP client for security checks
        self.http_session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Start security manager services."""
        self.logger.info("Starting security manager")

        # Initialize HTTP session for security checks
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
        """Stop security manager services."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

        self.logger.info("Security manager stopped")

    async def validate_security_posture(self) -> dict[str, Any]:
        """Perform comprehensive security posture validation.

        Returns:
            Security validation results
        """
        self.logger.info("Validating security posture")

        validation_results = {
            "overall_status": "secure",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "recommendations": [],
            "issues": [],
        }

        try:
            # Run security validation checks in parallel
            tasks = [
                self._validate_pod_security_standards(),
                self._validate_network_policies(),
                self._validate_rbac_configuration(),
                self._validate_certificates(),
                self._validate_sso_configuration(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            check_names = [
                "pod_security_standards",
                "network_policies",
                "rbac_configuration",
                "certificates",
                "sso_configuration",
            ]

            issues_found = False
            for i, result in enumerate(results):
                check_name = check_names[i]

                if isinstance(result, Exception):
                    validation_results["checks"][check_name] = {
                        "status": "error",
                        "message": f"Check failed: {result!s}",
                        "details": {"error": str(result)},
                    }
                    validation_results["issues"].append(
                        f"Security check '{check_name}' failed: {result!s}",
                    )
                    issues_found = True
                else:
                    validation_results["checks"][check_name] = result
                    if result.get("status") not in ["secure", "compliant"]:
                        issues_found = True
                        validation_results["issues"].extend(
                            result.get("issues", []),
                        )
                    validation_results["recommendations"].extend(
                        result.get("recommendations", []),
                    )

            # Set overall status
            if issues_found:
                validation_results["overall_status"] = "vulnerable"
            elif validation_results["recommendations"]:
                validation_results["overall_status"] = "warning"

            return validation_results

        except Exception as e:
            self.logger.exception(f"Security posture validation failed: {e}")
            return {
                "overall_status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "checks": {},
                "recommendations": ["Review security manager logs"],
                "issues": [f"Security validation failed: {e}"],
            }

    async def _validate_pod_security_standards(self) -> dict[str, Any]:
        """Validate pod security standards configuration."""
        self.logger.debug("Validating pod security standards")

        try:
            # Get namespace configuration
            namespaces_config = self.config_manager.get_config("namespaces")
            if not namespaces_config:
                return {
                    "status": "error",
                    "message": "No namespace configuration found",
                    "issues": ["Namespace configuration missing"],
                }

            # Check pod security standards for each namespace
            cmd = ["kubectl", "get", "namespaces", "-o", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to get namespaces: {stderr.decode()}",
                    "issues": ["Cannot validate pod security standards"],
                }

            import json

            namespaces = json.loads(stdout.decode())
            issues = []
            compliant_namespaces = 0

            for ns in namespaces.get("items", []):
                ns_name = ns["metadata"]["name"]
                labels = ns["metadata"].get("labels", {})

                # Check for pod security standard labels
                enforce_label = labels.get("pod-security.kubernetes.io/enforce")
                if not enforce_label:
                    issues.append(
                        f"Namespace '{ns_name}' missing pod security enforcement label",
                    )
                else:
                    compliant_namespaces += 1

            return {
                "status": "compliant" if not issues else "non_compliant",
                "message": f"{compliant_namespaces} namespaces have pod security standards",
                "details": {
                    "compliant_namespaces": compliant_namespaces,
                    "total_namespaces": len(namespaces.get("items", [])),
                },
                "issues": issues,
                "recommendations": (
                    ["Apply pod security standards to all namespaces"] if issues else []
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Pod security validation failed: {e}",
                "issues": [f"Pod security validation error: {e}"],
            }

    async def _validate_network_policies(self) -> dict[str, Any]:
        """Validate network policies configuration."""
        self.logger.debug("Validating network policies")

        try:
            cmd = ["kubectl", "get", "networkpolicies", "--all-namespaces", "-o", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to get network policies: {stderr.decode()}",
                    "issues": ["Cannot validate network policies"],
                }

            import json

            policies = json.loads(stdout.decode())
            policy_count = len(policies.get("items", []))

            # Check for default deny policies
            default_deny_found = False
            for policy in policies.get("items", []):
                policy_name = policy["metadata"]["name"]
                if "default-deny" in policy_name.lower():
                    default_deny_found = True
                    break

            issues = []
            recommendations = []

            if policy_count == 0:
                issues.append("No network policies found")
                recommendations.append("Implement network policies for security isolation")
            elif not default_deny_found:
                recommendations.append(
                    "Consider implementing default-deny network policies",
                )

            return {
                "status": "compliant" if not issues else "non_compliant",
                "message": f"Found {policy_count} network policies",
                "details": {
                    "policy_count": policy_count,
                    "default_deny_found": default_deny_found,
                },
                "issues": issues,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Network policy validation failed: {e}",
                "issues": [f"Network policy validation error: {e}"],
            }

    async def _validate_rbac_configuration(self) -> dict[str, Any]:
        """Validate RBAC configuration."""
        self.logger.debug("Validating RBAC configuration")

        try:
            # Check for overly permissive ClusterRoleBindings
            cmd = ["kubectl", "get", "clusterrolebindings", "-o", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to get RBAC configuration: {stderr.decode()}",
                    "issues": ["Cannot validate RBAC configuration"],
                }

            import json

            bindings = json.loads(stdout.decode())
            issues = []
            recommendations = []

            # Check for cluster-admin bindings
            admin_bindings = 0
            for binding in bindings.get("items", []):
                role_ref = binding.get("roleRef", {})
                if role_ref.get("name") == "cluster-admin":
                    admin_bindings += 1

            if admin_bindings > 3:  # Allow some admin bindings for system components
                recommendations.append(
                    f"Review {admin_bindings} cluster-admin bindings for necessity",
                )

            return {
                "status": "compliant",
                "message": f"RBAC validation completed ({admin_bindings} admin bindings)",
                "details": {
                    "cluster_admin_bindings": admin_bindings,
                    "total_bindings": len(bindings.get("items", [])),
                },
                "issues": issues,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"RBAC validation failed: {e}",
                "issues": [f"RBAC validation error: {e}"],
            }

    async def _validate_certificates(self) -> dict[str, Any]:
        """Validate certificate configuration and expiration."""
        self.logger.debug("Validating certificates")

        try:
            cmd = ["kubectl", "get", "certificates", "--all-namespaces", "-o", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "status": "warning",
                    "message": "No cert-manager certificates found",
                    "issues": [],
                    "recommendations": ["Install cert-manager for certificate management"],
                }

            import json

            certificates = json.loads(stdout.decode())
            issues = []
            recommendations = []
            expiring_soon = []

            for cert in certificates.get("items", []):
                cert_name = cert["metadata"]["name"]
                namespace = cert["metadata"]["namespace"]
                status = cert.get("status", {})

                # Check if certificate is ready
                conditions = status.get("conditions", [])
                ready = any(
                    condition.get("type") == "Ready" and condition.get("status") == "True"
                    for condition in conditions
                )

                if not ready:
                    issues.append(f"Certificate {namespace}/{cert_name} is not ready")

                # Check expiration (if available)
                renewal_time = status.get("renewalTime")
                if renewal_time:
                    try:
                        renewal_dt = datetime.fromisoformat(
                            renewal_time.replace("Z", "+00:00"),
                        )
                        days_until_renewal = (renewal_dt - datetime.now()).days

                        if days_until_renewal < 30:
                            expiring_soon.append(
                                f"{namespace}/{cert_name} (in {days_until_renewal} days)",
                            )
                    except Exception:
                        pass  # Skip if we can't parse the date

            if expiring_soon:
                recommendations.append(
                    f"Certificates expiring soon: {', '.join(expiring_soon)}",
                )

            return {
                "status": "secure" if not issues else "vulnerable",
                "message": f"Validated {len(certificates.get('items', []))} certificates",
                "details": {
                    "total_certificates": len(certificates.get("items", [])),
                    "expiring_soon": len(expiring_soon),
                },
                "issues": issues,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Certificate validation failed: {e}",
                "issues": [f"Certificate validation error: {e}"],
            }

    async def _validate_sso_configuration(self) -> dict[str, Any]:
        """Validate SSO configuration."""
        self.logger.debug("Validating SSO configuration")

        if not self.config_manager.context.sso_enabled:
            return {
                "status": "disabled",
                "message": "SSO not enabled in configuration",
                "issues": [],
                "recommendations": [],
            }

        try:
            # Check if Keycloak is deployed and accessible
            services_config = self.deployment_config.get("services", {})
            keycloak_config = services_config.get("discovery", {}).get("keycloak", {})

            if not keycloak_config:
                return {
                    "status": "error",
                    "message": "Keycloak configuration not found",
                    "issues": ["SSO provider not configured"],
                    "recommendations": ["Configure Keycloak for SSO"],
                }

            # Test Keycloak health endpoint
            if self.http_session:
                health_url = keycloak_config.get("internal_url", "")
                if health_url:
                    health_endpoint = f"{health_url}/auth/health/ready"
                    try:
                        async with self.http_session.get(
                            health_endpoint,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as response:
                            keycloak_healthy = response.status == 200
                    except Exception:
                        keycloak_healthy = False
                else:
                    keycloak_healthy = False
            else:
                keycloak_healthy = False

            issues = []
            recommendations = []

            if not keycloak_healthy:
                issues.append("Keycloak SSO provider not accessible")
                recommendations.append("Check Keycloak deployment and configuration")

            return {
                "status": "secure" if keycloak_healthy else "vulnerable",
                "message": "SSO configuration validated",
                "details": {
                    "keycloak_healthy": keycloak_healthy,
                    "sso_enabled": True,
                },
                "issues": issues,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"SSO validation failed: {e}",
                "issues": [f"SSO validation error: {e}"],
            }

    async def validate_pre_deployment(self) -> dict[str, Any]:
        """Validate security configuration before deployment.

        Returns:
            Pre-deployment security validation results
        """
        self.logger.info("Running pre-deployment security validation")

        validation_errors = []
        warnings = []

        # Validate security configuration
        security_config = self.config_manager.get_security_config()
        if not security_config:
            validation_errors.append("No security configuration found")
        else:
            # Check required security settings
            required_settings = [
                ("default_security_context", "Default security context not configured"),
                ("pod_security_standards", "Pod security standards not configured"),
            ]

            for setting, error_msg in required_settings:
                if setting not in security_config:
                    validation_errors.append(error_msg)

        # Validate certificate configuration
        domains_config = self.config_manager.get_domain_config()
        cert_config = domains_config.get("certificates", {})
        if not cert_config.get("issuer", {}).get("email"):
            warnings.append("Certificate issuer email not configured")

        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": warnings,
            "details": {
                "security_config_present": bool(security_config),
                "certificate_config_present": bool(cert_config),
            },
        }

    async def rotate_certificates(self) -> dict[str, Any]:
        """Rotate certificates for enhanced security.

        Returns:
            Certificate rotation results
        """
        self.logger.info("Starting certificate rotation")

        # This would implement certificate rotation logic
        # For now, return a placeholder
        return {
            "status": "not_implemented",
            "message": "Certificate rotation not yet implemented",
            "recommendations": ["Implement automated certificate rotation"],
        }

    async def audit_security_events(self) -> dict[str, Any]:
        """Audit security-related events.

        Returns:
            Security audit results
        """
        self.logger.info("Auditing security events")

        # This would implement security event auditing
        # For now, return a placeholder
        return {
            "status": "not_implemented",
            "message": "Security event auditing not yet implemented",
            "recommendations": ["Implement security event auditing"],
        }
