# Enhanced Testing Suite Documentation

## Overview

The `Enhanced Testing and Validation Suite` is designed to provide a comprehensive framework for testing and validating modern infrastructure components within a Kubernetes-based homelab setup. This suite integrates various testing tools and methodologies, including `Terratest`, `Helm Unittest`, `security validations`, and `performance benchmarking`, to ensure robustness, security, and performance compliance.

## Features

- **Terraform Module Testing**: Leverages `Terratest` for testing Terraform modules to ensure infrastructure components are provisioned correctly.
- **Helm Chart Testing**: Utilizes `helm-unittest` to validate Helm charts, focusing on templates and configuration correctness.
- **Security Testing**: Covers TLS, mTLS, RBAC, network policies, and certificate validation to ensure security standards and best practices.
- **Performance Benchmarking**: Includes detailed performance testing of the Kubernetes cluster, network throughput, response times, and more.
- **Infrastructure Compliance Scanning**: Performs compliance checks against configuration and infrastructure state.
- **CI/CD Integration**: Automates validation and testing through GitHub Actions workflows.
- **Type-Safe Testing**: Leverages Python type hints for improved code quality and IDE support.
- **Robust Error Handling**: Comprehensive error handling with retries and circuit breakers for resource cleanup.

## Type Hints and Static Analysis

The testing framework uses Python type hints extensively to improve code quality and maintainability:

```python
from typing import Dict, List, Optional, Tuple

class TestEnvironment:
    def __init__(self, quotas: Optional[Dict[str, str]] = None) -> None:
        self.namespace: str = f"test-{os.urandom(4).hex()}"
        self.quotas: Dict[str, str] = quotas or {
            "cpu": "2",
            "memory": "2Gi",
            "pods": "10",
        }
        self.api: CoreV1Api = None

    def validate_test_dependencies(self, test_config: Dict[str, List[str]]) -> bool:
        available: Set[str] = self.get_available_resources()
        required: List[str] = test_config.get("dependencies", [])
        return all(dep in available for dep in required)
```

Static type checking can be performed using Mypy:

```bash
mypy testing/ --strict
```

## Usage

Running the entire suite can be accomplished via the `run-enhanced-tests.sh` script:

### Script Usage

```shell
./testing/run-enhanced-tests.sh [OPTIONS]
```

### Options

- `--terratest` / `--no-terratest`: Enable or disable Terratest runs.
- `--helm-unittest` / `--no-helm-unittest`: Enable or disable Helm chart unit testing.
- `--security` / `--no-security`: Enable or disable security validation tests.
- `--performance` / `--no-performance`: Enable or disable performance benchmarks.
- `--compliance` / `--no-compliance`: Enable or disable infrastructure compliance scanning.
- `--timeout SECONDS`: Specify a maximum duration for tests.
- `--parallel-jobs N`: Set the number of parallel execution jobs.
- `--log-level LEVEL`: Adjust logging verbosity (DEBUG, INFO, WARNING, ERROR).
- `--clean`: Remove previous test artifacts before running new tests.
- `--dry-run`: Display planned actions without executing.

### Examples

- Run all tests with defaults:

  ```shell
  ./testing/run-enhanced-tests.sh
  ```

- Run only Terratest and skip performance tests:

  ```shell
  ./testing/run-enhanced-tests.sh --terratest --no-performance
  ```

- Use extended timeout and run more jobs in parallel:

  ```shell
  ./testing/run-enhanced-tests.sh --timeout 3600 --parallel-jobs 8
  ```

## Output

After running, results and reports are saved to the `test_results` directory, organized by category, with a summary report generated in markdown format.

## Error Handling and Resource Cleanup

The testing framework implements robust error handling and resource cleanup mechanisms to ensure reliable test execution and proper cleanup of test resources.

### Timeout Configurations

Timeouts are configurable at multiple levels:

```python
# Global test suite timeout
./run-enhanced-tests.sh --timeout 3600  # 1 hour timeout

# Individual test timeouts
class NetworkTest:
    def test_connectivity(self, timeout: int = 300):  # 5 minute timeout
        with TestTimeout(timeout):
            self.validate_network_connectivity()
```

### Namespace Deletion and Retry Logic

The framework implements retry logic with exponential backoff for namespace cleanup:

```python
from typing import Optional

class RetryConfig:
    def __init__(self, max_retries: int = 3, min_backoff: float = 0.1):
        self.max_retries = max_retries
        self.min_backoff = min_backoff

@with_retry(RetryConfig(max_retries=5, min_backoff=1.0))
def delete_namespace(name: str) -> None:
    try:
        api.delete_namespace(name=name)
        while check_namespace_exists(name):
            time.sleep(1)
    except ApiException as e:
        if e.status == 404:  # Already deleted
            return
        raise
```

### Error Handling During Cleanup

The framework employs a circuit breaker pattern to prevent cascading failures:

```python
class CircuitBreaker:
    def __init__(self, threshold: int = 3, window_size: float = 60):
        self.threshold = threshold
        self.window_size = window_size
        self.failures: List[float] = []

    def can_proceed(self) -> bool:
        now = time.time()
        self.failures = [t for t in self.failures 
                        if now - t < self.window_size]
        return len(self.failures) < self.threshold

    def record_failure(self) -> None:
        self.failures.append(time.time())
```

### Logging During Resource Cleanup

Comprehensive logging tracks cleanup progress and failures:

```python
class TestEnvironment:
    def teardown(self) -> None:
        logger.info(f"Starting cleanup of test namespace: {self.namespace}")
        try:
            self._delete_test_resources()
            self._delete_namespace()
            logger.info(f"Successfully cleaned up namespace: {self.namespace}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            logger.error("Attempting recovery actions...")
            self._execute_recovery_actions()
```

### Common Cleanup Issues and Solutions

1. **Stuck Namespace Deletion**
   - Issue: Namespace stuck in "Terminating" state
   - Solution: Framework implements force deletion of finalizers
   ```python
   def force_delete_namespace(name: str) -> None:
       patch = {"metadata": {"finalizers": None}}
       api.patch_namespace(name, patch)
   ```

2. **Resource Dependency Chains**
   - Issue: Resources must be deleted in correct order
   - Solution: Framework tracks dependencies and orders deletion
   ```python
   def delete_resources_ordered(self) -> None:
       order = ["deployments", "services", "configmaps", "secrets"]
       for resource_type in order:
           self._delete_resources_of_type(resource_type)
   ```

3. **Orphaned Resources**
   - Issue: Resources left behind after test failures
   - Solution: Framework maintains resource inventory
   ```python
   def track_test_resource(self, resource: Dict[str, Any]) -> None:
       self.test_resources.append(resource)
       logger.debug(f"Tracking resource for cleanup: {resource}")
   ```

### Troubleshooting Steps

1. **Check Resource Status**:
   ```bash
   # List resources in stuck namespace
   kubectl get all -n <namespace>
   
   # Check events
   kubectl get events -n <namespace>
   ```

2. **Analyze Cleanup Logs**:
   ```bash
   # View detailed cleanup logs
   ./run-enhanced-tests.sh --log-level DEBUG
   ```

3. **Force Cleanup**:
   ```bash
   # Force delete stuck namespace
   python -m testing.utils force_cleanup <namespace>
   ```

4. **Recovery Actions**:
   ```bash
   # Run recovery script for stuck resources
   ./testing/scripts/recover-resources.sh <namespace>
   ```

## Contribution

Contributions to enhance or extend the suite are welcome. Please follow the established coding patterns and contribute to feature-specific branches.

---
*Documentation generated by CI/CD pipeline based on latest testing suite updates.*
