---
name: Bug Report
about: Create a report to help us improve the homelab infrastructure
title: '[BUG] Brief description of the issue'
labels: 'bug, needs-triage'
assignees: ''

---

## Bug Description

**Brief Summary**
A clear and concise description of what the bug is.

**Expected Behavior**
A clear and concise description of what you expected to happen.

**Actual Behavior**
A clear and concise description of what actually happened.

## Environment Information

**Infrastructure Component** (check all that apply):

- [ ] Kubernetes cluster
- [ ] Helm charts
- [ ] Terraform modules
- [ ] Ansible playbooks
- [ ] GitOps deployment
- [ ] Monitoring stack
- [ ] Security components
- [ ] Homelab orchestrator
- [ ] Other: ___________

**Environment** (check one):

- [ ] Development
- [ ] Staging
- [ ] Production
- [ ] Local testing

**Deployment Method**:

- [ ] Helm
- [ ] Raw Kubernetes manifests
- [ ] GitOps (ArgoCD/Flux)
- [ ] Terraform
- [ ] Manual deployment

## System Information

**Kubernetes Version**:
**Helm Version**:
**Operating System**:
**Architecture**: (amd64/arm64)

**Cluster Information**:

- Node count:
- Total CPU cores:
- Total memory:
- Storage type:

## Reproduction Steps

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Minimal Reproduction Case**
If possible, provide a minimal configuration or set of commands that reproduce the issue.

```yaml
# Include relevant configuration snippets
```

```bash
# Include relevant commands
```

## Error Information

**Error Messages**

```
Paste any error messages here
```

**Relevant Logs**

```
Paste relevant log entries here
```

**Screenshots**
If applicable, add screenshots to help explain your problem.

## Impact Assessment

**Severity** (check one):

- [ ] Critical - System down or major functionality broken
- [ ] High - Important functionality impacted
- [ ] Medium - Minor functionality affected
- [ ] Low - Cosmetic or documentation issue

**Components Affected**:

- [ ] Authentication/Authorization
- [ ] Networking
- [ ] Storage
- [ ] Monitoring
- [ ] Security
- [ ] Performance
- [ ] Documentation

**User Impact**:

- [ ] Blocks deployment
- [ ] Degrades performance
- [ ] Security concern
- [ ] Usability issue
- [ ] Documentation gap

## Additional Context

**Workaround** (if known):
Describe any temporary workaround you've found.

**Related Issues**:
Link to any related issues or discussions.

**Additional Information**:
Add any other context about the problem here.

## Debugging Information

**Debug Commands Run**:

```bash
# Include any debugging commands you've run
kubectl get pods -A
kubectl describe pod <pod-name>
helm list -A
```

**Configuration Files**:
If relevant, attach or link to configuration files (ensure no secrets are included).

## Proposed Solution

If you have ideas for how to fix the issue, please describe them here.

---

**Checklist** (for maintainers):

- [ ] Issue reproduced
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Tests added
- [ ] Documentation updated
