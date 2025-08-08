"""Type definitions for homelab orchestrator results."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

class ResourceType(Enum):
    """Types of managed resources."""
    DEPLOYMENT = "deployment"
    SERVICE = "service" 
    VOLUME = "volume"
    SECRET = "secret"
    CONFIGMAP = "configmap"
    NAMESPACE = "namespace"

class OperationStatus(Enum):
    """Status values for operations."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ResourceResult:
    """Result of a resource operation."""
    name: str
    type: ResourceType
    status: OperationStatus
    message: str = ""
    error: Optional[Exception] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass 
class DeploymentResult:
    """Result of a deployment operation."""
    name: str
    status: OperationStatus
    resources: List[ResourceResult] = field(default_factory=list)
    duration: float = 0.0
    error: Optional[Exception] = None
    logs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class OrchestrationResult:
    """Result of a full orchestration run."""
    status: OperationStatus
    deployments: List[DeploymentResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    duration: float = 0.0
    error: Optional[Exception] = None
    logs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TestSuiteResult:
    """Result of a test suite run."""
    status: OperationStatus
    test_count: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    warnings: int = 0
    duration: float = 0.0
    error: Optional[Exception] = None
    logs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationResult:
    """Result of a validation run."""
    status: OperationStatus
    passed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration: float = 0.0
    error: Optional[Exception] = None
    logs: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
