# Configuration Management

This guide covers all aspects of configuring your homelab infrastructure, from basic environment variables to advanced service customization.

## 📁 Configuration Structure

```
homelab-infra/
├── .env                     # Public environment variables (safe defaults)
├── .env.private.local       # Private local overrides (not tracked)
├── examples/
│   ├── basic-setup/         # Basic configuration examples
│   └── private-config-template/  # Private configuration templates
│       ├── environments/    # Environment-specific settings
│       ├── secrets/         # Secret templates (placeholder values)
│       └── values/          # Helm values overrides
├── helm/
│   ├── environments/        # Helm environment values
│   └── charts/              # Chart definitions
└── config/                  # Your private config (local only)
    ├── environments/        # Your environment settings
    ├── secrets/             # Your actual secrets
    └── values/              # Your Helm overrides
```

## 🔧 Configuration Layers

The configuration system uses a layered approach for maximum flexibility:

### 1. Public Defaults (`.env`)
- Safe default values
- Network configurations with placeholder IPs
- Component versions
- Public settings that can be shared

### 2. Private Overrides (`.env.private.local`)
- Your actual network settings
- Server credentials
- Custom domain names
- Local environment overrides

### 3. Helm Values (`config/values/`)
- Application-specific settings
- Service configurations
- Resource limits and requests
- Custom application parameters

### 4. Environment Settings (`config/environments/`)
- Development, staging, production settings
- Environment-specific resource allocations
- Different service endpoints per environment

### 5. Secrets (`config/secrets/`)
- Encrypted credentials
- API keys and tokens
- Database passwords
- TLS certificates

## 🚀 Quick Setup

### 1. Initial Configuration

```bash
# Copy environment template
cp .env .env.private.local

# Copy configuration templates
cp -r examples/private-config-template/ config/

# Edit your private settings
nano .env.private.local
```

### 2. Basic Network Configuration

Edit `.env.private.local`:

```bash
# Your homelab server
HOMELAB_SERVER_IP=192.168.1.100
HOMELAB_SSH_USER=your-username

# Your network settings
HOMELAB_DOMAIN=homelab.local
METALLB_IP_RANGE=192.168.1.200-192.168.1.220

# Service IPs
GITLAB_IP=192.168.1.201
KEYCLOAK_IP=192.168.1.202
PROMETHEUS_IP=192.168.1.204
GRAFANA_IP=192.168.1.205
```

### 3. Service Customization

Edit `config/values/global.yaml`:

```yaml
global:
  domain: homelab.local
  timezone: America/New_York

ingress:
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod

storage:
  defaultClass: longhorn
  size: 10Gi
```

## 📝 Detailed Configuration Guides

### Environment Variables
- **[Complete Environment Variables Guide](environment-variables.md)**
- All available variables and their purposes
- Network configuration options
- Service-specific settings

### Private Configuration
- **[Private Configuration Management](private-configuration.md)**
- Managing secrets securely
- Environment-specific settings
- Best practices for sensitive data

### Helm Values
- **[Helm Values Customization](helm-values.md)**
- Application-specific configurations
- Resource management
- Advanced deployment options

### Service Configuration
- **[Individual Service Settings](services.md)**
- GitLab configuration
- Keycloak setup
- Monitoring configuration

## 🔐 Security Considerations

### What to Keep Private
- Server IP addresses and credentials
- Domain names (if sensitive)
- API keys and tokens
- Database passwords
- TLS certificates and keys

### What's Safe to Share
- Default resource allocations
- Public configuration templates
- Component versions
- General deployment settings

### File Protection
```bash
# Ensure private files have correct permissions
chmod 600 .env.private.local
chmod -R 600 config/secrets/

# Add to .gitignore (already configured)
echo ".env.private.local" >> .gitignore
echo "config/" >> .gitignore
```

## 🔄 Configuration Workflow

### Development Environment
1. Use example configurations as starting point
2. Override with local development settings
3. Test with VM deployment first
4. Validate all services are accessible

### Staging Environment
1. Copy development configuration
2. Update with staging-specific settings
3. Use staging domain names
4. Deploy to staging infrastructure

### Production Environment
1. Review all security settings
2. Use production domains and certificates
3. Enable monitoring and alerting
4. Configure backup procedures

## 🛠️ Configuration Tools

### Validation Scripts
```bash
# Validate configuration syntax
./scripts/validate-deployment-local.sh

# Test network connectivity
./scripts/test-deployment-readiness.sh

# Dry-run deployment
./scripts/test-deployment-dry-run.sh
```

### Configuration Management
```bash
# Check current configuration
./scripts/deploy-homelab.sh vm-test --dry-run

# Validate Kubernetes manifests
./scripts/validate-k8s-manifests.sh

# Update configuration from templates
cp -r examples/private-config-template/* config/
```

## 📋 Configuration Checklist

### Pre-Deployment Checklist
- [ ] Network settings configured in `.env.private.local`
- [ ] SSH keys set up and accessible
- [ ] Domain names configured (if using custom domains)
- [ ] Service IP addresses allocated
- [ ] Secrets configured in `config/secrets/`
- [ ] Helm values customized in `config/values/`
- [ ] Environment settings reviewed
- [ ] Configuration validated with scripts

### Post-Deployment Checklist
- [ ] All services accessible via web interfaces
- [ ] TLS certificates properly issued
- [ ] Monitoring dashboards displaying data
- [ ] Backup procedures configured
- [ ] Documentation updated with actual settings

## 🔍 Troubleshooting Configuration

### Common Issues
- **Service not accessible**: Check IP assignments and ingress configuration
- **TLS certificate issues**: Verify domain configuration and cert-manager settings
- **Resource constraints**: Review resource requests and limits in Helm values
- **Authentication problems**: Check Keycloak configuration and user setup

### Debug Commands
```bash
# Check current environment variables
env | grep HOMELAB

# Validate Helm values
helm lint helm/charts/*/

# Check Kubernetes configuration
kubectl get ingress -A
kubectl get certificates -A
```

## 📚 Related Documentation

- [Environment Variables Guide](environment-variables.md)
- [Private Configuration Guide](private-configuration.md)
- [Helm Values Reference](helm-values.md)
- [Service Configuration](services.md)
- [Security Best Practices](../security/best-practices.md)

---

**Next Steps**: Once configuration is complete, proceed to [VM Testing](../deployment/vm-testing.md) to validate your setup.
