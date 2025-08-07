import time
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry behavior with circuit breaker integration.
    
    Args:
        max_retries: Maximum number of retry attempts before giving up
        backoff_factor: Multiplicative factor for exponential backoff
        max_backoff: Maximum backoff time in seconds
        circuit_breaker_threshold: Number of failures before tripping circuit breaker
    """
    max_retries: int = 3 
    backoff_factor: float = 1.5
    max_backoff: int = 60
    circuit_breaker_threshold: int = 5

class CircuitBreaker:
    """Circuit breaker pattern implementation to prevent cascading failures.
    
    Args:
        threshold: Number of failures before tripping the circuit breaker
    """
    def __init__(self, threshold: int = 5):
        self.failures = 0
        self.threshold = threshold
        self.tripped = False
        self._last_failure_time = 0.0
        
    def record_failure(self) -> None:
        """Record a failure and potentially trip the circuit breaker."""
        self.failures += 1
        self._last_failure_time = time.time()
        if self.failures >= self.threshold:
            logger.warning(f"Circuit breaker tripped after {self.failures} failures")
            self.tripped = True
            
    def can_proceed(self) -> bool:
        """Check if the circuit breaker allows proceeding with the operation."""
        return not self.tripped
    
    def reset(self) -> None:
        """Reset the circuit breaker state."""
        self.failures = 0
        self.tripped = False
        self._last_failure_time = 0.0

class TestProgressMonitor:
    """Monitors test execution progress and identifies stalled tests.
    
    The monitor tracks test status and duration to identify tests that may have
    stalled or exceeded timeout thresholds.
    """
    def __init__(self):
        self.start_time = time.time()
        self.test_states = {}
        
    def update_progress(self, test_name: str, status: str) -> None:
        """Update the status and duration for a specific test.
        
        Args:
            test_name: Name of the test being monitored
            status: Current status of the test (e.g., 'running', 'completed', 'failed')
        """
        self.test_states[test_name] = {
            'status': status,
            'duration': time.time() - self.start_time
        }
        logger.debug(f"Updated test {test_name} status to {status}")
        
    def check_stalled_tests(self, timeout: float) -> List[str]:
        """Identify tests that have exceeded the timeout threshold.
        
        Args:
            timeout: Maximum allowed duration in seconds
            
        Returns:
            List of test names that have exceeded the timeout
        """
        stalled = [
            test for test, state in self.test_states.items()
            if state['status'] == 'running' 
            and state['duration'] > timeout
        ]
        
        if stalled:
            logger.warning(f"Found {len(stalled)} stalled tests: {', '.join(stalled)}")
        
        return stalled
    
    def get_test_duration(self, test_name: str) -> float:
        """Get the current duration of a specific test.
        
        Args:
            test_name: Name of the test to check
            
        Returns:
            Duration in seconds since the test started
        """
        if test_name in self.test_states:
            return self.test_states[test_name]['duration']
        return 0.0

"""
Health Monitor - Unified health monitoring and validation.

Consolidates all health checking logic from multiple scripts into a comprehensive
monitoring system with real-time status tracking and automated remediation.
"""

import asyncio
import contextlib
import logging
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .config_manager import ConfigManager


@dataclass
class HealthCheck:
    """Configuration for a health check."""

    name: str
    check_type: str  # http, tcp, kubernetes, command
    target: str
    timeout: int = 30
    interval: int = 60
    retries: int = 3
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResult:
    """Result of a health check."""

    check_name: str
    status: str  # healthy, unhealthy, warning, unknown
    timestamp: datetime
    duration: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class SystemHealth:
    """Overall system health status."""

    overall_status: str  # healthy, degraded, critical, unknown
    timestamp: datetime
    components: dict[str, HealthResult] = field(default_factory=dict)
    summary: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class HealthMonitor:
    """Comprehensive health monitoring system."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize health monitor.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Health check registry
        self.health_checks: dict[str, HealthCheck] = {}
        self.check_results: dict[str, HealthResult] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: asyncio.Task | None = None

        # HTTP client for health checks
        self.http_session: aiohttp.ClientSession | None = None

        # Register default health checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks based on configuration."""
        deployment_config = self.config_manager.get_deployment_config()
        services_config = deployment_config.get("services", {})

        # Kubernetes API health check
        self.register_check(
            HealthCheck(
                name="kubernetes_api",
                check_type="kubernetes",
                target="cluster-info",
                timeout=30,
                interval=60,
                required=True,
                metadata={"description": "Kubernetes API server health"},
            ),
        )

        # Service discovery health checks
        service_discovery = services_config.get("discovery", {})
        for service_name, service_config in service_discovery.items():
            if isinstance(service_config, dict):
                # HTTP health check for services with health paths
                health_path = service_config.get("health_path")
                if health_path:
                    internal_url = service_config.get("internal_url")
                    if internal_url:
                        self.register_check(
                            HealthCheck(
                                name=f"{service_name}_health",
                                check_type="http",
                                target=f"{internal_url}{health_path}",
                                timeout=15,
                                interval=120,
                                required=service_name in ["prometheus", "grafana"],
                                metadata={
                                    "service": service_name,
                                    "description": f"{service_name} service health",
                                },
                            ),
                        )

        # Infrastructure component checks
        self._register_infrastructure_checks()

        # Network connectivity checks
        self._register_network_checks()

    def _register_infrastructure_checks(self) -> None:
        """Register infrastructure component health checks."""
        # MetalLB health check
        self.register_check(
            HealthCheck(
                name="metallb_controller",
                check_type="kubernetes",
                target="deployment/metallb-controller -n metallb-system",
                timeout=30,
                interval=300,
                required=True,
                metadata={"component": "metallb", "description": "MetalLB controller health"},
            ),
        )

        # cert-manager health check
        self.register_check(
            HealthCheck(
                name="cert_manager",
                check_type="kubernetes",
                target="deployment/cert-manager -n cert-manager",
                timeout=30,
                interval=300,
                required=True,
                metadata={"component": "cert-manager", "description": "cert-manager health"},
            ),
        )

        # Ingress controller health check
        self.register_check(
            HealthCheck(
                name="ingress_nginx",
                check_type="kubernetes",
                target="deployment/ingress-nginx-controller -n ingress-nginx",
                timeout=30,
                interval=180,
                required=True,
                metadata={"component": "ingress", "description": "NGINX ingress controller health"},
            ),
        )

        # Longhorn health check
        self.register_check(
            HealthCheck(
                name="longhorn_manager",
                check_type="kubernetes",
                target="daemonset/longhorn-manager -n longhorn-system",
                timeout=30,
                interval=300,
                required=True,
                metadata={"component": "storage", "description": "Longhorn storage health"},
            ),
        )

    def _register_network_checks(self) -> None:
        """Register network connectivity health checks."""
        networking_config = self.config_manager.get_networking_config()

        # MetalLB IP pool connectivity
        metallb_config = networking_config.get("networking", {}).get("metallb", {})
        if metallb_config.get("enabled", False):
            default_pool = metallb_config.get("default_pool", {})
            if default_pool.get("addresses"):
                # Extract first IP from range for connectivity test
                ip_range = default_pool["addresses"]
                if "-" in ip_range:
                    first_ip = ip_range.split("-")[0]
                    self.register_check(
                        HealthCheck(
                            name="metallb_ip_connectivity",
                            check_type="tcp",
                            target=f"{first_ip}:80",
                            timeout=10,
                            interval=300,
                            required=False,
                            metadata={"description": "MetalLB IP pool connectivity"},
                        ),
                    )

        # DNS resolution check
        domains_config = self.config_manager.get_domain_config()
        primary_domain = domains_config.get("domains", {}).get("base", {}).get("primary")
        if primary_domain:
            self.register_check(
                HealthCheck(
                    name="dns_resolution",
                    check_type="command",
                    target=f"nslookup {primary_domain}",
                    timeout=10,
                    interval=600,
                    required=False,
                    metadata={"description": "DNS resolution for primary domain"},
                ),
            )

    def register_check(self, check: HealthCheck) -> None:
        """Register a health check.

        Args:
            check: Health check configuration
        """
        self.health_checks[check.name] = check
        self.logger.debug(f"Registered health check: {check.name}")

    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring already active")
            return

        self.logger.info("Starting health monitoring")
        self.monitoring_active = True

        # Initialize HTTP session
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context(),
            limit=10,
            limit_per_host=5,
        )
        self.http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
        )

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self.monitoring_active:
            return

        self.logger.info("Stopping health monitoring")
        self.monitoring_active = False

        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitoring_task

        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        check_intervals = {}  # Track next check time for each check

        while self.monitoring_active:
            try:
                current_time = datetime.now()

                # Determine which checks need to run
                checks_to_run = []
                for check_name, check in self.health_checks.items():
                    next_check_time = check_intervals.get(check_name, current_time)
                    if current_time >= next_check_time:
                        checks_to_run.append(check)
                        # Schedule next check
                        check_intervals[check_name] = current_time + timedelta(
                            seconds=check.interval,
                        )

                # Run checks concurrently
                if checks_to_run:
                    tasks = [self._execute_check(check) for check in checks_to_run]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Process results
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            self.logger.error(
                                f"Health check failed: {checks_to_run[i].name}: {result}",
                            )
                        elif isinstance(result, HealthResult):
                            self.check_results[result.check_name] = result

                # Sleep for minimum interval (10 seconds)
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Back off on errors

    async def _execute_check(self, check: HealthCheck) -> HealthResult:
        """Execute a single health check.

        Args:
            check: Health check to execute

        Returns:
            HealthResult with check outcome
        """
        start_time = datetime.now()

        try:
            # Execute check based on type
            if check.check_type == "http":
                result = await self._execute_http_check(check)
            elif check.check_type == "tcp":
                result = await self._execute_tcp_check(check)
            elif check.check_type == "kubernetes":
                result = await self._execute_kubernetes_check(check)
            elif check.check_type == "command":
                result = await self._execute_command_check(check)
            else:
                result = HealthResult(
                    check_name=check.name,
                    status="unknown",
                    timestamp=start_time,
                    duration=0.0,
                    message=f"Unknown check type: {check.check_type}",
                )

            result.duration = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=start_time,
                duration=(datetime.now() - start_time).total_seconds(),
                message=f"Check execution failed: {e}",
                details={"error": str(e)},
            )

    async def _execute_http_check(self, check: HealthCheck) -> HealthResult:
        """Execute HTTP health check."""
        if not self.http_session:
            msg = "HTTP session not initialized"
            raise RuntimeError(msg)

        try:
            async with self.http_session.get(
                check.target,
                timeout=aiohttp.ClientTimeout(total=check.timeout),
            ) as response:
                status = "healthy" if 200 <= response.status < 400 else "unhealthy"
                message = f"HTTP {response.status}"

                # Try to read response body for additional details
                try:
                    body = await response.text()
                    details = {"status_code": response.status, "response_size": len(body)}
                except Exception:
                    details = {"status_code": response.status}

                return HealthResult(
                    check_name=check.name,
                    status=status,
                    timestamp=datetime.now(),
                    duration=0.0,  # Will be set by caller
                    message=message,
                    details=details,
                )

        except asyncio.TimeoutError:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message="HTTP request timed out",
                details={"timeout": check.timeout},
            )
        except Exception as e:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"HTTP request failed: {e}",
                details={"error": str(e)},
            )

    async def _execute_tcp_check(self, check: HealthCheck) -> HealthResult:
        """Execute TCP connectivity check."""
        host, port = check.target.rsplit(":", 1)
        port = int(port)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=check.timeout,
            )
            writer.close()
            await writer.wait_closed()

            return HealthResult(
                check_name=check.name,
                status="healthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"TCP connection to {host}:{port} successful",
                details={"host": host, "port": port},
            )

        except asyncio.TimeoutError:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"TCP connection to {host}:{port} timed out",
                details={"host": host, "port": port, "timeout": check.timeout},
            )
        except Exception as e:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"TCP connection to {host}:{port} failed: {e}",
                details={"host": host, "port": port, "error": str(e)},
            )

    async def _execute_kubernetes_check(self, check: HealthCheck) -> HealthResult:
        """Execute Kubernetes resource health check."""
        cmd = ["kubectl", "get", *check.target.split()]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=check.timeout,
            )

            if process.returncode == 0:
                # Parse kubectl output for health status
                output = stdout.decode()
                lines = output.strip().split("\n")

                # Simple health determination based on kubectl output
                status = "healthy"
                message = "Kubernetes resource healthy"
                details = {"output_lines": len(lines)}

                # Check for common unhealthy indicators
                if "CrashLoopBackOff" in output or "Error" in output or "Failed" in output:
                    status = "unhealthy"
                    message = "Kubernetes resource in unhealthy state"

                return HealthResult(
                    check_name=check.name,
                    status=status,
                    timestamp=datetime.now(),
                    duration=0.0,
                    message=message,
                    details=details,
                )
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"kubectl command failed: {stderr.decode()}",
                details={"return_code": process.returncode},
            )

        except asyncio.TimeoutError:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message="Kubernetes check timed out",
                details={"timeout": check.timeout},
            )
        except Exception as e:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"Kubernetes check failed: {e}",
                details={"error": str(e)},
            )

    async def _execute_command_check(self, check: HealthCheck) -> HealthResult:
        """Execute command-based health check."""
        cmd = check.target.split()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=check.timeout,
            )

            status = "healthy" if process.returncode == 0 else "unhealthy"
            message = f"Command exit code: {process.returncode}"

            return HealthResult(
                check_name=check.name,
                status=status,
                timestamp=datetime.now(),
                duration=0.0,
                message=message,
                details={
                    "return_code": process.returncode,
                    "stdout_lines": len(stdout.decode().split("\n")),
                    "stderr_lines": len(stderr.decode().split("\n")),
                },
            )

        except asyncio.TimeoutError:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message="Command execution timed out",
                details={"timeout": check.timeout},
            )
        except Exception as e:
            return HealthResult(
                check_name=check.name,
                status="unhealthy",
                timestamp=datetime.now(),
                duration=0.0,
                message=f"Command execution failed: {e}",
                details={"error": str(e)},
            )

    async def comprehensive_health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check of all registered checks.

        Returns:
            Comprehensive health status dictionary
        """
        self.logger.info("Performing comprehensive health check")

        # Execute all health checks concurrently
        tasks = [self._execute_check(check) for check in self.health_checks.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        health_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = list(self.health_checks.keys())[i]
                health_results[check_name] = HealthResult(
                    check_name=check_name,
                    status="unknown",
                    timestamp=datetime.now(),
                    duration=0.0,
                    message=f"Check execution failed: {result}",
                    details={"error": str(result)},
                )
            else:
                health_results[result.check_name] = result

        # Calculate overall health status
        system_health = self._calculate_system_health(health_results)

        return {
            "status": system_health.overall_status,
            "timestamp": system_health.timestamp.isoformat(),
            "components": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "duration": result.duration,
                    "details": result.details,
                }
                for name, result in system_health.components.items()
            },
            "summary": system_health.summary,
            "recommendations": system_health.recommendations,
        }

    def _calculate_system_health(self, health_results: dict[str, HealthResult]) -> SystemHealth:
        """Calculate overall system health from individual check results.

        Args:
            health_results: Dictionary of health check results

        Returns:
            SystemHealth with overall status and recommendations
        """
        timestamp = datetime.now()

        # Count status types
        status_counts = {"healthy": 0, "unhealthy": 0, "warning": 0, "unknown": 0}
        required_unhealthy = 0

        for result in health_results.values():
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

            # Check if required service is unhealthy
            check_config = self.health_checks.get(result.check_name)
            if check_config and check_config.required and result.status == "unhealthy":
                required_unhealthy += 1

        # Determine overall status
        if required_unhealthy > 0:
            overall_status = "critical"
        elif status_counts["unhealthy"] > 0 or status_counts["warning"] > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        # Generate recommendations
        recommendations = []
        if required_unhealthy > 0:
            recommendations.append(f"{required_unhealthy} critical services are unhealthy")
        if status_counts["unhealthy"] > 0:
            recommendations.append(f"{status_counts['unhealthy']} services are unhealthy")
        if status_counts["unknown"] > 0:
            recommendations.append(f"{status_counts['unknown']} services have unknown status")

        return SystemHealth(
            overall_status=overall_status,
            timestamp=timestamp,
            components=health_results,
            summary=status_counts,
            recommendations=recommendations,
        )

    def get_current_health_status(self) -> dict[str, Any]:
        """Get current health status from cached results.

        Returns:
            Current health status dictionary
        """
        if not self.check_results:
            return {
                "status": "unknown",
                "message": "No health checks have been performed yet",
                "components": {},
                "summary": {},
            }

        system_health = self._calculate_system_health(self.check_results)

        return {
            "status": system_health.overall_status,
            "timestamp": system_health.timestamp.isoformat(),
            "components": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "last_check": result.timestamp.isoformat(),
                    "duration": result.duration,
                }
                for name, result in system_health.components.items()
            },
            "summary": system_health.summary,
            "recommendations": system_health.recommendations,
        }
