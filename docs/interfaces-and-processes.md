# Homelab Infrastructure - Interfaces and Process Guide

🔧 **Detailed documentation of refactored interfaces, new processes, and system interactions for technical team members.**

## 📋 Overview

This guide documents the refactored interfaces and processes following the major infrastructure modernization. All interfaces have been standardized with consistent error handling, logging, and security patterns.

---

## 🎯 Refactored Interface Categories

### 1. Testing Framework Interfaces

### 2. Deployment Interfaces  

### 3. Configuration Management Interfaces

### 4. Monitoring and Operations Interfaces

### 5. Security and Authentication Interfaces

---

## 🧪 Testing Framework Interfaces

### Unified Test Orchestrator Interface

**Entry Point**: `./run-tests.sh`

#### Command Syntax

```bash
./run-tests.sh [OPTIONS] [CATEGORIES...]
```

#### Options Reference

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--quick` | Fast health check (5-10 minutes) | false | `./run-tests.sh --quick` |
| `--full` | Comprehensive testing (15-30 minutes) | false | `./run-tests.sh --full` |
| `--python-only` | Python framework only | false | `./run-tests.sh --python-only` |
| `--k3s-only` | K3s validation framework only | false | `./run-tests.sh --k3s-only` |
| `--include-workstation` | Include workstation perspective tests | false | `./run-tests.sh --include-workstation` |
| `--output-format FORMAT` | Output format (console/json/markdown/all) | console | `./run-tests.sh --output-format json` |
| `--debug` | Enable debug logging | false | `./run-tests.sh --debug` |
| `--parallel` | Enable parallel test execution | false | `./run-tests.sh --parallel` |
| `--retry COUNT` | Retry failed tests COUNT times | 0 | `./run-tests.sh --retry 3` |
| `--timeout SECONDS` | Test timeout in seconds | 60 | `./run-tests.sh --timeout 120` |

#### Return Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | All tests passed |
| 1 | Test Failures | Some tests failed but system operational |
| 2 | Critical Failures | System-level issues detected |
| 3 | Configuration Error | Invalid configuration or missing dependencies |
| 4 | Permission Denied | Insufficient permissions for testing |

#### Output Formats

**Console Output Structure**:

```
🚀 Starting Homelab Infrastructure Test Suite...
📋 Configuration Validation: [PASS/FAIL/WARN]
🏥 Infrastructure Health: [PASS/FAIL/WARN]
🔧 Service Deployment: [PASS/FAIL/WARN]
🔒 Network Security: [PASS/FAIL/WARN]
🌐 Integration Testing: [PASS/FAIL/WARN]
📊 Final Results: X/Y tests passed (Z% success rate)
```

**JSON Output Schema**:

```json
{
  "timestamp": "ISO-8601",
  "overall_status": "pass|fail|warn",
  "frameworks": {
    "python": {"tests": 0, "passed": 0, "failed": 0, "warnings": 0},
    "k3s": {"tests": 0, "passed": 0, "failed": 0, "warnings": 0}
  },
  "categories": {
    "config": {"status": "pass|fail|warn", "details": []},
    "infrastructure": {"status": "pass|fail|warn", "details": []},
    "services": {"status": "pass|fail|warn", "details": []},
    "security": {"status": "pass|fail|warn", "details": []},
    "integration": {"status": "pass|fail|warn", "details": []}
  },
  "metrics": {
    "duration": 0.0,
    "success_rate": 0.0,
    "critical_failures": 0
  },
  "recommendations": [],
  "debug_info": {}
}
```

### Python Testing Framework Interface

**Entry Point**: `python scripts/testing/test_reporter.py`

#### Command Syntax

```bash
python scripts/testing/test_reporter.py [OPTIONS]
```

#### Core Options

```bash
# Configuration paths
--config-paths PATH [PATH...]          # Paths to configuration directories
--kubeconfig PATH                      # Kubernetes config file path

# Output control
--output-format FORMAT                 # console, json, markdown, all
--output-file PREFIX                   # Output file prefix
--log-level LEVEL                      # DEBUG, INFO, WARNING, ERROR

# Test scope
--include-workstation                  # Include workstation perspective
--exclude-categories CAT1 CAT2         # Exclude test categories
--timeout SECONDS                      # Per-test timeout

# Validation options
--skip-tls-verify                      # Skip TLS certificate verification
--export-issues                        # Export issue tracking data
```

#### Individual Module Interfaces

**Configuration Validator**:

```bash
python scripts/testing/config_validator.py [OPTIONS]
--directory PATH                       # Directory to validate
--file PATH                           # Single file to validate
--schema PATH                         # Custom schema file
--include-private                     # Include private configurations
```

**Infrastructure Health Monitor**:

```bash
python scripts/testing/infrastructure_health.py [OPTIONS]
--kubeconfig PATH                     # Kubernetes config
--continuous                          # Continuous monitoring mode
--report                             # Generate health report
--alert-on-failure                   # Alert mechanisms
```

**Service Checker**:

```bash
python scripts/testing/service_checker.py [OPTIONS]
--service NAME                        # Specific service to check
--namespace NAME                      # Kubernetes namespace
--monitor                            # Continuous monitoring
--timeout SECONDS                     # Service check timeout
```

**Network Security Validator**:

```bash
python scripts/testing/network_security.py [OPTIONS]
--check TYPE                          # tls, metallb, connectivity, rbac
--audit                              # Comprehensive security audit
--exclude-checks CHECK1 CHECK2       # Skip specific checks
```

**Integration Tester**:

```bash
python scripts/testing/integration_tester.py [OPTIONS]
--service NAME                        # Test specific service integration
--perspective VIEW                    # server, workstation, both
--include-workstation                 # Include workstation tests
--skip-sso                           # Skip SSO integration tests
```

### K3s Validation Framework Interface

**Entry Point**: `./testing/k3s-validation/orchestrator.sh`

#### Command Syntax

```bash
./testing/k3s-validation/orchestrator.sh [OPTIONS] [CATEGORIES...]
```

#### Categories

- `core`: Core Kubernetes functionality
- `k3s-specific`: K3s component validation  
- `performance`: Performance benchmarks
- `security`: Security validation
- `failure`: Chaos and failure testing
- `production`: Production readiness

#### Options

```bash
--all                                 # Run all test categories
--parallel                           # Enable parallel execution
--report-format FORMAT               # text, json, html, markdown
--output-dir PATH                    # Report output directory
--config PATH                        # Test configuration file
--verbose                            # Verbose output
--dry-run                            # Validate without execution
```

#### Module-Specific Interfaces

**Core Tests**:

```bash
./testing/k3s-validation/modules/core/api-server-health.sh
./testing/k3s-validation/modules/core/node-readiness.sh
./testing/k3s-validation/modules/core/dns-functionality.sh
./testing/k3s-validation/modules/core/storage-validation.sh
```

**K3s-Specific Tests**:

```bash
./testing/k3s-validation/modules/k3s-specific/traefik-ingress.sh
./testing/k3s-validation/modules/k3s-specific/servicelb-validation.sh
./testing/k3s-validation/modules/k3s-specific/local-path-provisioner.sh
```

**Performance Tests**:

```bash
./testing/k3s-validation/modules/performance/pod-startup-benchmark.sh
./testing/k3s-validation/modules/performance/network-throughput.sh [OPTIONS]
  --duration SECONDS                  # Test duration
  --parallel-connections COUNT        # Concurrent connections
  --packet-size BYTES                 # Packet size for testing

./testing/k3s-validation/modules/performance/storage-io.sh [OPTIONS]  
  --test-size SIZE                    # Test file size (e.g., 1G, 10G)
  --io-depth COUNT                    # I/O queue depth
  --test-type TYPE                    # read, write, randread, randwrite
```

---

## 🚀 Deployment Interfaces

### Secure Deployment Interface

**Entry Point**: `./scripts/deployment/deploy-with-privileges.sh`

#### Command Syntax

```bash
./scripts/deployment/deploy-with-privileges.sh COMMAND [OPTIONS] [COMPONENTS...]
```

#### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `deploy` | Deploy components | `deploy all` |
| `status` | Check deployment status | `status` |
| `check` | Validate deployment readiness | `check` |
| `teardown` | Remove components safely | `teardown gitlab` |
| `verify-permissions` | Validate user permissions | `verify-permissions` |

#### Component Names

- `all`: All components in dependency order
- `k3s`: K3s cluster and configuration
- `metallb`: MetalLB load balancer
- `cert-manager`: Certificate management
- `ingress-nginx`: NGINX ingress controller
- `monitoring`: Prometheus and Grafana
- `gitlab`: GitLab deployment
- `keycloak`: Keycloak identity management

#### Options

```bash
--dry-run                             # Validate without applying changes
--force-restart                       # Force restart of components
--skip-validation                     # Skip pre-deployment validation
--timeout SECONDS                     # Deployment timeout per component
--environment ENV                     # Target environment (dev/staging/prod)
```

#### Return Codes

| Code | Meaning | Action Required |
|------|---------|-----------------|
| 0 | Success | None |
| 1 | Partial Failure | Review failed components |
| 2 | Critical Failure | Manual intervention required |
| 3 | Permission Denied | Check user permissions |
| 4 | Configuration Error | Fix configuration issues |

### Traditional Deployment Interface

**Entry Point**: `./scripts/deployment/deploy.sh`

#### Command Syntax

```bash
./scripts/deployment/deploy.sh [OPTIONS] -e ENVIRONMENT
```

#### Required Parameters

- `-e, --environment ENV`: Target environment (development/staging/production)

#### Options

```bash
--dry-run                             # Validate deployment without applying
--skip-deps                           # Skip dependency updates
--components COMP1,COMP2              # Deploy specific components only
--config-override PATH                # Override configuration file
--parallel                           # Enable parallel deployment where safe
--rollback-on-failure                 # Automatic rollback on failure
```

#### Environment Configuration Files

```
config/environments/
├── development/values.yaml           # Development overrides
├── staging/values.yaml               # Staging configuration  
└── production/values.yaml            # Production settings
```

### Integrated Deployment with Validation

**Entry Point**: `./scripts/deployment/deploy-and-validate.sh`

#### Command Syntax

```bash
./scripts/deployment/deploy-and-validate.sh [OPTIONS]
```

#### Integration Options

```bash
--full-validation                     # Run comprehensive post-deployment tests
--include-workstation                 # Include workstation perspective validation
--validation-timeout SECONDS         # Timeout for validation phase
--rollback-on-validation-failure      # Rollback if validation fails
--generate-report                     # Generate deployment report
```

#### Process Flow

1. **Pre-deployment validation**: Configuration and prerequisite checks
2. **Deployment execution**: Component deployment in dependency order
3. **Post-deployment validation**: Service readiness and integration testing
4. **Report generation**: Comprehensive deployment and validation report

### Setup and Initialization Interface

**Entry Point**: `./scripts/deployment/setup-secure-deployment.sh`

#### Command Syntax

```bash
sudo ./scripts/deployment/setup-secure-deployment.sh [OPTIONS]
```

#### Options

```bash
--user USERNAME                       # Custom deployment user name
--group GROUPNAME                     # Custom deployment group
--home-dir PATH                       # Custom home directory
--ssh-key PATH                        # SSH key to install
--reset                              # Reset existing deployment user
--dry-run                            # Show what would be created
```

#### Created Resources

```bash
# User and group
homelab-deploy:homelab-deploy         # Deployment user and group

# Directory structure
/home/homelab-deploy/                 # Home directory
├── .ssh/                            # SSH configuration
├── .kube/                           # Kubernetes configuration
├── homelab-infra/                   # Project clone
└── logs/                            # Operation logs

# Sudo permissions
/etc/sudoers.d/homelab-deploy        # Minimal sudo permissions file
```

---

## ⚙️ Configuration Management Interfaces

### Configuration Validation Interface

**Entry Point**: `python scripts/testing/config_validator.py`

#### Validation Types

```bash
# Directory validation
python scripts/testing/config_validator.py --directory config/environments

# Single file validation  
python scripts/testing/config_validator.py --file config/environments/production/values.yaml

# Schema validation
python scripts/testing/config_validator.py --directory config --schema custom-schema.json

# Cross-environment comparison
python scripts/testing/config_validator.py --compare-environments
```

#### Supported File Types

- **YAML files**: Schema validation, syntax checking, structure validation
- **JSON files**: Schema validation, syntax checking
- **Helm values**: Chart compatibility, value structure validation
- **Ansible inventory**: Host definition validation, group variable checking
- **Environment files**: Variable format validation, required variable checking

#### Validation Output

```json
{
  "file": "config/environments/production/values.yaml",
  "status": "pass|fail|warn",
  "issues": [
    {
      "type": "error|warning|info",
      "message": "Description of issue",
      "line": 42,
      "column": 10,
      "suggestion": "Recommended fix"
    }
  ],
  "schema_compliance": true,
  "security_check": "pass"
}
```

### Private Configuration Management

**Entry Point**: `./scripts/maintenance/sync-private-config.sh`

#### Command Syntax

```bash
./scripts/maintenance/sync-private-config.sh COMMAND [OPTIONS]
```

#### Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `sync` | Synchronize private configuration | Initial setup |
| `update` | Update from remote repository | Regular updates |
| `validate` | Validate private configuration | Before deployment |
| `backup` | Create backup of private config | Before major changes |

#### Configuration Structure

```
config/private/                       # Private configuration directory
├── environments/                     # Environment-specific private configs
├── secrets/                         # Encrypted secrets
│   ├── development.env              # Development secrets
│   ├── staging.env                  # Staging secrets  
│   └── production.env               # Production secrets
├── certificates/                    # Private certificates
└── keys/                           # Private keys and credentials
```

#### Options

```bash
--repository URL                      # Private repository URL
--branch NAME                        # Target branch
--key-file PATH                      # SSH key for private repo access
--validate-only                      # Validate without applying changes
--backup-existing                    # Backup before sync
```

### Environment Configuration Generation

**Entry Point**: `./scripts/utilities/generate-config.sh`

#### Command Syntax

```bash
./scripts/utilities/generate-config.sh [OPTIONS] --environment ENV
```

#### Options

```bash
--environment ENV                     # Target environment
--template PATH                       # Configuration template
--output-dir PATH                     # Output directory
--include-private                     # Include private configurations
--validate                           # Validate generated configuration
--merge-base                         # Merge with base configuration
```

#### Generated Files

```
config/consolidated/ENV/              # Generated configuration
├── merged-values.yaml               # Merged Helm values
├── environment.env                  # Environment variables  
├── kubeconfig.yaml                 # Kubernetes configuration
└── validation-report.json          # Configuration validation report
```

---

## 📊 Monitoring and Operations Interfaces

### Health Monitoring Interface

**Entry Point**: `python scripts/testing/infrastructure_health.py`

#### Monitoring Modes

```bash
# One-time health check
python scripts/testing/infrastructure_health.py

# Continuous monitoring
python scripts/testing/infrastructure_health.py --continuous --interval 60

# Generate comprehensive report
python scripts/testing/infrastructure_health.py --report --output-format json

# Monitor with alerting
python scripts/testing/infrastructure_health.py --continuous --alert-on-failure
```

#### Health Check Categories

1. **Cluster Connectivity**: API server reachability and authentication
2. **Node Health**: Node status, resource availability, kubelet health
3. **Core Components**: etcd, scheduler, controller-manager status
4. **Network Health**: DNS resolution, inter-node communication
5. **Storage Health**: Persistent volume status, storage class validation
6. **Workload Health**: Pod status, deployment readiness

#### Monitoring Output Schema

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "cluster_id": "homelab-k3s",
  "overall_health": "healthy|degraded|critical",
  "components": {
    "api_server": {"status": "healthy", "response_time": 45},
    "nodes": {"healthy": 1, "total": 1, "details": []},
    "pods": {"running": 23, "pending": 0, "failed": 1},
    "services": {"ready": 12, "total": 12}
  },
  "resource_usage": {
    "cpu": {"used": 45.2, "available": 100.0},
    "memory": {"used": 3.8, "available": 8.0},
    "storage": {"used": 125.0, "available": 500.0}
  },
  "alerts": []
}
```

### Service Monitoring Interface

**Entry Point**: `python scripts/testing/service_checker.py`

#### Service-Specific Monitoring

```bash
# Monitor specific service
python scripts/testing/service_checker.py --service gitlab --namespace gitlab

# Monitor all services
python scripts/testing/service_checker.py --all-services

# Continuous service monitoring
python scripts/testing/service_checker.py --monitor --interval 30

# Service readiness validation
python scripts/testing/service_checker.py --readiness-check
```

#### Supported Services

| Service | Health Checks | Specific Validations |
|---------|---------------|---------------------|
| `gitlab` | Pod readiness, HTTP endpoints | Repository access, CI/CD functionality |
| `keycloak` | Pod readiness, admin console | Realm configuration, OIDC endpoints |
| `prometheus` | Pod readiness, metrics endpoint | Target discovery, rule evaluation |
| `grafana` | Pod readiness, web interface | Dashboard loading, data source connectivity |
| `nginx-ingress` | Pod readiness, ingress rules | SSL termination, routing functionality |
| `cert-manager` | Pod readiness, certificate status | Certificate generation, renewal |
| `metallb` | Pod readiness, IP allocation | Load balancer functionality, L2 advertisement |

### Performance Monitoring Interface

**Entry Point**: `./testing/k3s-validation/modules/performance/`

#### Performance Test Modules

```bash
# Network throughput testing
./testing/k3s-validation/modules/performance/network-throughput.sh [OPTIONS]
  --duration 300                      # Test duration in seconds
  --parallel-connections 10           # Number of parallel connections
  --packet-size 1024                  # Packet size in bytes
  --protocol tcp|udp                  # Protocol to test
  --bandwidth-limit 100M              # Bandwidth limit for testing

# Storage I/O performance
./testing/k3s-validation/modules/performance/storage-io.sh [OPTIONS]
  --test-size 10G                     # Test file size
  --io-depth 32                       # I/O queue depth
  --test-type randread                # Test type (read/write/randread/randwrite)
  --runtime 300                       # Test runtime in seconds

# Pod startup benchmarks
./testing/k3s-validation/modules/performance/pod-startup-benchmark.sh [OPTIONS]
  --pod-count 50                      # Number of pods to test
  --image nginx:alpine                # Container image to use
  --namespace benchmark               # Test namespace
  --cleanup                          # Clean up after test
```

#### Performance Metrics Output

```json
{
  "test_type": "network_throughput",
  "timestamp": "2025-01-28T10:30:00Z",
  "duration": 300,
  "results": {
    "bandwidth": {
      "average": "850.5 Mbps",
      "peak": "980.2 Mbps",
      "minimum": "745.1 Mbps"
    },
    "latency": {
      "average": "2.1 ms",
      "p95": "3.8 ms",
      "p99": "7.2 ms"
    },
    "packet_loss": "0.01%"
  },
  "recommendations": [
    "Network performance within expected range",
    "Consider MTU optimization for improved throughput"
  ]
}
```

---

## 🔐 Security and Authentication Interfaces

### Security Validation Interface

**Entry Point**: `python scripts/testing/network_security.py`

#### Security Check Categories

```bash
# TLS certificate validation
python scripts/testing/network_security.py --check tls

# Network policy enforcement
python scripts/testing/network_security.py --check network-policies

# RBAC validation
python scripts/testing/network_security.py --check rbac

# MetalLB security validation
python scripts/testing/network_security.py --check metallb

# Comprehensive security audit
python scripts/testing/network_security.py --audit
```

#### TLS Certificate Validation

```bash
# Certificate status check
python scripts/testing/network_security.py --check tls --verbose

# Certificate expiration monitoring
python scripts/testing/network_security.py --check tls --expiry-warning 30

# Certificate chain validation
python scripts/testing/network_security.py --check tls --validate-chain
```

#### RBAC Validation Interface

```bash
# Role and ClusterRole validation
./testing/k3s-validation/modules/security/rbac-validation.sh --check-roles

# ServiceAccount permissions
./testing/k3s-validation/modules/security/rbac-validation.sh --check-serviceaccounts

# User permissions audit
./testing/k3s-validation/modules/security/rbac-validation.sh --audit-users
```

### Permission Verification Interface

**Entry Point**: `python scripts/testing/permission_verifier.py`

#### Permission Categories

```bash
# Deployment user permissions
python scripts/testing/permission_verifier.py --user homelab-deploy

# Kubernetes RBAC permissions
python scripts/testing/permission_verifier.py --kubernetes

# File system permissions
python scripts/testing/permission_verifier.py --filesystem

# SSH access validation
python scripts/testing/permission_verifier.py --ssh
```

#### Permission Validation Output

```json
{
  "user": "homelab-deploy",
  "validation_timestamp": "2025-01-28T10:30:00Z",
  "permissions": {
    "sudo": {
      "status": "valid",
      "allowed_commands": [
        "/bin/systemctl restart k3s",
        "/usr/local/bin/k3s kubectl"
      ]
    },
    "kubernetes": {
      "status": "valid",
      "contexts": ["homelab-k3s"],
      "namespaces": ["default", "kube-system", "metallb-system"]
    },
    "filesystem": {
      "status": "valid",
      "readable_paths": ["/home/homelab-deploy", "/etc/rancher/k3s"],
      "writable_paths": ["/home/homelab-deploy", "/tmp"]
    }
  },
  "issues": [],
  "recommendations": []
}
```

### Rootless Compatibility Interface

**Entry Point**: `python scripts/testing/rootless_compatibility.py`

#### Compatibility Checks

```bash
# Full rootless compatibility check
python scripts/testing/rootless_compatibility.py

# Check specific component compatibility
python scripts/testing/rootless_compatibility.py --component k3s

# Generate compatibility report
python scripts/testing/rootless_compatibility.py --report --output-format json
```

#### Compatibility Categories

1. **User Configuration**: User account setup and permissions
2. **System Dependencies**: Required system packages and configurations
3. **Network Configuration**: Port binding and network access
4. **Storage Access**: File system permissions and storage requirements
5. **Process Management**: Service management without root privileges

---

## 🔄 Process Integration Patterns

### Testing → Deployment Integration

```bash
# Pre-deployment validation
./run-tests.sh --quick --categories config infrastructure
if [ $? -eq 0 ]; then
  ./scripts/deployment/deploy-with-privileges.sh deploy all
fi

# Post-deployment validation
./scripts/deployment/deploy-and-validate.sh --full-validation
```

### Configuration → Deployment Integration

```bash
# Configuration generation and validation
./scripts/utilities/generate-config.sh --environment production
python scripts/testing/config_validator.py --directory config/consolidated/production

# Deploy with validated configuration
./scripts/deployment/deploy.sh -e production --config-override config/consolidated/production
```

### Monitoring → Alerting Integration

```bash
# Continuous monitoring with alerting
python scripts/testing/infrastructure_health.py --continuous --alert-on-failure &
python scripts/testing/service_checker.py --monitor --alert-threshold 3 &
```

---

## 📋 Interface Standards and Conventions

### Common Option Patterns

- `--dry-run`: Validate without executing changes
- `--debug`: Enable detailed logging
- `--output-format FORMAT`: Specify output format
- `--timeout SECONDS`: Set operation timeout
- `--config PATH`: Specify configuration file
- `--help`: Display usage information

### Return Code Standards

- `0`: Success
- `1`: General failure or partial success
- `2`: Critical failure requiring intervention  
- `3`: Configuration or parameter error
- `4`: Permission or authentication error
- `5`: Network or connectivity error

### Logging Standards

All interfaces use consistent logging levels:

- `ERROR`: Critical issues requiring immediate attention
- `WARNING`: Issues that should be addressed but don't block operation
- `INFO`: General operational information
- `DEBUG`: Detailed troubleshooting information

### Environment Variable Standards

- `HOMELAB_ENVIRONMENT`: Target environment (development/staging/production)
- `KUBECONFIG`: Kubernetes configuration file path
- `LOG_LEVEL`: Logging verbosity level
- `TEST_TIMEOUT`: Default timeout for test operations
- `DEBUG_MODE`: Enable debug mode globally

---

## 🎯 Usage Examples and Patterns

### Daily Operations Workflow

```bash
# Morning health check
./run-tests.sh --quick --output-format json > daily-health-$(date +%Y%m%d).json

# Deploy updates if available
if git pull | grep -q "Already up to date"; then
  echo "No updates available"
else
  ./scripts/deployment/deploy-and-validate.sh --full-validation
fi
```

### Troubleshooting Workflow

```bash
# Generate comprehensive diagnostic report
./run-tests.sh --full --debug --output-format all --include-workstation

# Target specific issue
python scripts/testing/service_checker.py --service gitlab --debug
python scripts/testing/network_security.py --check connectivity --debug
```

### CI/CD Integration Pattern

```yaml
# Example GitHub Actions workflow
- name: Validate Configuration
  run: python scripts/testing/config_validator.py --directory config

- name: Deploy to Staging
  run: ./scripts/deployment/deploy.sh -e staging --dry-run

- name: Run Integration Tests
  run: ./run-tests.sh --python-only --output-format json
```

---

This comprehensive interface documentation provides technical team members with detailed information about all refactored processes and new interfaces. Each interface follows consistent patterns for options, return codes, and output formats, making the system predictable and easy to integrate into automated workflows.

---

*Generated: 2025-01-28 | Version: 2.0 | [View Source](interfaces-and-processes.md)*
