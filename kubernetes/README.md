# Kubernetes Manifests

Raw Kubernetes manifest files for deploying homelab infrastructure components directly to Kubernetes clusters.

## Overview

This directory contains production-ready Kubernetes manifests organized by component and functionality. These manifests provide an alternative to Helm-based deployments and serve as the foundation for GitOps workflows.

## Structure

```
kubernetes/
├── base/                          # Core infrastructure manifests
│   ├── cluster-issuers.yaml      # cert-manager cluster issuers
│   ├── gitlab-deployment.yaml    # GitLab CE deployment
│   ├── grafana-deployment.yaml   # Grafana monitoring dashboard
│   ├── ingress-config.yaml       # NGINX ingress configuration
│   ├── keycloak-deployment.yaml  # Keycloak identity provider
│   ├── longhorn.yaml             # Longhorn storage system
│   ├── metallb-config.yaml       # MetalLB load balancer
│   ├── namespaces.yaml           # Namespace definitions
│   ├── network-policies.yaml     # Network security policies
│   ├── oauth2-proxy.yaml         # OAuth2 Proxy for SSO
│   ├── pod-security-standards.yaml # Pod Security Standards
│   ├── prometheus-deployment.yaml # Prometheus monitoring
│   ├── rbac.yaml                 # Role-based access control
│   ├── resource-allocations.yaml # Resource quotas and limits
│   └── security-contexts.yaml    # Security context definitions
├── homelab-portal/               # Homelab portal application
│   ├── backend/                  # Backend API service
│   ├── frontend/                 # Frontend web interface
│   ├── helm/                     # Helm chart alternative
│   └── manifests/                # Raw Kubernetes manifests
├── keycloak/                     # Keycloak integration manifests
│   ├── gitlab-keycloak.yaml      # GitLab-Keycloak integration
│   ├── grafana-keycloak.yaml     # Grafana-Keycloak integration
│   ├── oauth2-proxy-multi-client.yaml # Multi-client OAuth2 setup
│   └── *.yaml                    # Other service integrations
├── monitoring/                   # Monitoring stack manifests
│   ├── alerting/                 # AlertManager configuration
│   └── prometheus/               # Prometheus operator setup
└── enhanced-portal.yaml          # Enhanced portal deployment
```

## Quick Start

### Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured with cluster access
- Sufficient cluster resources (see [Resource Requirements](#resource-requirements))

### Basic Deployment

```bash
# Create namespaces first
kubectl apply -f base/namespaces.yaml

# Deploy core infrastructure
kubectl apply -f base/metallb-config.yaml
kubectl apply -f base/longhorn.yaml
kubectl apply -f base/ingress-config.yaml

# Deploy security policies
kubectl apply -f base/network-policies.yaml
kubectl apply -f base/pod-security-standards.yaml
kubectl apply -f base/rbac.yaml

# Deploy applications
kubectl apply -f base/keycloak-deployment.yaml
kubectl apply -f base/gitlab-deployment.yaml
kubectl apply -f base/prometheus-deployment.yaml
kubectl apply -f base/grafana-deployment.yaml
```

### Ordered Deployment

For proper dependency management, deploy in this order:

1. **Namespaces and RBAC**

   ```bash
   kubectl apply -f base/namespaces.yaml
   kubectl apply -f base/rbac.yaml
   ```

2. **Storage and Networking**

   ```bash
   kubectl apply -f base/longhorn.yaml
   kubectl apply -f base/metallb-config.yaml
   kubectl apply -f base/ingress-config.yaml
   ```

3. **Security Infrastructure**

   ```bash
   kubectl apply -f base/cluster-issuers.yaml
   kubectl apply -f base/network-policies.yaml
   kubectl apply -f base/pod-security-standards.yaml
   ```

4. **Core Services**

   ```bash
   kubectl apply -f base/keycloak-deployment.yaml
   kubectl apply -f base/oauth2-proxy.yaml
   ```

5. **Applications**

   ```bash
   kubectl apply -f base/gitlab-deployment.yaml
   kubectl apply -f base/prometheus-deployment.yaml
   kubectl apply -f base/grafana-deployment.yaml
   ```

6. **Keycloak Integrations**

   ```bash
   kubectl apply -f keycloak/
   ```

## Component Details

### Core Infrastructure

#### MetalLB Load Balancer

**File**: `base/metallb-config.yaml`

- Provides LoadBalancer services for bare-metal clusters
- Configures IP address pools for external access
- Includes L2 and BGP advertisement configuration

#### Longhorn Storage

**File**: `base/longhorn.yaml`

- Distributed block storage for Kubernetes
- Provides persistent volumes with replication
- Includes backup and disaster recovery configuration

#### NGINX Ingress Controller

**File**: `base/ingress-config.yaml`

- HTTP/HTTPS load balancing and routing
- SSL termination and certificate management
- Rate limiting and security headers

### Security Components

#### Network Policies

**File**: `base/network-policies.yaml`

- Default deny-all policy for enhanced security
- Service-specific communication rules
- Namespace isolation and traffic control

#### Pod Security Standards

**File**: `base/pod-security-standards.yaml`

- Enforces Pod Security Standards across namespaces
- Restricted security profile for production workloads
- Audit and warning modes for compliance

#### RBAC Configuration

**File**: `base/rbac.yaml`

- Service account definitions
- Role and ClusterRole permissions
- RoleBinding and ClusterRoleBinding assignments

### Application Services

#### Keycloak Identity Provider

**File**: `base/keycloak-deployment.yaml`

- OAuth2/OIDC identity and access management
- PostgreSQL database backend
- Integrated with all homelab services for SSO

#### GitLab CE

**File**: `base/gitlab-deployment.yaml`

- Complete DevOps platform
- Git repository hosting
- CI/CD pipeline execution
- Container registry

#### Monitoring Stack

**Files**: `base/prometheus-deployment.yaml`, `base/grafana-deployment.yaml`

- Prometheus metrics collection and storage
- Grafana visualization and dashboards
- AlertManager for notification routing

### Homelab Portal

#### Architecture

The homelab portal provides a unified web interface for managing the entire infrastructure:

- **Backend API**: RESTful API for infrastructure management
- **Frontend Interface**: React-based web application
- **Database**: PostgreSQL for state management
- **Authentication**: Integrated with Keycloak SSO

#### Deployment

```bash
# Deploy portal infrastructure
kubectl apply -f homelab-portal/manifests/

# Or use enhanced version
kubectl apply -f enhanced-portal.yaml
```

## Configuration

### Environment-Specific Configurations

Use Kustomize overlays for environment-specific configurations:

```bash
# Development environment
kubectl apply -k overlays/development/

# Staging environment  
kubectl apply -k overlays/staging/

# Production environment
kubectl apply -k overlays/production/
```

### ConfigMap and Secret Management

#### Configuration Files

- Store non-sensitive configuration in ConfigMaps
- Reference from `config/consolidated/` for consistency
- Use Helm templating for dynamic values

#### Secrets Management

- Use Kubernetes Secrets for sensitive data
- Consider Sealed Secrets or External Secrets Operator
- Never commit plain-text secrets to version control

### Example ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: homelab
data:
  database.host: "postgresql.database.svc.cluster.local"
  redis.host: "redis.cache.svc.cluster.local"
  log.level: "INFO"
```

## Resource Requirements

### Minimum Requirements

- **CPU**: 4 cores total
- **Memory**: 8GB RAM
- **Storage**: 100GB available disk space
- **Network**: 1Gbps internal networking

### Recommended Requirements

- **CPU**: 8+ cores
- **Memory**: 16GB+ RAM  
- **Storage**: 500GB+ SSD storage
- **Network**: 10Gbps internal networking

### Per-Service Requirements

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|---------|------------|-----------|----------------|--------------|---------|
| Keycloak | 500m | 1000m | 1Gi | 2Gi | 10Gi |
| GitLab | 1000m | 2000m | 2Gi | 4Gi | 50Gi |
| Prometheus | 500m | 1000m | 2Gi | 4Gi | 100Gi |
| Grafana | 200m | 500m | 512Mi | 1Gi | 10Gi |
| Longhorn | 200m | 500m | 512Mi | 1Gi | Variable |

## Networking

### Service Discovery

- Internal services use cluster DNS resolution
- External access through LoadBalancer or NodePort services
- Ingress routing for HTTP/HTTPS traffic

### Port Allocations

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| Keycloak | 8080 | 80/443 | HTTP/HTTPS |
| GitLab | 80, 22 | 80/443, 2222 | HTTP/HTTPS, SSH |
| Grafana | 3000 | 80/443 | HTTP/HTTPS |
| Prometheus | 9090 | 9090 | HTTP |
| Portal | 8080 | 80/443 | HTTP/HTTPS |

### DNS Configuration

```yaml
# Internal DNS names
keycloak.homelab.svc.cluster.local
gitlab.homelab.svc.cluster.local
grafana.monitoring.svc.cluster.local
prometheus.monitoring.svc.cluster.local

# External DNS (configure in your DNS server)
keycloak.homelab.local
gitlab.homelab.local  
grafana.homelab.local
prometheus.homelab.local
```

## Security

### Network Security

- Default deny network policies
- Service mesh integration ready (Istio/Linkerd)
- mTLS between services where supported

### Pod Security

- Non-root user enforcement
- Read-only root filesystem where possible
- Security context enforcement
- Resource limits and quotas

### Secrets Management

- Kubernetes native secrets
- Sealed Secrets for GitOps workflows
- External Secrets Operator integration ready

### Certificate Management

- cert-manager for automatic certificate provisioning
- Let's Encrypt integration for public certificates
- Internal CA for service-to-service communication

## Monitoring and Observability

### Metrics Collection

- Prometheus scrapes metrics from all services
- Custom ServiceMonitor CRDs for application metrics
- Node and cluster-level metrics collection

### Logging

- Centralized logging with Loki/Fluentd
- Structured JSON logging where possible
- Log retention and rotation policies

### Alerting

- AlertManager for notification routing
- Pre-configured alerts for common issues
- Integration with external notification systems

### Dashboards  

- Pre-built Grafana dashboards for all services
- Infrastructure overview and service-specific views
- Custom dashboards for homelab-specific metrics

## Backup and Disaster Recovery

### Backup Strategy

- Velero for cluster-level backups
- Longhorn volume snapshots
- Database-specific backup procedures

### Disaster Recovery

- Cross-cluster replication setup
- Recovery time objectives (RTO) and recovery point objectives (RPO)
- Disaster recovery testing procedures

## Troubleshooting

### Common Issues

#### Pod Startup Failures

```bash
# Check pod status and events
kubectl get pods -n homelab
kubectl describe pod <pod-name> -n homelab

# Check resource constraints
kubectl top pods -n homelab
kubectl describe nodes
```

#### Service Connectivity Issues

```bash
# Test service resolution
kubectl run debug --image=busybox --rm -it -- nslookup <service-name>

# Check network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <policy-name> -n <namespace>
```

#### Storage Issues

```bash
# Check Longhorn status
kubectl get pods -n longhorn-system
kubectl get volumes -n longhorn-system

# Check PVC status
kubectl get pvc -A
kubectl describe pvc <pvc-name> -n <namespace>
```

### Debug Commands

```bash
# General cluster health
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods --all-namespaces

# Resource utilization
kubectl top nodes
kubectl top pods --all-namespaces

# Storage status
kubectl get pv
kubectl get pvc --all-namespaces

# Network status
kubectl get services --all-namespaces
kubectl get ingress --all-namespaces
```

## Migration and Upgrades

### From Helm to Raw Manifests

1. Export existing Helm resources: `helm get manifest <release>`
2. Extract and organize manifests by component
3. Apply resource labels and annotations for management
4. Test deployment in staging environment

### Kubernetes Version Upgrades

1. Review Kubernetes changelog for breaking changes
2. Update manifest API versions as needed
3. Test with validation tools: `kubectl apply --dry-run=server`
4. Perform rolling upgrades with minimal downtime

### Application Updates

1. Update container image tags in manifests
2. Apply changes with `kubectl apply`
3. Monitor rollout status: `kubectl rollout status deployment/<name>`
4. Rollback if issues occur: `kubectl rollout undo deployment/<name>`

## GitOps Integration

### ArgoCD Setup

```bash
# Deploy ArgoCD
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Configure applications
kubectl apply -f deployments/gitops/argocd/
```

### Flux Setup

```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux
flux bootstrap github --owner=<username> --repository=homelab-infra
```

## Best Practices

### Manifest Organization

- Group related resources in single files
- Use consistent labeling and annotations
- Include resource descriptions and documentation

### Resource Management

- Set appropriate resource requests and limits
- Use HorizontalPodAutoscaler for scalable services
- Implement PodDisruptionBudgets for high availability

### Security Hardening

- Follow Pod Security Standards
- Implement network segmentation
- Regular security scanning and updates
- Principle of least privilege for service accounts

### Operational Excellence

- Implement comprehensive monitoring
- Automate backup and recovery procedures
- Document incident response procedures
- Regular disaster recovery testing

## Contributing

When contributing new manifests:

1. Follow existing naming conventions
2. Include appropriate labels and annotations
3. Add resource requests and limits
4. Include security contexts and network policies
5. Update this README with new component documentation
6. Test manifests in development environment

## Related Documentation

- [Helm Charts](../helm/README.md) - Helm-based deployment alternative
- [Configuration Management](../config/README.md) - Unified configuration system
- [GitOps Deployments](../deployments/gitops/README.md) - GitOps workflow setup
- [Security Best Practices](../docs/security/best-practices.md) - Security guidelines
- [Monitoring Guide](../docs/operations/monitoring.md) - Monitoring setup and configuration
