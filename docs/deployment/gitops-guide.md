# GitOps Deployment Guide

This comprehensive guide covers GitOps implementation for the homelab infrastructure using ArgoCD and Flux, with automated deployment workflows, drift detection, and policy enforcement.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup and Installation](#setup-and-installation)
4. [Configuration Management](#configuration-management)
5. [Application Deployment](#application-deployment)
6. [Environment Management](#environment-management)
7. [Policy Enforcement](#policy-enforcement)
8. [Drift Detection](#drift-detection)
9. [Automated Workflows](#automated-workflows)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

## Overview

GitOps is a declarative approach to infrastructure and application management where the desired state is stored in Git repositories and automatically synchronized to the target environment. This implementation supports:

- **Declarative Infrastructure**: All infrastructure configuration stored in Git
- **Automated Deployment**: Push-triggered deployments with webhook integrations
- **Drift Detection**: Continuous monitoring and remediation of configuration drift
- **Policy Enforcement**: Automated compliance checking with Open Policy Agent
- **Multi-Environment Support**: Development, staging, and production environments
- **Security**: RBAC, network policies, and secret management

### Key Components

- **ArgoCD**: Primary GitOps operator for Kubernetes deployments
- **Flux**: Alternative GitOps operator with advanced features
- **Open Policy Agent (OPA) Gatekeeper**: Policy-as-code enforcement
- **Webhook Service**: Automated deployment triggering
- **Monitoring Stack**: Prometheus, Grafana, and custom metrics

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repository│    │  GitHub Webhook │    │   ArgoCD/Flux   │
│                 │────┤                 │────┤                 │
│ - Applications  │    │ - Signature     │    │ - Sync Engine   │
│ - Policies      │    │ - Event Filter  │    │ - Health Check  │
│ - Overlays      │    │ - App Mapping   │    │ - Drift Monitor │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Kubernetes    │
                    │    Cluster      │
                    │                 │
                    │ - Applications  │
                    │ - Policies      │
                    │ - Monitoring    │
                    └─────────────────┘
```

## Setup and Installation

### Prerequisites

- Kubernetes cluster (K3s recommended for homelab)
- Git repository access (GitHub/GitLab)
- kubectl configured for cluster access
- Helm 3.x installed

### Option 1: ArgoCD Installation

1. **Install ArgoCD**:
   ```bash
   # Create namespace
   kubectl create namespace argocd
   
   # Install ArgoCD
   kubectl apply -n argocd -f deployments/gitops/argocd/install.yaml
   
   # Configure repositories
   kubectl apply -n argocd -f deployments/gitops/argocd/repositories.yaml
   
   # Deploy App of Apps
   kubectl apply -n argocd -f deployments/gitops/argocd/app-of-apps.yaml
   ```

2. **Access ArgoCD UI**:
   ```bash
   # Get initial password
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   
   # Port forward (or use ingress)
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **Configure CLI**:
   ```bash
   # Login
   argocd login localhost:8080 --username admin --password <password>
   
   # List applications
   argocd app list
   ```

### Option 2: Flux Installation

1. **Install Flux CLI**:
   ```bash
   # Install flux CLI
   curl -s https://fluxcd.io/install.sh | sudo bash
   
   # Check prerequisites
   flux check --pre
   ```

2. **Bootstrap Flux**:
   ```bash
   # Bootstrap with GitHub
   flux bootstrap github \
     --owner=tzervas \
     --repository=homelab-infra \
     --branch=main \
     --path=./deployments/gitops/flux/clusters/homelab \
     --personal
   ```

3. **Verify Installation**:
   ```bash
   # Check flux components
   flux get all
   
   # Check sources
   flux get sources all
   ```

### Repository Configuration

1. **SSH Key Setup** (for private repositories):
   ```bash
   # Generate SSH key for ArgoCD/Flux
   ssh-keygen -t ed25519 -C "gitops@homelab" -f ~/.ssh/gitops_ed25519
   
   # Add public key to repository deploy keys
   cat ~/.ssh/gitops_ed25519.pub
   
   # Create Kubernetes secret
   kubectl create secret generic private-repo-secret \
     --from-file=sshPrivateKey=~/.ssh/gitops_ed25519 \
     -n argocd
   ```

2. **Webhook Configuration**:
   ```bash
   # Deploy webhook service
   kubectl apply -f deployments/gitops/webhooks/webhook-integration.yaml
   
   # Configure GitHub webhook
   # URL: https://webhook-service.homelab.local/webhook/github
   # Content type: application/json
   # Events: push, pull request
   ```

## Configuration Management

### Directory Structure

```
deployments/gitops/
├── argocd/                    # ArgoCD configuration
│   ├── install.yaml           # ArgoCD installation
│   ├── repositories.yaml      # Repository configurations
│   └── app-of-apps.yaml      # App-of-Apps pattern
├── flux/                      # Flux configuration
│   ├── install.yaml           # Flux system
│   └── clusters/homelab/      # Cluster-specific config
├── applications/              # Application definitions
│   ├── infrastructure.yaml    # Core infrastructure apps
│   └── monitoring.yaml       # Monitoring stack apps
├── overlays/                  # Environment-specific overlays
│   ├── development/           # Dev environment config
│   ├── staging/              # Staging environment config
│   └── production/           # Production environment config
├── policies/                  # Policy-as-code definitions
│   ├── gatekeeper-policies.yaml
│   └── drift-detection.yaml
└── webhooks/                  # Webhook integrations
    ├── webhook-integration.yaml
    ├── github-webhook.py
    └── requirements.txt
```

### Environment Configuration

Each environment (development, staging, production) has its own overlay with:

- **Resource Limits**: Environment-appropriate resource allocation
- **Replica Counts**: Single replica for dev, multiple for production
- **Storage Configuration**: Different storage classes and sizes
- **Network Configuration**: Environment-specific IP pools and ingress rules
- **Security Policies**: Graduated security requirements

### Kustomize Integration

Using Kustomize for environment-specific configuration:

```yaml
# overlays/development/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: default
resources:
  - ../../applications/infrastructure.yaml
  - ../../applications/monitoring.yaml

patchesStrategicMerge:
  - patches/resources-dev.yaml
  - patches/replicas-dev.yaml

commonLabels:
  environment: development
  managed-by: gitops
```

## Application Deployment

### Application Definition Structure

Applications are defined using ArgoCD Application CRDs:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: prometheus-stack
  namespace: argocd
spec:
  project: homelab
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 55.5.0
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Deployment Workflow

1. **Code Changes**: Developer pushes changes to Git repository
2. **Webhook Trigger**: GitHub webhook triggers deployment service
3. **Change Detection**: Service identifies affected applications
4. **Sync Trigger**: ArgoCD/Flux syncs affected applications
5. **Health Check**: Monitor deployment health and status
6. **Notification**: Send deployment status notifications

### App-of-Apps Pattern

Using the App-of-Apps pattern for managing multiple applications:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: homelab-apps
spec:
  source:
    path: deployments/gitops/applications
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Environment Management

### Development Environment

- **Purpose**: Development and testing
- **Resources**: Minimal resource allocation
- **Replicas**: Single replica for most services
- **Storage**: Reduced storage requirements
- **Ingress**: `.dev.homelab.local` domains
- **Certificates**: Self-signed or Let's Encrypt staging

### Staging Environment

- **Purpose**: Pre-production validation
- **Resources**: Production-like allocation
- **Replicas**: Multiple replicas for testing
- **Storage**: Full storage configuration
- **Ingress**: `.staging.homelab.local` domains
- **Certificates**: Let's Encrypt staging

### Production Environment

- **Purpose**: Live production workloads
- **Resources**: Full resource allocation
- **Replicas**: High availability configuration
- **Storage**: Full storage with backups
- **Ingress**: `.homelab.local` domains
- **Certificates**: Let's Encrypt production

### Environment Promotion

```bash
# Promote from dev to staging
git checkout staging
git merge dev
git push origin staging

# Promote from staging to production
git checkout main
git merge staging
git push origin main
```

## Policy Enforcement

### Open Policy Agent (OPA) Gatekeeper

Policy enforcement using OPA Gatekeeper for:

- **Required Labels**: Enforce environment and management labels
- **Security Contexts**: Require non-root users and read-only filesystems
- **Resource Limits**: Enforce CPU and memory limits
- **Image Policies**: Prevent latest tags and require signed images
- **Network Policies**: Enforce network segmentation

### Example Policy

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: must-have-environment
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
  parameters:
    labels: ["environment", "managed-by"]
```

### Policy Violations

When policies are violated:
1. **Admission Control**: Resources are rejected at creation
2. **Audit Mode**: Violations are logged for review
3. **Compliance Reporting**: Violations tracked in monitoring
4. **Automated Alerts**: Notifications sent to operations team

## Drift Detection

### Automated Drift Detection

Continuous monitoring for configuration drift:

- **Schedule**: Every 15 minutes via CronJob
- **Detection**: Compare desired state in Git with cluster state
- **Alerting**: Send notifications for detected drift
- **Remediation**: Automatic sync for approved drift types

### Drift Types

1. **Configuration Drift**: Changes to application configuration
2. **Resource Drift**: Manual changes to Kubernetes resources
3. **Security Drift**: Changes to security contexts or policies
4. **Scale Drift**: Manual scaling of deployments

### Remediation Strategies

- **Automatic Sync**: Immediate sync for low-risk changes
- **Manual Approval**: Human approval required for high-risk changes
- **Rollback**: Automatic rollback for failed deployments
- **Alert Only**: Notification without automatic action

## Automated Workflows

### GitHub Webhook Integration

Automated deployment triggered by Git events:

```python
# Webhook endpoint
@app.route('/webhook/github', methods=['POST'])
def github_webhook():
    # Verify signature
    # Parse payload
    # Determine affected applications
    # Trigger ArgoCD sync
    # Send notifications
```

### Supported Events

- **Push Events**: Trigger deployment for affected applications
- **Pull Request Events**: Trigger validation and preview environments
- **Tag Events**: Trigger production deployments
- **Release Events**: Trigger release-specific workflows

### Application Mapping

Webhook service maps changed files to affected applications:

```python
app_mappings = {
    'deployments/gitops/applications/infrastructure.yaml': 
        ['metallb', 'cert-manager', 'ingress-nginx', 'longhorn'],
    'helm/': ['homelab-apps'],
    'kubernetes/': ['homelab-apps']
}
```

## Monitoring and Observability

### GitOps Metrics

Monitor GitOps operations with custom metrics:

- **Sync Status**: Application sync success/failure rates
- **Drift Detection**: Frequency and types of drift detected
- **Deployment Time**: Time to deploy applications
- **Health Status**: Application health over time

### Prometheus Metrics

```prometheus
# ArgoCD application sync status
argocd_app_info{name, namespace, repo, path}

# Drift detection metrics
gitops_drift_detected_total{application, type}

# Webhook metrics
webhook_requests_total{event_type, status}
```

### Grafana Dashboards

- **GitOps Overview**: High-level GitOps health and metrics
- **Application Status**: Individual application deployment status
- **Drift Detection**: Drift detection and remediation tracking
- **Webhook Activity**: Webhook trigger and processing metrics

### Alerting Rules

```yaml
groups:
- name: gitops
  rules:
  - alert: GitOpsApplicationUnhealthy
    expr: argocd_app_health_status != 1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "GitOps application {{ $labels.name }} is unhealthy"

  - alert: GitOpsDriftDetected
    expr: increase(gitops_drift_detected_total[1h]) > 0
    labels:
      severity: warning
    annotations:
      summary: "Configuration drift detected in {{ $labels.application }}"
```

## Troubleshooting

### Common Issues

#### ArgoCD Application Stuck in Progressing

```bash
# Check application status
argocd app get <app-name>

# View detailed sync status
argocd app sync <app-name> --dry-run

# Check resource events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Force sync
argocd app sync <app-name> --force --prune
```

#### Webhook Not Triggering

```bash
# Check webhook service logs
kubectl logs -n monitoring deployment/webhook-service

# Verify webhook configuration
curl -X POST https://webhook-service.homelab.local/health

# Check GitHub webhook deliveries in repository settings
```

#### Policy Violations

```bash
# Check Gatekeeper violations
kubectl get constraints

# View specific constraint violations
kubectl describe k8srequiredlabels must-have-environment

# Check admission controller logs
kubectl logs -n gatekeeper-system deployment/gatekeeper-controller-manager
```

#### Flux Source Errors

```bash
# Check source status
flux get sources all

# View source events
kubectl describe gitrepository <source-name> -n flux-system

# Check Flux logs
kubectl logs -n flux-system deployment/source-controller
```

### Debug Commands

```bash
# ArgoCD CLI troubleshooting
argocd app get <app-name> --show-managed-fields
argocd app diff <app-name>
argocd app history <app-name>

# Kubernetes troubleshooting
kubectl get events --sort-by='.lastTimestamp' -A
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous

# Flux troubleshooting
flux get all --all-namespaces
flux logs --all-namespaces
flux suspend source git <source-name>
flux resume source git <source-name>
```

### Recovery Procedures

#### Rollback Failed Deployment

```bash
# ArgoCD rollback
argocd app rollback <app-name> <revision>

# Flux rollback
flux suspend kustomization <name>
# Fix issue in Git
flux resume kustomization <name>
```

#### Reset GitOps State

```bash
# Delete ArgoCD application (keeps resources)
argocd app delete <app-name> --cascade=false

# Recreate application
kubectl apply -f applications/app-definition.yaml

# Sync to desired state
argocd app sync <app-name>
```

## Best Practices

### Repository Management

1. **Branch Strategy**: Use GitFlow with protected main branch
2. **Code Reviews**: Require pull request reviews for all changes
3. **Semantic Versioning**: Tag releases with semantic versions
4. **Documentation**: Keep documentation updated with changes
5. **Security**: Use signed commits and branch protection rules

### Application Configuration

1. **Declarative**: Always use declarative Kubernetes manifests
2. **Immutable**: Treat infrastructure as immutable
3. **Version Control**: Store all configuration in Git
4. **Environment Separation**: Use separate overlays for environments
5. **Resource Limits**: Always define resource requests and limits

### Security Practices

1. **Least Privilege**: Use minimal RBAC permissions
2. **Secret Management**: Use sealed secrets or external secret managers
3. **Image Security**: Scan images and use signed images
4. **Network Policies**: Implement network segmentation
5. **Policy Enforcement**: Use OPA Gatekeeper for compliance

### Monitoring and Alerting

1. **Comprehensive Metrics**: Monitor all aspects of GitOps
2. **Proactive Alerting**: Alert on trends, not just failures
3. **Runbook Integration**: Link alerts to troubleshooting guides
4. **SLA Monitoring**: Track deployment time and success rates
5. **Audit Logging**: Maintain comprehensive audit logs

### Deployment Practices

1. **Progressive Delivery**: Use canary or blue-green deployments
2. **Health Checks**: Implement proper readiness and liveness probes
3. **Rollback Strategy**: Have automated rollback procedures
4. **Testing**: Validate deployments in lower environments first
5. **Change Management**: Document and communicate changes

## Conclusion

This GitOps implementation provides a robust, automated, and secure approach to infrastructure and application management. By following GitOps principles and leveraging the tools and practices outlined in this guide, you can achieve:

- **Consistency**: Identical deployments across environments
- **Reliability**: Automated recovery and drift correction  
- **Security**: Policy enforcement and audit trails
- **Velocity**: Faster, more frequent deployments
- **Observability**: Complete visibility into deployment processes

Regular review and improvement of GitOps processes ensures continued alignment with best practices and organizational needs.

## Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Flux Documentation](https://fluxcd.io/docs/)
- [Open Policy Agent](https://www.openpolicyagent.org/docs/latest/)
- [GitOps Toolkit](https://toolkit.fluxcd.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Note**: This guide assumes familiarity with Kubernetes, Git, and basic DevOps practices. Adjust configurations based on your specific requirements and environment constraints.
