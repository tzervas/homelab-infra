# Bash Strict Mode Compatibility Guide

This document outlines how the K3s testing framework handles `set -euo pipefail` (bash strict mode) and the patterns used to ensure robust script execution.

## Strict Mode Flags

- `set -e`: Exit immediately if any command exits with non-zero status
- `set -u`: Exit immediately if any undefined variable is referenced
- `set -o pipefail`: Exit if any command in a pipeline fails

## Common Patterns Used

### 1. Variable Initialization

```bash
# Initialize all variables to prevent unbound variable errors
TESTS_TOTAL=0
KUBECTL_CMD=""
TEST_NAMESPACE=""
```

### 2. Parameter Expansion with Defaults

```bash
# Use parameter expansion to provide defaults for potentially unset variables
local namespace="${2:-${TEST_NAMESPACE:-default}}"
local timeout="${3:-120}"
```

### 3. Conditional Command Execution

```bash
# Allow commands to fail without exiting the script
if command_that_might_fail >/dev/null 2>&1; then
    log_success "Command succeeded"
else
    log_error "Command failed"
    return 1
fi
```

### 4. Pipeline Safety

```bash
# Instead of: command | grep pattern (fails if grep finds nothing)
# Use:
local output
output=$(command 2>/dev/null || echo "")
if [[ -n "$output" ]]; then
    # Process output
fi
```

### 5. Cleanup Safety

```bash
# Cleanup operations should never fail the script
cleanup_function() {
    some_cleanup_command || true
    another_cleanup_command >/dev/null 2>&1 || true
}
```

### 6. Function Return Handling

```bash
# Functions that may fail should handle errors explicitly
test_function() {
    if ! some_test_command; then
        log_error "Test failed"
        return 1
    fi
    log_success "Test passed"
    return 0
}
```

### 7. Loop Safety

```bash
# Use || true for commands that might fail in loops
for item in "${array[@]}"; do
    process_item "$item" || true
done
```

## Testing Framework Specific Patterns

### 1. Resource Waiting Functions

```bash
wait_for_pod_ready() {
    local pod_name="$1"
    local namespace="${2:-${TEST_NAMESPACE:-default}}"
    local timeout="${3:-120}"

    if $KUBECTL_CMD wait --for=condition=Ready pod/"$pod_name" -n "$namespace" --timeout="${timeout}s" >/dev/null 2>&1; then
        return 0
    else
        log_debug "Pod $pod_name failed to become ready within ${timeout}s"
        return 1
    fi
}
```

### 2. Test Execution Safety

```bash
run_test() {
    start_test "Test name"

    # Test logic that might fail
    if test_condition; then
        log_success "Test passed"
    else
        log_error "Test failed"
        return 1  # This won't exit the script, just the function
    fi
}
```

### 3. Cleanup Trap Handling

```bash
# Cleanup should never fail
cleanup_framework() {
    cleanup_test_namespace || true
    remove_test_resources || true
}

# Set trap to ensure cleanup runs
trap cleanup_framework EXIT INT TERM
```

## Benefits of Strict Mode

1. **Early Error Detection**: Scripts fail fast when something goes wrong
2. **Undefined Variable Prevention**: Catches typos and uninitialized variables
3. **Pipeline Failure Detection**: Detects failures in command pipelines
4. **More Robust Scripts**: Forces explicit error handling

## Testing Strict Mode Compatibility

```bash
# Test script with strict mode
#!/bin/bash
set -euo pipefail

# This will fail with unbound variable
echo "$UNDEFINED_VAR"  # Bad

# This is safe
echo "${UNDEFINED_VAR:-default}"  # Good

# This might not catch pipeline failures
command1 | command2  # Potentially bad

# This is explicit
if command1 | command2; then
    echo "Pipeline succeeded"
else
    echo "Pipeline failed"
fi
```

## Migration Tips

When converting existing scripts to strict mode:

1. Initialize all variables at the top
2. Use parameter expansion for optional parameters
3. Add explicit error handling for expected failures
4. Test thoroughly with various scenarios
5. Use `|| true` for operations that are allowed to fail
