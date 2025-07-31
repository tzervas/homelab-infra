# Homelab Orchestrator - Manage Commands

The `manage` command group provides backup, teardown, and recovery operations for your homelab infrastructure.

## Commands Overview

- `homelab manage backup` - Backup infrastructure components
- `homelab manage teardown` - Safely remove deployments
- `homelab manage recover` - Restore services from backup states

## Usage Examples

### Backup Operations

```bash
# Backup all deployed components
homelab manage backup

# Backup specific components
homelab manage backup --components metallb --components cert-manager

# Environment-specific backup
homelab --environment production manage backup
```

### Teardown Operations

```bash
# Teardown all components (in reverse dependency order)
homelab manage teardown

# Teardown specific components
homelab manage teardown --components test-app --components monitoring

# Teardown in staging environment
homelab --environment staging manage teardown
```

### Recovery Operations

```bash
# Recover all components from latest backup
homelab manage recover

# Recover specific components
homelab manage recover --components metallb --components cert-manager

# Recover from specific backup (will be added in future versions)
# homelab manage recover --backup-path /path/to/backup/20240101_120000
```

## Component Management

The system manages the following component types:

1. **Helm Releases**: Charts deployed via Helm
2. **Kubernetes Resources**: Native K8s objects (namespaces, deployments, etc.)
3. **Configuration Files**: Application-specific configurations

### Backup Storage

Backups are stored in `backups/` directory with timestamp-based folders:

```
backups/
├── 20240101_120000/
│   ├── metallb/
│   │   ├── metallb-values.yaml
│   │   ├── metallb-manifest.yaml
│   │   └── metallb-resources.yaml
│   └── cert-manager/
│       ├── cert-manager-values.yaml
│       └── cert-manager-resources.yaml
```

## Dependency Management

The system handles component dependencies:

- **Deployment Order**: Core services → Infrastructure → Applications
- **Teardown Order**: Applications → Infrastructure → Core services (reverse)
- **Recovery Order**: Same as deployment order

## Safety Features

1. **Validation**: Pre-checks before operations
2. **Rollback**: Failed operations can be recovered
3. **Logging**: Comprehensive operation logs
4. **Dry-run**: Test operations without changes (for deploy)

## Integration with Existing Tools

The manage commands leverage:

- `kubectl` for Kubernetes operations
- `helm` for Helm chart management
- `ansible` for configuration management (future)
- `terraform` for infrastructure provisioning (future)

## Error Handling

- Partial failures are reported with detailed status
- Failed components are tracked separately
- Recommendations provided for resolution
- Logs available for debugging

## Future Enhancements

- Backup compression and encryption
- Remote backup storage (S3, etc.)
- Automated backup scheduling
- Cross-cluster recovery
- Integration with GitOps workflows
