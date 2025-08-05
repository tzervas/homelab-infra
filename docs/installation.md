# Installation & Setup Guide

Complete installation guide for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.10 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **CPU**: Minimum 2 cores (4 cores recommended)
- **Storage**: 50GB+ available space
- **Network**: Internet access for package downloads

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3.10 python3.10-pip python3.10-venv -y

# Install system dependencies
sudo apt install curl wget git openssl -y

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Installation Methods

### Method 1: Git Clone (Recommended)

```bash
# Clone the repository
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra

# Create Python virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install the orchestrator in development mode
pip install -e .
```

### Method 2: PyPI Installation

```bash
# Create virtual environment
python3.10 -m venv homelab-orchestrator
cd homelab-orchestrator
source bin/activate

# Install from PyPI (when available)
pip install homelab-testing-framework==0.9.0b0
```

## Initial Configuration

### 1. Generate Secure Secrets

```bash
# Generate all required secrets
./scripts/security/generate-secrets.sh
```

This creates a `.env` file with secure random secrets for:

- OAuth2 client secrets
- Cookie encryption keys
- Database passwords
- TLS certificate email

### 2. Configure Domain

Update `.env` file:

```bash
# Domain Configuration
HOMELAB_DOMAIN=homelab.local  # Change to your domain
TLS_CERT_EMAIL=admin@yourdomain.com  # Required for Let's Encrypt
```

### 3. Choose Environment

```bash
# Development (uses Let's Encrypt staging)
ENVIRONMENT=development

# Staging (uses Let's Encrypt staging)
ENVIRONMENT=staging

# Production (uses Let's Encrypt production)
ENVIRONMENT=production
```

## Kubernetes Cluster Setup

### Option 1: K3s (Recommended)

```bash
# Install K3s
curl -sfL https://get.k3s.io | sh -

# Set up kubectl access
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
export KUBECONFIG=~/.kube/config

# Verify cluster
kubectl cluster-info
```

### Option 2: Existing Kubernetes Cluster

Ensure you have:

- `kubectl` configured and working
- Cluster admin permissions
- Ingress controller support
- LoadBalancer support (for bare metal: MetalLB)

## Validation

### 1. Test Orchestrator

```bash
# Check version
python -m homelab_orchestrator --version

# Validate configuration
python -m homelab_orchestrator config validate

# Test cluster connectivity
kubectl cluster-info
```

### 2. Run System Check

```bash
# Run comprehensive system validation
python scripts/testing/test_mvp_deployment.py
```

Expected output:

```
🎯 MVP Test Results: 5/5 tests passed
✅ Security Configuration: PASSED
✅ Version Information: PASSED  
✅ Configuration Validation: PASSED
✅ Cluster Connectivity: PASSED
✅ Orchestrator Functionality: PASSED
```

## First Deployment

### 1. Deploy Certificate Management

```bash
# Deploy cert-manager and issuers
python -m homelab_orchestrator certificates deploy
```

### 2. Deploy Core Infrastructure

```bash
# Dry run first
python -m homelab_orchestrator deploy infrastructure --components metallb cert_manager --dry-run

# Deploy for real
python -m homelab_orchestrator --environment development deploy infrastructure
```

### 3. Validate Deployment

```bash
# Check system status
python -m homelab_orchestrator status

# Validate certificates
python -m homelab_orchestrator certificates validate

# Check health
python -m homelab_orchestrator health check --comprehensive
```

## Directory Structure

After installation, your project should look like:

```
homelab-infra/
├── .env                          # Generated secrets (keep private!)
├── .venv/                        # Python virtual environment
├── config/                       # Configuration files
│   └── consolidated/             # Unified configuration
├── docs/                         # Documentation
├── homelab_orchestrator/         # Main orchestrator code
├── kubernetes/                   # Kubernetes manifests
├── scripts/                      # Utility scripts
│   └── security/                 # Security scripts
└── testing/                      # Testing framework
```

## Post-Installation

### 1. Set up DNS

For `.local` domains, configure your router or add to `/etc/hosts`:

```bash
# Add to /etc/hosts
192.168.1.100 homelab.local
192.168.1.100 grafana.homelab.local
192.168.1.100 prometheus.homelab.local
192.168.1.100 auth.homelab.local
```

### 2. Configure Firewall

```bash
# Allow required ports
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 6443/tcp   # Kubernetes API
```

### 3. Set up Backup

```bash
# Create backup of secrets
cp .env .env.backup
chmod 600 .env.backup

# Store backup securely (not in version control)
```

## Troubleshooting Installation

### Python Version Issues

```bash
# Check Python version
python3 --version

# Install specific Python version on Ubuntu
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-pip -y
```

### Permission Issues

```bash
# Fix kubectl permissions
sudo chown $USER:$USER ~/.kube/config

# Fix script permissions
chmod +x scripts/security/generate-secrets.sh
```

### Network Issues

```bash
# Test internet connectivity
curl -I https://google.com

# Test Kubernetes cluster
kubectl get nodes

# Test DNS resolution
nslookup homelab.local
```

### Dependency Issues

```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## Next Steps

1. [Quick Start Guide](quickstart.md) - Deploy your first service
2. [Certificate Management](certificates.md) - Set up TLS certificates
3. [Security Guide](security.md) - Secure your installation
4. [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Support

- **Installation Issues**: [GitHub Issues](https://github.com/tzervas/homelab-infra/issues)
- **Documentation**: [Full Documentation Index](README.md)
- **Community**: [GitHub Discussions](https://github.com/tzervas/homelab-infra/discussions)
