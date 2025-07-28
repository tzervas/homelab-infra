# K3s Testing Framework Debug Information

## Issue Summary

The K3s testing framework exits immediately after creating the test namespace without running any tests.

## Execution Trace

1. Framework initializes successfully
2. Creates test namespace successfully
3. Immediately triggers cleanup and exits

## Debug Output

```bash
[INFO] K3s testing framework initialized
[INFO] Using kubectl command: kubectl
[INFO] Creating test namespace: k3s-testing-20250727_235744
[INFO] Cleaning up test namespace: k3s-testing-20250727_235744
```

## Analysis

The issue appears to be that the orchestrator script references test modules that don't exist:

### Expected modules in run_core_tests()

- modules/core/api-server-health.sh ✓ (exists)
- modules/core/node-validation.sh ✓ (exists)
- modules/core/system-pods.sh ✗ (missing)
- modules/core/basic-networking.sh ✗ (missing)
- modules/core/dns-resolution.sh ✗ (missing)
- modules/core/basic-storage.sh ✗ (missing)

### Actual modules present

```
modules/core/api-server-health.sh
modules/core/node-validation.sh
modules/k3s-specific/local-path-provisioner.sh
modules/k3s-specific/servicelb-validation.sh
modules/k3s-specific/traefik-validation.sh
modules/performance/startup-benchmarks.sh
```

## Script Behavior with set -euo pipefail

The orchestrator.sh uses `set -euo pipefail` which causes the script to exit on:

- Any command failure (set -e)
- Use of undefined variables (set -u)
- Pipe failures (set -o pipefail)

## Suspected Root Cause

The script may be exiting because:

1. Missing test modules cause the for loop to have issues
2. The log_warning function for missing modules might be causing an exit
3. There's no actual test execution happening, causing the script to complete and trigger cleanup

## Test Environment

- kubectl connectivity: ✓ Working
- K3s cluster: ✓ Running (homelab-test-vm, v1.27.4+k3s1)
- Namespace creation: ✓ Works manually
- SSH tunnel: ✓ Active on localhost:6443

## Recommendations Needed

1. Should we create the missing test modules?
2. Should we modify the orchestrator to handle missing modules gracefully?
3. Should we adjust the script's error handling behavior?
