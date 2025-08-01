# Branch Update Analysis

This document tracks branch status, update requirements and security needs.

## Branch Status Summary

| Branch | Fast-forward Status | Security Critical |
|--------|-------------------|------------------|
| backup/pre-consolidation-main-20250731-095024 | Needs rebase | Yes |
| backup/pre-signing-fix-20250731-115504 | Needs rebase | Yes |
| backup/pre-signing-rebase-20250731-130405 | Needs rebase | Yes |
| feat/config-base | Can fast-forward | No |
| feat/config-core-loading | Can fast-forward | No |
| feat/config-domains-env | Can fast-forward | No |
| feat/config-env-handling | Can fast-forward | No |
| feat/config-environments | Can fast-forward | No |
| feat/config-network | Can fast-forward | No |
| feat/config-resources | Can fast-forward | No |
| feat/config-service-specific | Can fast-forward | No |
| feat/config-services | Can fast-forward | No |
| feat/docs-update | Can fast-forward | No |
| feat/infra-apps | Can fast-forward | No |
| feat/infra-base | Can fast-forward | No |
| feat/infra-security | Can fast-forward | No |
| feat/kubernetes-base | Can fast-forward | No |
| feat/monitoring-base | Can fast-forward | No |
| feat/orch-config | Can fast-forward | No |
| feat/orch-core | Can fast-forward | No |
| feat/orch-core-config | Can fast-forward | No |
| feat/orch-core-gpu | Can fast-forward | No |
| feat/orch-core-health | Can fast-forward | No |
| feat/orch-core-state | Can fast-forward | No |
| feat/orch-deploy-base | Can fast-forward | No |
| feat/orch-deploy-components | Can fast-forward | No |
| feat/orch-deploy-core | Can fast-forward | No |
| feat/orch-deploy-hooks | Can fast-forward | No |
| feat/orch-deploy-lifecycle | Can fast-forward | No |
| feat/orch-deploy-utils | Can fast-forward | No |
| feat/orch-deployment | Can fast-forward | No |
| feat/orch-gpu | Can fast-forward | No |
| feat/orch-health | Can fast-forward | No |
| feat/orch-portal | Can fast-forward | No |
| feat/orch-portal-base | Can fast-forward | No |
| feat/orch-portal-manager | Can fast-forward | No |
| feat/orch-security | Can fast-forward | No |
| feat/orch-unified | Can fast-forward | No |
| feat/orch-validation | Can fast-forward | No |
| feat/orchestrator-core | Can fast-forward | No |
| feat/orchestrator-deployment | Can fast-forward | No |
| feat/orchestrator-security | Can fast-forward | No |
| feat/security-keycloak | Can fast-forward | No |
| feature/ai-ml-gpu-infrastructure | Can fast-forward | No |
| feature/authentication-sso | Can fast-forward | No |
| feature/configuration-management | Can fast-forward | No |
| feature/core-orchestrator-deployment | Can fast-forward | No |
| feature/core-orchestrator-foundation | Can fast-forward | No |
| feature/documentation-infrastructure | Can fast-forward | No |
| feature/monitoring-dashboards | Can fast-forward | No |
| feature/portal-web-interface | Can fast-forward | No |
| feature/security-cicd-infrastructure | Can fast-forward | No |
| feature/testing-validation | Can fast-forward | No |

## Summary

- Total branches analyzed: 52
- Branches needing rebase: 3
- Security-critical branches: 3

### Branches Requiring Attention

Backup branches needing rebase (with security commits):

1. backup/pre-consolidation-main-20250731-095024
2. backup/pre-signing-fix-20250731-115504
3. backup/pre-signing-rebase-20250731-130405

All feature branches are up-to-date and can be fast-forwarded from main.
