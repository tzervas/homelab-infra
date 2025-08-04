# Quick Start Guide

Get your Homelab Infrastructure Orchestrator up and running in 15 minutes.

## Prerequisites

- Linux system with Python 3.10+
- 4GB+ RAM, 2+ CPU cores
- Internet connection

## 🚀 15-Minute Setup

### Step 1: Install (2 minutes)

```bash
# Clone and setup
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip && pip install -r requirements.txt
pip install -e .
```

### Step 2: Install K3s (3 minutes)

```bash
# Install K3s Kubernetes
curl -sfL https://get.k3s.io | sh -

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config

# Test cluster
kubectl get nodes
```

### Step 3: Generate Secrets (1 minute)

```bash
# Generate all secure secrets automatically
./scripts/security/generate-secrets.sh

# Verify secrets were created
ls -la .env
```

### Step 4: Validate Setup (2 minutes)

```bash
# Test orchestrator
python -m homelab_orchestrator --version

# Validate configuration
python -m homelab_orchestrator config validate

# Run system tests
python scripts/testing/test_mvp_deployment.py
```

Expected output:
```
🎯 MVP Test Results: 5/5 tests passed
🎉 All MVP deployment tests passed! Ready for release.
```

### Step 5: Deploy Certificates (3 minutes)

```bash
# Deploy cert-manager and certificate issuers
python -m homelab_orchestrator certificates deploy

# Wait for cert-manager to be ready (this may take 2-3 minutes)
kubectl get pods -n cert-manager -w
```

### Step 6: Deploy Infrastructure (4 minutes)

```bash
# Deploy core infrastructure with dry-run first
python -m homelab_orchestrator deploy infrastructure --components metallb cert_manager ingress_nginx --dry-run

# Deploy for real (development environment uses Let's Encrypt staging)
python -m homelab_orchestrator --environment development deploy infrastructure --components metallb cert_manager ingress_nginx
```

## 🎯 Verification

### Check System Status

```bash
# Overall system status
python -m homelab_orchestrator status

# Check certificates
python -m homelab_orchestrator certificates validate

# Health check
python -m homelab_orchestrator health check --comprehensive
```

### Access Services

Check that your services are accessible:

```bash
# Check cluster info
kubectl cluster-info

# Check running pods
kubectl get pods -A

# Check certificates
kubectl get certificates -A
```

## 🌟 What You've Deployed

Your homelab now includes:

- **K3s Kubernetes Cluster**: Container orchestration
- **cert-manager**: Automatic TLS certificate management
- **MetalLB**: Load balancer for bare metal
- **NGINX Ingress**: HTTP/HTTPS routing
- **Certificate Issuers**: Let's Encrypt staging + self-signed fallback

## 🎨 Next Steps

### Deploy Applications

```bash
# Deploy monitoring stack
python -m homelab_orchestrator deploy infrastructure --components monitoring

# Deploy Keycloak (authentication)
python -m homelab_orchestrator deploy infrastructure --components keycloak

# Deploy everything
python -m homelab_orchestrator deploy infrastructure
```

### Configure Services

1. **Update domain**: Edit `.env` and change `HOMELAB_DOMAIN`
2. **Production certificates**: Change `ENVIRONMENT=production` in `.env`
3. **Custom configuration**: Modify files in `config/consolidated/`

### Access Web UIs

Add to your `/etc/hosts` file:
```
192.168.1.100 homelab.local
192.168.1.100 grafana.homelab.local
192.168.1.100 prometheus.homelab.local
192.168.1.100 auth.homelab.local
```

Then access:
- **Grafana**: https://grafana.homelab.local
- **Prometheus**: https://prometheus.homelab.local
- **Keycloak**: https://auth.homelab.local

## 🔧 Common Commands

```bash
# Check orchestrator version
python -m homelab_orchestrator --version

# View all available commands
python -m homelab_orchestrator --help

# Deploy specific components
python -m homelab_orchestrator deploy infrastructure --components <component>

# Check certificate expiry
python -m homelab_orchestrator certificates check-expiry

# Force certificate renewal
python -m homelab_orchestrator certificates renew <cert-name>

# System health check
python -m homelab_orchestrator health check

# View system status
python -m homelab_orchestrator status
```

## 🚨 Troubleshooting Quick Fixes

### Orchestrator Not Found
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall if needed
pip install -e .
```

### Kubectl Permission Denied
```bash
# Fix permissions
sudo chown $USER:$USER ~/.kube/config
```

### Certificate Issues
```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Check certificate status
kubectl get certificates -A

# Check certificate issuer status
kubectl get clusterissuers
```

### Services Not Accessible
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check services
kubectl get svc -A

# Check if MetalLB assigned IPs
kubectl get svc -n ingress-nginx
```

## 📚 Learn More

- **[Installation Guide](installation.md)**: Detailed installation instructions
- **[Certificate Management](certificates.md)**: Complete TLS setup
- **[Configuration](configuration.md)**: Customize your deployment
- **[Security Guide](security.md)**: Security best practices
- **[Troubleshooting](troubleshooting.md)**: Detailed problem solving

## 🎉 Success!

You now have a fully functional homelab infrastructure orchestrator with:

✅ **Kubernetes cluster** (K3s)  
✅ **Certificate management** (Let's Encrypt + self-signed)  
✅ **Load balancing** (MetalLB)  
✅ **Ingress routing** (NGINX)  
✅ **Security-first configuration** (no hardcoded secrets)  
✅ **Unified management** (single CLI interface)  

Ready to deploy applications and build your homelab! 🏠⚡