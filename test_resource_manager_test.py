import pytest
import logging
from concurrent.futures import ThreadPoolExecutor
from test_resource_manager import TestResourceManager, TestOrchestrator

@pytest.fixture
def resource_manager():
    """Fixture providing a TestResourceManager instance."""
    return TestResourceManager()

@pytest.fixture
def orchestrator():
    """Fixture providing a TestOrchestrator instance."""
    return TestOrchestrator()

def test_acquire_release(resource_manager):
    """Test basic lock acquisition and release."""
    with resource_manager.acquire('k3s'):
        assert 'k3s' in resource_manager.acquired
    assert 'k3s' not in resource_manager.acquired

def test_invalid_resource(resource_manager):
    """Test handling of invalid resource names."""
    with pytest.raises(KeyError):
        with resource_manager.acquire('nonexistent'):
            pass

def test_deadlock_detection(resource_manager):
    """Test deadlock detection with multiple locks."""
    with resource_manager.acquire('k3s'):
        assert not resource_manager.check_deadlock()
        with resource_manager.acquire('python_framework'):
            assert resource_manager.check_deadlock()
        assert not resource_manager.check_deadlock()

def test_lock_timeout():
    """Test lock timeout handling."""
    manager = TestResourceManager()
    
    def acquire_lock():
        with manager.acquire('k3s', timeout=1.0):
            return True
            
    # First acquisition should succeed
    with manager.acquire('k3s'):
        # Second acquisition should timeout
        with ThreadPoolExecutor() as executor:
            future = executor.submit(acquire_lock)
            with pytest.raises(TimeoutError):
                future.result()

def test_orchestrator_integration(orchestrator, caplog):
    """Test orchestrator integration with resource management."""
    caplog.set_level(logging.ERROR)
    orchestrator.run_integrated_test_suite()
    assert "Potential deadlock detected" in caplog.text
