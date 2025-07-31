"""Homelab Infrastructure Testing Framework.

A comprehensive testing framework for validating homelab infrastructure,
from configuration files to end-to-end service connectivity.

This framework integrates with the K3s validation framework located
in testing/k3s-validation/ for comprehensive cluster testing.
"""

__version__ = "0.1.0"
__author__ = "Tyler Zervas"
__email__ = "tz-dev@vectorweight.com"

# Import main classes for easy access
try:
    from .config_validator import ConfigValidator, ValidationResult
    from .infrastructure_health import ClusterHealth, InfrastructureHealthMonitor
    from .integrated_test_orchestrator import (
        IntegratedTestOrchestrator,
        IntegratedTestResults,
        K3sValidationResult,
    )
    from .integration_tester import IntegrationConnectivityTester, IntegrationTestResult
    from .network_security import NetworkSecurityValidator, SecurityStatus
    from .service_checker import ServiceDeploymentChecker, ServiceStatus
    from .test_reporter import HomelabTestReporter, TestSuiteResult
except ImportError as e:
    import warnings

    warnings.warn(f"ImportError in scripts.testing.__init__: {e}", ImportWarning)

__all__ = [
    "ClusterHealth",
    "ConfigValidator",
    "HomelabTestReporter",
    "InfrastructureHealthMonitor",
    "IntegratedTestOrchestrator",
    "IntegratedTestResults",
    "IntegrationConnectivityTester",
    "IntegrationTestResult",
    "K3sValidationResult",
    "NetworkSecurityValidator",
    "SecurityStatus",
    "ServiceDeploymentChecker",
    "ServiceStatus",
    "TestSuiteResult",
    "ValidationResult",
]
