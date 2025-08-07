"""Test utilities for managing test environments and fixtures.

This module provides utilities for test isolation, dependency validation,
and fixture management in the testing environment.
"""
import logging
import random
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, Iterator, List, Set

from kubernetes import client, config
from kubernetes.client.rest import ApiException

@dataclass
class RetryConfig:
    """Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplicative factor for exponential backoff
        max_backoff: Maximum backoff time in seconds
        min_backoff: Minimum backoff time in seconds
    """
    max_retries: int = 3
    backoff_factor: float = 1.5
    max_backoff: int = 60
    min_backoff: int = 1
    jitter: bool = True  # Add jitter to prevent thundering herd
# Configure logging
logger = logging.getLogger(__name__)

class TestProgressMonitor:
    """Monitors test execution progress and detects stalled tests.
    
    Attributes:
        start_time: Time when monitoring started
        test_states: Dictionary mapping test names to their current states
        state_history: History of state changes for analysis
    """
    
    def __init__(self) -> None:
        self.start_time = time.time()
        self.test_states: Dict[str, Dict[str, Any]] = {}
        self.state_history: List[Dict[str, Any]] = []
        
    def update_progress(self, test_name: str, status: str) -> None:
        """Update the status and duration for a specific test.
        
        Args:
            test_name: Name of the test being monitored
            status: Current status of the test
        """
        current_time = time.time()
        state = {
            'status': status,
            'duration': current_time - self.start_time,
            'timestamp': current_time
        }
        
        self.test_states[test_name] = state
        self.state_history.append({
            'test_name': test_name,
            'status': status,
            'timestamp': current_time
        })
        
        logger.debug(f"Updated test {test_name} status to {status}")
        
    def check_stalled_tests(self, timeout: float) -> List[str]:
        """Identify tests that have exceeded the timeout threshold.
        
        Args:
            timeout: Maximum allowed duration in seconds
            
        Returns:
            List of test names that have exceeded the timeout
        """
        current_time = time.time()
        stalled = [
            test_name for test_name, state in self.test_states.items()
            if state['status'] == 'running' 
            and (current_time - state['timestamp']) > timeout
        ]
        
        if stalled:
            logger.warning(
                f"Found {len(stalled)} stalled tests: {', '.join(stalled)}"
            )
            
        return stalled
    
    def get_test_duration(self, test_name: str) -> float:
        """Get the current duration of a specific test.
        
        Args:
            test_name: Name of the test to check
            
        Returns:
            Duration in seconds since the test started, or 0.0 if not found
        """
        if test_name in self.test_states:
            return time.time() - self.test_states[test_name]['timestamp']
        return 0.0
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of current test progress.
        
        Returns:
            Dictionary with test progress statistics
        """
        total = len(self.test_states)
        completed = sum(
            1 for state in self.test_states.values() 
            if state['status'] in ('passed', 'failed', 'skipped')
        )
        running = sum(
            1 for state in self.test_states.values()
            if state['status'] == 'running'
        )
        
        return {
            'total_tests': total,
            'completed': completed,
            'running': running,
            'completion_percentage': (completed / total * 100) if total > 0 else 0,
            'total_duration': time.time() - self.start_time
        }

class CircuitBreaker:
    """Circuit breaker pattern implementation to prevent cascading failures.
    
    Attributes:
        threshold: Number of failures before tripping the breaker
        window_size: Time window in seconds for failure counting
        reset_timeout: Time in seconds before attempting to reset breaker
    """
    
    def __init__(self, threshold: int = 5, window_size: int = 60, reset_timeout: int = 30) -> None:
        self.threshold = threshold
        self.window_size = window_size
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.tripped = False
        self.last_failure_time = 0.0
        self.last_trip_time = 0.0
        
    def record_failure(self) -> None:
        """Record a failure and potentially trip the circuit breaker."""
        current_time = time.time()
        # Reset failure count if outside window
        if current_time - self.last_failure_time > self.window_size:
            self.failures = 0
            
        self.failures += 1
        self.last_failure_time = current_time
        
        if self.failures >= self.threshold:
            self.trip()
            
    def trip(self) -> None:
        """Trip the circuit breaker."""
        self.tripped = True
        self.last_trip_time = time.time()
        logger.warning(f"Circuit breaker tripped after {self.failures} failures")
            
    def reset(self) -> None:
        """Reset the circuit breaker state."""
        self.failures = 0
        self.tripped = False
        self.last_failure_time = 0.0
        self.last_trip_time = 0.0
        logger.info("Circuit breaker reset")
        
    def can_proceed(self) -> bool:
        """Check if the circuit breaker allows proceeding with the operation."""
        if not self.tripped:
            return True
            
        # Check if we should attempt reset
        if time.time() - self.last_trip_time > self.reset_timeout:
            self.reset()
            return True
            
        return False

def with_retry(retry_config: RetryConfig | None = None):
    """Decorator for retrying operations with exponential backoff.
    
    Args:
        retry_config: Optional retry configuration. If not provided, defaults are used.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = retry_config or RetryConfig()
            attempt = 0
            last_error = None
            
            while attempt < config.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    attempt += 1
                    
                    if attempt < config.max_retries:
                        # Calculate backoff with optional jitter
                        backoff = min(
                            config.max_backoff,
                            config.min_backoff * (config.backoff_factor ** attempt)
                        )
                        if config.jitter:
                            backoff *= (1 + random.random() * 0.1)  # 10% jitter
                            
                        logger.warning(
                            f"Attempt {attempt} failed: {e}. Retrying in {backoff:.1f}s"
                        )
                        time.sleep(backoff)
                        
            # If we get here, all retries failed
            logger.error(f"All {config.max_retries} retry attempts failed")
            raise last_error
            
        return wrapper
    return decorator

class TestEnvironment:
    """Manages an isolated test environment with resource quotas and cleanup.
    
    This class handles the creation and cleanup of isolated test environments,
    including namespace management and resource quota enforcement.
    
    Attributes:
        namespace: Unique namespace for test isolation
        resources: Set of available resources in the environment
        quotas: Resource quotas for the namespace
        logger: Logger instance for the test environment
    """
    
    def __init__(self, 
                 quotas: Dict[str, str] | None = None,
                 logger: logging.Logger | None = None,
                 retry_config: RetryConfig | None = None,
                 circuit_breaker_config: Dict[str, int] | None = None) -> None:
        """Initialize a new test environment.
        
        Args:
            quotas: Optional custom resource quotas. If not provided, defaults are used.
            logger: Optional logger instance. If not provided, module logger is used.
        """
        self.namespace = f"test-{uuid.uuid4().hex[:8]}"
        self.resources: Set[str] = set()
        self.quotas = quotas or {
            'cpu': '2',
            'memory': '2Gi',
            'pods': '10'
        }
        self.logger = logger or logging.getLogger(__name__)
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(
            **(circuit_breaker_config or {})
        )
        self.progress_monitor = TestProgressMonitor()
        
        # Initialize Kubernetes client
        try:
            config.load_kube_config()
        except Exception:
            try:
                config.load_incluster_config()
            except Exception as e:
                self.logger.error(f"Failed to load Kubernetes configuration: {e}")
                raise
                
        self.api = client.CoreV1Api()
        
    def setup(self) -> None:
        """Set up isolated test environment.
        
        Creates a new namespace and applies resource quotas.
        
        Raises:
            ApiException: If namespace creation or quota application fails
            RuntimeError: If circuit breaker is open
        """
        if not self.circuit_breaker.can_proceed():
            raise RuntimeError("Circuit breaker is open")
            
        try:
            self.progress_monitor.update_progress("namespace_creation", "running")
            self._create_namespace()
            self.logger.info(f"Created test namespace: {self.namespace}")
            self.progress_monitor.update_progress("namespace_creation", "completed")
            
            self.progress_monitor.update_progress("quota_creation", "running")
            self._create_resource_quota()
            self.logger.info(f"Applied resource quotas to namespace: {self.namespace}")
            self.progress_monitor.update_progress("quota_creation", "completed")
            
        except ApiException as e:
            self.logger.error(f"Failed to set up test environment: {e}")
            self.circuit_breaker.record_failure()
            self.teardown()  # Cleanup any partially created resources
            raise
        except Exception as e:
            self.logger.error(f"Failed to set up test environment: {e}")
            self.circuit_breaker.record_failure()
            raise

    def teardown(self) -> None:
        """Clean up test environment.
        
        Deletes the namespace and all resources within it.
        """
        try:
            self.api.delete_namespace(
                name=self.namespace,
                body=client.V1DeleteOptions(
                    propagation_policy='Foreground'
                )
            )
            self.logger.info(f"Deleted test namespace: {self.namespace}")
            
        except ApiException as e:
            self.logger.error(f"Failed to delete namespace {self.namespace}: {e}")
            raise
            
    def get_available_resources(self) -> Set[str]:
        """Get the set of available resources in the environment.
        
        Returns:
            Set of resource names available in the environment
        """
        try:
            api_resources = self.api.get_api_resources()
            return {resource.name for resource in api_resources.resources 
                   if resource.namespaced}
        except ApiException as e:
            self.logger.error(f"Failed to get available resources: {e}")
            return set()
            
    def validate_test_dependencies(self, test_config: Dict[str, Any]) -> bool:
        """Validate test dependencies before execution.
        
        Args:
            test_config: Test configuration containing required dependencies
            
        Returns:
            bool: True if all dependencies are available, False otherwise
        """
        required = set(test_config.get('dependencies', []))
        available = self.get_available_resources()
        missing = required - available
        
        if missing:
            self.logger.error(f"Missing dependencies: {missing}")
            return False
        return True

    @with_retry()
    def _create_namespace(self) -> None:
        """Create Kubernetes namespace with retry."""
        ns = client.V1Namespace(
            metadata=client.V1ObjectMeta(name=self.namespace)
        )
        self.api.create_namespace(ns)

    @with_retry()
    def _create_resource_quota(self) -> None:
        """Create resource quota with retry."""
        quota_spec = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(name=f"{self.namespace}-quota"),
            spec=client.V1ResourceQuotaSpec(hard=self.quotas)
        )
        self.api.create_namespaced_resource_quota(
            self.namespace, quota_spec
        )

    @contextmanager
    def managed_test_fixture(self, fixture_config: Dict[str, Any]) -> Iterator[List[Any]]:
        """Manage test fixtures with proper cleanup.
        
        Context manager that handles the creation and cleanup of test fixtures.
        
        Args:
            fixture_config: Configuration for test fixtures
            
        Yields:
            List of created fixture objects
            
        Raises:
            Exception: If fixture creation fails
        """
        fixtures = []
        try:
            for fixture in fixture_config['fixtures']:
                fixture_obj = self.create_fixture(fixture)
                fixtures.append(fixture_obj)
            yield fixtures
            
        finally:
            # Clean up fixtures in reverse order
            for fixture in reversed(fixtures):
                try:
                    fixture.cleanup()
                except Exception as e:
                    self.logger.error(f"Fixture cleanup failed: {e}")
                    
    def create_fixture(self, fixture_config: Dict[str, Any]) -> Any:
        """Create a test fixture from configuration.
        
        Args:
            fixture_config: Configuration for the fixture to create
            
        Returns:
            Created fixture object
            
        Raises:
            ValueError: If fixture configuration is invalid
        """
        fixture_type = fixture_config.get('type')
        if not fixture_type:
            raise ValueError("Fixture configuration must specify 'type'")
            
        # Add fixture-specific creation logic here based on type
        raise NotImplementedError(
            f"Creation of fixture type '{fixture_type}' not implemented"
        )
