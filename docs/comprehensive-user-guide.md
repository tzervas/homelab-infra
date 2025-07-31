# Homelab Infrastructure - Comprehensive User Guide

🎯 **Complete guide to operating your production-ready homelab infrastructure with refactored processes, unified testing, and enhanced interfaces.**

## 📚 Table of Contents

1. [Introduction & Overview](#introduction--overview)
2. [Getting Started](#getting-started)
3. [Refactored Project Structure](#refactored-project-structure)
4. [New Unified Testing Framework](#new-unified-testing-framework)
5. [Enhanced Deployment Interfaces](#enhanced-deployment-interfaces)
6. [Configuration Management](#configuration-management)
7. [Operations & Maintenance](#operations--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage Patterns](#advanced-usage-patterns)

---

## Introduction & Overview

This homelab infrastructure has been completely refactored to provide a modern, industry-standard development and operations experience. The key improvements include:

### 🔄 Major Refactoring Achievements

- **Unified Testing Architecture**: Integrated Python-based framework with K3s-specific validation
- **Standardized Script Interface**: Consistent error handling, logging, and documentation across all scripts
- **Industry-Standard Structure**: Organized directory layout following DevOps best practices
- **Enhanced Security**: Rootless deployment patterns and privilege-separated operations
- **Comprehensive Documentation**: Complete guides for all team members and skill levels

### ✨ New Key Features

- **Integrated Test Orchestrator**: Single command for comprehensive infrastructure validation
- **Multi-Framework Testing**: Python framework + K3s validation framework working together
- **Enhanced Error Recovery**: Robust error handling with actionable remediation guidance
- **Cross-Platform Compatibility**: Supports multiple deployment patterns (rootless, privileged, hybrid)
- **Flexible Reporting**: Multiple output formats (console, JSON, markdown, HTML)

---

## Getting Started

### Prerequisites Checklist

- [ ] **Linux server** with 16GB+ RAM, 4+ CPU cores, 50GB+ storage
- [ ] **Network connectivity** with static IP configuration
- [ ] **SSH access** with sudo privileges
- [ ] **Client machine** with git, kubectl, Python 3.12+
- [ ] **UV package manager** for Python dependency management

### Initial Setup (5 minutes)

```bash
# 1. Clone and initialize
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra

# 2. Quick environment check
python3 scripts/testing/rootless_compatibility.py

# 3. Set up secure deployment user (recommended)
sudo ./scripts/deployment/setup-secure-deployment.sh

# 4. Run comprehensive validation
./run-tests.sh --quick
```

### Validation Checklist

After initial setup, verify these components:

- [ ] **K3s cluster** responsive and healthy
- [ ] **Network connectivity** between workstation and cluster
- [ ] **Load balancer** (MetalLB) operational
- [ ] **Certificate management** (cert-manager) functional
- [ ] **Basic services** deployed and accessible

---

## Refactored Project Structure

### New Directory Organization

```
homelab-infra/
├── 📚 docs/                    # Enhanced documentation hub
│   ├── setup/                  # Getting started guides
│   ├── deployment/             # Deployment procedures
│   ├── operations/             # Day-2 operations
│   ├── security/              # Security guides and best practices
│   └── troubleshooting/       # Problem resolution guides
│
├── ⚙️ config/                  # Configuration management
│   ├── environments/          # Environment-specific configs
│   ├── consolidated/          # Merged configuration files
│   └── private/              # Private/sensitive configurations
│
├── 🚀 deployments/             # Deployment manifests and IaC
│   ├── gitops/               # GitOps configurations
│   ├── security/             # Security policies and configs
│   └── infrastructure/       # Infrastructure as Code
│
├── 📜 scripts/                 # Refactored automation scripts
│   ├── deployment/           # Deployment orchestration
│   ├── testing/              # Python testing framework
│   ├── validation/           # Legacy validation (being phased out)
│   ├── utilities/            # General utilities
│   ├── maintenance/          # Maintenance and sync operations
│   └── setup/               # Initial setup and configuration
│
├── 🧪 testing/                 # Comprehensive testing framework
│   └── k3s-validation/       # K3s-specific testing framework
│       ├── modules/          # Test modules by category
│       ├── orchestrator.sh   # Bash-based test runner
│       └── lib/             # Shared bash libraries
│
├── 🛠️ tools/                   # Development and operational tools
├── ⎈ helm/                     # Helm charts and configurations
└── ☸️ kubernetes/              # Base Kubernetes manifests
```

### Key Improvements

1. **Clear Separation of Concerns**: Each directory has a specific, well-defined purpose
2. **Standardized Documentation**: Every directory includes comprehensive README files
3. **Enhanced Cross-Integration**: Components work together seamlessly
4. **Migration Support**: Legacy scripts maintained with deprecation paths

---

## New Unified Testing Framework

### 🎯 Testing Architecture Overview

The refactored testing system consists of two integrated frameworks:

#### Python Testing Framework (`scripts/testing/`)

- **Configuration Validation**: YAML/JSON schema validation
- **Infrastructure Health**: Cluster connectivity and resource monitoring
- **Service Deployment**: Pod readiness and application-specific checks
- **Network Security**: TLS certificates, network policies, RBAC validation
- **Integration Testing**: End-to-end connectivity and SSO flows
- **Issue Tracking**: Comprehensive reporting with severity classification

#### K3s Validation Framework (`testing/k3s-validation/`)

- **Core Kubernetes Tests**: API server, nodes, DNS, storage
- **K3s-Specific Components**: Traefik, ServiceLB, local-path provisioner
- **Performance Benchmarks**: Load testing, throughput, resource usage
- **Security Validation**: Pod security standards, network policies
- **Failure Scenarios**: Chaos engineering and recovery testing
- **Production Readiness**: Backup/restore, monitoring, high availability

### 🚀 Quick Testing Commands

#### Unified Test Suite (Recommended)

```bash
# Complete infrastructure validation
./run-tests.sh

# Quick health check (5-minute validation)
./run-tests.sh --quick

# Comprehensive testing with all reports
./run-tests.sh --full --output-format all

# Include workstation perspective testing
./run-tests.sh --include-workstation
```

#### Framework-Specific Testing

```bash
# Python framework only
./run-tests.sh --python-only

# K3s validation only
./run-tests.sh --k3s-only

# Custom integrated testing
python scripts/testing/integrated_test_orchestrator.py \
  --k3s-categories core k3s-specific performance \
  --include-workstation \
  --output-format all
```

#### Individual Test Modules

```bash
# Configuration validation
python scripts/testing/config_validator.py --directory config/environments

# Infrastructure health monitoring
python scripts/testing/infrastructure_health.py

# Service deployment validation
python scripts/testing/service_checker.py --service gitlab

# Network security testing
python scripts/testing/network_security.py --check tls

# Integration testing
python scripts/testing/integration_tester.py --include-workstation
```

### 📊 Testing Output Formats

#### Console Output (Default)

```bash
🚀 Starting Homelab Infrastructure Test Suite...

📋 Configuration Validation:
  ✅ YAML/JSON schemas validated (12/12)
  ✅ Helm values validation passed
  ✅ Environment configurations valid

🏥 Infrastructure Health:
  ✅ Cluster connectivity verified
  ✅ All nodes healthy (1/1)
  ✅ Core components operational

🔧 Service Deployment:
  ✅ GitLab deployment healthy (3/3 pods ready)
  ✅ Keycloak deployment healthy (2/2 pods ready)
  ⚠️ Prometheus deployment pending (1/3 pods ready)

🔒 Network Security:
  ✅ TLS certificates valid
  ✅ Network policies enforced
  ✅ RBAC policies verified

🌐 Integration Testing:
  ✅ End-to-end connectivity verified
  ✅ Service-to-service communication functional

📊 Final Results: 45/47 tests passed (95.7% success rate)
```

#### JSON Output (CI/CD Integration)

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "overall_status": "pass",
  "frameworks": {
    "python": {"tests": 32, "passed": 30, "failed": 2},
    "k3s": {"tests": 15, "passed": 15, "failed": 0}
  },
  "duration": 127.5,
  "success_rate": 95.7,
  "recommendations": [
    "Investigate Prometheus pod startup delays",
    "Consider increasing resource limits for monitoring stack"
  ]
}
```

#### Markdown Report (Documentation)

```markdown
# Infrastructure Test Report
*Generated: 2025-01-28 10:30:00*

## 🎯 Overall Status: ✅ PASS (95.7%)

### Framework Results
- **Python Framework**: 30/32 tests passed
- **K3s Validation**: 15/15 tests passed

### Critical Issues
- None detected

### Recommendations
1. Investigate Prometheus pod startup delays
2. Consider resource limit adjustments
```

### 🔍 Advanced Testing Features

#### Test Categories and Scope

```bash
# Run specific test categories
python scripts/testing/integrated_test_orchestrator.py \
  --categories config infrastructure services

# K3s-specific test categories
./testing/k3s-validation/orchestrator.sh \
  --categories core k3s-specific performance security
```

#### Parallel Execution

```bash
# Enable parallel testing for faster execution
./testing/k3s-validation/orchestrator.sh --all --parallel
```

#### Debug and Troubleshooting

```bash
# Enable debug mode for detailed output
./run-tests.sh --debug

# Generate comprehensive debug report
python scripts/testing/test_reporter.py --log-level DEBUG --output-format all
```

---

## Enhanced Deployment Interfaces

### 🔒 Secure Deployment Pattern (Recommended)

The refactored deployment system provides multiple deployment patterns optimized for security and operational efficiency.

#### Rootless Deployment Setup

```bash
# 1. Set up secure deployment user
sudo ./scripts/deployment/setup-secure-deployment.sh

# 2. Switch to deployment user
su - homelab-deploy

# 3. Deploy infrastructure
./scripts/deployment/deploy-with-privileges.sh deploy all

# 4. Verify deployment
./scripts/deployment/deploy-with-privileges.sh status
```

#### Benefits of Rootless Deployment

- **Principle of Least Privilege**: Minimal sudo permissions
- **Audit Trail**: All operations logged and tracked
- **Security Isolation**: Deployment user isolated from system administration
- **Reproducible Operations**: Consistent deployment environment

### 🚀 Deployment Command Interface

#### Core Deployment Commands

```bash
# Deploy all components in correct order
./scripts/deployment/deploy-with-privileges.sh deploy all

# Deploy specific components
./scripts/deployment/deploy-with-privileges.sh deploy k3s
./scripts/deployment/deploy-with-privileges.sh deploy metallb
./scripts/deployment/deploy-with-privileges.sh deploy cert-manager

# Check deployment status
./scripts/deployment/deploy-with-privileges.sh status

# Validate deployment readiness
./scripts/deployment/deploy-with-privileges.sh check
```

#### Environment-Specific Deployment

```bash
# Deploy to development environment
./scripts/deployment/deploy.sh -e development

# Deploy to production with validation
./scripts/deployment/deploy-and-validate.sh -e production

# Dry-run deployment (validate without applying)
./scripts/deployment/deploy.sh -e production --dry-run
```

#### Integrated Deployment with Testing

```bash
# Deploy and immediately validate
./scripts/deployment/deploy-and-validate.sh

# Deploy with comprehensive post-deployment testing
./scripts/deployment/deploy-and-validate.sh --full-validation

# Deploy with workstation connectivity testing
./scripts/deployment/deploy-and-validate.sh --include-workstation
```

### 🎛️ Management Interface

#### Backup Operations

```bash
# Backup all deployed components
homelab manage backup

# Backup specific components
homelab manage backup --components metallb cert-manager

# Environment-specific backup
homelab --environment production manage backup
```

#### Teardown Operations

```bash
# Safe teardown in dependency order
homelab manage teardown

# Teardown specific components
homelab manage teardown --components test-services monitoring

# Staging environment teardown
homelab --environment staging manage teardown
```

#### Recovery Operations

```bash
# Recover from latest backup
homelab manage recover

# Recover specific components
homelab manage recover --components metallb cert-manager
```

---

## Configuration Management

### 📁 Configuration Structure

The refactored configuration system provides flexible, environment-aware configuration management:

```
config/
├── environments/               # Environment-specific configurations
│   ├── development/           # Development environment
│   ├── staging/              # Staging environment
│   └── production/           # Production environment
├── consolidated/             # Merged configuration files
├── k3s/                     # K3s-specific configurations
├── monitoring/              # Monitoring stack configurations
└── security/               # Security policies and configurations
```

### 🔧 Configuration Management Commands

#### Environment Configuration

```bash
# Generate environment-specific configurations
./scripts/utilities/generate-config.sh --environment production

# Validate configuration consistency
python scripts/testing/config_validator.py --directory config/environments

# Merge configurations
./scripts/maintenance/merge-configs.sh --environment production
```

#### Private Configuration Management

```bash
# Sync private configuration repository
./scripts/maintenance/sync-private-config.sh sync

# Update private configuration
./scripts/maintenance/sync-private-config.sh update

# Validate private configuration integration
python scripts/testing/config_validator.py --include-private
```

### 🎯 Configuration Best Practices

1. **Environment Separation**: Keep environment-specific configurations isolated
2. **Version Control**: Track all configuration changes in git
3. **Validation**: Always validate configurations before deployment
4. **Security**: Keep sensitive data in private repository or encrypted
5. **Documentation**: Document configuration parameters and their effects

---

## Operations & Maintenance

### 📊 Monitoring & Observability

#### Health Monitoring

```bash
# Continuous health monitoring
python scripts/testing/infrastructure_health.py --continuous

# Generate health report
python scripts/testing/infrastructure_health.py --report

# Monitor specific services
python scripts/testing/service_checker.py --service gitlab --monitor
```

#### Performance Monitoring

```bash
# Run performance benchmarks
./testing/k3s-validation/orchestrator.sh performance

# Network performance testing
./testing/k3s-validation/modules/performance/network-throughput.sh

# Storage performance testing
./testing/k3s-validation/modules/performance/storage-io.sh
```

### 🔄 Maintenance Operations

#### Regular Maintenance Tasks

```bash
# Daily health check (recommended cron job)
0 8 * * * /usr/bin/python3 /path/to/scripts/testing/infrastructure_health.py

# Weekly comprehensive testing
0 6 * * 1 /path/to/run-tests.sh --full --output-format json > /var/log/weekly-tests.json

# Monthly configuration validation
0 0 1 * * /usr/bin/python3 /path/to/scripts/testing/config_validator.py --directory config
```

#### Synchronization Operations

```bash
# Sync private documentation
./scripts/maintenance/sync_private_docs.sh

# Sync untracked files across branches
./scripts/maintenance/sync_untracked.sh

# Update private configuration
./scripts/maintenance/sync-private-config.sh update
```

### 🔐 Security Operations

#### Security Validation

```bash
# Comprehensive security audit
python scripts/testing/network_security.py --audit

# Certificate management validation
python scripts/testing/network_security.py --check tls

# RBAC validation
./testing/k3s-validation/modules/security/rbac-validation.sh
```

#### Permission Verification

```bash
# Verify deployment permissions
python scripts/testing/permission_verifier.py

# Check rootless compatibility
python scripts/testing/rootless_compatibility.py

# Validate privilege separation
./scripts/deployment/deploy-with-privileges.sh verify-permissions
```

---

## Troubleshooting

### 🔍 Diagnostic Commands

#### Quick Diagnostics

```bash
# Quick system health check
./run-tests.sh --quick --debug

# Infrastructure connectivity test
python scripts/testing/infrastructure_health.py --debug

# Service-specific diagnostics
python scripts/testing/service_checker.py --service gitlab --debug
```

#### Comprehensive Diagnostics

```bash
# Full diagnostic report
./run-tests.sh --full --debug --output-format all

# Generate troubleshooting bundle
python scripts/testing/integrated_test_orchestrator.py \
  --debug \
  --output-format all \
  --generate-bundle
```

### 🚨 Common Issues and Solutions

#### Deployment Issues

**Issue**: Services not starting properly

```bash
# Diagnostic steps
kubectl get pods -A --show-labels
kubectl describe pod <pod-name> -n <namespace>

# Resolution
./scripts/deployment/deploy-with-privileges.sh deploy <component> --force-restart
```

**Issue**: Network connectivity problems

```bash
# Network diagnostic
python scripts/testing/network_security.py --check connectivity

# MetalLB troubleshooting
kubectl logs -n metallb-system -l app=metallb
```

#### Testing Issues

**Issue**: Tests failing due to timeouts

```bash
# Increase timeout values
python scripts/testing/test_reporter.py --timeout 120

# Run tests with retry logic
./run-tests.sh --retry 3
```

**Issue**: Permission denied errors

```bash
# Verify deployment user permissions
python scripts/testing/permission_verifier.py

# Reset permissions
sudo ./scripts/deployment/setup-secure-deployment.sh --reset
```

### 📋 Troubleshooting Checklist

#### Pre-Deployment Checks

- [ ] Network connectivity from workstation to server
- [ ] SSH access with appropriate keys
- [ ] Sufficient system resources (CPU, memory, storage)
- [ ] DNS resolution working correctly
- [ ] Firewall rules allowing required ports

#### Post-Deployment Validation

- [ ] All pods in Ready state
- [ ] Services have external IP addresses (LoadBalancer type)
- [ ] Ingress controllers responding to HTTP/HTTPS requests
- [ ] TLS certificates generated and valid
- [ ] Monitoring endpoints accessible

#### Regular Health Checks

- [ ] Run `./run-tests.sh --quick` daily
- [ ] Monitor resource usage trends
- [ ] Verify backup operations
- [ ] Check certificate expiration dates
- [ ] Validate security policy compliance

---

## Advanced Usage Patterns

### 🎯 Development Workflows

#### Development Environment Setup

```bash
# Set up isolated development environment
./scripts/deployment/deploy.sh -e development

# Enable development-specific features
export HOMELAB_ENVIRONMENT=development
./scripts/deployment/deploy-with-privileges.sh deploy all --dev-mode
```

#### Continuous Integration Integration

```yaml
# .github/workflows/homelab-ci.yml
name: Homelab Infrastructure CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Infrastructure Tests
        run: |
          python scripts/testing/config_validator.py --directory config
          python scripts/testing/test_reporter.py --output-format json
```

### 🔬 Advanced Testing Patterns

#### Custom Test Scenarios

```bash
# Create custom test configuration
cat > custom-test-config.yaml << EOF
categories:
  - config
  - infrastructure
  - services
frameworks:
  - python
  - k3s
output_format: all
include_workstation: true
parallel: true
EOF

# Run custom test scenario
python scripts/testing/integrated_test_orchestrator.py --config custom-test-config.yaml
```

#### Performance Benchmarking

```bash
# Comprehensive performance testing
./testing/k3s-validation/orchestrator.sh performance --parallel --report-format html

# Network throughput testing
./testing/k3s-validation/modules/performance/network-throughput.sh --duration 300

# Storage I/O benchmarking
./testing/k3s-validation/modules/performance/storage-io.sh --test-size 10G
```

### 🌐 Multi-Environment Management

#### Environment-Specific Operations

```bash
# Deploy to multiple environments
for env in development staging production; do
  ./scripts/deployment/deploy.sh -e $env --dry-run
done

# Cross-environment configuration validation
python scripts/testing/config_validator.py --compare-environments
```

#### GitOps Integration

```bash
# Generate GitOps manifests
./scripts/utilities/generate-gitops-manifests.sh --environment production

# Validate GitOps configuration
kubectl apply --dry-run=client -f deployments/gitops/
```

### 🔧 Customization and Extension

#### Adding Custom Services

```bash
# Template for new service deployment
mkdir -p helm/custom-services/my-service
cat > helm/custom-services/my-service/values.yaml << EOF
# Custom service configuration
name: my-service
image: my-app:latest
replicas: 2
EOF

# Deploy custom service
helm install my-service helm/custom-services/my-service
```

#### Custom Test Modules

```python
# scripts/testing/custom_validator.py
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CustomTestResult:
    name: str
    status: str
    message: str

class CustomValidator:
    def run_custom_tests(self) -> List[CustomTestResult]:
        # Implement custom validation logic
        return []
```

---

## 📚 Additional Resources

### Documentation Links

- **[Architecture Overview](architecture.md)** - System design and component relationships
- **[Security Best Practices](security/best-practices.md)** - Comprehensive security guide
- **[Deployment Checklist](deployment-checklist.md)** - Step-by-step validation checklist
- **[Troubleshooting Guide](troubleshooting/common-issues.md)** - Problem resolution guide

### Command Reference

- **[Scripts README](../scripts/README.md)** - Complete script documentation
- **[Testing Framework README](../scripts/testing/README.md)** - Testing framework guide
- **[K3s Validation README](../testing/k3s-validation/README.md)** - K3s-specific testing

### Community Resources

- **Issues**: [GitHub Issues](https://github.com/tzervas/homelab-infra/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tzervas/homelab-infra/discussions)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 🎉 Conclusion

This comprehensive user guide covers all aspects of the refactored homelab infrastructure, from initial setup to advanced operational patterns. The new unified testing framework, enhanced deployment interfaces, and standardized documentation provide a solid foundation for reliable homelab operations.

### Key Takeaways

1. **Use the unified testing framework** (`./run-tests.sh`) for regular infrastructure validation
2. **Follow the rootless deployment pattern** for enhanced security
3. **Leverage the integrated documentation** for step-by-step guidance
4. **Take advantage of automation** to reduce manual operational overhead
5. **Participate in the community** for continuous improvement

**Happy homelabbing!** 🚀

---

*Generated: 2025-01-28 | Version: 2.0 | [View Source](comprehensive-user-guide.md)*
