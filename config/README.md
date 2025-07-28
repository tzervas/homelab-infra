# Configuration Directory

This directory contains environment-specific configuration files for the homelab infrastructure deployment.

## Structure

```
config/
├── README.md                    # This documentation
├── environments/               # Environment-specific configurations
│   ├── development/           # Development environment settings
│   ├── staging/              # Staging environment settings
│   └── production/           # Production environment settings
├── k3s/                      # K3s cluster configuration (future)
├── monitoring/               # Monitoring stack configuration (future)
└── security/                 # Security policies and settings (future)
```

## Environment Configurations

### Development Environment (`environments/development/`)
- Minimal resource allocation
- Single replica deployments
- Self-signed certificates for internal testing
- Relaxed security policies for development ease

### Staging Environment (`environments/staging/`)
- Production-like configuration for testing
- Let's Encrypt staging certificates
- Resource allocation closer to production
- Full feature testing capabilities

### Production Environment (`environments/production/`)
- Full resource allocation
- High availability configurations
- Let's Encrypt production certificates
- Strict security policies and monitoring

## Usage

### Environment Variables
Configuration files in this directory work in conjunction with:
- `.env` - Public defaults and template values
- `.env.private.local` - Private overrides for local development
- `helm/environments/` - Helm-specific values files

### Deployment Integration
These configurations are automatically loaded by:
- `./scripts/deployment/deploy.sh` - Main deployment script
- `./scripts/deployment/deploy-with-privileges.sh` - Privileged deployment operations
- Helmfile configurations in `helm/environments/`

## Configuration Layers

1. **Base Configuration**: Default values from `.env`
2. **Environment Overrides**: Values from `config/environments/{env}/`
3. **Private Local**: Final overrides from `.env.private.local`
4. **Helm Values**: Application-specific overrides from `helm/environments/`

## Security Notes

⚠️ **Important**: This directory should contain only non-sensitive configuration data.

- **Store sensitive data** in `.env.private.local` or encrypted secrets
- **Keep passwords and keys** out of version control
- **Use placeholder values** for sensitive configuration in tracked files

## Future Expansion

Planned subdirectories for specialized configurations:

- `k3s/` - K3s cluster-specific settings (kubeconfig, cluster policies)
- `monitoring/` - Prometheus, Grafana, and logging configurations
- `security/` - Network policies, RBAC, and security standards

## Related Documentation

- [Configuration Management Guide](../docs/configuration/README.md)
- [Environment Variables Guide](../docs/configuration/environment-variables.md)  
- [Private Configuration Guide](../docs/configuration/private-configuration.md)
- [Deployment Guide](../docs/deployment/README.md)

## Quick Start

1. Copy environment template:
   ```bash
   cp -r examples/private-config-template/* config/
   ```

2. Customize for your environment:
   ```bash
   # Edit development settings
   nano config/environments/development/.env
   ```

3. Deploy with specific environment:
   ```bash
   ./scripts/deployment/deploy.sh -e development
   ```
