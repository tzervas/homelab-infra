# Legacy Migration Directory

This directory contains archived playbooks and configurations that were previously used for application deployments but have been migrated to Helm-based deployments.

## Migration Status

As of the homelab infrastructure refactoring, all application deployments have been migrated from Ansible to Helm charts for better Kubernetes-native management.

## Archived Components

### Application Deployment References
The following deployment references have been removed from the main Ansible structure:

- **GitLab Deployment**: Migrated to GitLab Helm chart in `helm/charts/gitlab/`
- **Keycloak Deployment**: Migrated to Keycloak Helm chart in `helm/charts/keycloak/`
- **cert-manager Deployment**: Migrated to cert-manager Helm chart in `helm/charts/cert-manager/`
- **MetalLB Deployment**: Migrated to MetalLB Helm chart in `helm/charts/metallb/`
- **Monitoring Stack**: Migrated to Prometheus/Grafana Helm charts in `helm/charts/monitoring/`
- **nginx-ingress Deployment**: Migrated to nginx-ingress Helm chart in `helm/charts/nginx-ingress/`

### Legacy site.yml References
The original `site.yml` contained include_tasks references for application deployments:
- `playbooks/deploy-gitlab.yml`
- `playbooks/deploy-keycloak.yml`
- `playbooks/deploy-cert-manager.yml`
- `playbooks/deploy-metallb.yml`
- `playbooks/deploy-monitoring.yml`
- `playbooks/deploy-nginx-ingress.yml`

These references have been removed as these playbooks were conceptual and never actually implemented.

## Migration Benefits

### Why Helm Instead of Ansible?
1. **Kubernetes Native**: Helm is purpose-built for Kubernetes application management
2. **Declarative State**: Better state management and rollback capabilities
3. **Version Control**: Helm chart versioning provides better change tracking
4. **Community Support**: Large ecosystem of maintained charts
5. **Templating**: Superior templating for Kubernetes resources
6. **Lifecycle Management**: Built-in upgrade, rollback, and uninstall capabilities

### What Ansible Still Handles
Ansible continues to be used for:
- Initial server provisioning and bootstrapping
- System-level configuration (network, storage, kernel parameters)
- OS package installation and updates
- User and SSH key management
- K3s cluster installation and initial setup
- System service configuration
- Infrastructure validation and health checks

## Historical Context

The original design included Ansible playbooks for application deployment to provide a single automation tool. However, as the project evolved and Kubernetes adoption matured, it became clear that Helm provides superior application lifecycle management within Kubernetes environments.

This migration represents a best-practice approach to infrastructure automation:
- **Ansible**: System-level provisioning and configuration
- **Terraform**: Infrastructure as Code for cloud/VM resources  
- **Helm**: Kubernetes application deployment and management

## Related Documentation

- [Main Ansible README](../README.md) - Current Ansible scope and usage
- [Helm Documentation](../../helm/README.md) - Application deployment with Helm
- [Migration Guide](../../docs/migration-guide.md) - Detailed migration process
- [Architecture Documentation](../../docs/architecture.md) - Overall system design

## Future Considerations

This legacy directory should be maintained for reference but not actively developed. Any new application deployments should use Helm charts, and system-level configurations should be added to the main Ansible playbooks.

If you need to reference the original application deployment intentions, the include_tasks references in the archived `site.yml` provide insight into the planned structure, though the actual playbooks were never fully implemented.
