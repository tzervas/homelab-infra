# Integration Testing Guide

## Overview

This guide covers integration testing procedures for the homelab infrastructure testing framework, including environment setup, test execution, and result validation.

## Test Categories

### Service-to-Service Communication

Tests validate communication between different services:

```python
@with_retry(RetryConfig(max_retries=3))
def test_service_communication():
    # Test GitLab to Keycloak SSO
    assert validate_sso_flow(
        source="gitlab",
        target="keycloak",
        timeout=30
    )
    
    # Test Prometheus to Grafana metrics
    assert validate_metrics_flow(
        source="prometheus",
        target="grafana",
        timeout=30
    )
```

### Network Policy Validation

Tests verify network policies are enforced:

```python
def test_network_policies():
    # Test default deny
    assert not can_access_unauthorized(
        source_ns="test-ns",
        target_ns="gitlab"
    )
    
    # Test allowed paths
    assert can_access_authorized(
        source_ns="monitoring",
        target_ns="gitlab",
        port=443
    )
```

### Cross-Component Dependencies

Tests verify component dependencies:

```python
def test_component_dependencies():
    # Test Keycloak DB connectivity
    assert validate_db_connection(
        service="keycloak",
        db="postgresql"
    )
    
    # Test GitLab cache
    assert validate_cache_connection(
        service="gitlab",
        cache="redis"
    )
```

## Test Setup

### Environment Preparation

1. Create isolated test namespace:
   ```python
   env = TestEnvironment(quotas={
       "cpu": "2",
       "memory": "2Gi",
       "pods": "10"
   })
   env.setup()
   ```

2. Deploy test services:
   ```python
   def deploy_test_services():
       deploy_minimal_gitlab()
       deploy_minimal_keycloak()
       deploy_test_database()
       wait_for_readiness()
   ```

3. Configure test data:
   ```python
   def configure_test_data():
       create_test_users()
       configure_sso_provider()
       setup_test_repositories()
   ```

### Test Prerequisites

1. Validate infrastructure:
   ```python
   def validate_prerequisites():
       assert check_cluster_health()
       assert check_resource_availability()
       assert validate_network_connectivity()
   ```

2. Verify dependencies:
   ```python
   def verify_dependencies():
       assert check_external_services()
       assert validate_certificates()
       assert check_dns_resolution()
   ```

## Test Execution

### Running Integration Tests

1. Basic execution:
   ```bash
   ./run-tests.sh --categories integration
   ```

2. With debugging:
   ```bash
   ./run-tests.sh --categories integration --debug --log-level DEBUG
   ```

3. Parallel execution:
   ```bash
   ./run-tests.sh --categories integration --parallel-jobs 4
   ```

### Test Monitoring

Monitor test progress:

```python
monitor = TestProgressMonitor()
monitor.start_monitoring()

try:
    run_integration_tests()
finally:
    results = monitor.get_results()
    monitor.stop_monitoring()
```

### Error Handling

Handle test failures:

```python
def run_with_recovery():
    try:
        run_integration_tests()
    except TestFailure as e:
        handle_test_failure(e)
        cleanup_failed_state()
    finally:
        ensure_cleanup()
```

## Resource Management

### Test Resource Tracking

Track test resources:

```python
tracker = ResourceTracker()

def create_test_resources():
    resources = create_resources()
    for resource in resources:
        tracker.track_resource(resource)

def cleanup_test_resources():
    tracker.cleanup_resources()
```

### Cleanup Order

Manage cleanup order:

```python
def ordered_cleanup():
    cleanup_applications()  # First
    cleanup_databases()     # Second
    cleanup_volumes()       # Third
    cleanup_networks()      # Fourth
```

## Result Validation

### Success Criteria

Define success criteria:

```python
def validate_test_results(results):
    assert results.service_tests_passed
    assert results.network_tests_passed
    assert results.no_resource_leaks
    assert results.cleanup_successful
```

### Failure Analysis

Analyze test failures:

```python
def analyze_failure(failure):
    error_type = categorize_error(failure)
    if error_type == "transient":
        retry_test()
    elif error_type == "configuration":
        fix_configuration()
    else:
        report_failure()
```

## Common Integration Scenarios

### SSO Integration

Test SSO flows:

```python
def test_sso_integration():
    # Configure SSO
    setup_keycloak_realm()
    configure_gitlab_oauth()
    
    # Test login flow
    with TestTimeout(30):
        initiate_login()
        complete_oauth_flow()
        verify_user_session()
```

### Monitoring Integration

Test monitoring setup:

```python
def test_monitoring_integration():
    # Check Prometheus metrics
    assert check_metric_collection()
    
    # Verify Grafana dashboards
    assert verify_dashboard_loading()
    
    # Test alerting
    assert verify_alert_routing()
```

### Storage Integration

Test storage systems:

```python
def test_storage_integration():
    # Test PVC creation
    pvc = create_test_pvc()
    
    # Test volume mounting
    pod = deploy_pod_with_volume(pvc)
    
    # Verify data persistence
    assert write_and_verify_data(pod)
```

## Best Practices

### Test Development

1. Use test fixtures:
   ```python
   @pytest.fixture
   def integration_env():
       env = TestEnvironment()
       env.setup()
       yield env
       env.teardown()
   ```

2. Implement health checks:
   ```python
   def health_check():
       assert check_api_health()
       assert check_db_health()
       assert check_cache_health()
   ```

3. Handle timeouts:
   ```python
   with TestTimeout(60):
       wait_for_deployment()
       verify_service_health()
```

### Error Handling

1. Implement retries:
   ```python
   @with_retry(RetryConfig(max_retries=3))
   def test_with_retry():
       perform_integration_test()
   ```

2. Use circuit breakers:
   ```python
   breaker = CircuitBreaker(threshold=3)
   if breaker.can_proceed():
       try:
           test_external_dependency()
       except Exception:
           breaker.record_failure()
   ```

### Resource Cleanup

1. Use context managers:
   ```python
   with managed_test_fixture(config) as fixture:
       run_integration_test(fixture)
   ```

2. Implement cleanup verification:
   ```python
   def verify_cleanup():
       assert no_leftover_resources()
       assert namespaces_cleaned_up()
       assert volumes_cleaned_up()
   ```

## Troubleshooting

### Common Issues

1. Resource cleanup failures:
   ```python
   def force_cleanup():
       remove_finalizers()
       delete_stuck_resources()
       verify_cleanup_complete()
   ```

2. Network connectivity issues:
   ```python
   def diagnose_network():
       check_dns_resolution()
       verify_network_policies()
       test_pod_connectivity()
   ```

3. Timeout handling:
   ```python
   def handle_timeout():
       capture_resource_state()
       log_timeout_context()
       initiate_cleanup()
   ```

### Debug Tools

1. Log collection:
   ```python
   def collect_debug_info():
       collect_pod_logs()
       capture_resource_state()
       export_event_logs()
   ```

2. State inspection:
   ```python
   def inspect_state():
       check_resource_status()
       verify_configurations()
       validate_dependencies()
   ```

## Reporting

### Test Reports

Generate test reports:

```python
reporter = TestReporter()
reporter.add_test_results(results)
reporter.add_metrics(metrics)
reporter.generate_report()
```

### Metrics Collection

Collect test metrics:

```python
def collect_metrics():
    record_execution_time()
    record_success_rate()
    record_resource_usage()
```

## Continuous Integration

### CI Pipeline Integration

```yaml
integration_tests:
  script:
    - ./run-tests.sh --categories integration
    - ./run-tests.sh --categories monitoring
    - ./run-tests.sh --categories storage
  artifacts:
    reports:
      junit: test-results.xml
```

### Scheduled Testing

```bash
# Daily integration tests
0 0 * * * cd /path/to/tests && ./run-tests.sh --categories integration

# Weekly full suite
0 0 * * 0 cd /path/to/tests && ./run-tests.sh --full
```
