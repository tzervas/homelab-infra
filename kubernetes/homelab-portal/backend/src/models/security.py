"""Security models for Homelab Portal."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityAlert(BaseModel):
    """Security alert model."""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    resolved: bool = False
    metadata: dict[str, any] = Field(default_factory=dict)


class CertificateInfo(BaseModel):
    """TLS certificate information."""

    common_name: str
    issuer: str
    not_before: datetime
    not_after: datetime
    days_until_expiry: int
    is_expired: bool = False
    is_expiring_soon: bool = False  # Within 30 days
    namespace: str
    secret_name: str


class NetworkPolicyStatus(BaseModel):
    """Network policy compliance status."""

    total_namespaces: int
    protected_namespaces: int
    unprotected_namespaces: list[str] = Field(default_factory=list)
    compliance_percentage: float


class RBACStatus(BaseModel):
    """RBAC audit status."""

    total_service_accounts: int
    privileged_accounts: int
    cluster_admin_bindings: int
    recent_changes: list[dict[str, any]] = Field(default_factory=list)


class PodSecurityStatus(BaseModel):
    """Pod security standards compliance."""

    total_pods: int
    compliant_pods: int
    non_compliant_pods: list[dict[str, str]] = Field(default_factory=list)
    enforcement_level: str = "baseline"


class AuthenticationMetrics(BaseModel):
    """Authentication metrics from Keycloak/OAuth2."""

    total_logins_24h: int = 0
    failed_logins_24h: int = 0
    active_sessions: int = 0
    unique_users_24h: int = 0
    suspicious_activities: list[dict[str, any]] = Field(default_factory=list)


class SecurityMetrics(BaseModel):
    """Aggregated security metrics."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cluster_name: str = "homelab"
    certificates: list[CertificateInfo] = Field(default_factory=list)
    network_policies: NetworkPolicyStatus | None = None
    rbac: RBACStatus | None = None
    pod_security: PodSecurityStatus | None = None
    authentication: AuthenticationMetrics | None = None
    recent_alerts: list[SecurityAlert] = Field(default_factory=list)
    security_score: int = 0  # 0-100
