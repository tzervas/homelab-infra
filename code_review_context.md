# Code Review Tasks

## Overview
This document contains code review comments and required fixes for the homelab orchestrator project.

## Overall Improvements Needed
1. Use the new `progress_bar` context manager consistently across all CLI commands to replace repeated `Progress(...)` blocks
2. Add missing `ssl` module import and fix SSL context creation in CertificateManager
3. Fix time module usage in cache warmup script
4. Address timezone awareness in certificate expiry calculations
5. Add Kubernetes in-cluster configuration support
6. Implement secure command execution

## Detailed Comments

### Missing SSL Module Import
**Location**: `homelab_orchestrator/core/certificates.py`
**Issue**: The `CertificateManager.start` method calls `ssl.create_default_context()` but there's no `import ssl` statement.
**Required Fix**: Add SSL module import and properly initialize SSL context for HTTP connections.

### Timezone Awareness in Certificate Expiry
**Location**: `homelab_orchestrator/core/certificates.py:414`
**Code Context**:
```python
for cert in certificates_data.get("items", []):
```
**Issue**: Potential timezone issues in expiry calculation. The `days_until_expiry` uses `datetime.now()` (naive) while `expiry_date` may be timezone-aware.
**Required Fix**: Use timezone-aware datetime objects consistently to prevent timezone-related errors.

### Kubernetes Configuration Support
**Location**: `homelab_orchestrator/core/certificates.py:210`
**Code Context**:
```python
async def _wait_for_cert_manager_ready(self, timeout: int = 300) -> bool:
    """Wait for cert-manager to be ready."""
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        start_time = asyncio.get_event_loop().time()
```
**Issue**: No support for in-cluster configuration
**Required Fix**: Add `config.load_incluster_config()` as fallback for running inside Kubernetes pods

### Cache Warmup Time Calculation
**Location**: Cache warmup script
**Issue**: Incorrect usage of `os.time()` (which doesn't exist) and missing `time` module import
**Required Fix**: Import time module and use `time.time()` for stale entry cleanup

### Security: Command Execution
**Location**: `homelab_orchestrator/core/certificates.py:488`
**Issue**: Unsafe use of `create_subprocess_exec` without proper input validation
**Security Impact**: Potential command injection vulnerability if input is controllable by external actors
**Required Fix**: Implement safe command execution with proper argument handling and input validation

## Implementation Notes
- All timezone-aware datetime operations should use UTC
- Follow existing codebase patterns and style
- Maintain comprehensive error handling
- Add tests for new functionality
- Update documentation to reflect changes
