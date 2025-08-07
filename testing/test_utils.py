"""Tests for test environment utilities."""
import pytest
import logging
import time
from unittest.mock import Mock, patch, call
from typing import Dict, Any

from .utils import TestEnvironment

@pytest.fixture
def mock_k8s_api():
    """Mock Kubernetes API client."""
    with patch('kubernetes.client.CoreV1Api') as mock_api:
        yield mock_api()

@pytest.fixture
def test_env(mock_k8s_api):
    """Create a test environment instance with mocked K8s API."""
    env = TestEnvironment()
    env.api = mock_k8s_api
    return env

def test_init_test_environment():
    """Test TestEnvironment initialization."""
    env = TestEnvironment()
    assert env.namespace.startswith('test-')
    assert len(env.namespace) == 13  # 'test-' + 8 hex chars
    assert env.quotas == {
        'cpu': '2',
        'memory': '2Gi',
        'pods': '10'
    }

def test_init_with_custom_quotas():
    """Test TestEnvironment initialization with custom quotas."""
    custom_quotas = {
        'cpu': '4',
        'memory': '4Gi',
        'pods': '20'
    }
    env = TestEnvironment(quotas=custom_quotas)
    assert env.quotas == custom_quotas

def test_setup_creates_namespace_and_quotas(test_env, mock_k8s_api):
    """Test environment setup creates namespace and applies quotas."""
    test_env.setup()
    
    # Verify namespace creation
    mock_k8s_api.create_namespace.assert_called_once()
    ns_name = mock_k8s_api.create_namespace.call_args[0][0].metadata.name
    assert ns_name == test_env.namespace
    
    # Verify quota creation
    mock_k8s_api.create_namespaced_resource_quota.assert_called_once()
    quota_name = mock_k8s_api.create_namespaced_resource_quota.call_args[0][1].metadata.name
    assert quota_name == f"{test_env.namespace}-quota"

def test_teardown_deletes_namespace(test_env, mock_k8s_api):
    """Test environment teardown deletes namespace."""
    test_env.teardown()
    mock_k8s_api.delete_namespace.assert_called_once_with(
        name=test_env.namespace,
        body=mock_k8s_api.delete_namespace.call_args[1]['body']
    )

def test_validate_dependencies_with_missing_deps(test_env):
    """Test dependency validation with missing dependencies."""
    test_config = {'dependencies': ['dep1', 'dep2']}
    with patch.object(test_env, 'get_available_resources', return_value={'dep1'}):
        assert not test_env.validate_test_dependencies(test_config)

def test_validate_dependencies_with_all_deps_available(test_env):
    """Test dependency validation with all dependencies available."""
    test_config = {'dependencies': ['dep1', 'dep2']}
    with patch.object(test_env, 'get_available_resources', 
                     return_value={'dep1', 'dep2', 'dep3'}):
        assert test_env.validate_test_dependencies(test_config)

def test_managed_fixture_cleanup(test_env):
    """Test fixture cleanup in managed_test_fixture."""
    fixture1 = Mock()
    fixture2 = Mock()
    
    with patch.object(test_env, 'create_fixture', 
                     side_effect=[fixture1, fixture2]) as mock_create:
        fixture_config = {
            'fixtures': [
                {'type': 'test1'},
                {'type': 'test2'}
            ]
        }
        
        with test_env.managed_test_fixture(fixture_config) as fixtures:
            assert len(fixtures) == 2
            assert fixtures[0] == fixture1
            assert fixtures[1] == fixture2
        
        # Verify cleanup was called in reverse order
        fixture2.cleanup.assert_called_once()
        fixture1.cleanup.assert_called_once()

def test_create_fixture_requires_type(test_env):
    """Test create_fixture requires type specification."""
    with pytest.raises(ValueError, match="must specify 'type'"):
        test_env.create_fixture({})

def test_create_fixture_not_implemented(test_env):
    """Test create_fixture raises NotImplementedError."""
    with pytest.raises(NotImplementedError, 
                      match="Creation of fixture type 'test' not implemented"):
        test_env.create_fixture({'type': 'test'})

def test_logging_during_setup(caplog, test_env, mock_k8s_api):
    """Test logging during environment setup."""
    with caplog.at_level(logging.INFO):
        test_env.setup()
        
    assert f"Created test namespace: {test_env.namespace}" in caplog.text
    assert f"Applied resource quotas to namespace: {test_env.namespace}" in caplog.text

def test_logging_during_teardown(caplog, test_env, mock_k8s_api):
    """Test logging during environment teardown."""
    with caplog.at_level(logging.INFO):
        test_env.teardown()
        
    assert f"Deleted test namespace: {test_env.namespace}" in caplog.text

def test_error_handling_during_setup(test_env, mock_k8s_api):
    """Test error handling during setup."""
    mock_k8s_api.create_namespace.side_effect = Exception("Test error")
    
    with pytest.raises(Exception, match="Test error"):
        test_env.setup()

# Test RetryConfig and with_retry decorator
def test_retry_with_success():
    """Test retry decorator with successful execution."""
    mock_func = Mock(return_value="success")
    decorated = with_retry()(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_with_eventual_success():
    """Test retry decorator with success after failures."""
    mock_func = Mock(side_effect=[ValueError, ValueError, "success"])
    retry_config = RetryConfig(max_retries=3, min_backoff=0.1)
    decorated = with_retry(retry_config)(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 3

def test_retry_with_all_failures():
    """Test retry decorator with all attempts failing."""
    error = ValueError("test error")
    mock_func = Mock(side_effect=error)
    retry_config = RetryConfig(max_retries=2, min_backoff=0.1)
    decorated = with_retry(retry_config)(mock_func)
    
    with pytest.raises(ValueError, match="test error"):
        decorated()
    assert mock_func.call_count == 2

# Test CircuitBreaker
@pytest.fixture
def circuit_breaker():
    """Fixture providing a CircuitBreaker instance."""
    return CircuitBreaker(threshold=2, window_size=1, reset_timeout=1)

def test_circuit_breaker_normal_operation(circuit_breaker):
    """Test circuit breaker under normal operation."""
    assert circuit_breaker.can_proceed()
    circuit_breaker.record_failure()
    assert circuit_breaker.can_proceed()

def test_circuit_breaker_trips_after_threshold(circuit_breaker):
    """Test circuit breaker trips after threshold reached."""
    for _ in range(circuit_breaker.threshold):
        circuit_breaker.record_failure()
    
    assert not circuit_breaker.can_proceed()

def test_circuit_breaker_resets_after_timeout(circuit_breaker):
    """Test circuit breaker resets after timeout."""
    # Trip the breaker
    for _ in range(circuit_breaker.threshold):
        circuit_breaker.record_failure()
    assert not circuit_breaker.can_proceed()
    
    # Wait for reset timeout
    time.sleep(circuit_breaker.reset_timeout)
    assert circuit_breaker.can_proceed()

# Test TestProgressMonitor
@pytest.fixture
def progress_monitor():
    """Fixture providing a TestProgressMonitor instance."""
    return TestProgressMonitor()

def test_test_progress_monitor_update(progress_monitor):
    """Test progress monitor state updates."""
    progress_monitor.update_progress("test1", "running")
    assert "test1" in progress_monitor.test_states
    assert progress_monitor.test_states["test1"]["status"] == "running"

def test_test_progress_monitor_stalled_tests(progress_monitor):
    """Test stalled test detection."""
    progress_monitor.update_progress("test1", "running")
    # Use a proper timeout mechanism instead of arbitrary sleep
    start_time = time.time()
    while time.time() - start_time < 0.1:
        pass  # Brief busy wait instead of sleep
    
    # No stalled tests yet
    assert not progress_monitor.check_stalled_tests(1.0)
    
    # Test should be stalled after timeout
    assert progress_monitor.check_stalled_tests(0.05) == ["test1"]

def test_test_progress_monitor_progress_summary(progress_monitor):
    """Test progress summary calculation."""
    progress_monitor.update_progress("test1", "passed")
    progress_monitor.update_progress("test2", "running")
    progress_monitor.update_progress("test3", "failed")
    
    summary = progress_monitor.get_progress_summary()
    assert summary["total_tests"] == 3
    assert summary["completed"] == 2
    assert summary["running"] == 1
    assert summary["completion_percentage"] == pytest.approx(66.67, rel=1e-2)
    """Test error handling during setup."""
    mock_k8s_api.create_namespace.side_effect = Exception("Test error")
    
    with pytest.raises(Exception, match="Test error"):
        test_env.setup()

def test_managed_fixture_cleanup_failure(test_env):
    """Test fixture cleanup in managed_test_fixture when creation fails."""
    fixture1 = Mock()
    
    # Second fixture creation fails
    with patch.object(test_env, 'create_fixture', 
                     side_effect=[fixture1, Exception("Creation failed")]) as mock_create:
        fixture_config = {
            'fixtures': [
                {'type': 'test1'},
                {'type': 'test2'}  # This will fail
            ]
        }
        
        with pytest.raises(Exception, match="Creation failed"):
            with test_env.managed_test_fixture(fixture_config):
                pass
        
        # Verify first fixture was cleaned up even though second failed
        fixture1.cleanup.assert_called_once()


def test_retry_with_non_retryable_exceptions():
    """Test retry decorator with non-retryable exceptions."""
    # KeyboardInterrupt should not be retried
    mock_func = Mock(side_effect=KeyboardInterrupt())
    retry_config = RetryConfig(max_retries=3, min_backoff=0.1)
    decorated = with_retry(retry_config)(mock_func)
    
    with pytest.raises(KeyboardInterrupt):
        decorated()
    assert mock_func.call_count == 1  # Should not retry
    
    # SystemExit should not be retried
    mock_func = Mock(side_effect=SystemExit())
    decorated = with_retry(retry_config)(mock_func)
    
    with pytest.raises(SystemExit):
        decorated()
    assert mock_func.call_count == 1  # Should not retry


def test_circuit_breaker_manual_reset(circuit_breaker):
    """Test circuit breaker reset after manual reset."""
    # Trip the breaker
    for _ in range(circuit_breaker.threshold):
        circuit_breaker.record_failure()
    
    assert not circuit_breaker.can_proceed()
    
    # Manual reset should restore normal operation immediately
    circuit_breaker.reset()
    assert circuit_breaker.can_proceed()