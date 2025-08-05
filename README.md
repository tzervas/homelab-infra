# Homelab Infrastructure Orchestrator

🧪 **Beta Release v0.9.0-beta** - Unified orchestration platform ready for testing!

Modern homelab infrastructure orchestrator with security-first deployment, comprehensive certificate management, and unified CLI interface.

## 🧪 Current Status: BETA TESTING

✅ **Unified Orchestrator**: Single Python-based CLI replacing all bash scripts  
✅ **Certificate Management**: Let's Encrypt + self-signed fallback automation  
✅ **Security-First**: No hardcoded secrets, environment-based configuration  
✅ **Multi-Environment**: Development, staging, and production support  
✅ **Testing Ready**: Comprehensive test suite validates all functionality  

## Overview

This repository contains a **comprehensive homelab orchestration platform** that unifies infrastructure management with a single, powerful CLI interface:

### 🚀 Core Features

- **Unified CLI**: Single `python -m homelab_orchestrator` command for all operations
- **Certificate Management**: Automated Let's Encrypt + self-signed certificate provisioning
- **Security-First**: Environment-based secrets, no hardcoded credentials  
- **Multi-Environment**: Development (staging certs), production (Let's Encrypt)
- **Health Monitoring**: Comprehensive system and certificate health validation
- **Configuration Management**: Centralized YAML-based configuration with overrides

### 🔧 Infrastructure Components

- **K3s Kubernetes**: Container orchestration platform
- **cert-manager**: Automated TLS certificate lifecycle management
- **MetalLB**: Load balancer for bare metal deployments
- **NGINX Ingress**: HTTP/HTTPS routing with TLS termination
- **Monitoring Stack**: Prometheus, Grafana, AlertManager
- **Authentication**: Keycloak with OAuth2 proxy integration

## Quick Start

### Prerequisites

- **Server**: Homelab server (Ubuntu 20.04+) with SSH access and sudo privileges
  - k3s cluster running on 192.168.16.26
  - Static IP configuration recommended
  - Configuration file: /etc/netplan/01-netcfg.yaml
- **Resources**: Minimum 4GB RAM, 2 CPU cores, 50GB storage
  - Example: 8GB RAM, 4 CPU cores
- **Tools**: Required software (will be installed by setup script)
  - Git
  - Docker
  - kubectl
  - Helm 3.x
  - Helmfile

```bash
# Clone repository on homelab server
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra

# Run secure deployment setup (requires initial sudo)
sudo ./scripts/deployment/setup-secure-deployment.sh

# This creates:
# - homelab-deploy user with minimal sudo permissions
# - Proper directory structure and SSH configuration
# - Docker access and environment setup
```

#### 2. Quick Validation

```bash
# Switch to deployment user
su - homelab-deploy

# Run comprehensive validation
python3 scripts/testing/validate_deployment.py

# Expected output: "✅ All validations passed - deployment is ready!"
```

#### 3. Deploy Infrastructure

```bash
# Deploy core infrastructure
./scripts/deployment/deploy-with-privileges.sh deploy all

# Check deployment status
./scripts/deployment/deploy-with-privileges.sh status
```

### 📋 Traditional Deployment

For traditional deployment with existing tools, you can customize the configuration using
the provided templates and examples for flexibility and security.

### Configuration Setup

This project uses a multi-repository approach for enhanced security:

1. **Main Repository** (this one): Contains public infrastructure code and documentation.
2. **Private Repository**: Holds sensitive configurations, secrets, and environment overrides.
3. **Examples Repository**: Contains template configurations for easy customization.

```yaml
# Configuration example
PRIVATE_CONFIG_REPO: git@github.com:username/homelab-infra-private.git
PRIVATE_CONFIG_BRANCH: main
PRIVATE_CONFIG_DIR: config
```

#### Setting Up Private Configuration

1. Create a private repository for sensitive configurations:

   ```bash
   # Example: Creating a private repository on GitHub/GitLab.
   git clone git@github.com:username/homelab-infra-private.git
   ```

2. Configure the private repository in your `.env` file:

   ```bash
   PRIVATE_CONFIG_REPO=git@github.com:username/homelab-infra-private.git
   PRIVATE_CONFIG_BRANCH=main
   PRIVATE_CONFIG_DIR=config
   ```

3. Initialize the private configuration:

   ```bash
   ./scripts/sync-private-config.sh sync
   ```

This setup will automatically clone the private repository, organize the directory structure, and load sensitive environment variables during deployment.

### Deploy Infrastructure

```bash
# Clone the repository
git clone <your-repo-url>
cd homelab-infra

# Deploy development environment
./scripts/deploy.sh -e development

# Deploy production environment
./scripts/deploy.sh -e production
```

## Private Documentation

This repository includes public documentation in the `docs/` directory. Detailed architecture
and sensitive documentation is maintained locally in `.private/docs/` (not tracked in git).
These private documents are synchronized across branches using backup scripts.

## 📁 Repository Structure

The project follows an industry-standard directory structure for improved maintainability:

```text
.
├── 📚 docs/                    # Comprehensive documentation
├── ⚙️ config/                  # Configuration management  
├── 🚀 deployments/             # Deployment manifests and IaC
├── 📜 scripts/                 # Automation and utility scripts
├── 🧪 testing/                 # Testing framework and validation
├── 🛠️ tools/                   # Development and operational tools
├── ⎈ helm/                     # Helm charts and configurations
├── ☸️ kubernetes/              # Base Kubernetes manifests
└── 🤖 ansible/                 # System-level automation (legacy)
```

### 📖 Documentation Navigation

Each directory contains comprehensive README documentation:

- **[📚 docs/README.md](docs/README.md)** - Complete documentation index
- **[⚙️ config/README.md](config/README.md)** - Configuration management guide
- **[🚀 deployments/README.md](deployments/README.md)** - Deployment strategy overview
- **[📜 scripts/README.md](scripts/README.md)** - Script organization and usage
- **[🧪 testing/k3s-validation/README.md](testing/k3s-validation/README.md)** - Testing framework guide
- **[🛠️ tools/README.md](tools/README.md)** - Development tools overview
- **[⎈ helm/README.md](helm/README.md)** - Helm deployment guide
- **[🤖 ansible/README.md](ansible/README.md)** - Ansible usage and migration status

## Migration Status

### Ansible to Helm Migration

The project has been successfully migrated from individual Ansible playbooks to a
Helmfile-based deployment strategy. The following playbooks were verified as safely
removed during the simplification effort:

- **Service Deployments**:
  - `deploy-gitlab.yml` → GitLab Helm chart
  - `deploy-keycloak.yml` → Keycloak Helm chart
  - `deploy-cert-manager.yml` → cert-manager Helm chart
  - `deploy-metallb.yml` → MetalLB Helm chart
  - `deploy-monitoring.yml` → Prometheus/Grafana Helm charts
  - `deploy-nginx-ingress.yml` → nginx-ingress Helm chart
  - `deploy-backup.yml` → Velero Helm chart

- **Infrastructure Management**:
  - `cleanup-k3s.yml` → Managed via Helm releases
  - `cleanup-vm.yml` → Managed via infrastructure scripts
  - `test-bastion-access.yml` → Replaced by simplified direct access

This migration simplifies deployment by:

- Centralizing configuration in Helm values files
- Enabling declarative state management
- Simplifying rollbacks and updates
- Reducing maintenance overhead

## 🌐 Network Configuration (Production Validated)

**Current Infrastructure Status**: ✅ All systems operational

### Server Details

- **k3s Master**: 192.168.16.26 (Debian GNU/Linux 12, kernel 6.1.0-29-amd64)
- **LoadBalancer**: 192.168.16.100 (MetalLB L2 Advertisement on eno2)
- **Network Range**: 192.168.16.0/16
- **Container Runtime**: containerd://1.7.11-k3s2

### MetalLB IP Pool (Deployed)

**Active Configuration**:

- **IP Pool**: 192.168.16.100-192.168.16.110
- **Advertisement**: L2 mode on eno2 interface  
- **Status**: ✅ Operational - External IP assigned to ingress-nginx-controller

### Network Topology

```
Workstation (192.168.16.43)
     ↓
Homelab Server (192.168.16.26)
     ↓
K3s Cluster + MetalLB (192.168.16.100)
     ↓
Services (grafana.homelab.local)
```

## Environments

### Development

- Reduced resource allocation
- Single replica deployment
- Basic monitoring
- Self-signed certificates

### Staging

- Production-like configuration
- Full monitoring stack
- Let's Encrypt staging certificates
- 2 replica deployment

### Production

- Full resource allocation
- High availability where possible
- Let's Encrypt production certificates
- 3 replica deployment for storage

## Key Components

### Core Infrastructure

- **MetalLB**: Load balancer for bare metal
- **cert-manager**: Automatic TLS certificates
- **ingress-nginx**: HTTP/HTTPS ingress
- **sealed-secrets**: Encrypted secret management

### Storage

- **Longhorn**: Distributed block storage with snapshots and backups
- **Local-path**: Fast local storage for non-critical data

### Monitoring

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Promtail**: Log collection agent

## 🧪 Testing and Validation

Comprehensive integrated testing framework that validates your entire homelab infrastructure:

### Integrated Testing Suite (Recommended)

```bash
# Run complete integrated test suite (Python + K3s validation)
./run-tests.sh

# Quick health check
./run-tests.sh --quick

# Comprehensive testing with all reports
./run-tests.sh --full --output-format all

# Include workstation perspective tests
./run-tests.sh --include-workstation
```

### Framework-Specific Testing

```bash
# Python framework only (config, infrastructure, services, security, integration)
python3 scripts/testing/test_reporter.py --output-format all --export-issues

# K3s validation framework only (cluster-specific tests)
./testing/k3s-validation/orchestrator.sh --all

# Integrated orchestrator (combines both frameworks)
python3 scripts/testing/integrated_test_orchestrator.py
```

### Individual Test Modules

```bash
# Quick compatibility check
python3 scripts/testing/rootless_compatibility.py

# Permission verification
python3 scripts/testing/permission_verifier.py

# Security validation
python3 scripts/testing/network_security.py

# Complete deployment validation
python3 scripts/testing/validate_deployment.py
```

### Test Categories

- **🔧 Configuration Validation**: YAML/JSON schema validation and checks
- **🏥 Infrastructure Health**: Cluster health and component monitoring
- **🚀 Service Deployment**: Pod readiness and resource management
- **🔒 Network Security**: TLS certificates, network policies, RBAC, security contexts
- **🔗 Integration Testing**: Service connectivity, SSO flows, end-to-end workflows
- **📊 Issue Tracking**: Comprehensive counting, severity classification, prioritized reporting

### Test Output Examples

```bash
🚨 ISSUE SUMMARY:
  Total Issues: 23
  Deployment Blocking: 5

🚨 CRITICAL ISSUES (2):
  - kubernetes_security_contexts: 15 privileged containers found (showing 5)
  - service_gitlab: Service not ready - 0/3 pods running

📊 Issues by Severity:
  🚨 Critical: 2
  ⚠️ High: 8  
  ⚡ Medium: 13

🔧 Component Status:
  - Security Contexts: 15 validation issues
  - Service Deployment: 8 configuration issues
```

## 📚 Documentation

### 🎯 New Enhanced Documentation

- **[Comprehensive User Guide](docs/comprehensive-user-guide.md)** - ⭐ Complete guide to refactored homelab infrastructure
- **[Interfaces and Process Guide](docs/interfaces-and-processes.md)** - ⭐ Detailed documentation of refactored interfaces and new processes  
- **[Testing Guide](docs/testing-guide.md)** - ⭐ Complete guide to unified testing framework and procedures

### 🚀 Essential Documentation

- **[Rootless Deployment Guide](docs/rootless-deployment-guide.md)**: Comprehensive security-hardened deployment
- **[Deployment Checklist](docs/deployment-checklist.md)**: Step-by-step validation checklist
- **[Architecture Overview](docs/architecture.md)**: System design and component relationships
- **[Security Guide](docs/security.md)**: Security practices and hardening

**[📚 Full Documentation Index](docs/README.md)**

## Deployment Commands

### Rootless Deployment (Recommended)

```bash
# Check prerequisites
./scripts/deployment/deploy-with-privileges.sh check

# Deploy components individually
./scripts/deployment/deploy-with-privileges.sh deploy k3s
./scripts/deployment/deploy-with-privileges.sh deploy metallb
./scripts/deployment/deploy-with-privileges.sh deploy cert-manager
./scripts/deployment/deploy-with-privileges.sh deploy gitlab

# Or deploy everything
./scripts/deployment/deploy-with-privileges.sh deploy all

# Check status
./scripts/deployment/deploy-with-privileges.sh status
```

### Traditional Deployment

```bash
# Deploy specific environment
./scripts/deployment/deploy.sh -e production

# Dry run deployment
./scripts/deployment/deploy.sh -e production --dry-run

# Skip dependency updates
./scripts/deployment/deploy.sh -e development --skip-deps

# Update only specific release
helmfile --environment production apply --selector name=prometheus
```

## 🌐 Access URLs (Currently Deployed)

**Live Services Status**: ✅ All services responding with HTTPS certificates

### ✅ Currently Available Services

- **Grafana**: <https://grafana.homelab.local> ✅ **Operational**
  - Status: Running with self-signed TLS certificate
  - Access: Add `192.168.16.100 grafana.homelab.local` to `/etc/hosts`
  - Authentication: Default Grafana login

### 🚧 Ready for Deployment (Infrastructure Prepared)

- **Longhorn**: <https://longhorn.homelab.local> (Storage system ready)
- **Prometheus**: <https://prometheus.homelab.local> (Monitoring infrastructure ready)
- **AlertManager**: <https://alertmanager.homelab.local> (Alerting system ready)

### 🔧 Access Setup Instructions

1. **Add DNS entries to your local machine**:

   ```bash
   sudo bash -c 'echo "192.168.16.100 grafana.homelab.local" >> /etc/hosts'
   ```

2. **Install CA certificate for trusted HTTPS** (optional):

   ```bash
   sudo cp /tmp/homelab-ca.crt /usr/local/share/ca-certificates/homelab-ca.crt
   sudo update-ca-certificates
   ```

3. **Test connectivity:**

   ```bash
   curl -k -I https://grafana.homelab.local
   # Expected: HTTP/2 302 (redirect to login)
   ```

## Security

### Authentication

- Basic authentication for Longhorn UI
- Grafana admin credentials in values files
- Sealed secrets for production credentials

### Network Policies

- Default deny-all policies
- Selective ingress/egress rules
- Namespace isolation

### Pod Security

- Pod Security Standards enforced
- Privileged access only where required
- Resource limits on all workloads

## System Observability

### System Metrics

- Node and pod metrics via node-exporter
- Application metrics via ServiceMonitor CRDs
- Custom dashboards in Grafana

### Log Management

- Centralized logging with Loki
- Log retention policies
- Grafana integration for log exploration

### Alert Configuration

- Prometheus AlertManager
- Critical system alerts
- Slack/email notification support (configure in values)

## Backup Strategy

### Longhorn Backups

- Configure S3/NFS backup targets in production values
- Automated snapshot schedules
- Cross-cluster disaster recovery

### Configuration Backups

- Git-based infrastructure as code
- Sealed secrets for sensitive data
- Regular cluster state exports

## Troubleshooting

### Common Issues

1. **MetalLB not assigning IPs**

   ```bash
   kubectl logs -n metallb-system -l app=metallb
   kubectl get ipaddresspool -n metallb-system
   ```

2. **Cert-manager certificate issues**

   ```bash
   kubectl describe certificate -A
   kubectl logs -n cert-manager -l app=cert-manager
   ```

3. **Longhorn storage issues**

   ```bash
   kubectl get volumes -n longhorn-system
   kubectl logs -n longhorn-system -l app=longhorn-manager
   ```

### Log Collection

```bash
# Collect all infrastructure logs
kubectl logs -n metallb-system -l app=metallb > metallb.log
kubectl logs -n cert-manager -l app=cert-manager > cert-manager.log
kubectl logs -n longhorn-system -l app=longhorn-manager > longhorn.log
```

## Contributing

1. Create feature branch from `develop`
2. Test changes in development environment
3. Update documentation as needed
4. Submit pull request to `develop`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
