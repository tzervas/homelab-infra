# Homelab Infrastructure Refactoring Plan

This document tracks major refactoring and security improvements identified during code review.

## 1. HomelabOrchestrator Refactoring

**Branch:** `refactor/orchestrator-services`

### Scope
- Split HomelabOrchestrator into focused service modules:
  - Event processing
  - Deployment management
  - Health monitoring
  - Resource teardown
- Update dependencies and tests
- Ensure backward compatibility

### Implementation Plan
1. Create base service interfaces
2. Implement focused service modules
3. Update HomelabOrchestrator to use new services
4. Add integration tests
5. Update documentation

## 2. OAuth2 Proxy Security

**Branch:** `security/oauth2-proxy-secrets`

### Scope
- Fix API key exposure in:
  - kubernetes/keycloak/oauth2-proxy-multi-client.yaml
  - kubernetes/base/oauth2-proxy.yaml
- Move sensitive data to Kubernetes secrets

### Implementation Plan
1. Create Kubernetes secrets for API keys
2. Update manifests to use secrets
3. Add documentation for secret management
4. Update deployment guides

## 3. Unified Deployment Security

**Branch:** `security/unified-deployment`

### Scope
- Fix asyncio shell command security issues in unified_deployment.py
- Consolidate shell commands under async command utility
- Add command validation and escaping

### Files to Update
- homelab_orchestrator/core/unified_deployment.py:247
- homelab_orchestrator/core/unified_deployment.py:331
- homelab_orchestrator/core/unified_deployment.py:356
- homelab_orchestrator/core/unified_deployment.py:378
- homelab_orchestrator/core/unified_deployment.py:398
- homelab_orchestrator/core/unified_deployment.py:416
- homelab_orchestrator/core/unified_deployment.py:535

### Implementation Plan
1. Update async command utility with validation
2. Migrate all shell commands to use utility
3. Add security tests
4. Update documentation

## 4. Command Execution Security

**Branch:** `security/command-execution`

### Scope
- Fix subprocess.run security issues
- Standardize on async command utility
- Add comprehensive command validation

### Files to Update
- homelab_orchestrator/utils/command_utils.py:90
- scripts/analyze_branches.py:26
- Any remaining direct subprocess usage

### Implementation Plan
1. Enhance command validation
2. Migrate subprocess calls to async utility
3. Add security tests
4. Update documentation

## Timeline

Suggested implementation order:

1. OAuth2 Proxy Security (Highest priority - exposed secrets)
2. Command Execution Security (Foundation for other changes)
3. Unified Deployment Security (Builds on command execution)
4. HomelabOrchestrator Refactoring (Major architectural change)

## Validation

Each branch should include:
- Comprehensive tests
- Security validation
- Documentation updates
- Migration guide if needed

## Notes

- Branches should be merged in order of dependency
- Each change should be backward compatible
- Security changes should be prioritized
- Consider adding CI checks for:
  - Secret detection
  - Command injection
  - Subprocess usage
