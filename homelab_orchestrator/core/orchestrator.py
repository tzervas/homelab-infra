import asyncio
import logging
from pathlib import Path
from typing import Any

from ..monitor import HealthMonitor
from ..network import IngressManager
from ..portal import PortalManager
from ..remote.cluster_manager import ClusterManager
from ..webhooks.manager import WebhookManager
from .certificates import CertificateManager
from .config_manager import ConfigManager
from .deployment import DeploymentManager
from .gpu_manager import GPUResourceManager


class HomelabOrchestrator:
    """Main orchestrator class for managing homelab deployment and operations."""

    def __init__(self, config_path: Path) -> None:
        """Initialize orchestrator with configuration path."""
        self.config_path = config_path

        # Load configuration
        self.config_manager = ConfigManager(config_path)
        config = self.config_manager.load_configuration()

        # Deployment managers
        deployment_config = config.get("deployment", {})
        self.deployment_manager = DeploymentManager(
            config_manager=self.config_manager,
        )

        # Certificate management
        self.certificate_manager = CertificateManager(
            config_manager=self.config_manager,
        )

        # GPU management (if enabled)
        if deployment_config.get("gpu", {}).get("enabled", False):
            self.gpu_manager = GPUResourceManager(
                config_manager=self.config_manager,
            )
        else:
            self.gpu_manager = None

        # Network management
        self.ingress_manager = IngressManager(
            config_manager=self.config_manager,
        )

        self.webhook_manager = WebhookManager(
            config_manager=self.config_manager,
        )

        self.health_monitor = HealthMonitor(
            config_manager=self.config_manager,
        )

    async def start(self) -> None:
        """Start orchestrator components."""
        # Start network monitoring
        await self.ingress_manager.start()
        await self.health_monitor.start()

        if self.gpu_manager:
            await self.gpu_manager.start_monitoring()

        # Start certificate manager
        await self.certificate_manager.start()

        # Start webhook server
        await self.webhook_manager.start()

    async def stop(self) -> None:
        """Stop orchestrator components."""
        await self.ingress_manager.stop()

        if self.gpu_manager:
            await self.gpu_manager.stop_monitoring()

        await self.health_monitor.stop_monitoring()
        await self.certificate_manager.stop()
        await self.webhook_manager.stop()

        # Shutdown thread pool
