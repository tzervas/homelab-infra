claude --dangerously-skip-permissions <<'EOF'
Please perform a comprehensive project analysis and create a detailed alignment strategy and refactoring plan. Based on the provided repository content:

1. Project Analysis:
   - Analyze the current architecture and infrastructure setup
   - Identify key components and their relationships
   - Review the deployment workflow and GitOps implementation
   - Evaluate the security measures and compliance status

2. Alignment Strategy:
   - Propose strategies to align all components with best practices
   - Suggest improvements for the GitOps workflow
   - Recommend security enhancements
   - Outline monitoring and observability improvements

3. Refactoring Plan:
   - Create a detailed, phased refactoring roadmap
   - Prioritize changes based on impact and complexity
   - Include specific code and configuration changes needed
   - Provide rollback procedures for each phase

Please provide specific recommendations and code examples where applicable. Consider both immediate improvements and long-term architectural goals.

Repository content:\n\nProject Structure:
.
├── analyze_branches.sh
├── ansible
│   ├── ansible.cfg
│   ├── AUTHENTICATION_SETUP.md
│   ├── deploy-k3s.log
│   ├── group_vars
│   │   └── all
│   ├── inventory
│   │   ├── hosts.yml
│   │   ├── hosts.yml.bak
│   │   └── vm-test-inventory.yml
│   ├── legacy-migration
│   │   ├── README.md
│   │   ├── REFACTORING_SUMMARY.md
│   │   └── site.yml.archived
│   ├── playbooks
│   │   ├── bootstrap-system.yml
│   │   ├── cleanup-system.yml
│   │   ├── configure-networking.yml
│   │   ├── configure-storage.yml
│   │   ├── configure-users.yml
│   │   ├── create-vm.yml
│   │   ├── deploy-k3s-fixed.yml
│   │   ├── deploy-k3s.yml
│   │   ├── install-longhorn-requirements.yml
│   │   ├── install-missing-tools.yml
│   │   ├── install-tools.yml
│   │   ├── setup-deployment-user.yml
│   │   ├── test-authentication.yml
│   │   └── validate-deployment-setup.yml
│   ├── README.md
│   ├── roles
│   │   └── deployment-user
│   ├── setup-passwordless-sudo.sh
│   └── site.yml
├── ATTRIBUTIONS.md
├── backups
│   ├── branch-consolidation-20250730_141255
│   ├── branch-consolidation-20250730_141256
│   ├── branch-consolidation-20250730_141303
│   ├── branch-consolidation-20250730_141310
│   │   └── refs-backup
│   ├── branch-consolidation-optimized
│   │   ├── checksum.sha256
│   │   ├── manifest.txt
│   │   └── working-directory-snapshot.tar.gz
│   └── branch-consolidation-optimized-45mb
│       ├── checksum.sha256
│       ├── large_files_excluded.txt
│       ├── manifest.txt
│       └── working-directory-snapshot.tar.gz
├── bandit-report.json
├── branch_mapping.yaml
├── CHANGELOG.md
├── comprehensive_validation.py
├── config
│   ├── consolidated
│   │   ├── domains.yaml
│   │   ├── environments.yaml
│   │   ├── namespaces.yaml
│   │   ├── networking.yaml
│   │   ├── README.md
│   │   ├── resources.yaml
│   │   ├── security.yaml
│   │   ├── services.yaml
│   │   └── storage.yaml
│   ├── environments
│   │   ├── development
│   │   ├── production
│   │   └── staging
│   ├── hooks
│   │   └── deployment-validation-hooks.yaml
│   ├── README.md
│   ├── services
│   │   ├── gitlab
│   │   └── monitoring
│   └── templates
│       └── deployment.yaml
├── deployment-plan.yaml
├── deployments
│   ├── gitops
│   │   ├── applications
│   │   ├── argocd
│   │   ├── flux
│   │   ├── overlays
│   │   ├── policies
│   │   ├── README.md
│   │   └── webhooks
│   ├── README.md
│   └── security
│       ├── mtls-configuration.yaml
│       ├── network-policy-templates.yaml
│       ├── README.md
│       ├── sealed-secrets-patterns.yaml
│       ├── secret-rotation-mechanisms.yaml
│       └── tls-certificate-management.yaml
├── docs
│   ├── architecture
│   │   └── terraform-integration.md
│   ├── architecture.md
│   ├── backup-solutions-guide.md
│   ├── branching-strategy.md
│   ├── BRANCH_MANAGEMENT.md
│   ├── branch_mapping.md
│   ├── branch_status.md
│   ├── branch_status_report.md
│   ├── comprehensive-user-guide.md
│   ├── configuration
│   │   └── README.md
│   ├── dependency_relationships.md
│   ├── deployment
│   │   ├── deployment-plan.md
│   │   ├── gitops-guide.md
│   │   ├── README.md
│   │   └── unified-deployment.md
│   ├── deployment-checklist.md
│   ├── environment-variables.md
│   ├── homelab-portal-enhancement-plan.md
│   ├── index.md
│   ├── interfaces-and-processes.md
│   ├── k3s-deployment-report.md
│   ├── k3s-setup.md
│   ├── manage-commands.md
│   ├── modernization
│   │   ├── assessment.md
│   │   └── migration-guide.md
│   ├── network.md
│   ├── network-validation-step10-results.md
│   ├── operations
│   │   ├── BACKUP_DOCUMENTATION.md
│   │   └── runbooks
│   ├── private-configuration-guide.md
│   ├── private_repo_info.md
│   ├── project-management
│   │   ├── BOOTSTRAP_ISSUES_TRACKER.md
│   │   └── CLAUDE_TASK_CONTEXT.md
│   ├── README.md
│   ├── REPOSITORY-ARCHITECTURE.md
│   ├── rootless-deployment-guide.md
│   ├── rootless-deployment-plan.md
│   ├── security
│   │   ├── bandit-configuration.md
│   │   ├── best-practices.md
│   │   └── tls-mtls-guide.md
│   ├── security_patch_status.md
│   ├── setup
│   │   └── quick-start.md
│   ├── specifications
│   │   └── project_specification.yaml
│   ├── testing-guide.md
│   ├── troubleshooting
│   │   └── migration-issues.md
│   └── validation-testing-plan.md
├── examples
│   ├── basic-setup
│   │   └── config
│   └── private-config-template
│       ├── environments
│       ├── secrets
│       └── values
├── final_branch_status.txt
├── helm
│   ├── charts
│   │   ├── core-infrastructure
│   │   ├── monitoring
│   │   ├── security-baseline
│   │   └── storage
│   ├── environments
│   │   ├── secrets-dev-plain.yaml
│   │   ├── secrets-dev.yaml
│   │   ├── secrets-dev.yaml.template
│   │   ├── secrets-prod.yaml
│   │   ├── secrets-prod.yaml.template
│   │   ├── secrets-staging.yaml
│   │   ├── values-default.yaml
│   │   ├── values-development.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-prod.yaml
│   │   ├── values-secrets-template.yaml
│   │   └── values-staging.yaml
│   ├── helmfile.lock
│   ├── helmfile.yaml
│   ├── README-ENHANCED.md
│   ├── README.md
│   ├── repositories.yaml
│   ├── SECRETS-AND-CONFIGURATION-VALIDATION.md
│   ├── SECURITY-COMPLIANCE-SUMMARY.md
│   ├── SECURITY-PRIVILEGE-REVIEW.md
│   ├── validate-charts.sh
│   └── validate-templates.sh
├── homelab_orchestrator
│   ├── cli.py
│   ├── config
│   │   └── consolidated
│   ├── core
│   │   ├── config_manager.py
│   │   ├── deployment.py
│   │   ├── gpu_manager.py
│   │   ├── health.py
│   │   ├── orchestrator.py
│   │   ├── security.py
│   │   └── unified_deployment.py
│   ├── __init__.py
│   ├── __main__.py
│   ├── portal
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── portal_manager.py
│   ├── README.md
│   ├── remote
│   │   ├── cluster_manager.py
│   │   └── __init__.py
│   ├── security
│   │   ├── __init__.py
│   │   └── privilege_manager.py
│   ├── tests
│   │   └── test_cli.py
│   ├── validation
│   │   ├── __init__.py
│   │   └── validator.py
│   └── webhooks
│       ├── __init__.py
│       └── manager.py
├── kubernetes
│   ├── base
│   │   ├── cluster-issuers.yaml
│   │   ├── gitlab-deployment.yaml
│   │   ├── gitlab-runner-arc.yaml
│   │   ├── grafana-deployment.yaml
│   │   ├── ingress-config.yaml
│   │   ├── jupyterlab-deployment.yaml
│   │   ├── keycloak-deployment.yaml
│   │   ├── keycloak-realm-enhanced.yaml
│   │   ├── landing-page.yaml
│   │   ├── longhorn.yaml
│   │   ├── metallb-config.yaml
│   │   ├── namespaces.yaml
│   │   ├── network-policies.yaml
│   │   ├── oauth2-proxy.yaml
│   │   ├── ollama-webui-deployment.yaml
│   │   ├── pod-security-standards.yaml
│   │   ├── prometheus-deployment.yaml
│   │   ├── rbac.yaml
│   │   ├── resource-allocations.yaml
│   │   ├── resource-optimization.yaml
│   │   └── security-contexts.yaml
│   ├── enhanced-portal.yaml
│   ├── homelab-portal
│   │   └── backend
│   ├── keycloak
│   │   ├── apply-keycloak-integration.sh
│   │   ├── gitlab-keycloak.yaml
│   │   ├── grafana-keycloak.yaml
│   │   ├── jupyterhub-keycloak.yaml
│   │   ├── keycloak-clients-config.yaml
│   │   ├── oauth2-proxy-multi-client.yaml
│   │   └── ollama-webui-keycloak.yaml
│   ├── monitoring
│   │   ├── alerting
│   │   ├── prometheus
│   │   └── README.md
│   ├── portal-ingress-noauth.yaml
│   └── README.md
├── LICENSE
├── LICENSES
│   ├── AGPL-3.0-REFERENCE.md
│   ├── Apache-2.0.txt
│   └── MIT.txt
├── logs
│   ├── deployment-validation-20250729_141541.log
│   ├── deployment-validation-20250729_143304.log
│   ├── homelab-teardown-20250729_141225.log
│   ├── k3s-deployment-20250727_222608.log
│   ├── k3s-deployment-progress-20250727_222608.log
│   ├── k3s-deployment-report-20250727_222608.txt
│   ├── k3s-validation-20250727_234202.log
│   ├── k3s-validation-20250727_234216.log
│   └── monitoring-validation-20250728-163608.log
├── Makefile
├── merge_report.md
├── merge_resolution_artifacts.tar.gz
├── metallb-config.yaml
├── migrate_to_unified_system.py
├── migration.log
├── monitoring
│   ├── README.md
│   └── terraform-state
│       └── terraform-state-monitor.py
├── mypy.ini
├── node_modules
├── NOTICE
├── PROJECT_STRUCTURE.md
├── pyproject.toml
├── README.md
├── reports
│   ├── README.md
│   └── validation-results
│       ├── comprehensive-validation-report-20250728.md
│       ├── homelab_issues_report_20250728_203559.md
│       ├── homelab_test_report_20250728_203559.json
│       ├── issues-and-recommendations-20250728.md
│       ├── network-validation-results
│       ├── REPORT-INDEX.md
│       ├── SECRETS-AND-CONFIGURATION-VALIDATION.md
│       ├── SECURITY-COMPLIANCE-SUMMARY.md
│       ├── SECURITY-PRIVILEGE-REVIEW.md
│       └── test-execution-summary-20250728.md
├── run_analysis.sh
├── scripts
│   ├── analyze_branches.py
│   ├── analyze_project.sh
│   ├── backup
│   │   └── create-optimized-backup.sh
│   ├── backup_branches.sh
│   ├── common
│   │   └── environment.sh
│   ├── consolidate_branches.sh
│   ├── generate-domains-config.py
│   ├── index_docs.py
│   ├── __init__.py
│   ├── logs
│   │   └── k3s-validation-20250728_163626.log
│   ├── map_features.py
│   ├── network-validation-results
│   │   ├── dns_test_20250728_164248.log
│   │   ├── ingress_test_20250728_164248.log
│   │   ├── metallb_test_20250728_163947.log
│   │   ├── metallb_test_20250728_164248.log
│   │   ├── network_policies_test_20250728_164248.log
│   │   ├── network_validation_report_20250728_164248.md
│   │   └── service_mesh_test_20250728_164248.log
│   ├── README.md
│   ├── security
│   │   ├── certificate-expiry-monitoring.py
│   │   ├── security-policy-compliance-checks.py
│   │   └── tls-configuration-validation.py
│   ├── testing
│   │   ├── common.py
│   │   ├── config.py
│   │   ├── config_validator.py
│   │   ├── deployment_smoke_tests.py
│   │   ├── deployment_validation_hooks.py
│   │   ├── infrastructure_health.py
│   │   ├── __init__.py
│   │   ├── integrated_test_orchestrator.py
│   │   ├── integration_tester.py
│   │   ├── issue_tracker.py
│   │   ├── network_security.py
│   │   ├── permission_verifier.py
│   │   ├── production_health_check.py
│   │   ├── __pycache__
│   │   ├── README.md
│   │   ├── rootless_compatibility.py
│   │   ├── service_checker.py
│   │   ├── terraform_validator.py
│   │   ├── test_reporter.py
│   │   ├── tls_validator.py
│   │   ├── validate_deployment.py
│   │   └── validate-enhanced-monitoring.sh
│   ├── test_results
│   │   ├── homelab_issues_report_20250728_203559.md
│   │   ├── homelab_test_report_20250728_203559.json
│   │   └── homelab_test_report_20250728_203559.md
│   ├── update-branches.sh
│   ├── update_protection.sh
│   ├── validate_structure.sh
│   └── validation
│       ├── validate_deployment.py
│       └── validate_yaml.py
├── simple_migration_test.py
├── templates
│   └── helm-chart
│       ├── Chart.yaml
│       └── values.yaml
├── terraform
│   ├── environments
│   │   └── development
│   ├── main.tf
│   ├── modules
│   │   ├── k3s-cluster
│   │   ├── networking
│   │   ├── security
│   │   └── storage
│   ├── providers
│   │   ├── homelab.tf
│   │   └── README.md
│   └── README.md
├── test_basic_functionality.py
├── testing
│   ├── authentication-integration-test.sh
│   ├── helm
│   │   └── helm-unittest
│   ├── integration
│   │   ├── test_cross_component_integration.py
│   │   └── test_unified_deployment.py
│   ├── k3s-validation
│   │   ├── CLAUDE.md
│   │   ├── config
│   │   ├── debug-info.md
│   │   ├── DEPLOYMENT_SUMMARY.md
│   │   ├── docs
│   │   ├── framework-status.md
│   │   ├── lib
│   │   ├── modules
│   │   ├── orchestrator.sh
│   │   ├── README.md
│   │   ├── reports
│   │   ├── STRICT_MODE_GUIDE.md
│   │   └── test-deployment.sh
│   ├── performance
│   │   └── benchmarks.py
│   ├── README.md
│   ├── regression_tests.py
│   ├── run-enhanced-tests.sh
│   ├── security
│   │   ├── certificate_validator.py
│   │   └── __init__.py
│   └── terraform
│       └── terratest
├── test_results
│   ├── branch_test_mapping.md
│   ├── homelab_issues_report_20250729_171022.md
│   ├── homelab_test_report_20250729_171022.json
│   ├── homelab_test_report_20250729_171022.md
│   ├── hooks
│   │   ├── phase_post-deployment_summary_20250729_045041.json
│   │   └── pre-deployment-validation_post-deployment_20250729_045041.json
│   ├── integrated_test_report_20250729_154124.json
│   ├── integrated_test_report_20250729_154124.md
│   ├── integrated_test_report_20250729_154606.json
│   ├── integrated_test_report_20250729_154606.md
│   ├── integrated_test_report_20250731_195313.json
│   └── integrated_test_report_20250731_195313.md
├── tmp
│   ├── rootless-deployment-prompt.md
│   └── rootless-deployment-summary.md
├── tools
│   └── README.md
├── untracked_backup
│   ├── develop
│   │   ├── docs
│   │   └── scripts
│   ├── feature
│   │   └── initial-setup
│   └── main
│       ├── docs
│       └── scripts
├── update_branches.sh
└── uv.lock

137 directories, 313 files

---

Project Specification:
---
# Project Specification for Homelab Infrastructure
# Generated: 2024-01-17

metadata:
  project: homelab-infrastructure
  maintainer: \"DevOps Team <tz-dev@vectorweight.com>\"
  status: active_development

minimum_viable_product:
  core_infrastructure:
    kubernetes:
      - Basic K3s cluster setup
      - Single-node deployment
      - Basic RBAC configuration
      - Essential namespaces

    networking:
      - Basic MetalLB configuration
      - Simple ingress controller
      - Core network policies
      - Basic DNS setup

    storage:
      - Local storage provisioner
      - Basic volume management
      - Simple backup capability

    security:
      - Basic TLS certificates
      - Simple secret management
      - Minimal RBAC policies
      - Basic network isolation

  required_features:
    - Load balancer for service exposure
    - Basic ingress routing
    - Simple monitoring setup
    - Essential security controls
    - Basic GitOps deployment

  success_criteria:
    - Functional K3s cluster
    - Working service exposure
    - Basic monitoring capability
    - Simple deployment workflow
    - Essential security controls

proof_of_concept:
  extended_features:
    infrastructure:
      - Multi-node K3s cluster
      - Advanced RBAC configuration
      - Custom resource definitions
      - Enhanced storage solutions

    networking:
      - Advanced MetalLB setup
      - Multiple ingress controllers
      - Complex network policies
      - Service mesh basics

    security:
      - Advanced certificate management
      - Enhanced secret handling
      - Security policy enforcement
      - Comprehensive RBAC

    monitoring:
      - Full metrics collection
      - Log aggregation
      - Basic alerting
      - Simple dashboards

  validation_criteria:
    - Multi-node cluster stability
    - Advanced networking functionality
    - Enhanced security controls
    - Basic monitoring and alerting
    - Automated deployment capabilities

production:
  full_features:
    infrastructure:
      - High availability K3s
      - Full resource management
      - Complete storage solution
      - Backup and disaster recovery

    networking:
      - Production MetalLB setup
      - HA ingress controllers
      - Full network policy suite
      - Service mesh with mTLS

    security:
      - Production certificate management
      - Vault integration
      - Policy as code
      - Complete security suite

    monitoring:
      - Full observability stack
      - Advanced alerting
      - Custom dashboards
      - Performance monitoring

    automation:
      - Complete GitOps workflow
      - CI/CD integration
      - Automated testing
      - Drift detection

  security_requirements:
    infrastructure:
      - Node security hardening
      - Container security
      - Network segmentation
      - Resource isolation

    access_control:
      - Fine-grained RBAC
      - Audit logging
      - SSO integration
      - Secret rotation

    compliance:
      - Security policies
      - Compliance monitoring
      - Regular audits
      - Policy enforcement

  performance_requirements:
    - Load testing capability
    - Performance monitoring
    - Resource optimization
    - Scalability testing

  reliability_requirements:
    - High availability setup
    - Automated failover
    - Backup solutions
    - Disaster recovery

deployment_stages:
  stage_1_mvp:
    duration: \"2-3 weeks\"
    objectives:
      - Basic cluster setup
      - Essential services
      - Simple deployment flow
      - Basic monitoring
    validation:
      - Core functionality tests
      - Basic security checks
      - Simple performance tests

  stage_2_poc:
    duration: \"4-6 weeks\"
    objectives:
      - Extended features
      - Enhanced security
      - Advanced networking
      - Improved monitoring
    validation:
      - Feature validation
      - Security assessment
      - Performance testing
      - Integration testing

  stage_3_production:
    duration: \"8-12 weeks\"
    objectives:
      - Full feature set
      - Production security
      - Complete automation
      - Comprehensive monitoring
    validation:
      - Production readiness
      - Security compliance
      - Performance verification
      - Disaster recovery testing

documentation_requirements:
  mvp:
    - Basic setup guide
    - Essential configurations
    - Simple troubleshooting
    - Core feature documentation

  poc:
    - Extended setup guide
    - Feature documentation
    - Security guidelines
    - Testing procedures
    - Troubleshooting guide

  production:
    - Complete documentation
    - Architecture details
    - Security guidelines
    - Operational procedures
    - Disaster recovery plans
    - Maintenance guides

branch_consolidation:
  strategy:
    # Group related features for efficient consolidation
    feature_groups:
      authentication:
        branches:
          - feature/authentication-sso
          - feat/security-keycloak
        priority: high
        dependencies: []

      configuration:
        branches:
          - feature/configuration-management
          - feat/config-base
          - feat/config-environments
        priority: high
        dependencies: []

      orchestration:
        branches:
          - feature/core-orchestrator-foundation
          - feat/orch-core
          - feat/orch-deployment
        priority: medium
        dependencies:
          - configuration

      monitoring:
        branches:
          - feature/monitoring-dashboards
          - feat/monitoring-base
        priority: medium
        dependencies:
          - configuration
          - orchestration

    merge_sequence:
      phase_1:
        name: \"Security Foundation\"
        branches:
          - feature/security-cicd-infrastructure
          - feat/security-keycloak
          - feature/authentication-sso

      phase_2:
        name: \"Core Infrastructure\"
        branches:
          - feature/configuration-management
          - feature/core-orchestrator-foundation
          - feat/infra-base

      phase_3:
        name: \"Feature Implementation\"
        branches:
          - feature/monitoring-dashboards
          - feature/portal-web-interface
          - feature/ai-ml-gpu-infrastructure

    validation_requirements:
      pre_merge:
        - Security scan
        - Code review
        - Integration tests
        - Documentation update

      post_merge:
        - Deployment validation
        - Security validation
        - Performance check
        - Documentation verification

---

Deployment Plan:
metadata:
  project: homelab-infra
  maintainer: yourname@example.com

mvp:
  description: \"Minimal infrastructure setup for homelab using K3s\"
  features:
    - K3s single node setup
    - MetalLB basic configuration
    - Basic ingress and egress traffic handling
    - Essential monitoring and alerting with Prometheus and Grafana
    - Configuration management via Ansible
  success_criteria:
    - Successful deployment of all specified features
    - Network communication between all nodes
    - Monitoring dashboard available

poc:
  description: \"Proof of concept involving multi-node and advanced configuration\"
  features:
    - K3s multi-node cluster
    - Advanced MetalLB configurations
    - Nginx ingress controller
    - Integrated GitOps workflow with Flux
    - Enhanced monitoring setup
    - Basic CI/CD pipeline
  success_criteria:
    - CI/CD pipeline triggering deployments
    - GitOps sync working correctly
    - Multi-node cluster operational

production:
  description: \"Full-scale production setup with redundancy and automation\"
  features:
    - Full HA K3s setup
    - Advanced network policies
    - Comprehensive monitoring and alerting
    - Full automation with ArgoCD and Helm
    - Secure secret management with HashiCorp Vault
  success_criteria:
    - Seamless failover support
    - Zero downtime deployment
    - Compliance with security best practices

---

Modernization Assessment:
# Infrastructure Modernization Assessment

**Assessment Date:** December 2024  
**Project:** Homelab Infrastructure  
**Assessment Scope:** Ansible → Helm + potential Terraform migration  

## Executive Summary

This assessment analyzes the current homelab infrastructure to identify components for modernization and migration. The project has already migrated from Ansible-based deployment to Helm/Helmfile for application deployments, with Ansible retained for system-level bootstrapping. This assessment identifies opportunities for further modernization using Terraform for infrastructure management.

## Current Infrastructure Analysis

### 1. Ansible Playbooks Audit

#### 1.1 Existing Playbooks Status

**✅ Migrated to Helm (Legacy/Reference Only):**

- `deploy-gitlab.yml` → GitLab Helm chart
- `deploy-keycloak.yml` → Keycloak Helm chart  
- `deploy-cert-manager.yml` → cert-manager Helm chart
- `deploy-metallb.yml` → MetalLB Helm chart
- `deploy-monitoring.yml` → Prometheus/Grafana Helm charts
- `deploy-nginx-ingress.yml` → nginx-ingress Helm chart

**🔄 Current Active Playbooks:**

- `site.yml` - Main orchestration playbook
- `deploy-k3s.yml` / `deploy-k3s-fixed.yml` - K3s cluster installation
- `create-vm.yml` - VM creation and configuration
- `setup-deployment-user.yml` - User privilege setup
- `install-tools.yml` / `install-missing-tools.yml` - System tools installation
- `test-authentication.yml` - Authentication validation
- `validate-deployment-setup.yml` - Pre-deployment checks

#### 1.2 Components Suitable for Migration

**Infrastructure Bootstrapping (Keep in Ansible):**

- System package installation and updates
- User account and SSH key management
- Basic system configuration
- Initial K3s installation

**Infrastructure Management (Terraform Candidates):**

- VM lifecycle management
- Network configuration and IP allocation
- Storage provisioning and management
- DNS and certificate management
- Infrastructure monitoring and alerting

### 2. Helm Charts and Dependencies Analysis

#### 2.1 Current Helmfile Structure

**Repository Configuration (`helmfile.yaml`):**

```yaml
repositories:
  - prometheus-community: https://prometheus-community.github.io/helm-charts
  - grafana: https://grafana.github.io/helm-charts
  - ingress-nginx: https://kubernetes.github.io/ingress-nginx
  - jetstack: https://charts.jetstack.io
  - metallb: https://metallb.github.io/metallb
  - longhorn: https://charts.longhorn.io
  - sealed-secrets: https://bitnami-labs.github.io/sealed-secrets
```

**Release Dependencies:**

```
Core Infrastructure (Deploy First):
├── metallb (v0.14.8) - Load balancer
├── cert-manager (v1.15.3) - Certificate management
├── ingress-nginx (v4.11.2) - Ingress controller
└── sealed-secrets (v2.16.1) - Secret management

Storage Layer (Deploy Second):
└── longhorn (v1.7.1) - Distributed storage

Monitoring Stack (Deploy Last):
├── kube-prometheus-stack (v61.7.2) - Metrics collection
├── loki (v6.6.4) - Log aggregation
├── promtail (v6.16.4) - Log shipping
└── grafana (v8.4.2) - Visualization
```

#### 2.2 Chart Dependencies and Integration

**Security Dependencies:**

- cert-manager → TLS certificate lifecycle
- sealed-secrets → Encrypted secret management
- ingress-nginx → TLS termination and routing

**Storage Dependencies:**

- longhorn → Persistent volume provisioning
- All stateful applications depend on longhorn storage class

**Monitoring Dependencies:**

- kube-prometheus-stack → Base metrics infrastructure
- loki → Log aggregation backend
- promtail → Log collection from all pods
- grafana → Unified observability dashboard

### 3. Infrastructure Components for Terraform Management

#### 3.1 Current Infrastructure State

**Physical Infrastructure:**

- Homelab server: 192.168.16.26 (user: kang)
- Network: 192.168.16.0/16 subnet
- Storage: Local storage with Longhorn distributed layer

**Virtualization Layer:**

- VM creation currently handled by Ansible
- Manual IP allocation and network configuration
- Basic resource allocation without orchestration

#### 3.2 Terraform Migration Candidates

**High Priority - Infrastructure as Code:**

1. **VM Lifecycle Management**
   - VM provisioning and configuration
   - Resource allocation (CPU, memory, storage)
   - Network interface configuration
   - Automated scaling capabilities

2. **Network Infrastructure**
   - VLAN configuration and management
   - IP address pool management
   - Load balancer IP allocation
   - DNS record management

3. **Storage Infrastructure**
   - Storage pool provisioning
   - Backup storage configuration
   - Volume lifecycle management
   - Snapshot scheduling

**Medium Priority - Service Infrastructure:**

1. **Certificate Management**
   - Let's Encrypt integration
   - Internal CA certificate lifecycle
   - Certificate rotation automation
   - TLS policy enforcement

2. **Monitoring Infrastructure**
   - External monitoring endpoints
   - Alerting webhook configuration
   - Backup destination management
   - Log retention policies

**Low Priority - Application Configuration:**

1. **Application Secrets Management**
   - External secret store integration
   - Secret rotation policies
   - Access control policies

## Migration Priority Matrix

### Priority Level 1: Critical Security Infrastructure

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| cert-manager | Helm | **CRITICAL** | Required for all TLS | Low (Already Helm) |
| sealed-secrets | Helm | **HIGH** | Encrypts all secrets | Low (Already Helm) |
| ingress-nginx | Helm | **HIGH** | TLS termination point | Low (Already Helm) |
| K3s Installation | Ansible | **CRITICAL** | Cluster security foundation | Medium (System-level) |

**Deployment Frequency:** Daily to weekly  
**Recommendation:** Maintain current Helm approach, enhance with Terraform for infrastructure provisioning

### Priority Level 2: Core Infrastructure

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| MetalLB | Helm | **MEDIUM** | Network-level security | Low (Already Helm) |
| Longhorn Storage | Helm | **HIGH** | Data encryption at rest | Low (Already Helm) |
| VM Management | Ansible | **MEDIUM** | Host-level security | High (Infrastructure) |
| Network Config | Manual/Ansible | **HIGH** | Network isolation | High (Infrastructure) |

**Deployment Frequency:** Weekly to monthly  
**Recommendation:** Migrate VM and network management to Terraform

### Priority Level 3: Monitoring and Observability

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| Prometheus Stack | Helm | **MEDIUM** | Internal TLS preferred | Low (Already Helm) |
| Grafana | Helm | **MEDIUM** | HTTPS required | Low (Already Helm) |
| Loki/Promtail | Helm | **LOW** | Internal encryption | Low (Already Helm) |
| Alert Routing | Configuration | **MEDIUM** | Webhook TLS | Medium (External deps) |

**Deployment Frequency:** Monthly to quarterly  
**Recommendation:** Maintain Helm, add Terraform for external integrations

### Priority Level 4: System Management

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| System Bootstrap | Ansible | **LOW** | SSH key management | Low (Keep Ansible) |
| Tool Installation | Ansible | **LOW** | Package verification | Low (Keep Ansible) |
| User Management | Ansible | **MEDIUM** | SSH/sudo security | Low (Keep Ansible) |
| Backup Config | Manual | **HIGH** | Backup encryption | High (New implementation) |

**Deployment Frequency:** Quarterly to annually  
**Recommendation:** Keep system-level tasks in Ansible, add Terraform for backup infrastructure

## Security and Compliance Assessment

### TLS/mTLS Implementation Status

#### Current TLS Coverage

✅ **Implemented:**

- cert-manager with Let's Encrypt integration
- Ingress TLS termination for all web services
- Internal CA for cluster-internal communications
- Kubernetes API server TLS

✅ **Partially Implemented:**

- Service-to-service communication (some encrypted)
- Log shipping with TLS (configurable)
- Monitoring scrape endpoints (mixed)

⚠️ **Needs Enhancement:**

- Comprehensive mTLS between all services
- Certificate rotation automation
- Certificate transparency monitoring
- Backup data encryption in transit

#### HTTPS Requirements

- **External Services:** All require HTTPS with valid certificates
- **Internal Services:** TLS preferred, plaintext acceptable for non-sensitive
- **Admin Interfaces:** HTTPS mandatory (Grafana, Longhorn UI)
- **API Endpoints:** TLS required for external access

### Security Criticality Analysis

**Critical Security Components:**

1. **Certificate Authority Management** - Foundation for all TLS
2. **Secret Management** - Controls access to all sensitive data
3. **Network Policies** - Controls service-to-service communication
4. **RBAC Configuration** - Controls human and service account access

**High Security Components:**

1. **Storage Encryption** - Protects data at rest
2. **Ingress Security** - Controls external access
3. **Monitoring Security** - Prevents information disclosure

## Migration Recommendations

### Phase 1: Infrastructure Foundation (Terraform)

**Timeline:** 2-4 weeks  
**Scope:** Core infrastructure provisioning

**Actions:**

1. **VM Infrastructure Management**

   ```hcl
   # terraform/infrastructure/vms.tf
   resource \"proxmox_vm_qemu\" \"homelab_nodes\" {
     count = var.node_count
     name = \"homelab-node-${count.index + 1}\"
     # VM configuration
   }
   ```

2. **Network Infrastructure**

   ```hcl
   # terraform/infrastructure/network.tf
   resource \"proxmox_vm_qemu\" \"metallb_pool\" {
     # IP pool management for MetalLB
   }
   ```

3. **Storage Infrastructure**

   ```hcl
   # terraform/infrastructure/storage.tf
   resource \"proxmox_lxc\" \"backup_storage\" {
     # Backup storage configuration
   }
   ```

### Phase 2: Enhanced Security Infrastructure (Terraform)

**Timeline:** 2-3 weeks  
**Scope:** Certificate and secret management

**Actions:**

1. **External Certificate Management**
   - Terraform integration with DNS providers
   - Automated Let's Encrypt certificate provisioning
   - Certificate lifecycle management

2. **Backup Infrastructure**
   - Automated backup storage provisioning
   - Encryption key management
   - Backup retention policies

### Phase 3: Integration and Automation (Terraform + Helm)

**Timeline:** 1-2 weeks  
**Scope:** Workflow optimization

**Actions:**

1. **GitOps Integration**
   - Terraform Cloud/Enterprise setup
   - Automated Helm deployments
   - Infrastructure drift detection

2. **Monitoring Enhancement**
   - Infrastructure monitoring with Terraform
   - Compliance monitoring
   - Automated remediation workflows

### Phase 4: Advanced Features (Optional)

**Timeline:** 2-4 weeks  
**Scope:** Advanced automation and scaling

**Actions:**

1. **Auto-scaling Infrastructure**
   - Dynamic VM provisioning
   - Load-based resource allocation
   - Cost optimization automation

2. **Multi-environment Support**
   - Development/staging environment automation
   - Environment promotion workflows
   - Configuration drift management

## Implementation Strategy

### Current State Preservation

- **Keep Ansible for:** System bootstrapping, user management, tool installation
- **Keep Helm for:** Application deployments, Kubernetes resources
- **Add Terraform for:** Infrastructure provisioning, network management, external integrations

### Migration Approach

1. **Parallel Implementation:** Build Terraform infrastructure alongside existing Ansible
2. **Gradual Migration:** Move components one at a time to minimize disruption
3. **Validation at Each Step:** Ensure functionality before deprecating old methods
4. **Rollback Capability:** Maintain ability to return to previous state

### Risk Mitigation

- **Backup Strategy:** Full system backup before each migration phase
- **Testing Environment:** Validate all changes in isolated environment first
- **Documentation:** Comprehensive documentation of new workflows
- **Training:** Team familiarity with new tools and processes

## Conclusion

The homelab infrastructure is well-positioned for modernization with a strong foundation already in place through the Ansible-to-Helm migration. The primary opportunities for improvement lie in:

1. **Infrastructure as Code:** Terraform for VM and network management
2. **Enhanced Security:** Comprehensive TLS/mTLS and certificate lifecycle management
3. **Operational Efficiency:** Automated provisioning and configuration management
4. **Scalability:** Foundation for future growth and multi-environment support

The proposed phased approach minimizes risk while maximizing the benefits of modern infrastructure management practices. The current Helm-based application deployment strategy should be maintained as it provides excellent declarative management for Kubernetes workloads.

## Next Steps

1. **Review and Approve Assessment** - Stakeholder review of findings and recommendations
2. **Resource Planning** - Allocate time and resources for migration phases
3. **Environment Setup** - Prepare Terraform workspace and testing environment
4. **Phase 1 Implementation** - Begin with VM infrastructure management migration
5. **Iterative Improvement** - Continuous improvement based on lessons learned

---

**Assessment Prepared By:** Infrastructure Team  
**Review Date:** December 2024  
**Next Review:** Post Phase 1 completion

---

Unified Deployment Workflow:
# Unified Deployment Workflows

**Version:** 2.0  
**Date:** December 2024  
**Author:** DevOps Team  

## Overview

This document describes the modernized unified deployment workflows that integrate Terraform, Helm, and GitOps for seamless infrastructure and application management. The unified approach provides consistency, reliability, and automated testing across all deployment scenarios.

## Architecture Overview

```mermaid
flowchart TD
    A[Developer Commits] --> B[Git Repository]
    B --> C[CI/CD Pipeline]
    C --> D[Terraform Validation]
    C --> E[Helm Validation]
    D --> F[Infrastructure Provisioning]
    E --> G[Application Deployment]
    F --> H[Security Validation]
    G --> H
    H --> I[Integration Testing]
    I --> J[Production Deployment]

    subgraph \"GitOps Loop\"
        K[ArgoCD/Flux]
        L[Continuous Sync]
        M[Drift Detection]
        N[Auto Remediation]
        K --> L --> M --> N --> K
    end

    J --> K
```

## Deployment Strategies

### 1. Unified Script Deployment

The primary deployment method using the integrated script that orchestrates all components:

```bash
# Basic deployment
./scripts/deployment/deploy-unified.sh --environment production

# With specific options
./scripts/deployment/deploy-unified.sh \\
  --environment staging \\
  --skip-terraform \\
  --debug

# Dry run deployment
./scripts/deployment/deploy-unified.sh \\
  --environment development \\
  --dry-run
```

### 2. Component-Specific Deployment

For targeted deployments when only specific components need updates:

```bash
# Infrastructure only
./scripts/deployment/deploy-unified.sh \\
  --environment production \\
  --skip-helmfile \\
  --skip-tests

# Applications only
./scripts/deployment/deploy-unified.sh \\
  --environment production \\
  --skip-terraform
```

### 3. GitOps Deployment

Continuous deployment through GitOps tools:

```bash
# ArgoCD deployment
kubectl apply -f deployments/gitops/argocd/app-of-apps.yaml

# Flux deployment
flux bootstrap github \\
  --owner=tzervas \\
  --repository=homelab-infra \\
  --branch=main \\
  --path=deployments/gitops/flux
```

## Deployment Phases

### Phase 1: Pre-Deployment Validation

**Duration:** 2-3 minutes  
**Purpose:** Validate prerequisites and configuration

```bash
# Automated checks performed:
# - Tool availability (terraform, helm, kubectl)
# - Kubernetes cluster connectivity
# - Configuration file validation
# - Environment-specific prerequisites

# Manual validation (optional)
python3 scripts/testing/validate_deployment.py --pre-deployment
```

**Key Validations:**

- Terraform state consistency
- Kubernetes cluster health
- Required tools and versions
- Environment configuration
- Network connectivity

### Phase 2: Infrastructure Provisioning (Terraform)

**Duration:** 5-10 minutes  
**Purpose:** Provision and configure infrastructure

```bash
# Terraform workflow:
terraform init
terraform plan -var=\"environment=$ENVIRONMENT\" -out=tfplan
terraform apply tfplan

# Components provisioned:
# - K3s cluster configuration
# - Network policies and MetalLB
# - Security components (cert-manager, sealed-secrets)
# - Storage classes and provisioners
```

**Terraform Modules Applied:**

1. **K3s Cluster Module**: Cluster configuration and node management
2. **Networking Module**: MetalLB, ingress, DNS configuration
3. **Security Module**: Certificate management, RBAC, policies
4. **Storage Module**: Storage classes and provisioners

### Phase 3: Application Deployment (Helm)

**Duration:** 8-15 minutes  
**Purpose:** Deploy applications and services

```bash
# Helmfile workflow:
helmfile --environment $ENVIRONMENT deps
helmfile --environment $ENVIRONMENT sync --wait --timeout 600

# Components deployed (in order):
# 1. Infrastructure tier (metallb, cert-manager, ingress-nginx)
# 2. Storage tier (longhorn)
# 3. Monitoring tier (prometheus, grafana, loki)
# 4. Application tier (custom applications)
```

**Deployment Tiers:**

- **Infrastructure**: Core cluster services
- **Storage**: Persistent volume management
- **Monitoring**: Observability stack
- **Applications**: Business applications

### Phase 4: Security Validation

**Duration:** 3-5 minutes  
**Purpose:** Validate security configurations

```bash
# Security checks performed:
python3 scripts/security/security-policy-compliance-checks.py
python3 scripts/security/tls-configuration-validation.py --check-all
python3 scripts/security/certificate-expiry-monitoring.py --check-expiry
```

**Security Validations:**

- TLS certificate validity and expiration
- Network policy enforcement
- RBAC configuration correctness
- Pod security standards compliance
- Secret encryption and rotation

### Phase 5: Integration Testing

**Duration:** 5-8 minutes  
**Purpose:** Comprehensive system validation

```bash
# Test suite execution:
python3 scripts/testing/test_reporter.py --environment $ENVIRONMENT
./testing/k3s-validation/orchestrator.sh --environment $ENVIRONMENT
python3 scripts/testing/integrated_test_orchestrator.py
```

**Test Categories:**

- Infrastructure health checks
- Service connectivity testing
- Application functionality validation
- Performance baseline verification
- Security compliance validation

## Environment-Specific Workflows

### Development Environment

**Characteristics:**

- Relaxed security policies for easier debugging
- Single-node deployment
- Local storage only
- Self-signed certificates
- Minimal resource allocation

```bash
# Development deployment
./scripts/deployment/deploy-unified.sh \\
  --environment development \\
  --skip-tests

# Quick iteration deployment
./scripts/deployment/deploy-unified.sh \\
  --environment development \\
  --skip-terraform \\
  --debug
```

**Development-Specific Configuration:**

```yaml
# environments/development/values.yaml
global:
  environment: development
  security:
    enforceNetworkPolicies: false
    useSelfSignedCerts: true
  resources:
    requests:
      cpu: \"100m\"
      memory: \"128Mi\"
```

### Staging Environment

**Characteristics:**

- Production-like configuration
- Let's Encrypt staging certificates
- Full monitoring stack
- Multiple replicas for testing
- Network policies enabled

```bash
# Staging deployment with full validation
./scripts/deployment/deploy-unified.sh \\
  --environment staging

# Staging-specific testing
./scripts/deployment/deploy-unified.sh \\
  --environment staging \\
  --skip-terraform \\
  python3 scripts/testing/staging_validation.py
```

**Staging-Specific Configuration:**

```yaml
# environments/staging/values.yaml
global:
  environment: staging
  security:
    enforceNetworkPolicies: true
    useLetsEncryptStaging: true
  replicas:
    min: 2
    max: 3
```

### Production Environment

**Characteristics:**

- Strict security policies
- Production Let's Encrypt certificates
- High availability configuration
- Full resource allocation
- Comprehensive monitoring and alerting

```bash
# Production deployment with all safeguards
./scripts/deployment/deploy-unified.sh \\
  --environment production

# Production maintenance deployment
./scripts/deployment/deploy-unified.sh \\
  --environment production \\
  --skip-terraform \\
  --maintenance-mode
```

**Production-Specific Configuration:**

```yaml
# environments/production/values.yaml
global:
  environment: production
  security:
    enforceNetworkPolicies: true
    useLetsEncryptProd: true
    enableRuntimeSecurity: true
  replicas:
    min: 3
    max: 5
  resources:
    requests:
      cpu: \"500m\"
      memory: \"1Gi\"
    limits:
      cpu: \"2000m\"
      memory: \"4Gi\"
```

## GitOps Integration

### ArgoCD Configuration

**App-of-Apps Pattern:**

```yaml
# deployments/gitops/argocd/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: infrastructure-apps
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/tzervas/homelab-infra
    targetRevision: main
    path: deployments/gitops/argocd/applications
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
```

**Individual Application:**

```yaml
# deployments/gitops/argocd/applications/monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monitoring
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/tzervas/homelab-infra
    targetRevision: main
    path: helm
    helm:
      valueFiles:
        - environments/production/values-monitoring.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Flux Configuration

**Flux Bootstrap:**

```bash
# Install Flux
flux bootstrap github \\
  --owner=tzervas \\
  --repository=homelab-infra \\
  --branch=main \\
  --path=deployments/gitops/flux \\
  --personal
```

**Flux Kustomization:**

```yaml
# deployments/gitops/flux/clusters/homelab/kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: homelab-infra
  path: \"./kubernetes/infrastructure\"
  prune: true
  validation: client
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: metallb-controller
      namespace: metallb-system
```

## CI/CD Pipeline Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Tools
        run: |
          # Install terraform, helm, kubectl
          ./scripts/setup/install-tools.sh

      - name: Validate Terraform
        run: |
          cd terraform
          terraform init
          terraform validate
          terraform plan -var=\"environment=staging\"

      - name: Validate Helm
        run: |
          cd helm
          helmfile --environment staging lint
          helmfile --environment staging diff

  deploy-staging:
    needs: validate
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v1
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Deploy to Staging
        run: |
          ./scripts/deployment/deploy-unified.sh \\
            --environment staging

      - name: Run Tests
        run: |
          python3 scripts/testing/test_reporter.py \\
            --environment staging \\
            --output-format json > test-results.json

      - name: Upload Test Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results-staging
          path: test-results.json

  deploy-production:
    needs: [validate, deploy-staging]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v1
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Deploy to Production
        run: |
          ./scripts/deployment/deploy-unified.sh \\
            --environment production

      - name: Verify Deployment
        run: |
          python3 scripts/testing/production_health_check.py

      - name: Notify Success
        if: success()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \\
            -H 'Content-type: application/json' \\
            --data '{\"text\":\"✅ Production deployment successful\"}'

      - name: Notify Failure
        if: failure()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \\
            -H 'Content-type: application/json' \\
            --data '{\"text\":\"❌ Production deployment failed\"}'
```

### GitLab CI/CD Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - deploy-staging
  - test-staging
  - deploy-production
  - verify-production

variables:
  TERRAFORM_VERSION: \"1.6.0\"
  HELM_VERSION: \"3.13.0\"

before_script:
  - ./scripts/setup/install-tools.sh

validate:
  stage: validate
  script:
    - ./scripts/deployment/deploy-unified.sh --dry-run --environment staging
  rules:
    - if: $CI_COMMIT_BRANCH

deploy-staging:
  stage: deploy-staging
  environment:
    name: staging
    url: https://staging.homelab.local
  script:
    - ./scripts/deployment/deploy-unified.sh --environment staging
  rules:
    - if: $CI_COMMIT_BRANCH == \"develop\"

test-staging:
  stage: test-staging
  script:
    - python3 scripts/testing/test_reporter.py --environment staging
  artifacts:
    reports:
      junit: test-results.xml
  rules:
    - if: $CI_COMMIT_BRANCH == \"develop\"

deploy-production:
  stage: deploy-production
  environment:
    name: production
    url: https://homelab.local
  script:
    - ./scripts/deployment/deploy-unified.sh --environment production
  rules:
    - if: $CI_COMMIT_BRANCH == \"main\"
  when: manual

verify-production:
  stage: verify-production
  script:
    - python3 scripts/testing/production_health_check.py
    - python3 scripts/testing/integration_tester.py --environment production
  rules:
    - if: $CI_COMMIT_BRANCH == \"main\"
```

## Monitoring and Observability

### Deployment Metrics

```yaml
# monitoring/deployment-metrics.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deployment-metrics
  namespace: monitoring
data:
  prometheus-rules.yaml: |
    groups:
    - name: deployment.rules
      rules:
      - alert: DeploymentDuration
        expr: deployment_duration_seconds > 900
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: \"Deployment taking longer than expected\"
          description: \"Deployment {{ $labels.environment }} has been running for {{ $value }} seconds\"

      - alert: DeploymentFailure
        expr: deployment_success == 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: \"Deployment failed\"
          description: \"Deployment {{ $labels.environment }} has failed\"
```

### Grafana Dashboard

```json
{
  \"dashboard\": {
    \"title\": \"Deployment Overview\",
    \"panels\": [
      {
        \"title\": \"Deployment Success Rate\",
        \"type\": \"stat\",
        \"targets\": [
          {
            \"expr\": \"rate(deployment_success_total[1h])\"
          }
        ]
      },
      {
        \"title\": \"Deployment Duration\",
        \"type\": \"graph\",
        \"targets\": [
          {
            \"expr\": \"deployment_duration_seconds\"
          }
        ]
      },
      {
        \"title\": \"Environment Status\",
        \"type\": \"table\",
        \"targets\": [
          {
            \"expr\": \"deployment_last_success_timestamp\"
          }
        ]
      }
    ]
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Terraform State Lock

**Symptoms:** Terraform operations fail with state lock error
**Solution:**

```bash
# Check lock status
terraform force-unlock LOCK_ID

# Identify lock holder
terraform show terraform.tfstate | grep serial

# Safely unlock if needed
terraform force-unlock LOCK_ID -force
```

#### 2. Helm Release Conflicts

**Symptoms:** Helm deployment fails with existing release
**Solution:**

```bash
# Check existing releases
helm list -A

# Rollback problematic release
helm rollback release-name revision-number

# Force upgrade if necessary
helm upgrade release-name chart-name --force
```

#### 3. GitOps Sync Issues

**Symptoms:** ArgoCD/Flux not syncing applications
**Solution:**

```bash
# ArgoCD troubleshooting
argocd app sync app-name --force
argocd app get app-name

# Flux troubleshooting
flux get kustomizations
flux reconcile kustomization flux-system
```

#### 4. Certificate Issues

**Symptoms:** TLS certificates not being issued
**Solution:**

```bash
# Check cert-manager status
kubectl get certificates -A
kubectl describe certificate certificate-name

# Check issuer status
kubectl get clusterissuers
kubectl describe clusterissuer letsencrypt-prod

# Force certificate renewal
kubectl annotate certificate certificate-name cert-manager.io/force-renew=true
```

### Debug Commands

```bash
# Enable debug logging for unified deployment
DEBUG=true ./scripts/deployment/deploy-unified.sh --environment development

# Check deployment status
kubectl get pods -A
kubectl get services -A
kubectl get ingresses -A

# Validate network connectivity
kubectl run debug-pod --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default

# Check logs
kubectl logs -n kube-system -l app=k3s
kubectl logs -n metallb-system -l app=metallb
kubectl logs -n cert-manager -l app=cert-manager
```

## Performance Optimization

### Deployment Speed Optimization

1. **Parallel Execution**: Use Terraform and Helm parallelism
2. **Incremental Updates**: Skip unchanged components
3. **Resource Pre-allocation**: Pre-create necessary resources
4. **Caching**: Use container registry caching

```bash
# Optimized deployment command
./scripts/deployment/deploy-unified.sh \\
  --environment production \\
  --parallel \\
  --incremental \\
  --cache-images
```

### Resource Optimization

1. **Right-sizing**: Optimize resource requests and limits
2. **Node Affinity**: Distribute workloads efficiently
3. **Storage Optimization**: Use appropriate storage classes
4. **Network Optimization**: Minimize cross-zone traffic

## Security Considerations

### Deployment Security

1. **Principle of Least Privilege**: Minimal permissions for deployment processes
2. **Secret Management**: Secure handling of sensitive data
3. **Audit Logging**: Complete audit trail of all deployments
4. **Approval Workflows**: Multi-stage approval for production deployments

### Runtime Security

1. **Network Policies**: Enforce network segmentation
2. **Pod Security Standards**: Enforce security contexts
3. **Image Security**: Scan containers for vulnerabilities
4. **Runtime Monitoring**: Detect and respond to security events

## Best Practices

### Development Workflow

1. **Feature Branches**: Use branches for all changes
2. **Pull Requests**: Code review before merging
3. **Automated Testing**: Comprehensive test coverage
4. **Documentation**: Keep documentation current

### Deployment Practices

1. **Blue-Green Deployments**: Zero-downtime deployments
2. **Canary Releases**: Gradual rollout of changes
3. **Rollback Procedures**: Quick recovery from failures
4. **Health Checks**: Comprehensive health monitoring

### Operational Excellence

1. **Monitoring**: Comprehensive observability
2. **Alerting**: Proactive issue detection
3. **Runbooks**: Documented procedures
4. **Post-mortems**: Learn from incidents

## Conclusion

The unified deployment workflows provide a robust, secure, and automated approach to infrastructure and application management. By integrating Terraform, Helm, and GitOps practices, the homelab infrastructure achieves:

- **Consistency**: Repeatable deployments across environments
- **Reliability**: Automated testing and validation
- **Security**: Built-in security practices and compliance
- **Observability**: Comprehensive monitoring and alerting
- **Maintainability**: Clear procedures and documentation

This approach scales from simple homelab deployments to enterprise-grade infrastructure management while maintaining security and operational excellence.

---

**Document Version:** 2.0  
**Last Updated:** December 2024  
**Next Review:** Quarterly  
**Maintainer:** DevOps Team  
**Contact:** <tz-dev@vectorweight.com>

---
EOF
