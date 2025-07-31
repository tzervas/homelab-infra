"""Service models for Homelab Portal."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Service health check result."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    response_time_ms: float | None = None
    error_message: str | None = None
    details: dict[str, any] = Field(default_factory=dict)


class Service(BaseModel):
    """Service information model."""

    name: str
    namespace: str
    service: str
    url: str
    icon: str = "🔧"
    description: str = ""
    health: ServiceHealth | None = None
    metrics: dict[str, any] = Field(default_factory=dict)

    @property
    def display_status(self) -> str:
        """Get display-friendly status."""
        if not self.health:
            return "Unknown"

        status_map = {
            ServiceStatus.HEALTHY: "Running",
            ServiceStatus.DEGRADED: "Degraded",
            ServiceStatus.UNHEALTHY: "Down",
            ServiceStatus.UNKNOWN: "Unknown",
        }
        return status_map.get(self.health.status, "Unknown")

    @property
    def status_class(self) -> str:
        """Get CSS class for status."""
        if not self.health:
            return "status-unknown"

        class_map = {
            ServiceStatus.HEALTHY: "status-running",
            ServiceStatus.DEGRADED: "status-starting",
            ServiceStatus.UNHEALTHY: "status-error",
            ServiceStatus.UNKNOWN: "status-unknown",
        }
        return class_map.get(self.health.status, "status-unknown")
