from threading import Lock, RLock
from contextlib import contextmanager
import logging
from typing import Set
from datetime import datetime, timezone
import concurrent.futures
import subprocess
from contextlib import contextmanager

class TestResourceManager:
    """Manages test resources with locking mechanism and deadlock detection."""
    
    def __init__(self) -> None:
        """Initialize the test resource manager with locks."""
        self.logger = logging.getLogger(__name__)
        self.locks = {
            'k3s': RLock(),
            'python_framework': RLock(),
            'cleanup': Lock()
        }
        self.acquired: Set[str] = set()
        
    @contextmanager
    def acquire(self, resource: str, timeout: float = 10.0) -> None:
        """
        Acquire a lock for the specified resource.
        
        Args:
            resource: The name of the resource to lock
            timeout: Maximum time to wait for lock acquisition
            
        Raises:
            TimeoutError: If lock cannot be acquired within timeout
            KeyError: If resource does not exist
        """
        if resource not in self.locks:
            raise KeyError(f"Unknown resource: {resource}")
            
        if not self.locks[resource].acquire(timeout=timeout):
            raise TimeoutError(f"Could not acquire {resource} lock")
            
        try:
            self.logger.debug(f"Acquired lock for {resource}")
            self.acquired.add(resource)
            yield
        finally:
            self.locks[resource].release()
            self.acquired.remove(resource)
            self.logger.debug(f"Released lock for {resource}")
            
    def check_deadlock(self) -> bool:
        """
        Check for potential deadlock conditions.
        
        Returns:
            bool: True if potential deadlock detected, False otherwise
        """
        if len(self.acquired) > 1:
            resources = ", ".join(sorted(self.acquired))
            self.logger.warning(f"Multiple locks held: {resources}")
            return True
        return False

class ProgressMonitor:
    """Monitor and track test execution progress."""

    def __init__(self):
        """Initialize the progress monitor."""
        self.test_states = {}

    def update_state(self, test_name: str, state: str):
        """Update the state of a test."""
        self.test_states[test_name] = state


class TestOrchestrator:
    """Orchestrates test execution with resource management."""
    
    def __init__(self) -> None:
        """Initialize the test orchestrator."""
        self.logger = logging.getLogger(__name__)
        self.resource_mgr = TestResourceManager()
        self.progress_monitor = ProgressMonitor()

    @contextmanager
    def error_context(self, operation: str):
        """Provide detailed context for errors."""
        try:
            yield
        except Exception as e:
            self.logger.error(
                "Error during %s: %s\nContext: %s",
                operation,
                str(e),
                {
                    'timestamp': datetime.now(timezone.utc),
                    'resource_state': self.resource_mgr.acquired,
                    'test_progress': self.progress_monitor.test_states
                }
            )
            raise

    def categorize_failure(self, error: Exception) -> dict:
        """Categorize test failures for better debugging."""
        categories = {
            'timeout': isinstance(error, (concurrent.futures.TimeoutError, subprocess.TimeoutExpired)),
            'resource': isinstance(error, (PermissionError, OSError)),
            'validation': isinstance(error, ValueError),
            'framework': isinstance(error, (ImportError, AttributeError)),
            'unknown': True  # Default category
        }
        return {cat: True for cat, matches in categories.items() if matches}
    
    def cleanup_test_resources(self):
        """Clean up test resources on failure."""
        with self.error_context('cleanup'):
            for resource in list(self.resource_mgr.acquired):
                try:
                    with self.resource_mgr.acquire('cleanup'):
                        # Perform resource-specific cleanup
                        self.logger.info(f"Cleaning up {resource}")
                except Exception as e:
                    self.logger.error(f"Cleanup failed for {resource}: {e}")
        
    def run_integrated_test_suite(self) -> None:
        """Run the integrated test suite with resource locking."""
        try:
            with self.resource_mgr.acquire('k3s'):
                with self.resource_mgr.acquire('python_framework'):
                    if self.resource_mgr.check_deadlock():
                        self.logger.error("Potential deadlock detected")
                    # Run test suite logic here
                    self.logger.info("Running integrated test suite")
        except TimeoutError as e:
            self.logger.error(f"Resource lock acquisition failed: {e}")
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {e}")
