# Homelab Infrastructure - Comprehensive Testing Guide

🧪 **Complete guide to testing your homelab infrastructure using the unified testing framework, covering validation, monitoring, and quality assurance procedures.**

## 📚 Table of Contents

1. [Testing Framework Overview](#testing-framework-overview)
2. [Quick Start Testing](#quick-start-testing)
3. [Testing Categories and Scope](#testing-categories-and-scope)
4. [Unified Testing Interface](#unified-testing-interface)
5. [Framework-Specific Testing](#framework-specific-testing)
6. [Testing Best Practices](#testing-best-practices)
7. [Continuous Testing and Monitoring](#continuous-testing-and-monitoring)
8. [Troubleshooting Test Issues](#troubleshooting-test-issues)
9. [Advanced Testing Scenarios](#advanced-testing-scenarios)

---

## Testing Framework Overview

### 🏗️ Architecture

The homelab infrastructure uses a **unified testing architecture** that combines two complementary frameworks:

#### Python-Based Testing Framework (`scripts/testing/`)

- **Configuration Validation**: Schema validation, syntax checking
- **Infrastructure Health**: Cluster connectivity, resource monitoring
- **Service Deployment**: Application-specific health checks
- **Network Security**: TLS certificates, RBAC, network policies
- **Integration Testing**: End-to-end connectivity, SSO workflows
- **Issue Tracking**: Comprehensive reporting and recommendations

#### K3s Validation Framework (`testing/k3s-validation/`)

- **Core Kubernetes Tests**: API server, DNS, storage functionality
- **K3s-Specific Tests**: Traefik, ServiceLB, local-path components
- **Performance Benchmarks**: Load testing, throughput analysis
- **Security Validation**: Pod security standards, RBAC enforcement
- **Failure Scenarios**: Chaos engineering, recovery testing
- **Production Readiness**: Backup/restore, monitoring validation

### 🎯 Key Benefits

1. **Comprehensive Coverage**: Tests everything from configuration files to production readiness
2. **Multi-Perspective Validation**: Server-side and workstation-side testing
3. **Integrated Reporting**: Unified results from both frameworks
4. **Flexible Execution**: Run specific frameworks, categories, or individual tests
5. **Multiple Output Formats**: Console, JSON, Markdown, HTML reports
6. **Continuous Monitoring**: Support for scheduled and continuous testing

---

## Quick Start Testing

### 🚀 Essential Commands

#### Basic Health Check (5 minutes)

```bash
# Quick infrastructure validation
./run-tests.sh --quick

# Expected output:
# 🚀 Starting Homelab Infrastructure Test Suite...
# 📋 Configuration Validation: ✅ PASS
# 🏥 Infrastructure Health: ✅ PASS
# 🔧 Service Deployment: ✅ PASS
# 📊 Final Results: 32/35 tests passed (91.4% success rate)
```

#### Comprehensive Testing (15-30 minutes)

```bash
# Full infrastructure validation
./run-tests.sh --full

# Include workstation perspective
./run-tests.sh --full --include-workstation

# Generate all report formats
./run-tests.sh --full --output-format all
```

#### Targeted Testing

```bash
# Test specific categories
./run-tests.sh config infrastructure services

# Framework-specific testing
./run-tests.sh --python-only
./run-tests.sh --k3s-only
```

### 📋 Initial Validation Checklist

After setting up your homelab, run through this validation sequence:

```bash
# 1. Environment compatibility check
python3 scripts/testing/rootless_compatibility.py

# 2. Configuration validation
python3 scripts/testing/config_validator.py --directory config/environments

# 3. Infrastructure health check
python3 scripts/testing/infrastructure_health.py

# 4. Service deployment validation
python3 scripts/testing/service_checker.py

# 5. Network security validation
python3 scripts/testing/network_security.py

# 6. Integration testing
python3 scripts/testing/integration_tester.py --include-workstation

# 7. Comprehensive validation
./run-tests.sh --full --include-workstation
```

---

## Testing Categories and Scope

### 📋 Configuration Validation

**Purpose**: Validate configuration files, schemas, and environment consistency

#### What's Tested

- **YAML/JSON Syntax**: Proper formatting and structure
- **Schema Compliance**: Adherence to defined schemas
- **Helm Values**: Chart compatibility and value structure
- **Ansible Inventory**: Host definitions and group variables
- **Environment Consistency**: Cross-environment configuration validation
- **Security Scanning**: Detection of potential credential leakage

#### Test Commands

```bash
# Directory-wide validation
python scripts/testing/config_validator.py --directory config/environments

# Single file validation
python scripts/testing/config_validator.py --file helm/environments/production/values.yaml

# Cross-environment comparison
python scripts/testing/config_validator.py --compare-environments

# Include private configurations
python scripts/testing/config_validator.py --directory config --include-private
```

#### Expected Results

- ✅ All configuration files parse correctly
- ✅ Required fields are present and valid
- ✅ No sensitive data in public configurations
- ✅ Environment-specific overrides are consistent

### 🏥 Infrastructure Health Monitoring

**Purpose**: Validate Kubernetes cluster health and resource availability

#### What's Tested

- **Cluster Connectivity**: API server reachability and authentication
- **Node Status**: Node readiness, resource capacity, kubelet health
- **Core Components**: etcd, scheduler, controller-manager status
- **Network Functionality**: DNS resolution, inter-node communication
- **Storage Systems**: Persistent volume status, storage class validation
- **Resource Utilization**: CPU, memory, and storage usage monitoring

#### Test Commands

```bash
# Basic health check
python scripts/testing/infrastructure_health.py

# Continuous monitoring
python scripts/testing/infrastructure_health.py --continuous --interval 60

# Generate detailed report
python scripts/testing/infrastructure_health.py --report --output-format json

# Monitor with alerting
python scripts/testing/infrastructure_health.py --continuous --alert-on-failure
```

#### Health Indicators

- ✅ API server responds within acceptable timeframe (< 5 seconds)
- ✅ All nodes in Ready state
- ✅ Core system pods running and healthy
- ✅ Resource utilization within normal ranges (< 80% CPU/memory)
- ✅ Storage systems operational and available

### 🔧 Service Deployment Validation

**Purpose**: Validate application deployments and service readiness

#### Supported Services

| Service | Health Checks | Specific Validations |
|---------|---------------|---------------------|
| **GitLab** | Pod readiness, HTTP endpoints | Repository access, CI/CD pipelines |
| **Keycloak** | Pod readiness, admin console | Realm configuration, OIDC endpoints |
| **Prometheus** | Pod readiness, metrics collection | Target discovery, rule evaluation |
| **Grafana** | Pod readiness, dashboard access | Data source connectivity, dashboard rendering |
| **nginx-ingress** | Pod readiness, ingress routing | SSL termination, routing rules |
| **cert-manager** | Pod readiness, certificate status | Certificate generation, renewal processes |
| **MetalLB** | Pod readiness, IP allocation | Load balancer functionality, L2 advertisement |

#### Test Commands

```bash
# Check all services
python scripts/testing/service_checker.py

# Check specific service
python scripts/testing/service_checker.py --service gitlab --namespace gitlab

# Continuous service monitoring
python scripts/testing/service_checker.py --monitor --interval 30

# Service readiness validation
python scripts/testing/service_checker.py --readiness-check --timeout 120
```

#### Service Health Criteria

- ✅ All pods in Running state
- ✅ Readiness and liveness probes passing
- ✅ Service endpoints accessible
- ✅ Application-specific functionality verified
- ✅ Resource usage within defined limits

### 🔒 Network Security Validation

**Purpose**: Validate network security policies, certificates, and access controls

#### Security Categories

1. **TLS Certificate Management**
   - Certificate presence and validity
   - Expiration date monitoring
   - Certificate chain validation
   - CA trust validation

2. **Network Policy Enforcement**
   - Default deny-all policies
   - Selective ingress/egress rules
   - Namespace isolation
   - Service-to-service communication rules

3. **RBAC Validation**
   - Role and ClusterRole definitions
   - ServiceAccount permissions
   - User access controls
   - Privilege escalation prevention

4. **MetalLB Security**
   - IP allocation security
   - L2 advertisement validation
   - Service isolation
   - External access controls

#### Test Commands

```bash
# Comprehensive security audit
python scripts/testing/network_security.py --audit

# TLS certificate validation
python scripts/testing/network_security.py --check tls --expiry-warning 30

# Network policy testing
python scripts/testing/network_security.py --check network-policies

# RBAC validation
python scripts/testing/network_security.py --check rbac

# MetalLB security check
python scripts/testing/network_security.py --check metallb
```

#### Security Validation Results

- ✅ TLS certificates valid and not expiring soon
- ✅ Network policies properly enforced
- ✅ RBAC permissions follow principle of least privilege
- ✅ No unauthorized access paths discovered

### 🌐 Integration Testing

**Purpose**: Validate end-to-end functionality and service integration

#### Integration Categories

1. **Service-to-Service Communication**
   - Internal API connectivity
   - Database connections
   - Message queue functionality
   - Service mesh validation

2. **SSO Integration Flows**
   - Keycloak SSO with GitLab
   - Grafana authentication
   - Token exchange validation
   - Session management

3. **External Access Validation**
   - Ingress controller functionality
   - Load balancer accessibility
   - DNS resolution
   - SSL termination

4. **Multi-Perspective Testing**
   - Server-side validation
   - Workstation-side validation
   - Cross-network connectivity
   - External endpoint accessibility

#### Test Commands

```bash
# Basic integration testing
python scripts/testing/integration_tester.py

# Include workstation perspective
python scripts/testing/integration_tester.py --include-workstation

# Test specific service integration
python scripts/testing/integration_tester.py --service gitlab --perspective both

# Skip SSO testing
python scripts/testing/integration_tester.py --skip-sso
```

#### Integration Test Scenarios

- ✅ All service endpoints accessible from expected networks
- ✅ SSO authentication flows complete successfully
- ✅ Cross-service API calls function correctly
- ✅ External access through ingress controllers works
- ✅ Load balancer distributes traffic appropriately

### 🎛️ K3s-Specific Validation

**Purpose**: Validate K3s-specific components and functionality

#### Test Categories

**Core Kubernetes Tests**:

```bash
# API server functionality
./testing/k3s-validation/modules/core/api-server-health.sh

# Node readiness and resources
./testing/k3s-validation/modules/core/node-readiness.sh

# DNS functionality
./testing/k3s-validation/modules/core/dns-functionality.sh

# Storage validation
./testing/k3s-validation/modules/core/storage-validation.sh
```

**K3s-Specific Component Tests**:

```bash
# Traefik ingress controller
./testing/k3s-validation/modules/k3s-specific/traefik-ingress.sh

# ServiceLB functionality
./testing/k3s-validation/modules/k3s-specific/servicelb-validation.sh

# Local path provisioner
./testing/k3s-validation/modules/k3s-specific/local-path-provisioner.sh
```

**Performance Benchmarks**:

```bash
# Pod startup performance
./testing/k3s-validation/modules/performance/pod-startup-benchmark.sh --pod-count 50

# Network throughput testing
./testing/k3s-validation/modules/performance/network-throughput.sh --duration 300

# Storage I/O performance
./testing/k3s-validation/modules/performance/storage-io.sh --test-size 10G
```

**Security Validation**:

```bash
# Pod security standards
./testing/k3s-validation/modules/security/pod-security-standards.sh

# RBAC enforcement
./testing/k3s-validation/modules/security/rbac-validation.sh

# Network policy validation
./testing/k3s-validation/modules/security/network-policy-validation.sh
```

---

## Unified Testing Interface

### 🎯 Primary Entry Point: `./run-tests.sh`

The unified testing interface provides a single command to orchestrate both testing frameworks.

#### Basic Usage Patterns

```bash
# Default comprehensive testing
./run-tests.sh

# Quick health check (5-10 minutes)
./run-tests.sh --quick

# Full comprehensive testing (15-30 minutes)
./run-tests.sh --full

# Include workstation perspective
./run-tests.sh --include-workstation
```

#### Framework Selection

```bash
# Python framework only
./run-tests.sh --python-only

# K3s validation framework only
./run-tests.sh --k3s-only

# Both frameworks (default)
./run-tests.sh
```

#### Output Format Control

```bash
# Console output (default)
./run-tests.sh

# JSON output for CI/CD
./run-tests.sh --output-format json

# Markdown report for documentation
./run-tests.sh --output-format markdown

# Generate all formats
./run-tests.sh --output-format all
```

#### Advanced Options

```bash
# Enable debug logging
./run-tests.sh --debug

# Enable parallel execution
./run-tests.sh --parallel

# Retry failed tests
./run-tests.sh --retry 3

# Custom timeout
./run-tests.sh --timeout 120

# Dry run (validate test setup)
./run-tests.sh --dry-run
```

### 📊 Output Formats and Interpretation

#### Console Output

```bash
🚀 Starting Homelab Infrastructure Test Suite...

📋 Configuration Validation: ✅ PASS (12/12 tests)
  ✅ YAML/JSON schemas validated
  ✅ Helm values validation passed
  ✅ Environment configurations valid

🏥 Infrastructure Health: ✅ PASS (8/8 tests)
  ✅ Cluster connectivity verified
  ✅ All nodes healthy (1/1)
  ✅ Core components operational

🔧 Service Deployment: ⚠️ WARN (15/17 tests)
  ✅ GitLab deployment healthy (3/3 pods ready)
  ✅ Keycloak deployment healthy (2/2 pods ready)
  ⚠️ Prometheus deployment pending (2/3 pods ready)

🔒 Network Security: ✅ PASS (10/10 tests)
  ✅ TLS certificates valid
  ✅ Network policies enforced
  ✅ RBAC policies verified

🌐 Integration Testing: ✅ PASS (12/12 tests)
  ✅ End-to-end connectivity verified
  ✅ Service-to-service communication functional

📊 Final Results: 57/59 tests passed (96.6% success rate)

🔍 Issues Detected:
  ⚠️ Prometheus pod startup delay - investigating resource constraints

💡 Recommendations:
  - Consider increasing memory limits for monitoring stack
  - Monitor Prometheus pod logs for startup issues
```

#### JSON Output Schema

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "version": "2.0",
  "overall_status": "pass",
  "success_rate": 96.6,
  "total_tests": 59,
  "passed_tests": 57,
  "failed_tests": 0,
  "warning_tests": 2,
  "duration": 487.2,

  "frameworks": {
    "python": {
      "status": "pass",
      "tests": 35,
      "passed": 34,
      "failed": 0,
      "warnings": 1
    },
    "k3s": {
      "status": "pass",
      "tests": 24,
      "passed": 23,
      "failed": 0,
      "warnings": 1
    }
  },

  "categories": {
    "config": {
      "status": "pass",
      "tests": 12,
      "passed": 12,
      "details": ["Schema validation passed", "No security issues found"]
    },
    "infrastructure": {
      "status": "pass",
      "tests": 8,
      "passed": 8,
      "details": ["Cluster healthy", "All nodes ready"]
    },
    "services": {
      "status": "warn",
      "tests": 17,
      "passed": 15,
      "warnings": 2,
      "details": ["Prometheus pod startup delay", "GitLab fully operational"]
    },
    "security": {
      "status": "pass",
      "tests": 10,
      "passed": 10,
      "details": ["TLS certificates valid", "RBAC properly configured"]
    },
    "integration": {
      "status": "pass",
      "tests": 12,
      "passed": 12,
      "details": ["All endpoints accessible", "SSO flows functional"]
    }
  },

  "issues": [
    {
      "severity": "warning",
      "category": "services",
      "service": "prometheus",
      "message": "Pod startup delay detected",
      "recommendation": "Increase memory limits for monitoring stack"
    }
  ],

  "recommendations": [
    "Consider increasing memory limits for monitoring stack",
    "Monitor Prometheus pod logs for startup issues"
  ],

  "metrics": {
    "cluster_health": "healthy",
    "resource_utilization": {
      "cpu": 45.2,
      "memory": 67.8,
      "storage": 25.1
    },
    "response_times": {
      "api_server": 0.045,
      "ingress": 0.120
    }
  }
}
```

---

## Framework-Specific Testing

### 🐍 Python Testing Framework

The Python framework provides modular, extensible testing with rich output formatting.

#### Test Reporter (Main Orchestrator)

```bash
# Basic usage
python scripts/testing/test_reporter.py

# Custom configuration paths
python scripts/testing/test_reporter.py --config-paths config/environments helm/environments

# Include workstation testing
python scripts/testing/test_reporter.py --include-workstation

# Export issue tracking data
python scripts/testing/test_reporter.py --export-issues --output-format json
```

#### Individual Module Testing

**Configuration Validator**:

```bash
# Validate all configurations
python scripts/testing/config_validator.py --directory config/environments

# Validate single file with custom schema
python scripts/testing/config_validator.py \
  --file config/environments/production/values.yaml \
  --schema schemas/helm-values.json

# Include private configuration validation
python scripts/testing/config_validator.py --directory config --include-private
```

**Infrastructure Health Monitor**:

```bash
# One-time health check
python scripts/testing/infrastructure_health.py

# Continuous monitoring mode
python scripts/testing/infrastructure_health.py --continuous --interval 30

# Generate health report
python scripts/testing/infrastructure_health.py --report --output-format markdown
```

**Service Checker**:

```bash
# Check all services
python scripts/testing/service_checker.py

# Monitor specific service
python scripts/testing/service_checker.py --service gitlab --monitor

# Readiness check with custom timeout
python scripts/testing/service_checker.py --readiness-check --timeout 180
```

**Network Security Validator**:

```bash
# Comprehensive security audit
python scripts/testing/network_security.py --audit

# Check specific security aspects
python scripts/testing/network_security.py --check tls --expiry-warning 30
python scripts/testing/network_security.py --check rbac --verbose
```

**Integration Tester**:

```bash
# End-to-end integration testing
python scripts/testing/integration_tester.py

# Test from workstation perspective
python scripts/testing/integration_tester.py --include-workstation

# Test specific service integration
python scripts/testing/integration_tester.py --service keycloak --perspective both
```

### 🛠️ K3s Validation Framework

The K3s framework provides comprehensive cluster-specific testing with performance benchmarking.

#### Main Orchestrator

```bash
# Run all test categories
./testing/k3s-validation/orchestrator.sh --all

# Run specific categories
./testing/k3s-validation/orchestrator.sh core k3s-specific performance

# Enable parallel execution
./testing/k3s-validation/orchestrator.sh --all --parallel

# Generate HTML report
./testing/k3s-validation/orchestrator.sh --all --report-format html --output-dir reports/
```

#### Category-Specific Testing

**Core Kubernetes Tests**:

```bash
# Full core test suite
./testing/k3s-validation/orchestrator.sh core

# Individual core tests
./testing/k3s-validation/modules/core/api-server-health.sh
./testing/k3s-validation/modules/core/node-readiness.sh --detailed
./testing/k3s-validation/modules/core/dns-functionality.sh --test-external
```

**K3s-Specific Tests**:

```bash
# Full K3s component suite
./testing/k3s-validation/orchestrator.sh k3s-specific

# Individual component tests
./testing/k3s-validation/modules/k3s-specific/traefik-ingress.sh --test-ssl
./testing/k3s-validation/modules/k3s-specific/servicelb-validation.sh --check-failover
```

**Performance Benchmarks**:

```bash
# Performance test suite
./testing/k3s-validation/orchestrator.sh performance

# Network throughput testing
./testing/k3s-validation/modules/performance/network-throughput.sh \
  --duration 300 \
  --parallel-connections 20 \
  --bandwidth-limit 1G

# Storage I/O benchmarks
./testing/k3s-validation/modules/performance/storage-io.sh \
  --test-size 5G \
  --test-type randread \
  --runtime 180

# Pod startup benchmarks
./testing/k3s-validation/modules/performance/pod-startup-benchmark.sh \
  --pod-count 100 \
  --image nginx:alpine \
  --measure-scheduling-latency
```

**Security Validation**:

```bash
# Security test suite
./testing/k3s-validation/orchestrator.sh security

# Pod security standards
./testing/k3s-validation/modules/security/pod-security-standards.sh --strict

# RBAC validation
./testing/k3s-validation/modules/security/rbac-validation.sh --audit-users
```

#### Custom Test Configuration

Create custom test configurations:

```yaml
# custom-test-config.yaml
categories:
  - core
  - k3s-specific
  - performance
execution:
  parallel: true
  timeout: 300
  retry_failed: 2
output:
  format: html
  directory: custom-reports
  include_debug: true
performance:
  network_duration: 180
  storage_test_size: "2G"
  pod_benchmark_count: 25
```

Run with custom configuration:

```bash
./testing/k3s-validation/orchestrator.sh --config custom-test-config.yaml
```

---

## Testing Best Practices

### 🎯 Testing Strategy

#### Test Frequency Recommendations

```bash
# Daily (automated)
./run-tests.sh --quick --output-format json > daily-health-$(date +%Y%m%d).json

# Weekly (automated)
./run-tests.sh --full --output-format all

# Pre-deployment (manual)
./run-tests.sh --categories config infrastructure services

# Post-deployment (manual)
./run-tests.sh --full --include-workstation

# Monthly (manual)
./testing/k3s-validation/orchestrator.sh --all --report-format html
```

#### Environment-Specific Testing

```bash
# Development environment
export HOMELAB_ENVIRONMENT=development
./run-tests.sh --quick --skip-performance

# Staging environment  
export HOMELAB_ENVIRONMENT=staging
./run-tests.sh --full --include-workstation

# Production environment
export HOMELAB_ENVIRONMENT=production
./run-tests.sh --full --include-workstation --retry 2
```

### 📋 Pre-Deployment Testing

Always run these tests before deploying changes:

```bash
# 1. Configuration validation
python scripts/testing/config_validator.py --directory config/environments
python scripts/testing/config_validator.py --compare-environments

# 2. Compatibility check
python scripts/testing/rootless_compatibility.py

# 3. Infrastructure readiness
python scripts/testing/infrastructure_health.py

# 4. Quick validation
./run-tests.sh --quick --categories config infrastructure

# 5. Deploy only if all tests pass
if [ $? -eq 0 ]; then
  echo "✅ Pre-deployment tests passed - proceeding with deployment"
  ./scripts/deployment/deploy-and-validate.sh
else
  echo "❌ Pre-deployment tests failed - deployment blocked"
  exit 1
fi
```

### 🔄 Post-Deployment Testing

After deploying changes, validate the deployment:

```bash
# 1. Wait for services to start
sleep 60

# 2. Run comprehensive validation
./run-tests.sh --full --include-workstation

# 3. Performance validation
./testing/k3s-validation/orchestrator.sh performance

# 4. Security audit
python scripts/testing/network_security.py --audit

# 5. Generate deployment report
./run-tests.sh --full --output-format all --generate-report
```

### 🔍 Debugging Failed Tests

When tests fail, follow this troubleshooting process:

```bash
# 1. Enable debug mode
./run-tests.sh --debug --categories failing_category

# 2. Run individual modules with verbose output
python scripts/testing/service_checker.py --service failing_service --debug

# 3. Check infrastructure health
python scripts/testing/infrastructure_health.py --debug

# 4. Validate permissions
python scripts/testing/permission_verifier.py --debug

# 5. Generate comprehensive diagnostic report
./run-tests.sh --full --debug --output-format all --include-workstation
```

### 📊 Test Result Analysis

#### Interpreting Success Rates

- **95-100%**: Excellent - System operating optimally
- **90-94%**: Good - Minor issues that should be addressed
- **80-89%**: Concerning - Investigate and resolve issues promptly
- **Below 80%**: Critical - Immediate attention required

#### Common Warning Patterns

- **Pod startup delays**: Usually resource constraints or image pull issues
- **Certificate expiration warnings**: Plan certificate renewal
- **Network connectivity timeouts**: Investigate network configuration
- **RBAC warnings**: Review and update permissions

---

## Continuous Testing and Monitoring

### ⏰ Scheduled Testing

#### Cron Job Setup

```bash
# Daily health check at 8 AM
0 8 * * * cd /home/homelab-deploy/homelab-infra && ./run-tests.sh --quick --output-format json > /var/log/homelab/daily-health-$(date +\%Y\%m\%d).json

# Weekly comprehensive test on Sundays at 6 AM
0 6 * * 0 cd /home/homelab-deploy/homelab-infra && ./run-tests.sh --full --output-format all

# Monthly performance benchmarks on 1st of month at midnight
0 0 1 * * cd /home/homelab-deploy/homelab-infra && ./testing/k3s-validation/orchestrator.sh performance --report-format html
```

### 📊 Continuous Monitoring

#### Health Monitoring Setup

```bash
# Start continuous infrastructure monitoring
python scripts/testing/infrastructure_health.py --continuous --interval 300 --alert-on-failure &

# Start continuous service monitoring  
python scripts/testing/service_checker.py --monitor --interval 60 --alert-threshold 3 &

# Start security monitoring
python scripts/testing/network_security.py --check tls --continuous --expiry-warning 30 &
```

#### Integration with Monitoring Stack

**Prometheus Metrics Export**:

```bash
# Export test results as Prometheus metrics
./run-tests.sh --output-format prometheus-metrics > /var/lib/prometheus/homelab-tests.prom
```

**Grafana Dashboard Integration**:

```json
{
  "dashboard": {
    "title": "Homelab Test Results",
    "panels": [
      {
        "title": "Test Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "homelab_test_success_rate"
          }
        ]
      },
      {
        "title": "Failed Tests",
        "type": "table",
        "targets": [
          {
            "expr": "homelab_test_failures"
          }
        ]
      }
    ]
  }
}
```

### 🚨 Alerting Configuration

#### Slack Integration

```bash
# Alert on test failures
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

./run-tests.sh --quick
if [ $? -ne 0 ]; then
  curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"🚨 Homelab tests failed! Check infrastructure status."}' \
    "$SLACK_WEBHOOK_URL"
fi
```

#### Email Alerting

```bash
# Email on critical failures
./run-tests.sh --full --output-format json > test-results.json
CRITICAL_FAILURES=$(jq '.metrics.critical_failures' test-results.json)

if [ "$CRITICAL_FAILURES" -gt 0 ]; then
  mail -s "Critical Homelab Infrastructure Failures Detected" admin@homelab.local < test-results.json
fi
```

---

## Troubleshooting Test Issues

### 🔍 Common Test Failures

#### Configuration Validation Failures

```bash
# Issue: YAML syntax errors
# Solution:
python scripts/testing/config_validator.py --file config/problematic-file.yaml --debug

# Issue: Schema validation failures
# Solution:
python scripts/testing/config_validator.py --file config/file.yaml --schema schemas/custom.json
```

#### Infrastructure Health Failures

```bash
# Issue: API server connectivity
# Diagnostic:
kubectl cluster-info
kubectl get nodes
python scripts/testing/infrastructure_health.py --debug

# Issue: Node readiness problems
# Diagnostic:
kubectl describe nodes
kubectl get pods -A --field-selector=status.phase!=Running
```

#### Service Deployment Failures

```bash
# Issue: Pod startup failures
# Diagnostic:
kubectl get pods -A
kubectl describe pod <failing-pod> -n <namespace>
kubectl logs <failing-pod> -n <namespace>

# Targeted testing:
python scripts/testing/service_checker.py --service <failing-service> --debug
```

#### Network Security Failures

```bash
# Issue: TLS certificate problems
# Diagnostic:
kubectl get certificates -A
kubectl describe certificate <cert-name> -n <namespace>
python scripts/testing/network_security.py --check tls --debug

# Issue: Network policy violations
# Diagnostic:
kubectl get networkpolicies -A
python scripts/testing/network_security.py --check network-policies --debug
```

### 🛠️ Test Environment Issues

#### Permission Problems

```bash
# Verify user permissions
python scripts/testing/permission_verifier.py --debug

# Reset deployment user permissions
sudo ./scripts/deployment/setup-secure-deployment.sh --reset

# Verify Kubernetes RBAC
kubectl auth can-i get pods --all-namespaces
```

#### Resource Constraints

```bash
# Check resource availability
kubectl top nodes
kubectl top pods -A

# Performance impact assessment
./testing/k3s-validation/modules/performance/resource-utilization.sh --detailed
```

#### Network Connectivity Issues

```bash
# Network diagnostic
python scripts/testing/network_security.py --check connectivity --debug

# DNS resolution testing
./testing/k3s-validation/modules/core/dns-functionality.sh --verbose

# Ingress controller validation
kubectl get ingress -A
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### 📋 Diagnostic Workflow

#### Step-by-Step Troubleshooting

```bash
# 1. Quick diagnostic
./run-tests.sh --quick --debug

# 2. Identify failing category
./run-tests.sh --categories <failing-category> --debug

# 3. Run individual module tests
python scripts/testing/<failing-module>.py --debug

# 4. Check infrastructure health
python scripts/testing/infrastructure_health.py --debug

# 5. Validate environment
python scripts/testing/rootless_compatibility.py --debug

# 6. Generate comprehensive report
./run-tests.sh --full --debug --output-format all --generate-bundle
```

---

## Advanced Testing Scenarios

### 🎭 Chaos Engineering

#### Failure Scenario Testing

```bash
# Node failure simulation
./testing/k3s-validation/modules/failure/node-failure-recovery.sh

# Pod eviction testing
./testing/k3s-validation/modules/failure/pod-eviction-scenarios.sh

# Network partition simulation
./testing/k3s-validation/modules/failure/network-partition-testing.sh

# Storage failure recovery
./testing/k3s-validation/modules/failure/storage-failure-recovery.sh
```

#### Chaos Testing Configuration

```yaml
# chaos-test-config.yaml
chaos_scenarios:
  - name: "random_pod_kill"
    frequency: "5m"
    target_namespaces: ["default", "monitoring"]
  - name: "network_delay"
    duration: "2m"
    delay: "100ms"
  - name: "cpu_stress"
    intensity: "50%"
    duration: "5m"
```

### 🔬 Performance Testing

#### Load Testing Scenarios

```bash
# High pod density testing
./testing/k3s-validation/modules/performance/high-density-pods.sh --pod-count 500

# Network stress testing
./testing/k3s-validation/modules/performance/network-stress.sh \
  --connections 1000 \
  --duration 600

# Storage I/O stress testing
./testing/k3s-validation/modules/performance/storage-stress.sh \
  --concurrent-ops 50 \
  --test-duration 300
```

#### Performance Benchmarking

```bash
# Comprehensive performance suite
./testing/k3s-validation/orchestrator.sh performance --benchmark-mode

# Custom benchmark configuration
./testing/k3s-validation/modules/performance/custom-benchmark.sh \
  --config performance-benchmarks.yaml \
  --output-format json \
  --comparison-baseline baseline-results.json
```

### 🔐 Security Testing

#### Penetration Testing

```bash
# Security audit
./testing/k3s-validation/modules/security/security-audit.sh --comprehensive

# Vulnerability scanning
./testing/k3s-validation/modules/security/vulnerability-scan.sh --update-db

# RBAC privilege escalation testing
./testing/k3s-validation/modules/security/privilege-escalation-test.sh --audit-users
```

#### Compliance Validation

```bash
# CIS Kubernetes Benchmark
./testing/k3s-validation/modules/security/cis-benchmark.sh --generate-report

# Pod Security Standards compliance
./testing/k3s-validation/modules/security/pss-compliance.sh --enforce-restricted
```

### 🌐 Multi-Environment Testing

#### Cross-Environment Validation

```bash
# Test configuration consistency across environments
python scripts/testing/config_validator.py --compare-environments --detailed

# Cross-environment deployment testing
for env in development staging production; do
  export HOMELAB_ENVIRONMENT=$env
  ./run-tests.sh --quick --output-format json > results-$env.json
done

# Compare results
python scripts/testing/compare-environments.py results-*.json
```

#### GitOps Validation

```bash
# Validate GitOps manifests
kubectl apply --dry-run=client -f deployments/gitops/ --validate=true

# Test GitOps deployment pipeline
./scripts/deployment/test-gitops-pipeline.sh --environment staging
```

---

## 🎉 Conclusion

This comprehensive testing guide provides everything needed to validate, monitor, and maintain your homelab infrastructure. The unified testing framework ensures reliable operations through:

### Key Takeaways

1. **Use `./run-tests.sh` as your primary testing interface** for daily operations
2. **Run quick health checks regularly** to catch issues early
3. **Perform comprehensive testing before and after deployments**
4. **Set up continuous monitoring** for proactive issue detection
5. **Follow the troubleshooting workflow** when tests fail
6. **Leverage both Python and K3s frameworks** for complete coverage

### Testing Workflow Summary

```bash
# Daily operations
./run-tests.sh --quick

# Pre-deployment
./run-tests.sh --categories config infrastructure services

# Post-deployment  
./run-tests.sh --full --include-workstation

# Performance validation
./testing/k3s-validation/orchestrator.sh performance

# Security audit
python scripts/testing/network_security.py --audit

# Troubleshooting
./run-tests.sh --debug --output-format all
```

The unified testing framework provides the foundation for reliable homelab operations, ensuring your infrastructure remains healthy, secure, and performant.

**Happy testing!** 🧪

---

*Generated: 2025-01-28 | Version: 2.0 | [View Source](testing-guide.md)*
