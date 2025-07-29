<<<<<<< HEAD
# Unified Configuration Management

This directory provides a unified configuration management strategy for the homelab infrastructure, consolidating settings across Helm, Kubernetes, Terraform, and Ansible. The structure has been optimized to eliminate duplication and provide clear integration points.
=======
# Centralized Configuration Management

This directory provides a unified configuration management strategy for the homelab infrastructure, consolidating settings across Helm, Kubernetes, Terraform, and Ansible.
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)

## Unified Structure

```
config/
├── README.md                    # This documentation
<<<<<<< HEAD
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
=======
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
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
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

<<<<<<< HEAD
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
=======
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
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)

## Security Notes

⚠️ **Important**: This directory should contain only non-sensitive configuration data.

- **Store sensitive data** in `.env.private.local` or encrypted secrets
- **Keep passwords and keys** out of version control
- **Use placeholder values** for sensitive configuration in tracked files

## Tool Integration

### Helm Integration

<<<<<<< HEAD
- Helm values files reference consolidated configurations via YAML anchors
- Environment-specific helmfiles consume unified values from `config/consolidated/`
=======
- Helm values files reference base configurations via YAML anchors
- Environment-specific helmfiles consume consolidated values
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
- Shared templates reduce chart duplication

### Kubernetes Integration

<<<<<<< HEAD
- Kustomize overlays use consolidated configurations as references
- ConfigMaps generated from unified settings in `config/consolidated/`
=======
- Kustomize overlays use base configurations as references
- ConfigMaps generated from consolidated settings
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
- Consistent namespace and label management

### Terraform Integration

<<<<<<< HEAD
- Variable files consume consolidated YAML configurations via `yamldecode()`
- Module parameters standardized across environments using `config/consolidated/`
=======
- Variable files consume YAML configurations via `yamldecode()`
- Module parameters standardized across environments
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
- Infrastructure settings aligned with application configs

### Ansible Integration

<<<<<<< HEAD
- Group variables loaded from `config/consolidated/` configs
- Inventory settings derived from unified networking configurations
=======
- Group variables loaded from centralized configs
- Inventory settings derived from networking configurations
>>>>>>> 7c4b6fe (Step 3: Establish comprehensive user and admin bootstrap processes)
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
