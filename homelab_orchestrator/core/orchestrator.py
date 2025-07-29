"""
Homelab Orchestrator - Main orchestration engine.

Unified orchestration system that coordinates all homelab operations:
- Configuration management integration
- Deployment coordination with hooks
- Health monitoring and validation
- Event processing and webhooks
- Resource management (including GPU)
- Security and SSO coordination
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..remote.cluster_manager import ClusterManager
from ..webhooks.manager import WebhookManager
from .config_manager import ConfigManager
from .deployment import DeploymentManager
from .gpu_manager import GPUResourceManager
from .health import HealthMonitor
from .security import SecurityManager


@dataclass
class OrchestrationEvent:
    """Event data structure for orchestration events."""

    event_type: str
    timestamp: datetime
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    correlation_id: str | None = None


@dataclass
class OrchestrationResult:
    """Result of orchestration operation."""

    operation: str
    status: str  # success, failure, warning, partial
    duration: float
    events: list[OrchestrationEvent] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class HomelabOrchestrator:
    """Main orchestration engine for unified homelab automation."""

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        project_root: Path | None = None,
        log_level: str = "INFO",
    ) -> None:
        """Initialize the homelab orchestrator.

        Args:
            config_manager: Configuration manager instance
            project_root: Path to project root directory
            log_level: Logging level
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        self.project_root = project_root or Path.cwd()
        self.config_manager = config_manager or ConfigManager.from_environment()

        # Initialize core managers
        self._initialize_managers()

        # Event system
        self.event_queue = asyncio.Queue()
        self.event_handlers: dict[str, list[Callable]] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}

        # Thread pool for blocking operations
        self.thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="homelab-")

        self.logger.info("Homelab Orchestrator initialized")

    def _initialize_managers(self) -> None:
        """Initialize all component managers."""
        deployment_config = self.config_manager.get_deployment_config()

        # Core managers
        self.deployment_manager = DeploymentManager(
            config_manager=self.config_manager,
            project_root=self.project_root,
        )

        self.health_monitor = HealthMonitor(
            config_manager=self.config_manager,
        )

        self.security_manager = SecurityManager(
            config_manager=self.config_manager,
        )

        # GPU management (if enabled)
        if deployment_config.get("gpu", {}).get("enabled", False):
            self.gpu_manager = GPUResourceManager(
                config_manager=self.config_manager,
            )
        else:
            self.gpu_manager = None

        # Webhook management
        self.webhook_manager = WebhookManager(
            config_manager=self.config_manager,
        )

        # Cluster management (for remote/hybrid deployments)
        if self.config_manager.context.cluster_type in ["remote", "hybrid"]:
            self.cluster_manager = ClusterManager(
                config_manager=self.config_manager,
            )
        else:
            self.cluster_manager = None

        self.logger.debug("All component managers initialized")

    async def start(self) -> None:
        """Start the orchestrator and all background services."""
        self.logger.info("Starting Homelab Orchestrator...")

        # Start event processing
        asyncio.create_task(self._process_events())

        # Start health monitoring
        if self.config_manager.context.monitoring_enabled:
            await self.health_monitor.start_monitoring()

        # Start GPU monitoring if enabled
        if self.gpu_manager:
            await self.gpu_manager.start_monitoring()

        # Start webhook server
        await self.webhook_manager.start()

        # Register core event handlers
        self._register_core_handlers()

        self.logger.info("Homelab Orchestrator started successfully")

    async def stop(self) -> None:
        """Stop the orchestrator and clean up resources."""
        self.logger.info("Stopping Homelab Orchestrator...")

        # Stop all running tasks
        for task in self.running_tasks.values():
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Stop component managers
        if self.gpu_manager:
            await self.gpu_manager.stop_monitoring()

        await self.health_monitor.stop_monitoring()
        await self.webhook_manager.stop()

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        self.logger.info("Homelab Orchestrator stopped")

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for specific event types.

        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for event type: {event_type}")

    async def emit_event(self, event: OrchestrationEvent) -> None:
        """Emit an event to the orchestration system.

        Args:
            event: Event to emit
        """
        await self.event_queue.put(event)
        self.logger.debug(f"Emitted event: {event.event_type} from {event.source}")

    async def _process_events(self) -> None:
        """Process events from the event queue."""
        while True:
            try:
                event = await self.event_queue.get()
                await self._handle_event(event)
                self.event_queue.task_done()
            except Exception as e:
                self.logger.exception(f"Error processing event: {e}")

    async def _handle_event(self, event: OrchestrationEvent) -> None:
        """Handle a single event by calling registered handlers.

        Args:
            event: Event to handle
        """
        handlers = self.event_handlers.get(event.event_type, [])

        if not handlers:
            self.logger.debug(f"No handlers registered for event type: {event.event_type}")
            return

        # Execute all handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(handler(event))
            tasks.append(task)

        # Wait for all handlers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any handler exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Event handler {i} failed for {event.event_type}: {result}")

    def _register_core_handlers(self) -> None:
        """Register core event handlers for system events."""
        # Deployment events
        self.register_event_handler("deployment.started", self._handle_deployment_started)
        self.register_event_handler("deployment.completed", self._handle_deployment_completed)
        self.register_event_handler("deployment.failed", self._handle_deployment_failed)

        # Health events
        self.register_event_handler("health.check.failed", self._handle_health_failure)
        self.register_event_handler("health.check.recovered", self._handle_health_recovery)

        # Security events
        self.register_event_handler("security.violation", self._handle_security_violation)
        self.register_event_handler("certificate.expiring", self._handle_certificate_expiry)

        # GPU events (if enabled)
        if self.gpu_manager:
            self.register_event_handler("gpu.resource.allocated", self._handle_gpu_allocation)
            self.register_event_handler("gpu.resource.released", self._handle_gpu_release)

        self.logger.debug("Core event handlers registered")

    async def deploy_full_infrastructure(
        self,
        environment: str | None = None,
        components: list[str] | None = None,
        dry_run: bool = False,
    ) -> OrchestrationResult:
        """Deploy the complete homelab infrastructure.

        Args:
            environment: Target environment (development, staging, production)
            components: Specific components to deploy (None for all)
            dry_run: Perform validation without actual deployment

        Returns:
            OrchestrationResult with deployment status and details
        """
        start_time = datetime.now()
        self.logger.info(f"Starting full infrastructure deployment (dry_run={dry_run})")

        # Emit deployment started event
        await self.emit_event(
            OrchestrationEvent(
                event_type="deployment.started",
                timestamp=start_time,
                source="orchestrator",
                data={"environment": environment, "components": components, "dry_run": dry_run},
            ),
        )

        try:
            # Pre-deployment validation
            validation_result = await self._run_pre_deployment_validation()
            if not validation_result["valid"]:
                return OrchestrationResult(
                    operation="deploy_full_infrastructure",
                    status="failure",
                    duration=(datetime.now() - start_time).total_seconds(),
                    details={"validation_errors": validation_result["errors"]},
                    recommendations=["Fix validation errors before deployment"],
                )

            # Deploy infrastructure components
            deployment_result = await self.deployment_manager.deploy_infrastructure(
                environment=environment,
                components=components,
                dry_run=dry_run,
            )

            # GPU resource setup (if enabled)
            if self.gpu_manager and not dry_run:
                gpu_result = await self.gpu_manager.setup_gpu_resources()
                deployment_result.details["gpu_setup"] = gpu_result

            # Post-deployment validation
            if not dry_run:
                health_result = await self.health_monitor.comprehensive_health_check()
                deployment_result.details["health_check"] = health_result

                # Security validation
                security_result = await self.security_manager.validate_security_posture()
                deployment_result.details["security_validation"] = security_result

            # Emit completion event
            await self.emit_event(
                OrchestrationEvent(
                    event_type="deployment.completed"
                    if deployment_result.status == "success"
                    else "deployment.failed",
                    timestamp=datetime.now(),
                    source="orchestrator",
                    data={
                        "result": deployment_result.status,
                        "duration": deployment_result.duration,
                        "dry_run": dry_run,
                    },
                ),
            )

            return deployment_result

        except Exception as e:
            self.logger.exception(f"Infrastructure deployment failed: {e}")

            await self.emit_event(
                OrchestrationEvent(
                    event_type="deployment.failed",
                    timestamp=datetime.now(),
                    source="orchestrator",
                    data={"error": str(e), "dry_run": dry_run},
                ),
            )

            return OrchestrationResult(
                operation="deploy_full_infrastructure",
                status="failure",
                duration=(datetime.now() - start_time).total_seconds(),
                details={"error": str(e)},
                recommendations=["Check logs for detailed error information"],
            )

    async def validate_system_health(self) -> OrchestrationResult:
        """Perform comprehensive system health validation.

        Returns:
            OrchestrationResult with health status and recommendations
        """
        start_time = datetime.now()
        self.logger.info("Starting comprehensive system health validation")

        try:
            # Run parallel health checks
            health_tasks = [
                self.health_monitor.comprehensive_health_check(),
                self.security_manager.validate_security_posture(),
            ]

            # Add GPU health check if enabled
            if self.gpu_manager:
                health_tasks.append(self.gpu_manager.check_gpu_health())

            # Add cluster health check for remote deployments
            if self.cluster_manager:
                health_tasks.append(self.cluster_manager.check_cluster_health())

            # Execute all health checks concurrently
            results = await asyncio.gather(*health_tasks, return_exceptions=True)

            # Process results
            overall_status = "success"
            details = {}
            recommendations = []

            health_result = results[0] if not isinstance(results[0], Exception) else None
            security_result = results[1] if not isinstance(results[1], Exception) else None

            if health_result:
                details["health"] = health_result
                if health_result.get("status") != "healthy":
                    overall_status = "warning"
                    recommendations.extend(health_result.get("recommendations", []))

            if security_result:
                details["security"] = security_result
                if security_result.get("status") != "secure":
                    overall_status = "warning"
                    recommendations.extend(security_result.get("recommendations", []))

            # Process GPU results if available
            if self.gpu_manager and len(results) > 2:
                gpu_result = results[2] if not isinstance(results[2], Exception) else None
                if gpu_result:
                    details["gpu"] = gpu_result
                    if gpu_result.get("status") != "healthy":
                        overall_status = "warning"
                        recommendations.extend(gpu_result.get("recommendations", []))

            # Process cluster results if available
            if self.cluster_manager and len(results) > (3 if self.gpu_manager else 2):
                cluster_result = results[-1] if not isinstance(results[-1], Exception) else None
                if cluster_result:
                    details["cluster"] = cluster_result
                    if cluster_result.get("status") != "healthy":
                        overall_status = "warning"
                        recommendations.extend(cluster_result.get("recommendations", []))

            return OrchestrationResult(
                operation="validate_system_health",
                status=overall_status,
                duration=(datetime.now() - start_time).total_seconds(),
                details=details,
                recommendations=list(set(recommendations)),  # Remove duplicates
            )

        except Exception as e:
            self.logger.exception(f"System health validation failed: {e}")
            return OrchestrationResult(
                operation="validate_system_health",
                status="failure",
                duration=(datetime.now() - start_time).total_seconds(),
                details={"error": str(e)},
                recommendations=["Check orchestrator logs for detailed error information"],
            )

    async def manage_gpu_resources(self, operation: str, **kwargs) -> OrchestrationResult:
        """Manage GPU resources (allocate, release, monitor).

        Args:
            operation: GPU operation (allocate, release, monitor, discover)
            **kwargs: Operation-specific arguments

        Returns:
            OrchestrationResult with GPU operation status
        """
        if not self.gpu_manager:
            return OrchestrationResult(
                operation=f"gpu_{operation}",
                status="failure",
                duration=0.0,
                details={"error": "GPU management not enabled"},
                recommendations=["Enable GPU support in configuration"],
            )

        start_time = datetime.now()
        self.logger.info(f"Managing GPU resources: {operation}")

        try:
            if operation == "discover":
                result = await self.gpu_manager.discover_gpu_resources()
            elif operation == "allocate":
                result = await self.gpu_manager.allocate_gpu_resource(**kwargs)
            elif operation == "release":
                result = await self.gpu_manager.release_gpu_resource(**kwargs)
            elif operation == "monitor":
                result = await self.gpu_manager.get_resource_status()
            else:
                msg = f"Unknown GPU operation: {operation}"
                raise ValueError(msg)

            return OrchestrationResult(
                operation=f"gpu_{operation}",
                status="success" if result.get("success", True) else "failure",
                duration=(datetime.now() - start_time).total_seconds(),
                details=result,
                recommendations=result.get("recommendations", []),
            )

        except Exception as e:
            self.logger.exception(f"GPU operation {operation} failed: {e}")
            return OrchestrationResult(
                operation=f"gpu_{operation}",
                status="failure",
                duration=(datetime.now() - start_time).total_seconds(),
                details={"error": str(e)},
                recommendations=["Check GPU manager logs for detailed error information"],
            )

    async def _run_pre_deployment_validation(self) -> dict[str, Any]:
        """Run pre-deployment validation checks.

        Returns:
            Validation result with status and errors
        """
        self.logger.info("Running pre-deployment validation")

        errors = []
        warnings = []

        # Configuration validation
        config_validation = self.config_manager.validate_configuration()
        if config_validation["status"] != "valid":
            errors.extend(config_validation["issues"])
        warnings.extend(config_validation["warnings"])

        # Security validation
        try:
            security_result = await self.security_manager.validate_pre_deployment()
            if not security_result.get("valid", True):
                errors.extend(security_result.get("errors", []))
        except Exception as e:
            warnings.append(f"Security pre-validation failed: {e}")

        # Resource validation
        try:
            resource_result = await self.deployment_manager.validate_resources()
            if not resource_result.get("valid", True):
                errors.extend(resource_result.get("errors", []))
        except Exception as e:
            warnings.append(f"Resource validation failed: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # Event handlers
    async def _handle_deployment_started(self, event: OrchestrationEvent) -> None:
        """Handle deployment started event."""
        self.logger.info(f"Deployment started: {event.data}")
        # Could trigger notifications, webhooks, etc.

    async def _handle_deployment_completed(self, event: OrchestrationEvent) -> None:
        """Handle deployment completed event."""
        self.logger.info(f"Deployment completed: {event.data}")
        # Could trigger success notifications

    async def _handle_deployment_failed(self, event: OrchestrationEvent) -> None:
        """Handle deployment failed event."""
        self.logger.error(f"Deployment failed: {event.data}")
        # Could trigger alert notifications

    async def _handle_health_failure(self, event: OrchestrationEvent) -> None:
        """Handle health check failure event."""
        self.logger.warning(f"Health check failed: {event.data}")
        # Could trigger automated remediation

    async def _handle_health_recovery(self, event: OrchestrationEvent) -> None:
        """Handle health check recovery event."""
        self.logger.info(f"Health check recovered: {event.data}")

    async def _handle_security_violation(self, event: OrchestrationEvent) -> None:
        """Handle security violation event."""
        self.logger.error(f"Security violation detected: {event.data}")
        # Could trigger immediate security response

    async def _handle_certificate_expiry(self, event: OrchestrationEvent) -> None:
        """Handle certificate expiring event."""
        self.logger.warning(f"Certificate expiring: {event.data}")
        # Could trigger automatic renewal

    async def _handle_gpu_allocation(self, event: OrchestrationEvent) -> None:
        """Handle GPU resource allocation event."""
        self.logger.info(f"GPU resource allocated: {event.data}")

    async def _handle_gpu_release(self, event: OrchestrationEvent) -> None:
        """Handle GPU resource release event."""
        self.logger.info(f"GPU resource released: {event.data}")

    def get_system_status(self) -> dict[str, Any]:
        """Get current system status and metrics.

        Returns:
            System status dictionary
        """
        return {
            "orchestrator": {
                "status": "running",
                "event_queue_size": self.event_queue.qsize(),
                "running_tasks": len(self.running_tasks),
                "thread_pool_active": self.thread_pool._threads,
            },
            "configuration": {
                "environment": self.config_manager.context.environment,
                "cluster_type": self.config_manager.context.cluster_type,
                "gpu_enabled": self.config_manager.context.gpu_enabled,
                "sso_enabled": self.config_manager.context.sso_enabled,
                "monitoring_enabled": self.config_manager.context.monitoring_enabled,
            },
            "managers": {
                "deployment": self.deployment_manager is not None,
                "health": self.health_monitor is not None,
                "security": self.security_manager is not None,
                "gpu": self.gpu_manager is not None,
                "webhook": self.webhook_manager is not None,
                "cluster": self.cluster_manager is not None,
            },
        }
