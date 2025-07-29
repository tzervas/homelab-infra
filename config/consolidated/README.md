# Consolidated Configuration Management

This directory contains the centralized configuration strategy for the homelab infrastructure project. All configuration settings that were previously duplicated across Helm charts, Kubernetes manifests, Terraform modules, and Ansible playbooks are now consolidated here.

## Directory Structure

```
config/consolidated/
├── README.md              # This file
├── domains.yaml          # Domain and DNS configuration
├── networking.yaml       # Network policies, MetalLB, ingress
├── storage.yaml          # Storage classes, Longhorn, PVC defaults
├── security.yaml         # Security contexts, RBAC, pod security
├── resources.yaml        # CPU/memory limits, HPA configuration
├── namespaces.yaml       # Namespace definitions and policies
├── environments.yaml     # Environment-specific configurations
└── services.yaml         # Service discovery and health checks
```

## Configuration Files

### domains.yaml

- **Purpose**: Single source of truth for all domain-related settings
- **Consolidates**: Domain names, certificate management, DNS configuration
- **Replaces**: Hardcoded `homelab.local` references in 61+ files

### networking.yaml

- **Purpose**: Centralized network configuration
- **Consolidates**: MetalLB IP pools, ingress settings, network policies
- **Replaces**: Scattered networking configs across environments

### storage.yaml

- **Purpose**: Storage class and persistent volume configuration
- **Consolidates**: Longhorn settings, storage class definitions, backup policies
- **Replaces**: Duplicated storage configurations in 33+ files

### security.yaml

- **Purpose**: Security contexts and policy enforcement
- **Consolidates**: Pod security standards, RBAC, network policies, security contexts
- **Replaces**: Repeated security configurations across all charts

### resources.yaml

- **Purpose**: Resource allocation and scaling policies
- **Consolidates**: CPU/memory limits, resource tiers, autoscaling configuration
- **Replaces**: Duplicated resource definitions across services

### namespaces.yaml

- **Purpose**: Namespace definitions and policies
- **Consolidates**: Namespace creation, labels, resource quotas, network policies
- **Replaces**: Scattered namespace configurations

### environments.yaml

- **Purpose**: Environment-specific overrides and feature flags
- **Consolidates**: Development/staging/production differences
- **Replaces**: Multiple values files with similar content

### services.yaml

- **Purpose**: Service discovery and monitoring configuration
- **Consolidates**: Service ports, health checks, dependencies, monitoring
- **Replaces**: Scattered service configurations

## Usage Patterns

### Helm Charts

```yaml
# In helmfile.yaml or values files
values:
  - ../config/consolidated/domains.yaml
  - ../config/consolidated/networking.yaml
  - ../config/consolidated/storage.yaml
  - ../config/consolidated/security.yaml
  - ../config/consolidated/resources.yaml
  - ../config/consolidated/namespaces.yaml
  - ../config/consolidated/services.yaml
  - ../config/consolidated/environments.yaml
```

### Kubernetes Manifests

Reference consolidated values using tools like `yq` or `envsubst`:

```bash
# Example: Generate namespace from template
yq eval '.namespaces.core.monitoring' config/consolidated/namespaces.yaml > kubernetes/base/monitoring-namespace.yaml
```

### Terraform

```hcl
# Load consolidated configuration
locals {
  config = yamldecode(file("../config/consolidated/networking.yaml"))
  metallb_pool = local.config.networking.metallb.ip_pools.production.addresses
}
```

### Ansible

```yaml
# Load configuration in playbooks
- name: Load consolidated configuration
  include_vars:
    file: ../config/consolidated/domains.yaml
    name: domains_config
```

### Scripts

```bash
# Source configuration in deployment scripts
DOMAINS_CONFIG=$(yq eval '.domains.base.primary' config/consolidated/domains.yaml)
METALLB_IP=$(yq eval '.networking.metallb.ip_pools.production.addresses' config/consolidated/networking.yaml | cut -d'-' -f1)
```

## Benefits

1. **Single Source of Truth**: All configuration in one place
2. **Consistency**: No more conflicting settings across tools
3. **Environment Management**: Clean separation of dev/staging/prod
4. **Security**: Centralized security policies and contexts
5. **Maintainability**: Easy to update settings across entire infrastructure
6. **Version Control**: All configuration changes tracked in one location
7. **Documentation**: Self-documenting configuration structure

## Migration Strategy

1. **Phase 1**: Create consolidated configuration files (✅ Complete)
2. **Phase 2**: Update Helm charts to reference consolidated configs
3. **Phase 3**: Update Kubernetes manifests to use consolidated values
4. **Phase 4**: Update Terraform modules to reference consolidated configs
5. **Phase 5**: Update Ansible playbooks to use consolidated variables
6. **Phase 6**: Update deployment scripts to source consolidated configs
7. **Phase 7**: Remove duplicated configuration files

## Environment-Specific Overrides

Each environment can override specific values:

```yaml
# config/environments/development/overrides.yaml
networking:
  metallb:
    ip_pools:
      development:
        addresses: "192.168.25.200-192.168.25.205"  # Smaller pool for dev

resources:
  defaults:
    limits:
      memory: "512Mi"  # Reduced memory for development
```

## Validation

Use the provided validation scripts to ensure configuration consistency:

```bash
# Validate configuration syntax
scripts/validate-consolidated-config.sh

# Check for duplicate values across environments
scripts/check-config-duplicates.sh

# Generate configuration reports
scripts/generate-config-report.sh
```

## Security Considerations

- **Secrets**: No sensitive data in these files - use sealed secrets or external secret management
- **Environment Separation**: Clear boundaries between dev/staging/production
- **Access Control**: Restrict write access to production configurations
- **Validation**: Automated checks prevent invalid configurations

## Future Enhancements

- **GitOps Integration**: Automatic deployment when configurations change
- **Schema Validation**: JSON schema validation for configuration files
- **Configuration Drift Detection**: Monitor for manual changes
- **Template Generation**: Auto-generate manifests from consolidated configs
- **Multi-Cluster Support**: Extend for multiple Kubernetes clusters
