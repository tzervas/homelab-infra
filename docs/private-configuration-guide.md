# Private Configuration Setup Guide

This guide explains how to set up and manage the private configuration repository for your homelab infrastructure.

## Overview

The homelab infrastructure uses a three-repository architecture:

1. **Main Repository** (`homelab-infra`): Public infrastructure code, documentation, and examples
2. **Private Repository** (`homelab-infra-private`): Sensitive configurations, secrets, and overrides
3. **Examples Repository** (optional): Template configurations for different scenarios

## Setting Up Private Configuration

### Step 1: Create Private Repository

Create a private repository to store your sensitive configurations:

```bash
# Example using GitHub
git clone git@github.com:username/homelab-infra-private.git
cd homelab-infra-private

# Initialize with basic structure
git init
echo "# Private Homelab Configuration" > README.md
git add README.md
git commit -m "Initial commit"
git push -u origin main
```

### Step 2: Configure Environment Variables

In your main repository, update the `.env` file:

```bash
# Private Configuration Repository
PRIVATE_CONFIG_REPO=git@github.com:username/homelab-infra-private.git
PRIVATE_CONFIG_BRANCH=main
PRIVATE_CONFIG_DIR=config
```

### Step 3: Initialize Private Configuration

Run the sync script to set up the private configuration:

```bash
./scripts/sync-private-config.sh sync
```

This will:
- Clone your private repository to `.private-config/`
- Create the directory structure
- Copy example configurations
- Create template files

## Directory Structure

Your private repository will have the following structure:

```
.private-config/
├── README.md                    # Documentation
├── .env.private                 # Private environment variables
└── config/                      # Configuration directory
    ├── values/                  # Helm values overrides
    │   ├── global.yaml         # Global configuration
    │   ├── gitlab.yaml         # GitLab configuration
    │   ├── keycloak.yaml       # Keycloak configuration
    │   └── monitoring.yaml     # Monitoring configuration
    ├── secrets/                # Encrypted secrets
    │   ├── gitlab-secrets.yaml
    │   ├── keycloak-secrets.yaml
    │   └── tls-certificates.yaml
    └── environments/           # Environment-specific configs
        ├── development.yaml
        ├── staging.yaml
        └── production.yaml
```

## Configuration Files

### Private Environment Variables (`.env.private`)

This file contains sensitive environment variables that override values in the main `.env` file:

```bash
# Sensitive Configuration
GITLAB_ROOT_PASSWORD=your-secure-password
KEYCLOAK_ADMIN_PASSWORD=your-keycloak-password
POSTGRES_PASSWORD=your-postgres-password

# SMTP Configuration
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_HOST=smtp.your-domain.com
SMTP_PORT=587

# Backup Configuration
BACKUP_S3_ACCESS_KEY=your-s3-access-key
BACKUP_S3_SECRET_KEY=your-s3-secret-key
BACKUP_S3_ENDPOINT=s3.your-provider.com
BACKUP_S3_BUCKET=homelab-backups

# SSL Certificates
SSL_CERT_EMAIL=admin@your-domain.com
```

### Global Configuration (`config/values/global.yaml`)

Global overrides that apply across all services:

```yaml
global:
  domain: "homelab.yourdomain.com"
  storageClass: "longhorn"
  timezone: "America/New_York"

  # TLS Configuration
  tls:
    enabled: true
    issuer: "letsencrypt-prod"

  # Resource defaults
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

### GitLab Configuration (`config/values/gitlab.yaml`)

GitLab-specific overrides:

```yaml
gitlab:
  global:
    hosts:
      domain: homelab.yourdomain.com

  gitlab:
    gitlab-shell:
      hostKeys:
        secret: gitlab-shell-host-keys

  redis:
    auth:
      existingSecret: gitlab-redis-secret

  postgresql:
    auth:
      existingSecret: gitlab-postgresql-secret
```

## Security Best Practices

### 1. Encryption

Always encrypt sensitive data in your private repository:

```bash
# Using SOPS for encryption
sops -e config/secrets/gitlab-secrets.yaml > config/secrets/gitlab-secrets.enc.yaml

# Using sealed-secrets
kubeseal -f config/secrets/gitlab-secrets.yaml -w config/secrets/gitlab-secrets-sealed.yaml
```

### 2. Access Control

- Limit repository access to authorized users only
- Use SSH keys for authentication
- Enable branch protection rules
- Require signed commits

### 3. Credential Rotation

- Regularly rotate passwords and API keys
- Update secrets in both the private repository and Kubernetes cluster
- Use external secret management when possible (HashiCorp Vault, etc.)

## Usage During Deployment

The deployment script automatically handles private configuration:

```bash
# The deployment script will:
# 1. Sync the private repository
# 2. Load .env.private variables
# 3. Use private configurations during deployment

./scripts/deploy-homelab.sh vm-test
```

## Management Commands

### Sync Private Configuration

```bash
# Sync latest changes from private repository
./scripts/sync-private-config.sh sync

# Initialize structure (for new repositories)
./scripts/sync-private-config.sh init

# Validate configuration
./scripts/sync-private-config.sh validate

# Clean local cache
./scripts/sync-private-config.sh clean
```

### Manual Operations

```bash
# Access private configuration directory
cd .private-config

# Make changes to private configuration
vim config/values/gitlab.yaml

# Commit changes to private repository
git add .
git commit -m "Update GitLab configuration"
git push
```

## Environment-Specific Configurations

### Development Environment

```yaml
# config/environments/development.yaml
environment: development

gitlab:
  replicas: 1
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

keycloak:
  replicas: 1
  database:
    vendor: h2  # In-memory database for development
```

### Production Environment

```yaml
# config/environments/production.yaml
environment: production

gitlab:
  replicas: 3
  resources:
    requests:
      memory: "4Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"

keycloak:
  replicas: 2
  database:
    vendor: postgres
    existingSecret: keycloak-db-secret
```

## Troubleshooting

### Common Issues

1. **Private repository not found**
   ```bash
   # Check repository URL and access
   git ls-remote $PRIVATE_CONFIG_REPO
   ```

2. **SSH key issues**
   ```bash
   # Test SSH connection
   ssh -T git@github.com

   # Check SSH agent
   ssh-add -l
   ```

3. **Configuration validation errors**
   ```bash
   # Validate YAML syntax
   yamllint config/values/

   # Check Helm values
   helm template -f config/values/global.yaml chart-name
   ```

### Getting Help

- Check the main repository documentation
- Review example configurations
- Validate YAML syntax before committing
- Test changes in development environment first

## Migration Guide

### From Single Repository

If you're migrating from a single repository setup:

1. Identify sensitive files and configurations
2. Move them to the private repository
3. Update references in the main repository
4. Test the deployment with the new structure
5. Remove sensitive data from the main repository history (if needed)

### Backup and Recovery

- Regularly backup your private repository
- Store encrypted backups in multiple locations
- Document the recovery process
- Test restoration procedures periodically

## Integration with CI/CD

The private configuration system works seamlessly with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Sync Private Configuration
  run: ./scripts/sync-private-config.sh sync
  env:
    PRIVATE_CONFIG_REPO: ${{ secrets.PRIVATE_CONFIG_REPO }}

- name: Deploy Infrastructure
  run: ./scripts/deploy-homelab.sh bare-metal
```

Remember to store the private repository URL and access credentials as secrets in your CI/CD system.
