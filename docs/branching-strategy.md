# Unified Branching Strategy

*Established: 2025-07-30*  
*Status: Active*

## Overview

This document defines the unified branching strategy for the homelab infrastructure project following the comprehensive branch consolidation completed in July 2025.

## Branch Structure

### Main Branches

- **`main`**: Production-ready code
  - Always deployable
  - Protected branch with required reviews
  - All changes must come via Pull Requests
  - Automatic deployments to production environment

- **`develop`**: Integration branch for ongoing development
  - Latest development changes
  - Continuous integration testing
  - Semi-automatic deployments to staging environment

### Feature Branches

Pattern: `feature/<descriptive-name>`

Examples:

- `feature/monitoring-dashboard-enhancement`
- `feature/k8s-security-policies`
- `feature/terraform-state-management`

**Lifecycle**:

1. Branch from `develop`
2. Implement feature with tests
3. Create PR to `develop`
4. Delete after merge

### Release Branches

Pattern: `release/<version>`

Examples:

- `release/v2.0.0`
- `release/v2.1.0-rc1`

**Purpose**:

- Prepare releases
- Final testing and bug fixes
- Version bump and changelog updates

**Lifecycle**:

1. Branch from `develop` when feature-complete
2. Bug fixes and documentation updates only
3. Merge to both `main` and `develop`
4. Tag release on `main`
5. Delete after successful deployment

### Hotfix Branches

Pattern: `hotfix/<issue-description>`

Examples:

- `hotfix/security-patch-cve-2025-001`
- `hotfix/gitlab-auth-failure`

**Purpose**:

- Critical production fixes
- Urgent security patches

**Lifecycle**:

1. Branch from `main`
2. Implement fix with tests
3. Merge to both `main` and `develop`
4. Deploy immediately to production
5. Delete after verification

### Cleanup Branches

Pattern: `cleanup/<scope>`

Examples:

- `cleanup/remove-legacy-configs`
- `cleanup/update-dependencies`

**Purpose**:

- Technical debt reduction
- Code organization improvements
- Non-functional enhancements

## Workflow Guidelines

### Feature Development

```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/new-awesome-feature

# Work on feature
git add .
git commit -m "feat: implement awesome feature"

# Keep updated with develop
git fetch origin
git rebase origin/develop

# Create PR when ready
gh pr create --base develop --title "feat: Add awesome feature"
```

### Release Process

```bash
# Create release branch
git checkout develop
git pull origin develop
git checkout -b release/v2.1.0

# Prepare release
./scripts/prepare-release.sh v2.1.0
git commit -m "chore: prepare release v2.1.0"

# Create release PR to main
gh pr create --base main --title "release: v2.1.0"

# After approval and merge
git tag v2.1.0
git push origin v2.1.0
```

### Hotfix Process

```bash
# Emergency fix
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Implement fix
git add .
git commit -m "fix: address critical security vulnerability"

# Create PR to main
gh pr create --base main --title "hotfix: Critical security fix"

# After merge, backport to develop
git checkout develop
git cherry-pick <hotfix-commit-hash>
```

## Commit Conventions

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code formatting (no logic changes)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Test additions or modifications
- **chore**: Build process or auxiliary tool changes
- **ci**: CI/CD pipeline changes
- **security**: Security-related changes

### Scopes

- **ansible**: Ansible playbooks and roles
- **helm**: Helm charts and values
- **k8s**: Kubernetes manifests
- **terraform**: Terraform modules and configurations
- **docs**: Documentation
- **scripts**: Automation scripts
- **config**: Configuration files
- **monitoring**: Monitoring and alerting
- **security**: Security policies and controls

### Examples

```bash
feat(helm): add monitoring dashboard for GitLab
fix(ansible): resolve SSH key deployment issue
docs(config): update configuration management guide
security(k8s): implement network policies for isolation
chore(deps): update Helm chart dependencies
```

## Branch Protection Rules

### Main Branch

- Require pull request reviews (2 approvers)
- Require status checks to pass
- Require branches to be up to date
- Require conversation resolution
- Restrict pushes to administrators only
- Allow force pushes: NO
- Allow deletions: NO

### Develop Branch

- Require pull request reviews (1 approver)
- Require status checks to pass
- Allow force pushes from administrators
- Allow deletions: NO

## Automated Processes

### CI/CD Integration

- **Feature branches**: Run tests and validation
- **Develop**: Deploy to staging environment
- **Main**: Deploy to production environment
- **Release branches**: Full integration testing
- **Hotfix**: Immediate deployment pipeline

### Dependency Management

- Automated dependency updates via Dependabot
- Security vulnerability scanning
- License compliance checking
- Automatic PR creation for updates

## Post-Consolidation Cleanup

Following the branch consolidation of July 2025, these branches were archived:

- `cleanup/remove-internal-docs` → Merged and archived
- `cleanup/remove-reports-summaries` → Merged and archived
- Various feature branches → Consolidated into unified structure

### Legacy Branch Handling

Archived branches are preserved in:

- Git bundle backups in `backups/branch-consolidation-*/`
- Documentation in `docs/consolidation-reports/`
- Historical reference maintained

## Maintenance Procedures

### Weekly Tasks

- Review open PRs and ensure timely reviews
- Update dependency security status
- Clean up merged feature branches
- Monitor branch protection rule compliance

### Monthly Tasks

- Review and update this branching strategy
- Analyze branch creation/merge patterns
- Update automation and CI/CD processes
- Conduct security audit of branch permissions

### Quarterly Tasks

- Major dependency updates
- Comprehensive security review
- Process improvement assessment
- Documentation updates

## Emergency Procedures

### Production Outage

1. Create hotfix branch immediately
2. Implement minimal viable fix
3. Fast-track review process (1 approver)
4. Deploy directly to production
5. Backport to develop post-incident

### Security Incident

1. Create security hotfix branch
2. Coordinate with security team
3. Implement patches across all affected versions
4. Emergency deployment authorization
5. Post-incident review and documentation

## Related Documentation

- [Configuration Management Guide](configuration/README.md)
- [Deployment Process](deployment/README.md)
- [Testing Framework](../testing/README.md)
- [Security Best Practices](security/best-practices.md)
- [Branch Consolidation Reports](consolidation-reports/)

---

**Last Updated**: 2025-07-30  
**Next Review**: 2025-10-30  
**Owner**: Infrastructure Team
