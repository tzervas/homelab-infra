# Ansible Directory

This directory contains Ansible configurations and playbooks for the homelab infrastructure project.

## Current Status

⚠️ **Note**: This project has migrated from Ansible-based deployment to a Helm/Helmfile approach. The Ansible directory is maintained for:
- Legacy compatibility
- Specific system-level configurations not handled by Kubernetes
- Infrastructure bootstrapping tasks

## Structure

```
ansible/
├── README.md                    # This documentation
├── ansible.cfg                 # Ansible configuration
├── inventory/                  # Inventory files
│   ├── hosts.yml              # Host definitions  
│   └── group_vars/            # Group variable definitions
└── playbooks/                 # Ansible playbooks (legacy)
```

## Migration Status

### ✅ Migrated to Helm/Helmfile
The following functionality has been successfully migrated to Helm-based deployment:

- **Service Deployments**: GitLab, Keycloak, monitoring stack
- **Infrastructure Components**: MetalLB, cert-manager, ingress controllers
- **Storage Solutions**: Longhorn distributed storage
- **Monitoring Stack**: Prometheus, Grafana, alerting

### 🔄 Current Ansible Usage
Ansible is now used for:

- **System Bootstrapping**: Initial server setup and configuration
- **SSH Key Management**: Automated SSH key distribution
- **System-level Configuration**: OS-level settings not managed by Kubernetes
- **Infrastructure Validation**: Pre-deployment system checks

## Integration with New Structure

### Configuration Integration
- Uses configuration from `../config/environments/` for environment-specific settings
- Integrates with `.env` and `.env.private.local` for host definitions
- Complements rather than conflicts with Helm deployments

### Script Integration
- Called by setup scripts in `../scripts/setup/`
- Used for initial system preparation before K3s deployment
- Supports the overall deployment workflow

## Usage

### System Bootstrap
```bash
# Bootstrap homelab server
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap-system.yml

# Configure SSH access
ansible-playbook -i inventory/hosts.yml playbooks/setup-ssh.yml
```

### Validation
```bash
# Validate system readiness
ansible-playbook -i inventory/hosts.yml playbooks/validate-system.yml

# Check connectivity
ansible all -i inventory/hosts.yml -m ping
```

## Future Direction

### Planned Evolution
- **Reduce Scope**: Focus on system-level tasks only
- **Complement Helm**: Work alongside, not replace, Helm deployments
- **Bootstrap Focus**: Primarily for initial system preparation
- **Validation Role**: System health and readiness checks

### Migration Benefits
The migration to Helm provides:
- **Declarative Management**: Better state management for applications
- **Rollback Capabilities**: Easy rollback and update procedures
- **Kubernetes Native**: Better integration with K3s cluster
- **Simplified Operations**: Reduced complexity in deployment management

## Related Documentation

- [Main README](../README.md) - Project overview and migration status
- [Helm Documentation](../helm/README.md) - Current deployment approach
- [Scripts Documentation](../scripts/README.md) - Automation scripts
- [Configuration Management](../config/README.md) - Configuration structure

## Legacy Playbooks

The following playbooks were part of the previous deployment approach and have been superseded:

- `deploy-gitlab.yml` → GitLab Helm chart
- `deploy-keycloak.yml` → Keycloak Helm chart  
- `deploy-cert-manager.yml` → cert-manager Helm chart
- `deploy-metallb.yml` → MetalLB Helm chart
- `deploy-monitoring.yml` → Prometheus/Grafana Helm charts
- `deploy-nginx-ingress.yml` → nginx-ingress Helm chart

These are maintained for reference but are no longer actively used in the deployment process.

## Contributing

When working with Ansible components:

1. **Focus on System Tasks**: Use Ansible for OS-level configuration only
2. **Avoid Application Deployment**: Use Helm for application deployments
3. **Complement Helm**: Ensure Ansible tasks support rather than conflict with Helm
4. **Update Documentation**: Keep this README updated with any changes
