# Homelab Infrastructure Testing Framework

A comprehensive, modular testing framework for validating your entire homelab infrastructure stack, from configuration files to end-to-end service connectivity.

## 🚀 Overview

This testing framework provides six integrated modules that validate every aspect of your homelab infrastructure:

1. **Config Validator** - Validates YAML/JSON configurations, Ansible inventory, and Helm values
2. **Infrastructure Health Monitor** - Monitors Kubernetes cluster health, nodes, and resources
3. **Service Deployment Checker** - Validates service deployments with intelligent retry logic
4. **Network & Security Validator** - Tests network connectivity, TLS certificates, and security policies
5. **Integration & Connectivity Tester** - End-to-end service testing and SSO validation
6. **Test Reporter & Aggregator** - Orchestrates all tests and provides comprehensive reporting

## 📁 Module Structure

```
scripts/testing/
├── README.md                    # This documentation
├── config_validator.py         # Configuration file validation
├── infrastructure_health.py    # Kubernetes cluster health monitoring
├── service_checker.py          # Service deployment validation
├── network_security.py         # Network and security validation
├── integration_tester.py       # End-to-end integration testing
└── test_reporter.py            # Test orchestration and reporting
```

## 🛠️ Requirements

### Python Dependencies
```bash
pip install kubernetes requests pyyaml jsonschema
```

### System Requirements
- Python 3.8+
- kubectl configured for your cluster
- Network access to your homelab services
- Optional: helm CLI for Helm chart validation

## 🎯 Quick Start

### Run Complete Test Suite
```bash
# Run all tests with comprehensive reporting
python scripts/testing/test_reporter.py

# Include workstation perspective testing
python scripts/testing/test_reporter.py --include-workstation

# Generate reports in all formats
python scripts/testing/test_reporter.py --output-format all
```

### Run Individual Test Modules
```bash
# Configuration validation
python scripts/testing/config_validator.py --directory ansible/inventory

# Infrastructure health check
python scripts/testing/infrastructure_health.py

# Service deployment check
python scripts/testing/service_checker.py --service gitlab

# Network security validation
python scripts/testing/network_security.py --check metallb

# Integration testing
python scripts/testing/integration_tester.py --include-workstation
```

## 📊 Test Categories

### 1. Configuration Validation
- **YAML/JSON Schema Validation**: Validates against defined schemas
- **Ansible Inventory Validation**: Checks host definitions and group variables
- **Helm Values Validation**: Validates Helm chart values files
- **Environment Configuration**: Tests environment-specific configurations
- **Sensitive Data Detection**: Identifies potential credential leakage

**Usage:**
```bash
python scripts/testing/config_validator.py --directory ansible/inventory
python scripts/testing/config_validator.py --file helm/environments/dev/values.yaml
```

### 2. Infrastructure Health Monitoring
- **Cluster Connectivity**: Tests Kubernetes API server connectivity
- **Node Status**: Validates all nodes are healthy and ready
- **Core Components**: Checks API server, etcd, scheduler, controller-manager
- **Resource Availability**: Monitors CPU, memory, and storage capacity
- **Network Connectivity**: Tests inter-node communication

**Usage:**
```bash
python scripts/testing/infrastructure_health.py
python scripts/testing/infrastructure_health.py --kubeconfig ~/.kube/config
```

### 3. Service Deployment Validation
- **Pod Status Monitoring**: Tracks pod health with intelligent retry logic
- **Service Readiness**: Validates readiness and liveness probes
- **Resource Usage**: Monitors CPU and memory consumption
- **Application-Specific Checks**: Custom health checks for each service
- **Deployment Rollout Status**: Validates successful deployments

**Services Monitored:**
- GitLab
- Keycloak
- Prometheus
- Grafana
- nginx-ingress
- cert-manager
- MetalLB

**Usage:**
```bash
python scripts/testing/service_checker.py
python scripts/testing/service_checker.py --service gitlab --namespace gitlab
```

### 4. Network & Security Validation
- **Network Connectivity**: External and internal network testing
- **TLS Certificate Validation**: Certificate presence and expiry checking
- **Network Policy Enforcement**: Tests network segmentation policies
- **MetalLB LoadBalancer**: Validates load balancer functionality
- **DNS Service Discovery**: Tests service name resolution
- **RBAC Security**: Validates role-based access controls

**Usage:**
```bash
python scripts/testing/network_security.py
python scripts/testing/network_security.py --check tls
python scripts/testing/network_security.py --check metallb
```

### 5. Integration & Connectivity Testing
- **End-to-End Service Connectivity**: Tests all service endpoints
- **SSO Integration Flows**: Validates Keycloak SSO with GitLab/Grafana
- **Ingress Routing**: Tests external access through ingress controllers
- **Service-to-Service Communication**: Validates inter-service connectivity
- **Multi-Perspective Testing**: Tests from both server and workstation views
- **API Endpoint Validation**: Tests all critical API endpoints

**Usage:**
```bash
python scripts/testing/integration_tester.py
python scripts/testing/integration_tester.py --include-workstation
python scripts/testing/integration_tester.py --service gitlab --perspective server
```

### 6. Test Reporting & Aggregation
- **Comprehensive Test Orchestration**: Runs all test modules in sequence
- **Multiple Output Formats**: JSON, Markdown, and console reporting
- **Metrics Calculation**: Test success rates, duration analysis
- **Trend Analysis**: Historical test result comparison
- **Actionable Recommendations**: Specific remediation suggestions

**Usage:**
```bash
python scripts/testing/test_reporter.py --output-format json
python scripts/testing/test_reporter.py --output-format markdown --output-file report
python scripts/testing/test_reporter.py --config-paths ansible/inventory helm/environments
```

## 🏠 Homelab-Specific Configuration

### Service Endpoints
The testing framework is pre-configured for your homelab services:

```python
# Internal IP addresses (server perspective)
gitlab: http://192.168.16.201
keycloak: http://192.168.16.202:8080
prometheus: http://192.168.16.204:9090
grafana: http://192.168.16.205:3000

# External URLs (workstation perspective)
gitlab: https://gitlab.homelab.local
keycloak: https://keycloak.homelab.local
prometheus: https://prometheus.homelab.local
grafana: https://grafana.homelab.local
```

### MetalLB Configuration
- **IP Range**: 192.168.25.200-192.168.25.250
- **L2Advertisement Mode**: Tests load balancer IP assignment
- **Service Validation**: Ensures LoadBalancer services get external IPs

### Network Policies
- **default-deny-all**: Tests default traffic blocking
- **allow-dns**: Validates DNS resolution permissions
- **monitoring-ingress**: Tests monitoring stack connectivity

## 📈 Report Formats

### JSON Output
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "pass",
  "duration": 45.2,
  "summary": {
    "total_tests": 127,
    "passed": 115,
    "failed": 3,
    "warnings": 9
  },
  "metrics": {
    "success_rate": 90.6,
    "critical_failures": 0
  }
}
```

### Markdown Report
```markdown
# Homelab Infrastructure Test Report
*Generated: 2024-01-15 10:30:00*

## 🎯 Overall Status: ✅ PASS

### Test Summary
- **Total Tests**: 127
- **Passed**: 115 (90.6%)
- **Failed**: 3 (2.4%)
- **Warnings**: 9 (7.1%)

### Service Status
✅ GitLab - Healthy
✅ Keycloak - Healthy
⚠️ Prometheus - Minor Issues
✅ Grafana - Healthy
```

### Console Output
```
🚀 Starting Homelab Infrastructure Test Suite...

📋 Configuration Validation:
  ✅ Ansible inventory validation passed
  ✅ Helm values validation passed

🏥 Infrastructure Health:
  ✅ Cluster connectivity verified
  ✅ All nodes healthy (3/3)

🔧 Service Deployment:
  ✅ GitLab deployment healthy
  ✅ Keycloak deployment healthy
  ⚠️ Prometheus pending restart

🔒 Network Security:
  ✅ TLS certificates valid
  ✅ Network policies enforced
  ✅ MetalLB operational

🌐 Integration Testing:
  ✅ End-to-end connectivity verified
  ✅ SSO flows functional

📊 Final Results: 115/127 tests passed (90.6%)
```

## 🔧 Advanced Usage

### Custom Configuration Paths
```bash
python scripts/testing/test_reporter.py \
  --config-paths ansible/inventory helm/environments \
  --kubeconfig ~/.kube/homelab-config \
  --output-format json \
  --output-file /tmp/test-results
```

### Environment Variables
```bash
export KUBECONFIG=~/.kube/homelab-config
export TEST_LOG_LEVEL=DEBUG
export TEST_TIMEOUT=60
python scripts/testing/test_reporter.py
```

### Integration with CI/CD
```yaml
# .github/workflows/homelab-tests.yml
- name: Run Homelab Tests
  run: |
    python scripts/testing/test_reporter.py \
      --output-format json \
      --output-file test-results.json

- name: Archive Results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test-results.json
```

## 🐛 Troubleshooting

### Common Issues

**Kubernetes Connection Failed**
```bash
# Check kubeconfig
kubectl cluster-info

# Test with specific config
python scripts/testing/infrastructure_health.py --kubeconfig ~/.kube/config
```

**Service Timeout Errors**
```bash
# Check service status
kubectl get pods -A
kubectl get services -A

# Test with longer timeout
python scripts/testing/integration_tester.py --timeout 60
```

**Permission Denied**
```bash
# Check RBAC permissions
kubectl auth can-i get pods --all-namespaces

# Use service account
kubectl create serviceaccount homelab-tester
kubectl create clusterrolebinding homelab-tester --clusterrole=view --serviceaccount=default:homelab-tester
```

### Debug Mode
```bash
# Enable debug logging
python scripts/testing/test_reporter.py --log-level DEBUG

# Run single test with verbose output
python scripts/testing/service_checker.py --service gitlab --log-level DEBUG
```

## 🚀 Best Practices

### Regular Testing Schedule
```bash
# Daily health checks
0 8 * * * /usr/bin/python3 /path/to/scripts/testing/infrastructure_health.py

# Weekly comprehensive tests
0 6 * * 1 /usr/bin/python3 /path/to/scripts/testing/test_reporter.py --output-format json --output-file /var/log/homelab-tests.json
```

### Test-Driven Infrastructure
1. **Pre-Deployment**: Validate configurations before applying
2. **Post-Deployment**: Verify successful deployment and integration
3. **Continuous Monitoring**: Regular health and security checks
4. **Change Validation**: Test after infrastructure modifications

### Alerting Integration
```bash
# Slack notification on failures
python scripts/testing/test_reporter.py | grep -q "FAIL" && curl -X POST -H 'Content-type: application/json' --data '{"text":"Homelab tests failed!"}' YOUR_SLACK_WEBHOOK_URL
```

## 📝 Contributing

### Adding New Tests
1. Create test methods following the existing pattern
2. Use dataclasses for structured results
3. Include comprehensive error handling
4. Add logging with appropriate levels
5. Update documentation and usage examples

### Module Integration
All modules use consistent interfaces and can be imported individually or used together through the test reporter.

## 🔐 Security Considerations

- **Credential Handling**: No hardcoded credentials; uses environment variables and kubeconfig
- **SSL Verification**: Configurable SSL verification for internal vs external testing
- **Sensitive Data**: Automatic detection and flagging of potential credential leakage
- **RBAC Compliance**: Validates and operates within Kubernetes RBAC constraints

---

*This testing framework provides comprehensive validation for your homelab infrastructure, ensuring reliability, security, and operational excellence.*
