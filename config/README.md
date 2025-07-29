# Centralized Configuration Management

This directory provides a unified configuration management strategy for the homelab infrastructure, consolidating settings across Helm, Kubernetes, Terraform, and Ansible.

## Structure

```
config/
├── README.md                    # This documentation
├── base/                       # Base configuration values
│   ├── global.yaml            # Global settings (domains, namespaces, etc.)
│   ├── networking.yaml         # Network configuration (IPs, ports, CIDRs)
│   ├── storage.yaml            # Storage classes and persistent volumes
│   ├── security.yaml           # Security contexts and policies
│   └── resources.yaml          # Default resource limits and requests
├── environments/               # Environment-specific overrides
│   ├── development/           # Development environment settings
│   │   ├── values.yaml        # Environment-specific overrides
│   │   └── secrets.yaml.template # Sanitized secrets template
│   ├── staging/              # Staging environment settings
│   │   ├── values.yaml        # Environment-specific overrides
│   │   └── secrets.yaml.template # Sanitized secrets template
│   └── production/           # Production environment settings
│       ├── values.yaml        # Environment-specific overrides
│       └── secrets.yaml.template # Sanitized secrets template
├── services/                   # Service-specific configurations
│   ├── gitlab/                # GitLab configuration templates
│   ├── keycloak/              # Keycloak realm and client configs
│   ├── monitoring/            # Prometheus, Grafana, Loki settings
│   └── ingress/               # Ingress and certificate configurations
└── templates/                  # Reusable configuration templates
    ├── deployment.yaml        # Standard deployment template
    ├── service.yaml           # Standard service template
    └── ingress.yaml           # Standard ingress template
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

1. **Base Configuration**: Default values from `config/base/`
2. **Environment Overrides**: Values from `config/environments/{env}/`
3. **Service-Specific**: Service configs from `config/services/`
4. **Private Local**: Final overrides from `.env.private.local`
5. **Tool Integration**: Tool-specific consumption (Helm, Terraform, Ansible)

## Consolidation Benefits

- **Single Source of Truth**: Eliminates duplicate configuration across tools
- **Environment Consistency**: Standardized settings across dev/staging/prod
- **Version Control Safety**: Sanitized templates with secret placeholders
- **Easier Maintenance**: Centralized updates propagate to all tools
- **Configuration Validation**: Structured YAML enables schema validation

## Security Notes

⚠️ **Important**: This directory should contain only non-sensitive configuration data.

- **Store sensitive data** in `.env.private.local` or encrypted secrets
- **Keep passwords and keys** out of version control
- **Use placeholder values** for sensitive configuration in tracked files

## Tool Integration

### Helm Integration

- Helm values files reference base configurations via YAML anchors
- Environment-specific helmfiles consume consolidated values
- Shared templates reduce chart duplication

### Kubernetes Integration

- Kustomize overlays use base configurations as references
- ConfigMaps generated from consolidated settings
- Consistent namespace and label management

### Terraform Integration

- Variable files consume YAML configurations via `yamldecode()`
- Module parameters standardized across environments
- Infrastructure settings aligned with application configs

### Ansible Integration

- Group variables loaded from centralized configs
- Inventory settings derived from networking configurations
- Playbook variables consistent with deployment settings

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
