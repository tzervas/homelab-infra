"""Comprehensive system validation and testing.

Consolidates all validation logic into a unified testing framework that can
validate configurations, deployments, security posture, and system health.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from homelab_orchestrator.core.config_manager import ConfigManager


@dataclass
class ValidationResult:
    """Result of a validation test."""

    test_name: str
    status: str  # pass, fail, warning, skip
    duration: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationSuite:
    """Collection of validation results."""

    suite_name: str
    overall_status: str  # pass, fail, warning
    duration: float
    results: list[ValidationResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class SystemValidator:
    """Comprehensive system validation framework."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize system validator.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Validation configuration
        self.deployment_config = config_manager.get_deployment_config()

    async def run_comprehensive_validation(self) -> ValidationSuite:
        """Run comprehensive system validation.

        Returns:
            Complete validation results
        """
        self.logger.info("Starting comprehensive system validation")
        start_time = datetime.now()

        # Run all validation suites
        suites = [
            await self._validate_configuration(),
            await self._validate_prerequisites(),
            await self._validate_security_posture(),
            await self._validate_networking(),
            await self._validate_storage(),
            await self._validate_kubernetes_cluster(),
            await self._validate_services(),
        ]

        # Consolidate results
        all_results = []
        for suite in suites:
            all_results.extend(suite.results)

        # Calculate overall status
        statuses = [result.status for result in all_results]
        if "fail" in statuses:
            overall_status = "fail"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "pass"

        # Create summary
        summary = {
            "pass": statuses.count("pass"),
            "fail": statuses.count("fail"),
            "warning": statuses.count("warning"),
            "skip": statuses.count("skip"),
        }

        # Collect recommendations
        recommendations = []
        for suite in suites:
            recommendations.extend(suite.recommendations)

        duration = (datetime.now() - start_time).total_seconds()

        return ValidationSuite(
            suite_name="Comprehensive System Validation",
            overall_status=overall_status,
            duration=duration,
            results=all_results,
            summary=summary,
            recommendations=list(set(recommendations)),  # Remove duplicates
            timestamp=start_time,
        )

    async def _validate_configuration(self) -> ValidationSuite:
        """Validate configuration files and structure."""
        self.logger.debug("Validating configuration")
        start_time = datetime.now()
        results = []

        # Configuration file validation
        config_validation = self.config_manager.validate_configuration()

        if config_validation["status"] == "valid":
            results.append(
                ValidationResult(
                    test_name="Configuration Files",
                    status="pass",
                    duration=0.1,
                    message=f"All {config_validation['config_files_loaded']} configuration files loaded successfully",
                    details=config_validation,
                ),
            )
        else:
            results.append(
                ValidationResult(
                    test_name="Configuration Files",
                    status="fail",
                    duration=0.1,
                    message="Configuration validation failed",
                    details=config_validation,
                    recommendations=["Fix configuration issues before deployment"],
                ),
            )

        # Environment-specific validation
        env_config = self.config_manager.get_environment_config()
        if env_config:
            results.append(
                ValidationResult(
                    test_name="Environment Configuration",
                    status="pass",
                    duration=0.05,
                    message=f"Environment '{self.config_manager.context.environment}' configured",
                    details={"environment": self.config_manager.context.environment},
                ),
            )
        else:
            results.append(
                ValidationResult(
                    test_name="Environment Configuration",
                    status="warning",
                    duration=0.05,
                    message=f"No specific configuration for environment '{self.config_manager.context.environment}'",
                    recommendations=["Create environment-specific configuration"],
                ),
            )

        # Consolidate suite results
        duration = (datetime.now() - start_time).total_seconds()
        suite_status = "fail" if any(r.status == "fail" for r in results) else "pass"

        return ValidationSuite(
            suite_name="Configuration Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_prerequisites(self) -> ValidationSuite:
        """Validate system prerequisites and dependencies."""
        self.logger.debug("Validating prerequisites")
        start_time = datetime.now()
        results = []

        # Required tools validation
        required_tools = ["kubectl", "helm", "docker"]
        for tool in required_tools:
            try:
                process = await asyncio.create_subprocess_exec(
                    "which",
                    tool,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await process.communicate()

                if process.returncode == 0:
                    results.append(
                        ValidationResult(
                            test_name=f"Tool: {tool}",
                            status="pass",
                            duration=0.1,
                            message=f"{tool} is available",
                        ),
                    )
                else:
                    results.append(
                        ValidationResult(
                            test_name=f"Tool: {tool}",
                            status="fail",
                            duration=0.1,
                            message=f"{tool} not found",
                            recommendations=[f"Install {tool}"],
                        ),
                    )
            except Exception as e:
                results.append(
                    ValidationResult(
                        test_name=f"Tool: {tool}",
                        status="fail",
                        duration=0.1,
                        message=f"Failed to check {tool}: {e}",
                        recommendations=[f"Verify {tool} installation"],
                    ),
                )

        # Network connectivity validation
        try:
            # Test basic internet connectivity
            process = await asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "1",
                "-W",
                "3",
                "8.8.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.communicate()

            if process.returncode == 0:
                results.append(
                    ValidationResult(
                        test_name="Internet Connectivity",
                        status="pass",
                        duration=0.5,
                        message="Internet connectivity available",
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Internet Connectivity",
                        status="warning",
                        duration=0.5,
                        message="Limited internet connectivity",
                        recommendations=["Check network configuration"],
                    ),
                )
        except Exception as e:
            results.append(
                ValidationResult(
                    test_name="Internet Connectivity",
                    status="fail",
                    duration=0.5,
                    message=f"Connectivity test failed: {e}",
                ),
            )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = "fail" if any(r.status == "fail" for r in results) else "pass"

        return ValidationSuite(
            suite_name="Prerequisites Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_security_posture(self) -> ValidationSuite:
        """Validate security configuration and posture."""
        self.logger.debug("Validating security posture")
        start_time = datetime.now()
        results = []

        # Security configuration validation
        security_config = self.config_manager.get_security_config()

        if security_config:
            results.append(
                ValidationResult(
                    test_name="Security Configuration",
                    status="pass",
                    duration=0.1,
                    message="Security configuration loaded",
                    details={
                        "contexts_configured": len(security_config.get("service_contexts", {})),
                    },
                ),
            )

            # Check default security context
            default_context = security_config.get("default_security_context", {})
            if default_context.get("runAsNonRoot", False):
                results.append(
                    ValidationResult(
                        test_name="Default Security Context",
                        status="pass",
                        duration=0.05,
                        message="Non-root security context configured",
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Default Security Context",
                        status="warning",
                        duration=0.05,
                        message="Default security context allows root",
                        recommendations=["Configure non-root security contexts"],
                    ),
                )
        else:
            results.append(
                ValidationResult(
                    test_name="Security Configuration",
                    status="fail",
                    duration=0.1,
                    message="Security configuration not found",
                    recommendations=["Configure security settings"],
                ),
            )

        # Pod security standards validation
        pod_security = security_config.get("pod_security_standards", {}) if security_config else {}
        if pod_security:
            default_enforce = pod_security.get("default", {}).get("enforce", "")
            if default_enforce in ["baseline", "restricted"]:
                results.append(
                    ValidationResult(
                        test_name="Pod Security Standards",
                        status="pass",
                        duration=0.05,
                        message=f"Pod security enforced at '{default_enforce}' level",
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Pod Security Standards",
                        status="warning",
                        duration=0.05,
                        message="Pod security standards not enforced",
                        recommendations=["Enable pod security standards"],
                    ),
                )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = (
            "warning" if any(r.status in ["fail", "warning"] for r in results) else "pass"
        )

        return ValidationSuite(
            suite_name="Security Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_networking(self) -> ValidationSuite:
        """Validate networking configuration."""
        self.logger.debug("Validating networking")
        start_time = datetime.now()
        results = []

        networking_config = self.config_manager.get_networking_config()

        if networking_config:
            # MetalLB validation
            metallb_config = networking_config.get("networking", {}).get("metallb", {})
            if metallb_config.get("enabled", False):
                default_pool = metallb_config.get("default_pool", {})
                if default_pool.get("addresses"):
                    results.append(
                        ValidationResult(
                            test_name="MetalLB Configuration",
                            status="pass",
                            duration=0.1,
                            message=f"MetalLB pool configured: {default_pool['addresses']}",
                            details=default_pool,
                        ),
                    )
                else:
                    results.append(
                        ValidationResult(
                            test_name="MetalLB Configuration",
                            status="fail",
                            duration=0.1,
                            message="MetalLB enabled but no IP pool configured",
                            recommendations=["Configure MetalLB IP address pool"],
                        ),
                    )
            else:
                results.append(
                    ValidationResult(
                        test_name="MetalLB Configuration",
                        status="skip",
                        duration=0.05,
                        message="MetalLB disabled",
                    ),
                )

            # Ingress validation
            ingress_config = networking_config.get("networking", {}).get("ingress", {})
            if ingress_config.get("nginx", {}).get("enabled", False):
                results.append(
                    ValidationResult(
                        test_name="Ingress Configuration",
                        status="pass",
                        duration=0.05,
                        message="NGINX ingress controller configured",
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Ingress Configuration",
                        status="warning",
                        duration=0.05,
                        message="No ingress controller configured",
                        recommendations=["Configure ingress controller for external access"],
                    ),
                )
        else:
            results.append(
                ValidationResult(
                    test_name="Networking Configuration",
                    status="fail",
                    duration=0.1,
                    message="No networking configuration found",
                    recommendations=["Configure networking settings"],
                ),
            )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = "fail" if any(r.status == "fail" for r in results) else "pass"

        return ValidationSuite(
            suite_name="Networking Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_storage(self) -> ValidationSuite:
        """Validate storage configuration."""
        self.logger.debug("Validating storage")
        start_time = datetime.now()
        results = []

        storage_config = self.config_manager.get_config("storage", "storage", {})

        if storage_config:
            # Default storage class validation
            default_class = storage_config.get("default_class")
            if default_class:
                results.append(
                    ValidationResult(
                        test_name="Default Storage Class",
                        status="pass",
                        duration=0.05,
                        message=f"Default storage class: {default_class}",
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Default Storage Class",
                        status="warning",
                        duration=0.05,
                        message="No default storage class configured",
                        recommendations=["Configure default storage class"],
                    ),
                )

            # Storage classes validation
            storage_classes = storage_config.get("classes", {})
            if storage_classes:
                results.append(
                    ValidationResult(
                        test_name="Storage Classes",
                        status="pass",
                        duration=0.1,
                        message=f"{len(storage_classes)} storage classes configured",
                        details={"classes": list(storage_classes.keys())},
                    ),
                )
            else:
                results.append(
                    ValidationResult(
                        test_name="Storage Classes",
                        status="fail",
                        duration=0.1,
                        message="No storage classes configured",
                        recommendations=["Configure storage classes"],
                    ),
                )
        else:
            results.append(
                ValidationResult(
                    test_name="Storage Configuration",
                    status="fail",
                    duration=0.1,
                    message="No storage configuration found",
                    recommendations=["Configure storage settings"],
                ),
            )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = "fail" if any(r.status == "fail" for r in results) else "pass"

        return ValidationSuite(
            suite_name="Storage Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_kubernetes_cluster(self) -> ValidationSuite:
        """Validate Kubernetes cluster connectivity and health."""
        self.logger.debug("Validating Kubernetes cluster")
        start_time = datetime.now()
        results = []

        try:
            # Test cluster connectivity
            process = await asyncio.create_subprocess_exec(
                "kubectl",
                "cluster-info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode == 0:
                results.append(
                    ValidationResult(
                        test_name="Cluster Connectivity",
                        status="pass",
                        duration=1.0,
                        message="Kubernetes cluster accessible",
                        details={"cluster_info": stdout.decode().strip()},
                    ),
                )

                # Get node information
                try:
                    node_process = await asyncio.create_subprocess_exec(
                        "kubectl",
                        "get",
                        "nodes",
                        "-o",
                        "wide",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    node_stdout, _ = await node_process.communicate()

                    if node_process.returncode == 0:
                        node_lines = node_stdout.decode().strip().split("\n")
                        node_count = len(node_lines) - 1  # Exclude header

                        results.append(
                            ValidationResult(
                                test_name="Cluster Nodes",
                                status="pass",
                                duration=0.5,
                                message=f"{node_count} nodes found",
                                details={"node_count": node_count},
                            ),
                        )
                    else:
                        results.append(
                            ValidationResult(
                                test_name="Cluster Nodes",
                                status="warning",
                                duration=0.5,
                                message="Could not retrieve node information",
                            ),
                        )

                except Exception as e:
                    results.append(
                        ValidationResult(
                            test_name="Cluster Nodes",
                            status="warning",
                            duration=0.5,
                            message=f"Node check failed: {e}",
                        ),
                    )
            else:
                results.append(
                    ValidationResult(
                        test_name="Cluster Connectivity",
                        status="fail",
                        duration=1.0,
                        message=f"Cluster not accessible: {stderr.decode()}",
                        recommendations=["Check cluster configuration and connectivity"],
                    ),
                )

        except asyncio.TimeoutError:
            results.append(
                ValidationResult(
                    test_name="Cluster Connectivity",
                    status="fail",
                    duration=30.0,
                    message="Cluster connectivity test timed out",
                    recommendations=["Check network connectivity to cluster"],
                ),
            )
        except Exception as e:
            results.append(
                ValidationResult(
                    test_name="Cluster Connectivity",
                    status="fail",
                    duration=1.0,
                    message=f"Cluster test failed: {e}",
                    recommendations=["Verify kubectl configuration"],
                ),
            )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = "fail" if any(r.status == "fail" for r in results) else "pass"

        return ValidationSuite(
            suite_name="Kubernetes Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )

    async def _validate_services(self) -> ValidationSuite:
        """Validate service configurations."""
        self.logger.debug("Validating services")
        start_time = datetime.now()
        results = []

        services_config = self.config_manager.get_config("services", "services", {})

        if services_config:
            # Service discovery validation
            discovery = services_config.get("discovery", {})
            if discovery:
                results.append(
                    ValidationResult(
                        test_name="Service Discovery",
                        status="pass",
                        duration=0.1,
                        message=f"{len(discovery)} services configured",
                        details={"services": list(discovery.keys())},
                    ),
                )

                # Validate individual services
                for service_name, service_config in discovery.items():
                    if isinstance(service_config, dict):
                        if service_config.get("namespace"):
                            results.append(
                                ValidationResult(
                                    test_name=f"Service: {service_name}",
                                    status="pass",
                                    duration=0.05,
                                    message=f"{service_name} namespace configured",
                                ),
                            )
                        else:
                            results.append(
                                ValidationResult(
                                    test_name=f"Service: {service_name}",
                                    status="warning",
                                    duration=0.05,
                                    message=f"{service_name} missing namespace configuration",
                                    recommendations=[f"Configure namespace for {service_name}"],
                                ),
                            )
            else:
                results.append(
                    ValidationResult(
                        test_name="Service Discovery",
                        status="warning",
                        duration=0.1,
                        message="No service discovery configuration",
                        recommendations=["Configure service discovery"],
                    ),
                )
        else:
            results.append(
                ValidationResult(
                    test_name="Services Configuration",
                    status="warning",
                    duration=0.1,
                    message="No services configuration found",
                    recommendations=["Configure services"],
                ),
            )

        duration = (datetime.now() - start_time).total_seconds()
        suite_status = (
            "warning" if any(r.status in ["fail", "warning"] for r in results) else "pass"
        )

        return ValidationSuite(
            suite_name="Services Validation",
            overall_status=suite_status,
            duration=duration,
            results=results,
        )
