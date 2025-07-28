# Claude Code RAG Configuration for K3s Testing Framework

## Project Overview

K3s Testing Framework - Comprehensive validation suite for K3s clusters with modular architecture, error recovery, and multi-level debugging.

## Core Architecture

### Framework Structure

```
k3s-validation/
├── orchestrator.sh          # Main test orchestrator with category management
├── lib/
│   ├── common.sh            # Core utilities, logging, kubectl management
│   └── debug.sh             # Debug system with tracing and error recovery
├── modules/
│   ├── core/               # Essential Kubernetes tests (6 modules)
│   ├── performance/        # Performance benchmarking (4 modules)
│   ├── k3s-specific/      # K3s component tests (5 modules)
│   ├── security/          # Security validation (pending)
│   ├── failure/           # Chaos testing (pending)
│   └── production/        # Production readiness (pending)
└── reports/               # Test output and reports
```

### Key Design Patterns

#### Module Pattern

```bash
# Standard module structure:
run_module_name() {
    start_test_module "Description"
    test_function_1
    test_function_2
}

# Independent execution:
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_module_name
    cleanup_framework
fi
```

#### Error Recovery Pattern

```bash
# Graceful error handling:
set_safe_mode
if safe_exec "description" source "$module" && \
   with_error_recovery "execute function" "$function"; then
    log_success "Module completed"
else
    log_error "Module failed (continuing)"
fi
restore_strict_mode
```

## Critical Implementation Details

### Namespace Management

- **Format**: `k3s-testing-YYYYMMDD-HHMMSS` (DNS-1123 compliant)
- **Creation**: Direct kubectl with fallback to existing namespace check
- **Cleanup**: Automatic via trap with safe execution

### Arithmetic Operations

- **Use**: `$((variable + 1))` NOT `((variable++))`
- **Reason**: Compatibility with `set -euo pipefail`

### Module Discovery

- **Pattern**: `"modules/path/file.sh:function_name"`
- **Execution**: Source module then call function
- **Missing**: Log warning and continue (no exit)

## Debug System Usage

### Debug Levels

```bash
--verbose     # Basic debugging (functions, recovery)
--debug       # Enhanced (commands, variables)  
--debug-all   # Full tracing (call stack, safe mode)
```

### Debug Functions

```bash
debug_enter "context"        # Function entry
debug_exit code             # Function exit
debug_exec command          # Command execution
safe_exec "desc" command    # Non-fatal execution
with_error_recovery "desc" func  # Retry mechanism
```

## Common Issues & Solutions

### Issue: Orchestrator exits immediately after namespace creation

**Root Cause**: Missing modules + strict error handling
**Solution**: Module pattern with error recovery, graceful missing module handling

### Issue: Arithmetic operation failures  

**Root Cause**: `((var++))` incompatible with `set -euo pipefail`
**Solution**: Use `$((var + 1))` format

### Issue: Invalid namespace names

**Root Cause**: Underscores in timestamps
**Solution**: Use hyphens: `YYYYMMDD-HHMMSS`

### Issue: Color variable redefinition

**Root Cause**: Multiple sourcing of common.sh
**Solution**: Conditional readonly declarations

## Test Categories & Modules

### Core (6/6 Complete)

- `api-server-health.sh` - API connectivity, health endpoints, performance
- `node-validation.sh` - Node status, kubelet health, resource capacity
- `system-pods.sh` - kube-system pods, CoreDNS, metrics-server
- `basic-networking.sh` - Pod-to-pod, service discovery, external connectivity
- `dns-resolution.sh` - CoreDNS functionality, cluster DNS, external DNS
- `basic-storage.sh` - Storage classes, PVC provisioning, local-path

### Performance (4/4 Complete)  

- `startup-benchmarks.sh` - Cluster startup timing
- `network-throughput.sh` - iperf3 testing, cross-node, concurrent connections
- `storage-io.sh` - PVC I/O performance, local path benchmarking
- `load-testing.sh` - API server load, pod creation, service discovery

### K3s-Specific (5/5 Complete)

- `traefik-validation.sh` - Ingress controller validation
- `servicelb-validation.sh` - Load balancer functionality  
- `local-path-provisioner.sh` - Storage provisioner testing
- `embedded-db-health.sh` - etcd/SQLite health, consistency checks
- `agent-server-comm.sh` - Node communication, registration, networking

## Quick Reference Commands

### Essential Operations

```bash
# Framework validation
./test-deployment.sh

# Dry run preview
./orchestrator.sh --dry-run core

# Standard execution
./orchestrator.sh --verbose core

# Debug troubleshooting
./orchestrator.sh --debug-all core

# Individual module testing
bash modules/core/system-pods.sh
```

### Report Generation

```bash
./orchestrator.sh --report-format html core
./orchestrator.sh --report-format json core performance
```

## Token Optimization Notes

### High-Priority Context

- Framework architecture and module patterns
- Error handling and recovery mechanisms  
- Namespace management and naming conventions
- Debug system usage and troubleshooting

### Medium-Priority Context

- Individual module implementations
- Performance testing specifics
- K3s-specific component details

### Low-Priority Context

- Detailed test output examples
- Historical debugging information
- Comprehensive module listings

## Environment Requirements

- **kubectl**: Configured and accessible
- **K3s cluster**: Running and accessible via kubectl
- **Dependencies**: jq, curl, timeout, bc (checked by framework)
- **Images**: busybox:1.35, nginx:1.25-alpine, networkstatic/iperf3:latest

## Framework Status

✅ **FULLY OPERATIONAL** - All core functionality implemented and tested

- 15 modules across 3 categories
- Comprehensive error handling and debugging
- Production-ready with graceful failure handling
