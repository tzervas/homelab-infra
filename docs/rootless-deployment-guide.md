# Rootless Deployment Guide for Homelab Infrastructure

This comprehensive guide covers deploying and managing the homelab infrastructure using rootless, security-hardened practices with proper privilege separation.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Server Setup](#initial-server-setup)
4. [Deployment User Configuration](#deployment-user-configuration)
5. [Security Context Configuration](#security-context-configuration)
6. [Deployment Process](#deployment-process)
7. [Testing and Validation](#testing-and-validation)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

## Overview

The rootless deployment approach provides enhanced security by:

- **Principle of Least Privilege**: Running containers and services as non-root users
- **Privilege Separation**: Dedicated deployment user with minimal sudo permissions
- **Security Contexts**: Comprehensive pod and container security policies
- **Audit Trail**: Full logging of privileged operations
- **Defense in Depth**: Multiple security layers and controls

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ or Debian 11+
- **Resources**: Minimum 4GB RAM, 2 CPU cores, 50GB storage
- **Network**: Static IP configuration recommended
- **Access**: SSH access with sudo privileges for initial setup

### Required Packages

The setup script will install these automatically:

- `sudo`, `openssh-server`, `curl`, `wget`, `git`, `acl`
- Docker (latest stable version)
- Kubernetes tools (kubectl, helm)

## Initial Server Setup

### 1. Clone Repository

```bash
# On the homelab server (192.168.16.26)
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra
```

### 2. Run Initial Security Setup

```bash
# This script requires initial sudo access
sudo ./scripts/deployment/setup-secure-deployment.sh

# Optional: Run with custom deployment user
sudo ./scripts/deployment/setup-secure-deployment.sh -u custom-deploy-user

# Verify setup only
sudo ./scripts/deployment/setup-secure-deployment.sh --verify-only
```

### 3. What the Setup Script Does

1. **Creates deployment user** (`homelab-deploy` by default)
2. **Configures SSH access** with key-based authentication
3. **Sets up sudo permissions** with minimal required commands
4. **Installs Docker** and adds user to docker group
5. **Creates directory structure** for deployment operations
6. **Sets up environment configuration** with secure defaults

## Deployment User Configuration

### User Structure

```
/home/homelab-deploy/
├── .ssh/                    # SSH keys and config
├── .kube/                   # Kubernetes configuration
├── .local/
│   ├── bin/                 # User binaries
│   └── log/                 # Deployment logs
├── .credentials/            # Secure credential storage
├── .environment            # Environment configuration
└── .bashrc                  # Shell configuration
```

### Environment Variables

The deployment user environment includes:

```bash
# Core configuration
export HOMELAB_USER="homelab-deploy"
export HOMELAB_HOME="/home/homelab-deploy"
export HOMELAB_DEPLOYMENT_MODE="rootless"

# Kubernetes configuration
export KUBECONFIG="$HOME/.kube/config"

# Helm configuration
export HELM_CACHE_HOME="$HOME/.cache/helm"
export HELM_CONFIG_HOME="$HOME/.config/helm"
export HELM_DATA_HOME="$HOME/.local/share/helm"

# Path configuration
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
```

### Sudo Permissions

The deployment user has passwordless sudo access to these specific commands:

```bash
# Systemd service management for K3s
systemctl {start,stop,restart,enable,disable,status} k3s*
systemctl daemon-reload

# Package management (limited)
apt update
apt install curl wget git
snap install kubectl helm

# File operations in system directories
mkdir -p /etc/rancher/k3s*
chown homelab-deploy:homelab-deploy /etc/rancher/k3s*

# K3s and Docker operations
/usr/local/bin/k3s*
docker system prune -f
```

## Security Context Configuration

### Global Security Standards

All Helm charts include security contexts:

```yaml
global:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
    capabilities:
      drop:
        - ALL
```

### Component-Specific Security

#### Standard Applications

```yaml
# For most applications (GitLab, Keycloak, monitoring)
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false  # When app needs write access
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
      - ALL
```

#### System Components

```yaml
# For components that need specific permissions (Longhorn, nginx)
securityContext:
  runAsNonRoot: false  # When root access is required
  runAsUser: 0
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE  # For port binding
      - SYS_ADMIN        # For storage operations
```

### Pod Security Standards

Namespaces are configured with appropriate security policies:

- **Production**: `enforce: restricted`
- **Staging**: `enforce: restricted`
- **Development**: `enforce: baseline`
- **System**: `enforce: privileged` (for infrastructure components)

## Deployment Process

### 1. Environment Configuration

```bash
# Switch to deployment user
su - homelab-deploy

# Configure environment variables
cp helm/environments/.env.template .env
# Edit .env with your specific values
```

### 2. Credential Management

```bash
# Set up credentials securely
cd .credentials
cp .env.template .env
# Fill in sensitive values

# Ensure proper permissions
chmod 600 .env
chmod 700 .credentials/
```

### 3. Run Compatibility Check

```bash
# Verify rootless deployment readiness
python3 scripts/testing/rootless_compatibility.py --log-level INFO

# Export detailed report
python3 scripts/testing/rootless_compatibility.py --output compatibility-report.md
```

### 4. Deploy Infrastructure

```bash
# Check prerequisites
./scripts/deployment/deploy-with-privileges.sh check

# Deploy core infrastructure
./scripts/deployment/deploy-with-privileges.sh deploy k3s
./scripts/deployment/deploy-with-privileges.sh deploy metallb
./scripts/deployment/deploy-with-privileges.sh deploy cert-manager

# Deploy applications
./scripts/deployment/deploy-with-privileges.sh deploy gitlab
./scripts/deployment/deploy-with-privileges.sh deploy keycloak
./scripts/deployment/deploy-with-privileges.sh deploy monitoring

# Or deploy everything at once
./scripts/deployment/deploy-with-privileges.sh deploy all
```

### 5. Verify Deployment

```bash
# Check deployment status
./scripts/deployment/deploy-with-privileges.sh status

# Run comprehensive tests
./scripts/deployment/deploy-with-privileges.sh test
```

## Testing and Validation

### Compatibility Testing

```bash
# Run rootless compatibility check
python3 scripts/testing/rootless_compatibility.py

# Expected output for successful setup:
# - Compatible Components: 5/5
# - Overall Status: ✅ Ready for rootless deployment
```

### Security Validation

```bash
# Run security context validation
python3 scripts/testing/network_security.py --log-level INFO

# Check for security issues
python3 scripts/testing/test_reporter.py --output-format issues
```

### Service Health Checks

```bash
# Infrastructure health monitoring
python3 scripts/testing/infrastructure_health.py

# Service deployment validation
python3 scripts/testing/service_checker.py

# Integration testing
python3 scripts/testing/integration_tester.py
```

### Comprehensive Test Suite

```bash
# Run complete test suite with issue tracking
python3 scripts/testing/test_reporter.py \
  --output-format all \
  --export-issues \
  --log-level INFO

# This generates:
# - Console summary with issue counts
# - JSON report with detailed results
# - Markdown report with issue breakdown
# - Dedicated issue report with prioritization
```

## Troubleshooting

### Common Issues

#### 1. Deployment User Creation Fails

```bash
# Check if script has proper permissions
ls -la scripts/deployment/setup-secure-deployment.sh

# Run with debug output
sudo DEBUG=true ./scripts/deployment/setup-secure-deployment.sh

# Check system logs
sudo tail -f /var/log/homelab-secure-setup.log
```

#### 2. Kubernetes Connection Issues

```bash
# Verify K3s service status
sudo systemctl status k3s

# Check cluster connectivity
kubectl cluster-info

# Verify kubeconfig permissions
ls -la ~/.kube/config
```

#### 3. Permission Denied Errors

```bash
# Check sudo configuration
sudo -l

# Verify user groups
groups

# Test specific sudo commands
sudo systemctl status k3s
```

#### 4. Security Context Violations

```bash
# Check pod security standards
kubectl get ns -o yaml | grep pod-security

# Verify security contexts in running pods
kubectl get pods -o jsonpath='{.items[*].spec.securityContext}'

# Check for privileged containers
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].securityContext}'
```

### Log Locations

- **Setup logs**: `/var/log/homelab-secure-setup.log`
- **Deployment logs**: `~/.local/log/homelab-deploy.log`
- **Sudo audit logs**: `/var/log/sudo-io/homelab-deploy/`
- **Test results**: `test_results/`

### Debugging Commands

```bash
# Check deployment user configuration
./scripts/deployment/setup-secure-deployment.sh --verify-only

# Test deployment prerequisites
./scripts/deployment/deploy-with-privileges.sh check

# Run compatibility check with debug output
python3 scripts/testing/rootless_compatibility.py --log-level DEBUG

# Check specific security contexts
kubectl get pods -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,USER:.spec.securityContext.runAsUser,NONROOT:.spec.securityContext.runAsNonRoot"
```

## Security Best Practices

### 1. Credential Management

- **Never commit secrets** to version control
- **Use environment variables** for sensitive values
- **Implement secret rotation** regularly
- **Use Kubernetes secrets** for runtime credentials
- **Encrypt sensitive files** at rest

### 2. Access Control

- **Principle of least privilege** for all operations
- **Regular audit** of sudo permissions
- **SSH key-based authentication** only
- **Multi-factor authentication** where possible
- **Network segmentation** for services

### 3. Monitoring and Alerting

- **Log all privileged operations** with sudo audit
- **Monitor security context violations**
- **Alert on privilege escalation attempts**
- **Regular security scans** with testing framework
- **Automated compliance checking**

### 4. Backup and Recovery

- **Regular configuration backups**
- **Credential backup** (encrypted)
- **Infrastructure as Code** for reproducibility
- **Disaster recovery procedures**
- **Tested restore processes**

### 5. Updates and Maintenance

- **Regular security updates** for base system
- **Container image scanning** for vulnerabilities
- **Kubernetes version management**
- **Dependency vulnerability monitoring**
- **Security patch management**

## Advanced Configuration

### Custom Security Contexts

For applications requiring special permissions:

```yaml
# Example: Application needing specific capabilities
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  fsGroup: 1001
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
      - ALL
    add:
      - NET_ADMIN  # Only if absolutely necessary
  allowPrivilegeEscalation: false
```

### Network Security Policies

```yaml
# Example: Restrictive network policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53  # Allow DNS only
```

### Custom Deployment User

```bash
# Create custom deployment user
sudo ./scripts/deployment/setup-secure-deployment.sh -u custom-user

# Update Ansible configuration
export HOMELAB_USER=custom-user

# Update deployment scripts
./scripts/deployment/deploy-with-privileges.sh -u custom-user deploy all
```

## Conclusion

This rootless deployment approach provides a security-hardened foundation for homelab infrastructure while maintaining operational flexibility. The combination of dedicated deployment users, comprehensive security contexts, and robust testing ensures both security and reliability.

Regular validation using the provided testing framework helps maintain security posture and quickly identify any configuration drift or security issues.

For additional support or questions, refer to the project documentation or create an issue in the repository.
