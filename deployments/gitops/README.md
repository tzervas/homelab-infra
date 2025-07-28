# GitOps Configuration Management

This directory contains GitOps-ready configuration management for the homelab infrastructure, implementing declarative infrastructure state management, automated drift detection, and policy-as-code enforcement.

## Directory Structure

```
deployments/gitops/
├── README.md                          # This documentation
├── argocd/                           # ArgoCD configuration templates
│   ├── install.yaml                  # ArgoCD installation manifest
│   ├── repositories.yaml             # Repository configurations
│   └── app-of-apps.yaml             # App-of-Apps pattern implementation
├── flux/                             # Flux configuration templates
│   ├── install.yaml                  # Flux system installation
│   └── clusters/homelab/             # Homelab cluster configuration
│       ├── kustomization.yaml        # Cluster-level kustomization
│       └── sources.yaml              # Git and Helm repository sources
├── applications/                     # Application manifests for GitOps
│   ├── infrastructure.yaml           # Core infrastructure applications
│   └── monitoring.yaml              # Monitoring stack applications
├── overlays/                         # Environment-specific overlays
│   ├── development/                  # Development environment
│   │   ├── kustomization.yaml        # Dev-specific kustomization
│   │   ├── metallb-config.yaml       # MetalLB development config
│   │   └── patches/                  # Environment-specific patches
│   │       └── resources-dev.yaml    # Resource patches for development
│   ├── staging/                      # Staging environment (future)
│   └── production/                   # Production environment (future)
├── policies/                         # Policy-as-code configurations
│   ├── gatekeeper-policies.yaml      # OPA Gatekeeper policies
│   └── drift-detection.yaml          # Drift detection configuration
└── webhooks/                         # Webhook integrations
    ├── webhook-integration.yaml      # Webhook service deployment
    ├── github-webhook.py             # GitHub webhook handler
    ├── Dockerfile                    # Webhook service container
    └── requirements.txt              # Python dependencies
```

## Quick Start

### Prerequisites

- Kubernetes cluster (K3s recommended)
- kubectl configured with cluster access
- Helm 3.x installed
- Git repository access (public or private with SSH keys)

### Option 1: Deploy with ArgoCD

1. **Install ArgoCD**:
   ```bash
   # Create namespace and install ArgoCD
   kubectl create namespace argocd
   kubectl apply -n argocd -f argocd/install.yaml
   
   # Wait for ArgoCD to be ready
   kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
   ```

2. **Configure repositories**:
   ```bash
   # Apply repository configurations
   kubectl apply -n argocd -f argocd/repositories.yaml
   
   # Deploy App-of-Apps pattern
   kubectl apply -n argocd -f argocd/app-of-apps.yaml
   ```

3. **Access ArgoCD UI**:
   ```bash
   # Get admin password
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   
   # Port forward to access UI
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   # Open https://localhost:8080
   ```

### Option 2: Deploy with Flux

1. **Install Flux CLI**:
   ```bash
   curl -s https://fluxcd.io/install.sh | sudo bash
   flux check --pre
   ```

2. **Bootstrap Flux**:
   ```bash
   # Replace with your repository details
   flux bootstrap github \
     --owner=tzervas \
     --repository=homelab-infra \
     --branch=main \
     --path=./deployments/gitops/flux/clusters/homelab \
     --personal
   ```

3. **Verify installation**:
   ```bash
   flux get all
   flux get sources all
   ```

## Configuration Components

### Core Infrastructure Applications

The `applications/infrastructure.yaml` defines core infrastructure components:

- **MetalLB**: Load balancer for bare metal Kubernetes
- **cert-manager**: Automatic TLS certificate management
- **ingress-nginx**: HTTP/HTTPS ingress controller
- **Longhorn**: Distributed block storage

### Monitoring Stack

The `applications/monitoring.yaml` defines monitoring components:

- **Prometheus Stack**: Metrics collection and alerting
- **Loki Stack**: Log aggregation and analysis
- **Grafana**: Visualization and dashboards (included in Prometheus stack)

### Environment Overlays

Environment-specific configurations using Kustomize overlays:

- **Development**: Minimal resources, single replicas, reduced storage
- **Staging**: Production-like configuration for testing
- **Production**: Full resources, high availability, comprehensive monitoring

### Policy Enforcement

Open Policy Agent Gatekeeper policies enforce:

- **Required Labels**: Environment and management labels
- **Security Contexts**: Non-root users, read-only filesystems
- **Resource Limits**: CPU and memory constraints
- **Image Policies**: Prevent latest tags, enforce signed images

### Drift Detection

Automated drift detection with:

- **CronJob**: Runs every 15 minutes to detect drift
- **Notifications**: Webhook notifications for detected drift
- **Remediation**: Configurable auto-sync and manual approval workflows

## Environment Management

### Development Environment

```bash
# Deploy development environment
kubectl apply -k overlays/development/

# Or with ArgoCD
argocd app create homelab-dev \
  --repo https://github.com/tzervas/homelab-infra.git \
  --path deployments/gitops/overlays/development \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default \
  --sync-policy automated
```

### IP Address Allocation

Each environment has dedicated IP ranges:

- **Development**: 192.168.25.200-192.168.25.210
- **Staging**: 192.168.25.220-192.168.25.235  
- **Production**: 192.168.25.240-192.168.25.250

## Webhook Integration

### GitHub Webhook Setup

1. **Deploy webhook service**:
   ```bash
   kubectl apply -f webhooks/webhook-integration.yaml
   ```

2. **Configure GitHub webhook**:
   - URL: `https://webhook-service.homelab.local/webhook/github`
   - Content type: `application/json`
   - Events: `push`, `pull_request`
   - Secret: Configure webhook secret in Kubernetes secret

3. **Build and deploy webhook container**:
   ```bash
   cd webhooks/
   docker build -t webhook-service:latest .
   # Push to your container registry
   ```

### Supported Webhook Events

- **Push Events**: Trigger application sync for affected applications
- **Pull Request Events**: Trigger validation workflows
- **Drift Notifications**: Handle configuration drift alerts
- **Health Notifications**: Process application health status changes

## Security Configuration

### SSH Key Management

For private repositories:

```bash
# Generate SSH key for GitOps
ssh-keygen -t ed25519 -C "gitops@homelab" -f ~/.ssh/gitops_ed25519

# Add public key to repository deploy keys
cat ~/.ssh/gitops_ed25519.pub

# Create Kubernetes secret
kubectl create secret generic private-repo-secret \
  --from-file=sshPrivateKey=~/.ssh/gitops_ed25519 \
  -n argocd
```

### RBAC Configuration

ArgoCD and Flux are configured with minimal required permissions:

- **Cluster-wide**: CRD management, namespace creation
- **Namespace-scoped**: Application deployment and management
- **Project-based**: Environment-specific access controls

### Secret Management

- **Sealed Secrets**: Encrypted secrets stored in Git
- **External Secrets**: Integration with external secret managers
- **Webhook Secrets**: Secure webhook authentication tokens

## Monitoring and Observability

### GitOps Metrics

Monitor GitOps operations through:

- **Application Sync Status**: Success/failure rates
- **Drift Detection Frequency**: Drift occurrence patterns
- **Deployment Times**: Application deployment duration
- **Policy Violations**: Compliance monitoring

### Prometheus Metrics

Key metrics exposed:

```prometheus
# ArgoCD application health
argocd_app_health_status{name, namespace, project}

# Sync operation results
argocd_app_sync_total{name, namespace, operation}

# Drift detection events
gitops_drift_detected_total{application, type, severity}

# Webhook processing
webhook_requests_total{event_type, status}
```

### Grafana Dashboards

Included dashboards for:

- **GitOps Overview**: High-level health and status
- **Application Details**: Per-application metrics
- **Drift Detection**: Configuration drift tracking
- **Policy Compliance**: OPA Gatekeeper violations

## Troubleshooting

### Common Issues

1. **Application sync failures**:
   ```bash
   # Check application status
   argocd app get <app-name>
   
   # View sync errors
   argocd app sync <app-name> --dry-run
   
   # Force sync if needed
   argocd app sync <app-name> --force --prune
   ```

2. **Webhook not triggering**:
   ```bash
   # Check webhook service logs
   kubectl logs -n monitoring deployment/webhook-service
   
   # Test webhook endpoint
   curl -X POST https://webhook-service.homelab.local/health
   ```

3. **Policy violations**:
   ```bash
   # Check Gatekeeper constraints
   kubectl get constraints
   
   # View violation details
   kubectl describe k8srequiredlabels must-have-environment
   ```

### Debug Commands

```bash
# ArgoCD troubleshooting
argocd app list
argocd app diff <app-name>
argocd app history <app-name>

# Flux troubleshooting
flux get all
flux logs --all-namespaces
flux get sources all

# Kubernetes events
kubectl get events --sort-by='.lastTimestamp' -A
```

## Best Practices

### Repository Management

1. **Use protected branches** for production deployments
2. **Require pull request reviews** for all changes
3. **Implement signed commits** for security
4. **Tag releases** with semantic versioning
5. **Maintain comprehensive documentation**

### Application Configuration

1. **Always use declarative manifests**
2. **Define resource requests and limits**
3. **Implement proper health checks**
4. **Use meaningful labels and annotations**
5. **Separate configuration by environment**

### Security Practices

1. **Implement least privilege access**
2. **Use encrypted secrets management**
3. **Enforce security policies with OPA**
4. **Regular security scanning of images**
5. **Monitor for policy violations**

### Deployment Practices

1. **Test changes in development first**
2. **Use progressive deployment strategies**
3. **Implement proper rollback procedures**
4. **Monitor deployment metrics**
5. **Document operational procedures**

## Migration from Existing Infrastructure

### From Helm/Helmfile

1. **Convert existing Helmfile** to ArgoCD Applications
2. **Migrate values files** to application-specific configurations
3. **Implement environment overlays** for existing environments
4. **Test deployments** in development environment first

### From Manual Deployments

1. **Export existing configurations** as YAML manifests
2. **Organize into logical applications**
3. **Implement proper labeling** and annotations
4. **Add resource limits** and health checks
5. **Gradually migrate** applications to GitOps

## Integration with Existing Tools

### CI/CD Integration

- **GitHub Actions**: Trigger validation on pull requests
- **GitLab CI**: Automated testing and security scanning
- **Jenkins**: Integration with existing CI/CD pipelines

### Monitoring Integration

- **Prometheus**: Custom metrics for GitOps operations
- **Grafana**: Dashboards for GitOps visibility
- **Alertmanager**: Alerts for deployment failures and drift

### Security Integration

- **Trivy**: Container image vulnerability scanning
- **Falco**: Runtime security monitoring
- **OPA**: Policy enforcement and compliance

## Additional Resources

- [Complete GitOps Guide](../../docs/deployment/gitops-guide.md)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Flux Documentation](https://fluxcd.io/docs/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/)
- [Kustomize Documentation](https://kustomize.io/)

## Support and Contributing

### Getting Help

1. **Check troubleshooting section** in this README
2. **Review application logs** using kubectl
3. **Consult the comprehensive guide** in docs/
4. **Check GitHub issues** for known problems

### Contributing

1. **Fork the repository** and create feature branch
2. **Test changes thoroughly** in development environment
3. **Update documentation** as needed
4. **Submit pull request** with detailed description
5. **Ensure all CI checks pass**

---

This GitOps configuration provides a production-ready foundation for declarative infrastructure management with automated deployment, drift detection, and policy enforcement. Start with the development environment and gradually promote configurations through staging to production.
