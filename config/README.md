# Unified Configuration Management

This directory provides a unified configuration management strategy for the homelab infrastructure, consolidating settings across Helm, Kubernetes, Terraform, and Ansible. The structure has been optimized to eliminate duplication and provide clear integration points.

## Unified Structure

```
config/
├── README.md                    # This documentation
├── consolidated/               # **PRIMARY CONFIG** - Single source of truth
│   ├── README.md              # Consolidated configuration guide
│   ├── domains.yaml           # All domain and DNS configuration
│   ├── networking.yaml        # Network policies, MetalLB, ingress
│   ├── storage.yaml           # Storage classes, Longhorn, PVC defaults
│   ├── security.yaml          # Security contexts, RBAC, pod security
│   ├── resources.yaml         # CPU/memory limits, HPA configuration
│   ├── namespaces.yaml        # Namespace definitions and policies
│   ├── environments.yaml      # Environment-specific configurations
│   └── services.yaml          # Service discovery and health checks
├── environments/               # Environment-specific overrides
│   ├── development/           # Development environment settings
│   │   └── values.yaml        # Environment-specific overrides
│   ├── staging/              # Staging environment settings
│   │   └── values.yaml        # Environment-specific overrides
│   └── production/           # Production environment settings
│       └── values.yaml        # Environment-specific overrides
├── services/                   # Service-specific configurations
│   ├── gitlab/                # GitLab configuration templates
│   └── monitoring/            # Prometheus, Grafana, Loki settings
├── hooks/                      # Deployment validation hooks
│   └── deployment-validation-hooks.yaml
└── templates/                  # Reusable configuration templates
    └── deployment.yaml        # Standard deployment template
```

## Migration from Duplicated Structure

The configuration has been unified from previous duplicated structures:

- `config/base/` → Merged into `config/consolidated/`
- Multiple scattered domain configs → Single `domains.yaml`
- Duplicated networking configs → Unified `networking.yaml`

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

## Configuration Layers (Unified)

1. **Consolidated Base**: All defaults from `config/consolidated/` (single source of truth)
2. **Environment Overrides**: Values from `config/environments/{env}/`
3. **Service-Specific**: Service configs from `config/services/`
4. **Private Local**: Final overrides from `.env.private.local`
5. **Tool Integration**: Consistent consumption across Helm, Terraform, Ansible

## Unified Structure Benefits

- **Eliminated Duplication**: Removed `config/base/` duplication with `config/consolidated/`
- **Single Source of Truth**: All configuration consolidated in `config/consolidated/`
- **Consistent Integration**: Unified consumption patterns across all tools
- **Simplified Maintenance**: One location for all configuration updates
- **Clear Dependencies**: Explicit configuration layer hierarchy
- **Version Control Safety**: Sanitized templates with secret placeholders

## Security Notes

⚠️ **Important**: This directory should contain only non-sensitive configuration data.

- **Store sensitive data** in `.env.private.local` or encrypted secrets
- **Keep passwords and keys** out of version control
- **Use placeholder values** for sensitive configuration in tracked files

## Tool Integration

### Helm Integration

- Helm values files reference consolidated configurations via YAML anchors
- Environment-specific helmfiles consume unified values from `config/consolidated/`
- Shared templates reduce chart duplication

### Kubernetes Integration

- Kustomize overlays use consolidated configurations as references
- ConfigMaps generated from unified settings in `config/consolidated/`
- Consistent namespace and label management

### Terraform Integration

- Variable files consume consolidated YAML configurations via `yamldecode()`
- Module parameters standardized across environments using `config/consolidated/`
- Infrastructure settings aligned with application configs

### Ansible Integration

- Group variables loaded from `config/consolidated/` configs
- Inventory settings derived from unified networking configurations
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
