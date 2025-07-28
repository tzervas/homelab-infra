# Deployments Directory

This directory contains deployment manifests, scripts, and Infrastructure as Code (IaC) configurations for the homelab infrastructure.

## Structure

```
deployments/
├── README.md                     # This documentation
├── k3s/                         # K3s cluster deployment files
├── gitops/                      # GitOps-ready configuration management
│   ├── argocd/                  # ArgoCD configuration templates
│   ├── flux/                    # Flux configuration templates
│   ├── applications/            # Application manifests for GitOps
│   ├── overlays/                # Environment-specific overlays
│   ├── policies/                # Policy-as-code configurations
│   └── webhooks/                # Webhook integrations
├── security/                    # Security configurations and policies
├── applications/                # Application deployment manifests (future)
├── infrastructure/              # Infrastructure as Code (future)
└── helm-charts/                 # Custom Helm charts (future)
```

## Current Implementation

### K3s Deployment (`k3s/`)
Contains K3s cluster-specific deployment configurations:
- Cluster initialization scripts
- Node configuration files
- Network policy definitions
- Bootstrap configurations

### Planned Directories

#### Applications (`applications/`)
Will contain application-specific deployment manifests:
- GitLab deployment configurations
- Keycloak identity management
- Monitoring stack deployments
- Custom application manifests

#### Infrastructure (`infrastructure/`)
Will house Infrastructure as Code configurations:
- Terraform modules for infrastructure provisioning
- Ansible playbooks for system configuration
- Cloud-native infrastructure definitions

#### Helm Charts (`helm-charts/`)
Will contain custom Helm charts developed for this homelab:
- Custom application charts
- Infrastructure component charts
- Shared library charts
- Testing and development charts

## Deployment Strategy

### Current Approach
The project currently uses a hybrid deployment approach:

1. **Helm-based Deployment**: Primary deployment method using Helmfile
   - Location: `helm/` directory
   - Configuration: `helm/environments/` for environment-specific values
   - Orchestration: `helm/helmfile.yaml`

2. **Script-based Deployment**: Automated deployment scripts
   - Location: `scripts/deployment/`
   - Main scripts: `deploy.sh`, `deploy-with-privileges.sh`
   - Specialized scripts: `deploy-homelab.sh`, `deploy-gitlab-keycloak.sh`

### Future Migration
This `deployments/` directory is structured to support:
- Migration from script-based to declarative deployments
- Better separation of concerns
- Environment-specific deployment strategies
- GitOps-ready configurations

## Integration with Existing System

### Script Integration
Current deployment scripts automatically work with this structure:
```bash
# Main deployment script
./scripts/deployment/deploy.sh -e production

# Privileged deployment operations
./scripts/deployment/deploy-with-privileges.sh deploy all

# Specialized GitLab + Keycloak deployment
./scripts/deployment/deploy-gitlab-keycloak.sh vm-test
```

### Helm Integration
Helmfile configurations reference deployment artifacts:
```bash
# Deploy using Helmfile
helmfile --environment production apply

# Sync specific releases
helmfile --environment development sync
```

## Environment Management

### Development Deployments
- Minimal resource requirements
- Single-node configurations
- Development-specific networking
- Rapid iteration capabilities

### Staging Deployments
- Production-like configurations
- Multi-node testing capabilities
- Integration testing environments
- Performance validation setups

### Production Deployments
- High availability configurations
- Security-hardened deployments
- Monitoring and alerting enabled
- Backup and disaster recovery

## Security Considerations

### Manifest Security
- No hardcoded secrets in deployment files
- Use of Kubernetes secrets and ConfigMaps
- Sealed secrets for encrypted storage
- RBAC configurations for access control

### Network Security
- Network policies for traffic control
- TLS termination at ingress
- Service mesh considerations (future)
- Pod security policies/standards

## Automation and CI/CD

### Current Automation
- Script-based deployment automation
- Environment-specific configurations
- Validation and testing integration

### Future CI/CD Integration
- GitOps workflow implementation
- Automated deployment pipelines
- Progressive delivery strategies
- Rollback and recovery automation

## Monitoring and Observability

### Deployment Monitoring
- Health checks for deployed applications
- Resource utilization monitoring
- Performance metrics collection
- Log aggregation and analysis

### Deployment Validation
- Pre-deployment testing
- Post-deployment verification
- Integration testing automation
- Security scanning and compliance

## Usage Examples

### Deploy Specific Environment
```bash
# Development environment
./scripts/deployment/deploy.sh -e development

# Production environment with validation
./scripts/deployment/deploy-with-privileges.sh deploy all
./run-tests.sh --full
```

### Check Deployment Status
```bash
# Overall system status
./scripts/deployment/deploy-with-privileges.sh status

# Specific service status
kubectl get pods -n gitlab
kubectl get ingress -A
```

### Troubleshooting Deployments
```bash
# View deployment logs
kubectl logs -n kube-system -l app=k3s

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Validate configurations
./scripts/validation/validate-k8s-manifests.sh
```

## Related Documentation

- [Deployment Guide](../docs/deployment/README.md)
- [Configuration Management](../config/README.md)
- [Scripts Documentation](../scripts/README.md)
- [Testing Framework](../testing/k3s-validation/README.md)

## Contributing

When adding new deployment configurations:

1. **Follow directory structure**: Place files in appropriate subdirectories
2. **Document dependencies**: Clear documentation of prerequisites
3. **Environment separation**: Support for dev/staging/production
4. **Security review**: Ensure no sensitive data in manifests
5. **Testing**: Include validation and testing procedures

## Migration Notes

This structure supports the ongoing migration from:
- **From**: Script-heavy deployment approaches
- **To**: Declarative, Infrastructure as Code methodologies

The migration maintains backward compatibility while enabling future enhancements.
