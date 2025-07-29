"""
Homelab Orchestrator - Unified Infrastructure Automation System.

A minimalist, clean Python framework that consolidates all homelab automation:
- Configuration management integration
- Deployment orchestration with hooks
- Health monitoring and validation
- SSO and security management
- GPU resource discovery and management
- Webhook and event processing
- Remote server/cluster integration

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License
"""

__version__ = "1.0.0"
__author__ = "Tyler Zervas"

from .core.config_manager import ConfigManager
from .core.deployment import DeploymentManager
from .core.gpu_manager import GPUResourceManager
from .core.health import HealthMonitor
from .core.orchestrator import HomelabOrchestrator
from .core.security import SecurityManager
from .remote.cluster_manager import ClusterManager
from .webhooks.manager import WebhookManager


__all__ = [
<<<<<<< HEAD
    "ClusterManager",
    "ConfigManager",
    "DeploymentManager",
    "GPUResourceManager",
    "HealthMonitor",
    "HomelabOrchestrator",
    "SecurityManager",
    "WebhookManager",
=======
    "ConfigManager",
    "HomelabOrchestrator",
    "DeploymentManager",
    "HealthMonitor",
    "SecurityManager",
    "GPUResourceManager",
    "WebhookManager",
    "ClusterManager",
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
]
