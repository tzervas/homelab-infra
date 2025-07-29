# Scripts Directory

This directory contains utility and automation scripts organized by function according to industry standards. All scripts follow the new standardized directory structure for improved maintainability and discoverability.

## Directory Structure

```
scripts/
├── setup/              # Initial setup and configuration scripts
├── maintenance/        # Maintenance and synchronization scripts  
├── backup/             # Backup and restore scripts (empty - ready for future scripts)
├── utilities/          # General utility scripts and tools
├── deployment/         # Deployment orchestration scripts
├── validation/         # Validation and testing scripts
└── testing/            # Testing framework and test modules
```

## Script Categories

### Setup Scripts (`setup/`)

Initial setup and configuration scripts for system components:

- `setup-k3s-access.sh` - Configure port forwarding and kubectl access for K3s
- `setup-vm-auth.sh` - Set up SSH authentication for homelab test VMs
- `setup_ssh.sh` - SSH configuration and key management

### Maintenance Scripts (`maintenance/`)

Scripts for ongoing maintenance and synchronization:

- `sync-private-config.sh` - Sync private configuration repository
- `sync_private_docs.sh` - Sync private documentation across git branches
- `sync_untracked.sh` - Sync untracked files across branches

### Backup Scripts (`backup/`)

Backup and restore functionality:

- *(Directory ready for backup/restore scripts)*

### Utility Scripts (`utilities/`)

General-purpose utilities and development tools:

- `analyze-and-test-develop.sh` - Development branch analysis and testing
- `check-unsigned-commits.sh` - Verify commit signatures
- `claude-task.sh` - AI-assisted task automation
- `code-quality.sh` - Comprehensive code quality checks and fixes
- `fix-vm-network.sh` - Fix VM network connectivity and SSH access

### Deployment Scripts (`deployment/`)

Deployment orchestration and automation:

- `deploy-homelab.sh` - Comprehensive GitLab + Keycloak homelab deployment
- `deploy-ai-ml.sh` - AI/ML workload deployment
- `deploy-and-adjust-network.sh` - Network-aware deployment with adjustments
- `deploy-and-validate.sh` - Deploy with integrated validation
- `deploy-gitlab-keycloak.sh` - GitLab and Keycloak specific deployment
- `deploy-k3s-automated.sh` - Automated K3s cluster deployment
- `deploy.sh` - General deployment orchestrator
- `deploy-with-privileges.sh` - Privileged deployment operations
- `setup-secure-deployment.sh` - Security-focused deployment setup

### Validation Scripts (`validation/`)

Testing, validation, and readiness checks:

- `validate-k3s-cluster.sh` - K3s cluster health validation (legacy)
- `validate-k3s-simple.sh` - Simple K3s validation checks
- `validate-k8s-manifests.sh` - Kubernetes manifest validation
- `validate-deployment-comprehensive.sh` - Comprehensive deployment validation
- `validate-deployment-local.sh` - Local deployment validation
- `validate_deployment.py` - Python-based deployment validation
- `test-deployment-dry-run.sh` - Dry-run deployment testing
- `test-deployment-readiness.sh` - Deployment readiness checks
- `test-ssh-readiness.sh` - SSH connectivity testing

### Testing Framework (`testing/`)

Comprehensive testing framework with modules for:

- Core infrastructure testing
- Integration testing
- Network security validation
- Permission verification
- Service health checks
- Issue tracking and reporting

See `testing/README.md` for detailed information about the testing framework.

## Usage Guidelines

### Script Execution

All scripts should be executed from the project root directory:

```bash
# From project root
./scripts/setup/setup-k3s-access.sh
./scripts/deployment/deploy-homelab.sh vm-test
./scripts/validation/validate-k3s-cluster.sh
```

### Environment Variables

Many scripts support configuration through environment variables:

- Load from `.env` file in project root
- Override with `.env.private.local` for local customization
- Use script-specific environment variables where documented

### Error Handling

Scripts follow consistent error handling patterns:

- Exit codes: 0 (success), non-zero (failure)
- Colored output for status messages
- Comprehensive logging where appropriate

### Dependencies

Scripts may require:

- SSH access to homelab infrastructure
- kubectl/k3s for Kubernetes operations
- Ansible for automation playbooks
- Python 3.12+ with UV for Python scripts
- Various CLI tools (documented in individual scripts)

## Migration Notes

This reorganization was completed as part of PROJECT_STRUCTURE.md implementation:

- ✅ All existing functionality preserved
- ✅ Path references updated where necessary  
- ✅ Testing framework reorganized and enhanced
- ✅ Legacy scripts maintain backward compatibility
- ✅ New directory structure fully implemented
- ✅ Documentation updated to reflect new paths

## Development Guidelines

When adding new scripts:

1. Place in appropriate subdirectory based on function
2. Follow existing naming conventions
3. Include proper error handling and logging
4. Document dependencies and usage
5. Update this README when adding new categories

## Script Integration with New Structure

### Integration Points

Scripts in this directory integrate seamlessly with the new project structure:

- **Configuration**: Uses configs from `../config/` directory
- **Deployments**: Works with manifests in `../deployments/` directory  
- **Documentation**: References docs in `../docs/` directory
- **Tools**: Complements utilities in `../tools/` directory
- **Testing**: Integrates with `../testing/` framework

### Environment Integration

```bash
# Scripts automatically detect and use:
# - .env (project root) - Base configuration
# - .env.private.local (project root) - Private overrides
# - config/environments/{env}/ - Environment-specific settings
# - helm/environments/{env}/ - Helm values
```

### Path Resolution

All scripts use relative paths from project root:

```bash
# Always run scripts from project root
cd /path/to/homelab-infra
./scripts/deployment/deploy.sh
./scripts/validation/validate-deployment.sh
```

## Quality Standards

### Script Standards

- ✅ Consistent error handling and logging
- ✅ Environment variable support
- ✅ Comprehensive documentation headers
- ✅ Exit codes: 0 (success), non-zero (failure)
- ✅ Colored output for status messages

### Security Standards

- ✅ No hardcoded credentials or secrets
- ✅ Proper input validation and sanitization
- ✅ Secure temporary file handling
- ✅ Appropriate file permissions

## See Also

- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Overall project organization
- [testing/README.md](testing/README.md) - Testing framework documentation
- [Configuration Guide](../config/README.md) - Configuration management
- [Deployment Guide](../deployments/README.md) - Deployment structure
- [Tools Documentation](../tools/README.md) - Development tools
- Individual script headers for specific usage instructions
