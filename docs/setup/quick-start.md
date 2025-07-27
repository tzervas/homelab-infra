# Quick Start Guide

Get your GitLab + Keycloak homelab infrastructure running in 30 minutes!

## 🎯 What You'll Get

- **🦊 GitLab**: Complete DevOps platform with CI/CD pipelines
- **🔐 Keycloak**: Single Sign-On (SSO) identity management
- **📊 Monitoring**: Prometheus + Grafana dashboards
- **🌐 Ingress**: NGINX with automatic TLS certificates
- **🔒 Security**: Network policies and secure bastion access

## ⚡ Prerequisites (5 minutes)

### Required

- **Linux server** with 16GB RAM, 4+ CPU cores, 200GB+ storage
- **SSH access** to your server with sudo privileges
- **Internet connection** for downloading dependencies
- **Local machine** with git, SSH, and Ansible installed

### Network Requirements

- **Static IP** for your homelab server
- **Port access**: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **IP range** for MetalLB load balancer (e.g., 192.168.1.200-220)

## 🚀 Quick Setup (10 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/tzervas/homelab-infra.git
cd homelab-infra

# Create your private configuration
cp .env .env.private.local
cp -r examples/private-config-template/ config/
```

### 2. Configure Network Settings

Edit `.env.private.local` with your actual network settings:

```bash
# Your homelab server details
HOMELAB_SERVER_IP=192.168.1.100      # Your server's IP
HOMELAB_SSH_USER=your-username        # Your SSH username
HOMELAB_DOMAIN=homelab.local          # Your domain

# MetalLB IP range (adjust to your network)
METALLB_IP_RANGE=192.168.1.200-192.168.1.220

# Service IP assignments
GITLAB_IP=192.168.1.201
KEYCLOAK_IP=192.168.1.202
REGISTRY_IP=192.168.1.203
PROMETHEUS_IP=192.168.1.204
GRAFANA_IP=192.168.1.205
```

### 3. Setup SSH Access

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy SSH key to your server
ssh-copy-id your-username@192.168.1.100

# Test SSH connection
ssh your-username@192.168.1.100 'echo "SSH works!"'
```

## 🧪 Test Deployment (10 minutes)

### 1. VM Testing (Recommended First Step)

```bash
# Test with a virtual machine first
./scripts/deploy-homelab.sh vm-test
```

This will:

- Create a test VM on your server
- Deploy the full stack
- Verify all components are working
- Test the bastion host security pattern

### 2. Validation

```bash
# Verify all services are running
kubectl get pods -A

# Check service URLs
kubectl get ingress -A

# Test web interfaces
curl -I https://gitlab.dev.homelab.local
curl -I https://keycloak.dev.homelab.local
```

## 🏗️ Production Deployment (5 minutes)

Once VM testing succeeds:

```bash
# Deploy to bare metal
./scripts/deploy-homelab.sh bare-metal
```

## 🌐 Access Your Services

Add these entries to your `/etc/hosts` file or router DNS:

```
192.168.1.201  gitlab.homelab.local
192.168.1.202  keycloak.homelab.local
192.168.1.204  prometheus.homelab.local
192.168.1.205  grafana.homelab.local
```

### Service URLs

- **GitLab**: <https://gitlab.homelab.local>
- **Keycloak**: <https://keycloak.homelab.local>
- **Grafana**: <https://grafana.homelab.local>
- **Prometheus**: <https://prometheus.homelab.local>

### Default Credentials

- **GitLab**: root / (check `kubectl get secret` for password)
- **Keycloak**: admin / (configured in your secrets)
- **Grafana**: admin / (configured in your secrets)

## 🔧 First-Time Setup Tasks

### 1. Configure Keycloak SSO

1. Access Keycloak admin console
2. Create realm for your organization
3. Configure GitLab OIDC integration
4. Set up user groups and permissions

### 2. Setup GitLab

1. Change root password
2. Configure SMTP settings
3. Enable container registry
4. Create your first project

### 3. Configure Monitoring

1. Access Grafana dashboards
2. Set up AlertManager notifications
3. Configure backup monitoring

## 🎉 Success Checklist

- [ ] All services accessible via HTTPS
- [ ] TLS certificates automatically provisioned
- [ ] Keycloak SSO working with GitLab
- [ ] Monitoring dashboards showing data
- [ ] Container registry functional
- [ ] CI/CD pipelines can run

## 🚨 Troubleshooting

### Services Not Accessible

```bash
# Check pod status
kubectl get pods -A

# Check ingress configuration
kubectl get ingress -A

# Check service endpoints
kubectl get svc -A
```

### TLS Certificate Issues

```bash
# Check cert-manager
kubectl get certificates -A
kubectl logs -n cert-manager deployment/cert-manager

# Check cluster issuer
kubectl get clusterissuer
```

### Resource Issues

```bash
# Check node resources
kubectl top nodes
kubectl describe node

# Check pod resources
kubectl top pods -A
```

## 📚 Next Steps

### Learn More

- **[Architecture Overview](architecture.md)** - Understand the system design
- **[Configuration Guide](../configuration/README.md)** - Customize your deployment
- **[Security Best Practices](../security/best-practices.md)** - Harden your installation

### Advanced Features

- **[Backup & Recovery](../operations/backup-recovery.md)** - Protect your data
- **[Monitoring Setup](../operations/monitoring.md)** - Advanced monitoring
- **[Scaling Guide](../operations/scaling.md)** - Grow your homelab

### Operations

- **[Maintenance Guide](../operations/maintenance.md)** - Keep it running smoothly
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Fix common problems

## 🆘 Getting Help

- **Issues**: [GitHub Issues](https://github.com/tzervas/homelab-infra/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tzervas/homelab-infra/discussions)
- **Documentation**: Browse other guides in this documentation

---

**🎊 Congratulations!** You now have a production-ready homelab infrastructure with GitLab, Keycloak, and comprehensive monitoring. Time to start building amazing projects!
