# Configuration Guide

Comprehensive configuration guide for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## Configuration Architecture

The orchestrator uses a hierarchical configuration system:

```
config/
├── consolidated/           # Single source of truth
│   ├── certificates.yaml  # Certificate management
│   ├── domains.yaml       # Domain configuration
│   ├── namespaces.yaml    # Kubernetes namespaces
│   ├── networking.yaml    # Network configuration
│   ├── resources.yaml     # Resource allocation
│   ├── security.yaml      # Security settings
│   ├── services.yaml      # Service definitions
│   └── storage.yaml       # Storage configuration
├── environments/          # Environment overrides
│   ├── development.yaml   # Development settings
│   ├── staging.yaml       # Staging settings
│   └── production.yaml    # Production settings
└── templates/             # Configuration templates
```

## Environment Variables

### Required Variables

Create these in your `.env` file (use `./scripts/security/generate-secrets.sh`):

```bash
# Security Configuration - REQUIRED
OAUTH2_CLIENT_SECRET=<base64-encoded-secret>
OAUTH2_COOKIE_SECRET=<base64-encoded-32-byte-key>
PROMETHEUS_OAUTH2_CLIENT_SECRET=<base64-encoded-secret>
PROMETHEUS_OAUTH2_COOKIE_SECRET=<base64-encoded-32-byte-key>

# Authentication
GRAFANA_ADMIN_PASSWORD=<secure-password>

# TLS/SSL Configuration
TLS_CERT_EMAIL=admin@yourdomain.com
ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory
CERT_EXPIRY_WEBHOOK_URL=

# Storage
LONGHORN_REPLICA_COUNT=3
LONGHORN_BACKUP_TARGET=
LONGHORN_BACKUP_SECRET=<encryption-key>

# Environment
ENVIRONMENT=development  # development, staging, or production
DEBUG=false
HOMELAB_DOMAIN=homelab.local
```

### Optional Variables

```bash
# Custom CA (if using internal PKI)
CUSTOM_CA_CERT=
CUSTOM_CA_KEY=

# Monitoring
PROMETHEUS_RETENTION_DAYS=30
PROMETHEUS_STORAGE_SIZE=50Gi
LOKI_STORAGE_SIZE=20Gi
GRAFANA_STORAGE_SIZE=10Gi

# Backup Configuration
BACKUP_RETENTION_DAYS=30
```

## Core Configuration Files

### certificates.yaml

Certificate management configuration:

```yaml
certificates:
  issuers:
    letsencrypt_prod:
      enabled: true
      type: "letsencrypt"
      server: "https://acme-v02.api.letsencrypt.org/directory"
      email: "${TLS_CERT_EMAIL}"
      solver:
        type: "http01"
        ingress_class: "nginx"
    
    selfsigned:
      enabled: true
      type: "selfsigned"
      common_name: "homelab.local"

  requests:
    wildcard_homelab:
      enabled: true
      issuer: "letsencrypt_prod"
      fallback_issuer: "selfsigned"
      dns_names:
        - "homelab.local"
        - "*.homelab.local"
```

### networking.yaml

Network configuration:

```yaml
networking:
  cluster:
    pod_cidr: "10.42.0.0/16"
    service_cidr: "10.43.0.0/16"
    dns_domain: "cluster.local"
  
  ingress:
    class: "nginx"
    default_backend: "default-http-backend"
    ssl_redirect: true
    
  load_balancer:
    type: "metallb"
    ip_pool: "192.168.1.100-192.168.1.110"
```

### services.yaml

Service definitions and discovery:

```yaml
services:
  discovery:
    grafana:
      namespace: "monitoring"
      port: 3000
    prometheus:
      namespace: "monitoring"
      port: 9090
    keycloak:
      namespace: "keycloak"
      port: 8080

  urls:
    external:
      grafana: "https://grafana.homelab.local"
      prometheus: "https://prometheus.homelab.local"
      keycloak: "https://auth.homelab.local"
```

### security.yaml

Security configuration:

```yaml
security:
  pod_security_standards:
    default: "restricted"
    monitoring: "baseline"
    kube-system: "privileged"
  
  network_policies:
    enabled: true
    default_deny: true
    
  image_security:
    enforce_signed_images: false
    allowed_registries:
      - "docker.io"
      - "quay.io"
      - "gcr.io"
```

## Environment-Specific Configuration

### Development Environment

```yaml
# config/environments/development.yaml
environment: development

certificates:
  issuers:
    letsencrypt_prod:
      enabled: false
    letsencrypt_staging:
      enabled: true

security:
  pod_security_standards:
    default: "baseline"  # More permissive for development
    
monitoring:
  retention_days: 7
  storage_size: "10Gi"
```

### Production Environment

```yaml
# config/environments/production.yaml
environment: production

certificates:
  issuers:
    letsencrypt_prod:
      enabled: true
    letsencrypt_staging:
      enabled: false

security:
  pod_security_standards:
    default: "restricted"  # Strict security
  network_policies:
    enabled: true
    
monitoring:
  retention_days: 90
  storage_size: "100Gi"
  alerting:
    enabled: true
```

## Configuration Validation

### Validate Configuration

```bash
# Validate all configuration
python -m homelab_orchestrator config validate

# Validate specific environment
python -m homelab_orchestrator --environment production config validate

# Show configuration (without secrets)
python -m homelab_orchestrator config show

# Show specific configuration section
python -m homelab_orchestrator config show networking
```

### Common Validation Errors

#### Missing Required Fields

```bash
# Error: Missing 'environment' field in helm/environments/secrets-dev.yaml
# Fix: Add environment field
echo "environment: development" >> helm/environments/secrets-dev.yaml
```

#### Invalid YAML Syntax

```bash
# Error: YAML syntax error
# Fix: Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/consolidated/networking.yaml'))"
```

#### Missing Configuration Files

```bash
# Error: Missing required configuration: certificates
# Fix: Ensure file exists
ls -la config/consolidated/certificates.yaml
```

## Configuration Customization

### Override Configuration

Create environment-specific overrides:

```yaml
# config/environments/custom.yaml
environment: custom

# Override specific settings
networking:
  load_balancer:
    ip_pool: "192.168.10.100-192.168.10.110"

certificates:
  requests:
    wildcard_homelab:
      dns_names:
        - "custom.local"
        - "*.custom.local"
```

### Template Processing

Configuration files support environment variable substitution:

```yaml
# config/consolidated/certificates.yaml
certificates:
  issuers:
    letsencrypt_prod:
      email: "${TLS_CERT_EMAIL}"  # Replaced with .env value
      
# config/consolidated/domains.yaml
domains:
  primary: "${HOMELAB_DOMAIN}"  # Replaced with .env value
```

## Advanced Configuration

### Custom Resource Allocation

```yaml
# config/consolidated/resources.yaml
resources:
  node_allocations:
    master:
      cpu: "2"
      memory: "4Gi"
    worker:
      cpu: "4"
      memory: "8Gi"
      
  service_resources:
    monitoring:
      prometheus:
        cpu: "500m"
        memory: "2Gi"
        storage: "50Gi"
      grafana:
        cpu: "200m"
        memory: "512Mi"
```

### Storage Configuration

```yaml
# config/consolidated/storage.yaml
storage:
  classes:
    - name: "fast-ssd"
      provisioner: "local-path"
      reclaim_policy: "Retain"
    - name: "longhorn"
      provisioner: "driver.longhorn.io"
      reclaim_policy: "Delete"
      
  longhorn:
    replica_count: 3
    backup_target: "s3://my-bucket"
    data_path: "/var/lib/longhorn"
```

### Network Policies

```yaml
# config/consolidated/security.yaml
security:
  network_policies:
    enabled: true
    policies:
      - name: "deny-all-default"
        namespace: "default"
        spec:
          podSelector: {}
          policyTypes:
            - Ingress
            - Egress
            
      - name: "allow-monitoring"
        namespace: "monitoring"
        spec:
          podSelector: {}
          ingress:
            - from:
                - namespaceSelector:
                    matchLabels:
                      name: "ingress-nginx"
```

## Configuration Management Best Practices

### 1. Version Control

```bash
# Track configuration changes
git add config/
git commit -m "Update configuration for production deployment"
```

### 2. Environment Separation

- **Development**: Use staging certificates, relaxed security
- **Staging**: Production-like configuration, staging certificates
- **Production**: Strict security, production certificates

### 3. Secret Management

```bash
# Never commit secrets to version control
echo ".env" >> .gitignore
echo "*.secret" >> .gitignore

# Use secure secret generation
./scripts/security/generate-secrets.sh

# Backup secrets securely
cp .env .env.backup-$(date +%Y%m%d)
chmod 600 .env.backup-*
```

### 4. Configuration Testing

```bash
# Test configuration changes
python -m homelab_orchestrator config validate

# Test deployment with dry-run
python -m homelab_orchestrator deploy infrastructure --dry-run

# Test in development first
python -m homelab_orchestrator --environment development deploy infrastructure
```

### 5. Documentation

Document all configuration changes:

```yaml
# config/consolidated/custom-config.yaml
# Purpose: Custom configuration for specific deployment
# Author: Your Name
# Date: 2025-08-04
# Changes: Added custom domain and resource overrides

# Your configuration here...
```

## Troubleshooting Configuration

### Debug Configuration Loading

```bash
# Enable debug logging
python -m homelab_orchestrator --log-level DEBUG config validate

# Check configuration merging
python -c "
from homelab_orchestrator.core.config_manager import ConfigManager
cm = ConfigManager.from_environment()
import json
print(json.dumps(cm.get_deployment_config(), indent=2, default=str))
"
```

### Common Issues

#### Environment Variables Not Loaded

```bash
# Ensure .env file exists and is readable
ls -la .env
cat .env | head -5

# Source variables manually if needed
source .env
env | grep OAUTH2
```

#### Configuration Not Applied

```bash
# Check configuration cache
rm -rf ~/.cache/homelab-orchestrator/

# Restart orchestrator
python -m homelab_orchestrator config validate
```

## Migration and Updates

### Migrating Configuration

When updating from older versions:

1. **Backup existing configuration**:
   ```bash
   tar -czf config-backup-$(date +%Y%m%d).tar.gz config/
   ```

2. **Update configuration schema**:
   ```bash
   python -m homelab_orchestrator config validate --fix-schema
   ```

3. **Test configuration**:
   ```bash
   python -m homelab_orchestrator config validate
   python -m homelab_orchestrator deploy infrastructure --dry-run
   ```

### Configuration Schema Updates

The orchestrator automatically handles configuration schema updates, but you may need to:

1. Add new required fields
2. Update deprecated settings
3. Migrate old format to new format

## Next Steps

- [Certificate Management](certificates.md) - Configure TLS certificates
- [Security Guide](security.md) - Secure your configuration
- [Deployment Guide](deployment.md) - Deploy with your configuration
- [Troubleshooting](troubleshooting.md) - Fix configuration issues