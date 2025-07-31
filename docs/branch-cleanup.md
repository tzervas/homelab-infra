# Branch Consolidation Strategy

## Active Development Branches

### Configuration Manager Split

We've split the configuration manager into three focused branches:

1. `feat/config-core-loading`
   - Core configuration loading functionality
   - Basic YAML file loading and caching
   - Generic config retrieval with dot-notation support

2. `feat/config-env-handling`
   - Environment-specific configuration management
   - Environment context and overrides
   - Environment validation

3. `feat/config-service-specific`
   - Service-specific configuration handling:
     - Domain configuration with environment overrides
     - Network config with MetalLB pool handling
     - Security config with context-aware overrides

## Cleanup Plan

### Branches to Keep

- `main` - Main development branch
- `backup/pre-consolidation-main-20250731-095024` - Pre-consolidation backup
- `feat/config-core-loading` - Core config functionality
- `feat/config-env-handling` - Environment config handling
- `feat/config-service-specific` - Service-specific config

### Branches to Delete (Merged/Obsolete)

- All `feat/orch-*` branches (functionality moved to new config branches)
- All `feat/config-*` branches except the three new ones
- All `feature/*` branches (already consolidated)
- All other feature branches

### Process

1. Ensure all valuable documentation is preserved in backup branch
2. Create PRs for the three new config branches
3. Delete obsolete local and remote branches
4. Update main branch with consolidated changes
