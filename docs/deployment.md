# Deployment Guide

Comprehensive deployment guide for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## Deployment Overview

The orchestrator provides a unified deployment workflow that replaces multiple bash scripts with a single, cohesive Python-based system.

## Deployment Architecture

```
Deployment Flow:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Prerequisites │ -> │  Core Infrastructure │ -> │   Applications  │
│   Validation    │    │   (metallb, nginx,  │    │   (monitoring,  │
│                 │    │    cert-manager)    │    │    keycloak)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Prerequisites

### System Requirements

- **Kubernetes Cluster**: K3s or standard Kubernetes
- **Python**: 3.10+ with virtual environment
- **Resources**: 4GB+ RAM, 2+ CPU cores
- **Network**: Internet access for Let's Encrypt and container images

### Pre-Deployment Validation

```bash
# Validate system prerequisites
python -m homelab_orchestrator config validate

# Check cluster connectivity
kubectl cluster-info

# Verify resource availability  
kubectl top nodes

# Test orchestrator functionality
python scripts/testing/test_mvp_deployment.py
```

## Deployment Workflows

### Quick Deployment (Development)

For development and testing environments:

```bash
# 1. Generate secrets
./scripts/security/generate-secrets.sh

# 2. Deploy certificate management
python -m homelab_orchestrator certificates deploy

# 3. Deploy core infrastructure
python -m homelab_orchestrator --environment development deploy infrastructure

# 4. Validate deployment
python -m homelab_orchestrator certificates validate
python -m homelab_orchestrator health check --comprehensive
```

### Production Deployment

For production environments with Let's Encrypt certificates:

```bash
# 1. Configure production environment
export ENVIRONMENT=production
echo "ENVIRONMENT=production" >> .env
echo "TLS_CERT_EMAIL=admin@yourdomain.com" >> .env

# 2. Validate configuration
python -m homelab_orchestrator --environment production config validate

# 3. Deploy with dry-run first
python -m homelab_orchestrator --environment production deploy infrastructure --dry-run

# 4. Deploy core infrastructure
python -m homelab_orchestrator --environment production deploy infrastructure --components metallb cert_manager ingress_nginx

# 5. Deploy applications
python -m homelab_orchestrator --environment production deploy infrastructure --components keycloak monitoring

# 6. Comprehensive validation
python -m homelab_orchestrator certificates validate
python -m homelab_orchestrator health check --comprehensive
```

### Staged Deployment

Deploy components in controlled phases:

```bash
# Phase 1: Network infrastructure
python -m homelab_orchestrator deploy infrastructure --components metallb

# Phase 2: Certificate management  
python -m homelab_orchestrator certificates deploy
python -m homelab_orchestrator certificates validate

# Phase 3: Ingress and routing
python -m homelab_orchestrator deploy infrastructure --components ingress_nginx

# Phase 4: Core applications
python -m homelab_orchestrator deploy infrastructure --components keycloak monitoring

# Phase 5: Additional services
python -m homelab_orchestrator deploy infrastructure --components gitlab ai_tools jupyter
```

## Component Deployment

### Infrastructure Components

#### MetalLB Load Balancer

```bash
# Deploy MetalLB
python -m homelab_orchestrator deploy infrastructure --components metallb

# Verify IP pool assignment
kubectl get svc -n ingress-nginx
kubectl get ipaddresspool -A
```

**Configuration**: `config/consolidated/networking.yaml`

```yaml
networking:
  load_balancer:
    type: "metallb"
    ip_pool: "192.168.1.100-192.168.1.110"
```

#### Certificate Management

```bash
# Deploy cert-manager and issuers
python -m homelab_orchestrator certificates deploy

# Check certificate issuer status
kubectl get clusterissuers

# Validate certificates
python -m homelab_orchestrator certificates validate
```

**Features**:

- Let's Encrypt production and staging issuers
- Self-signed certificate fallback
- Automatic certificate renewal
- Wildcard certificate support

#### NGINX Ingress Controller

```bash
# Deploy NGINX ingress
python -m homelab_orchestrator deploy infrastructure --components ingress_nginx

# Check ingress controller status
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

**Features**:

- TLS termination
- HTTP to HTTPS redirect
- Security headers
- Rate limiting

### Application Components

#### Keycloak (Authentication)

```bash
# Deploy Keycloak
python -m homelab_orchestrator deploy infrastructure --components keycloak

# Check deployment status
kubectl get pods -n keycloak
kubectl get ingress -n keycloak
```

**Access**: <https://auth.homelab.local>
**Default Admin**: Admin credentials in `.env` file

#### Monitoring Stack

```bash
# Deploy Prometheus + Grafana
python -m homelab_orchestrator deploy infrastructure --components monitoring

# Access monitoring services
kubectl port-forward -n monitoring svc/grafana 3000:3000
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

**Services**:

- **Prometheus**: <https://prometheus.homelab.local>
- **Grafana**: <https://grafana.homelab.local>
- **AlertManager**: Integrated with Prometheus

#### GitLab DevOps Platform  

```bash
# Deploy GitLab
python -m homelab_orchestrator deploy infrastructure --components gitlab

# Check GitLab status
kubectl get pods -n gitlab
kubectl get pvc -n gitlab  # Check persistent storage
```

**Access**: <https://gitlab.homelab.local>
**Features**: Git repositories, CI/CD, container registry

#### AI/ML Tools

```bash
# Deploy Ollama + OpenWebUI
python -m homelab_orchestrator deploy infrastructure --components ai_tools

# Check AI tools status
kubectl get pods -n ai-ml
```

**Access**: <https://ollama.homelab.local>
**Features**: Local LLM deployment, web interface

#### JupyterLab

```bash  
# Deploy JupyterLab
python -m homelab_orchestrator deploy infrastructure --components jupyter

# Check JupyterLab status
kubectl get pods -n jupyter
```

**Access**: <https://jupyter.homelab.local>
**Features**: Data science environment, notebook server

## Deployment Validation

### Health Checks

```bash
# Overall system health
python -m homelab_orchestrator health check

# Comprehensive health check
python -m homelab_orchestrator health check --comprehensive

# Component-specific health check
python -m homelab_orchestrator health check --component prometheus --component grafana
```

### Certificate Validation

```bash
# Validate all certificates
python -m homelab_orchestrator certificates validate

# Check certificate expiry
python -m homelab_orchestrator certificates check-expiry

# Test specific endpoints
curl -I https://grafana.homelab.local
curl -I https://prometheus.homelab.local
```

### Network Connectivity

```bash
# Test ingress controller
kubectl get svc -n ingress-nginx

# Test external connectivity
curl -I http://homelab.local
curl -I https://homelab.local

# Test internal DNS
kubectl run test-dns --image=busybox --restart=Never -- nslookup kubernetes.default
```

### Storage Validation

```bash
# Check persistent volumes
kubectl get pv,pvc -A

# Check storage classes
kubectl get storageclass

# Test storage provisioning
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

kubectl get pvc test-pvc
kubectl delete pvc test-pvc
```

## Environment-Specific Deployments

### Development Environment

**Configuration**:

- Uses Let's Encrypt staging certificates
- Relaxed security policies
- Smaller resource allocations
- Debug logging enabled

```bash
# Deploy development environment
python -m homelab_orchestrator --environment development deploy infrastructure

# Configuration override
cat config/environments/development.yaml
```

### Staging Environment

**Configuration**:

- Production-like setup
- Let's Encrypt staging certificates  
- Full monitoring and alerting
- Performance testing enabled

```bash
# Deploy staging environment
python -m homelab_orchestrator --environment staging deploy infrastructure

# Validate staging deployment
python -m homelab_orchestrator --environment staging health check --comprehensive
```

### Production Environment

**Configuration**:

- Let's Encrypt production certificates
- Strict security policies
- High availability setup
- Comprehensive monitoring

```bash
# Deploy production environment
python -m homelab_orchestrator --environment production deploy infrastructure

# Production validation
python -m homelab_orchestrator --environment production certificates validate
python -m homelab_orchestrator --environment production health check --comprehensive
```

## Deployment Hooks

The orchestrator supports deployment hooks for custom actions:

### Pre-Deployment Hooks

Executed before deployment starts:

```python
# Example: Pre-deployment validation
async def pre_deployment_validation():
    # Custom validation logic
    return {"status": "success", "message": "Validation passed"}
```

### Post-Deployment Hooks

Executed after successful deployment:

```python
# Example: Post-deployment health check
async def post_deployment_health_check():
    # Custom health check logic
    return {"status": "success", "healthy_services": ["prometheus", "grafana"]}
```

### Failure Hooks

Executed when deployment fails:

```python
# Example: Failure notification
async def failure_notification(error_details):
    # Send notification about deployment failure
    return {"status": "notified", "channels": ["email", "slack"]}
```

## Rollback Procedures

### Automatic Rollback

```bash
# Deploy with automatic rollback on failure
python -m homelab_orchestrator deploy infrastructure --auto-rollback

# Manual rollback to previous state
python -m homelab_orchestrator manage rollback --to-previous
```

### Component Rollback

```bash
# Rollback specific component
kubectl rollout undo deployment/prometheus -n monitoring

# Check rollout status
kubectl rollout status deployment/prometheus -n monitoring
```

### Configuration Rollback

```bash
# Backup current configuration
cp -r config/ config-backup-$(date +%Y%m%d)/

# Restore from backup
rm -rf config/
cp -r config-backup-20250804/ config/

# Redeploy with restored configuration
python -m homelab_orchestrator config validate
python -m homelab_orchestrator deploy infrastructure --dry-run
```

## Backup and Recovery

### Pre-Deployment Backup

```bash
# Create backup before deployment
python -m homelab_orchestrator manage backup

# Backup specific components
python -m homelab_orchestrator manage backup --components prometheus grafana
```

### Recovery Procedures

```bash
# Recover from backup
python -m homelab_orchestrator manage recover

# Recover specific components
python -m homelab_orchestrator manage recover --components monitoring
```

### Data Persistence

```bash
# Check persistent data
kubectl get pvc -A

# Backup persistent volumes
kubectl get pv -o yaml > pv-backup-$(date +%Y%m%d).yaml

# Restore persistent volumes
kubectl apply -f pv-backup-20250804.yaml
```

## Monitoring Deployment

### Deployment Metrics

The orchestrator provides metrics for deployment operations:

```bash
# View deployment metrics
python -m homelab_orchestrator status --format json | jq '.deployment_metrics'

# Monitor deployment progress
python -m homelab_orchestrator deploy infrastructure --monitor
```

### Logging

```bash
# Enable detailed deployment logging
python -m homelab_orchestrator --log-level DEBUG deploy infrastructure

# Check deployment logs
kubectl logs -n homelab-system deployment/orchestrator

# View component-specific logs
kubectl logs -n monitoring deployment/prometheus
```

## Troubleshooting Deployments

### Common Issues

#### Component Dependencies

```bash
# Check dependency order
python -m homelab_orchestrator config show services --key dependencies

# Deploy in correct order
python -m homelab_orchestrator deploy infrastructure --components metallb
python -m homelab_orchestrator deploy infrastructure --components cert_manager
python -m homelab_orchestrator deploy infrastructure --components ingress_nginx
```

#### Resource Constraints

```bash
# Check resource availability
kubectl top nodes
kubectl describe nodes

# Check resource requests
kubectl describe pod <pod-name> -n <namespace>

# Adjust resource limits
kubectl patch deployment <deployment> -n <namespace> --patch='
spec:
  template:
    spec:
      containers:
      - name: <container>
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
'
```

#### Image Pull Issues

```bash
# Check image pull status
kubectl describe pod <pod-name> -n <namespace>

# Check image availability
docker pull <image-name>

# Use different image registry
kubectl patch deployment <deployment> -n <namespace> --patch='
spec:
  template:
    spec:
      containers:
      - name: <container>
        image: quay.io/<image-name>
'
```

### Deployment Debugging

```bash
# Debug deployment issues
python -m homelab_orchestrator --log-level DEBUG deploy infrastructure --components <component>

# Check deployment events
kubectl get events --sort-by=.metadata.creationTimestamp

# Describe problematic resources
kubectl describe deployment <deployment> -n <namespace>
kubectl describe pod <pod> -n <namespace>
kubectl describe service <service> -n <namespace>
```

## Performance Optimization

### Resource Optimization

```bash
# Optimize resource allocation
kubectl patch deployment <deployment> -n <namespace> --patch='
spec:
  template:
    spec:
      containers:
      - name: <container>
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
'
```

### Scaling

```bash
# Scale deployments
kubectl scale deployment <deployment> -n <namespace> --replicas=3

# Horizontal Pod Autoscaling
kubectl autoscale deployment <deployment> -n <namespace> --cpu-percent=50 --min=1 --max=10
```

### Storage Optimization

```bash
# Check storage usage
kubectl exec -it <pod> -n <namespace> -- df -h

# Optimize persistent volume claims
kubectl patch pvc <pvc-name> -n <namespace> --patch='
spec:
  resources:
    requests:
      storage: 10Gi
'
```

## Best Practices

### Deployment Best Practices

1. **Always validate first**: Run `config validate` before deployment
2. **Use dry-run**: Test deployments with `--dry-run` flag
3. **Deploy incrementally**: Deploy components in phases
4. **Monitor health**: Check health after each component
5. **Backup before changes**: Create backups before major deployments

### Security Best Practices

1. **Environment separation**: Use different environments for dev/staging/prod
2. **Certificate validation**: Always validate certificates after deployment
3. **Secret management**: Use environment variables, never hardcode secrets
4. **Network policies**: Implement network segmentation
5. **Resource limits**: Set appropriate resource limits

### Operational Best Practices

1. **Documentation**: Document all deployment customizations
2. **Version control**: Track configuration changes in git
3. **Monitoring**: Set up comprehensive monitoring and alerting
4. **Testing**: Test deployments in development first
5. **Recovery planning**: Have rollback and recovery procedures ready

## Next Steps

- [Health Monitoring](health-monitoring.md) - Monitor your deployment
- [Certificate Management](certificates.md) - Manage TLS certificates
- [Security Guide](security.md) - Secure your deployment
- [Troubleshooting](troubleshooting.md) - Fix deployment issues

---

**🚀 Ready to Deploy**: Your comprehensive deployment guide is complete. Start with development environment testing, then progress to staging and production deployments!
