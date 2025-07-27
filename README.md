# Homelab Infrastructure

Infrastructure as Code (IaC) for managing homelab k3s environment with Helm and GitOps
principles.

## Overview

This repository contains infrastructure configuration for a homelab environment, featuring:
following features:

- **k3s** - Lightweight Kubernetes distribution
- **Helm/Helmfile** - Declarative application deployment
- **MetalLB** - Bare metal load balancer
- **Longhorn** - Distributed block storage
- **Prometheus Stack** - Comprehensive monitoring
- **Cert-Manager** - Automatic TLS certificate management
- **Ingress-Nginx** - Ingress controller

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

## Repository Structure

```text
.
├── docs/                    # Documentation
│   ├── k3s-setup.md        # k3s installation guide
│   └── claude_integration.md
├── helm/                    # Helm configurations
│   ├── charts/             # Custom Helm charts
│   │   ├── core-infrastructure/  # MetalLB, cert-manager, ingress
│   │   ├── monitoring/     # Prometheus, Grafana, Loki
│   │   └── storage/        # Longhorn storage
│   ├── environments/       # Environment-specific values
│   ├── repositories.yaml   # Helm repository definitions
│   └── helmfile.yaml      # Declarative release management
├── kubernetes/             # Base Kubernetes manifests
│   └── base/              # Namespace, RBAC, network policies
├── scripts/               # Deployment and utility scripts
└── terraform/            # Future Terraform configurations
```

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

## Network Configuration

For network setup, use the provided configuration files and templates.

### Server Details

- **k3s Master**: 192.168.16.26
- **Network Range**: 192.168.25.x

### MetalLB IP Allocation

Configuration files should be customized according to your setup requirements.

- **Development**: 192.168.25.200-192.168.25.210
- **Staging**: 192.168.25.220-192.168.25.235
- **Production**: 192.168.25.240-192.168.25.250

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

This homelab includes a testing framework with issue tracking and status reporting:

### Comprehensive Testing Suite

```bash
# Run all tests with detailed issue reporting
python3 scripts/testing/test_reporter.py --output-format all --export-issues

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

- **[Rootless Deployment Guide](docs/rootless-deployment-guide.md)**: Comprehensive security-hardened deployment
- **[Deployment Checklist](docs/deployment-checklist.md)**: Step-by-step validation checklist
- **[Architecture Overview](docs/architecture.md)**: System design and component relationships
- **[Security Guide](docs/security.md)**: Security practices and hardening

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
./scripts/deploy.sh -e production

# Dry run deployment
./scripts/deploy.sh -e production --dry-run

# Skip dependency updates
./scripts/deploy.sh -e development --skip-deps

# Update only specific release
helmfile --environment production apply --selector name=prometheus
```

## Access URLs

After deployment, services will be available at:

### Development URLs

- Grafana: <https://grafana.dev.homelab.local>
- Longhorn: <https://longhorn.dev.homelab.local>
- Prometheus: <https://prometheus.dev.homelab.local>

### Production URLs

- Grafana: <https://grafana.homelab.local>
- Longhorn: <https://longhorn.homelab.local>
- Prometheus: <https://prometheus.homelab.local>

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
