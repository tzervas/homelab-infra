# Helm Directory

This directory contains Helm charts, configurations, and environment-specific values for the homelab infrastructure deployment.

## Structure

```
helm/
├── README.md                    # This documentation
├── helmfile.yaml               # Main Helmfile configuration
├── repositories.yaml           # Helm repository definitions
├── charts/                     # Custom Helm charts
│   ├── core-infrastructure/   # MetalLB, cert-manager, ingress
│   ├── monitoring/            # Prometheus, Grafana, Loki
│   └── storage/               # Longhorn storage
└── environments/              # Environment-specific values
    ├── development/           # Development environment values
    ├── staging/              # Staging environment values
    └── production/           # Production environment values
```

## Key Components

### Helmfile Configuration (`helmfile.yaml`)
- Main orchestration file for all Helm releases
- Defines release dependencies and order
- Environment-specific configurations
- Integration with external value files

### Repository Definitions (`repositories.yaml`)
- Helm repository configurations
- Chart source definitions
- Authentication and access settings

### Custom Charts (`charts/`)
- **core-infrastructure**: Essential cluster components
- **monitoring**: Observability stack
- **storage**: Persistent storage solutions

### Environment Values (`environments/`)
- **development**: Minimal resources, single replicas
- **staging**: Production-like testing environment  
- **production**: Full resources, high availability

## Usage

### Deploy All Services
```bash
# Deploy to development environment
helmfile --environment development apply

# Deploy to production environment
helmfile --environment production apply
```

### Deploy Specific Services
```bash
# Deploy only monitoring stack
helmfile --environment production --selector name=prometheus apply

# Deploy core infrastructure
helmfile --environment production --selector category=infrastructure apply
```

### Environment Management
```bash
# Check differences
helmfile --environment production diff

# Dry run deployment
helmfile --environment production --debug apply --dry-run

# Sync specific release
helmfile --environment production sync --selector name=gitlab
```

## Integration with Project Structure

### Configuration Integration
- Works with `../config/` directory for environment-specific settings
- Loads values from `../config/environments/{env}/`
- References secrets from encrypted storage

### Script Integration
- Deployed via `../scripts/deployment/deploy.sh`
- Validated with `../scripts/validation/validate-k8s-manifests.sh`
- Monitored through `../scripts/testing/` framework

### Deployment Integration
- Complements `../deployments/` directory structure
- Provides declarative deployment definitions
- Supports GitOps workflows

## Best Practices

### Chart Development
- Follow Helm best practices for chart structure
- Include comprehensive documentation
- Implement proper templating and validation
- Support multiple environments

### Value Management
- Use environment-specific value files
- Avoid hardcoded configurations
- Implement secure secret management
- Support configuration overrides

### Release Management
- Use semantic versioning for charts
- Implement proper dependency management
- Test deployments in development first
- Maintain rollback capabilities

## Related Documentation

- [Main README](../README.md) - Project overview
- [Deployment Scripts](../scripts/README.md) - Automation scripts
- [Configuration Management](../config/README.md) - Configuration structure
- [Testing Framework](../testing/k3s-validation/README.md) - Validation testing

## Migration Notes

This Helm-based approach replaced individual Ansible playbooks to:
- Simplify deployment management
- Enable declarative state management
- Improve rollback and update capabilities
- Reduce operational complexity

The migration maintains all functionality while providing better maintainability and standardization.
