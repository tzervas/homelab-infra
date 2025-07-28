# Enhanced Helm-based Deployment Architecture

This directory contains a comprehensive, security-first Helm deployment architecture for homelab infrastructure. The implementation focuses on security baseline policies, standardized templates, and automated deployment hooks.

## 🏗️ Architecture Overview

The enhanced architecture implements:

- **Security Baseline Chart**: Standardized security policies and templates
- **Enhanced Helmfile**: Comprehensive templating with pre/post deployment hooks
- **Automated Validation**: Pre-deployment validation and post-deployment health checks
- **Certificate Management**: Automated certificate rotation and TLS management
- **Network Security**: Default-deny network policies with controlled access
- **RBAC Integration**: Role-based access control with minimal privileges

## 📁 Directory Structure

```
helm/
├── helmfile.yaml                 # Enhanced deployment orchestration
├── repositories.yaml             # Helm repository definitions
│
├── charts/
│   ├── security-baseline/        # 🔒 Security policies and templates
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── templates/
│   │   │   ├── _helpers.tpl      # Security template helpers
│   │   │   ├── network-policies.yaml
│   │   │   ├── rbac.yaml
│   │   │   └── hooks/            # Deployment hooks
│   │   │       ├── pre-deployment-validation.yaml
│   │   │       ├── post-deployment-health.yaml
│   │   │       └── cert-rotation.yaml
│   │   
│   ├── core-infrastructure/      # Core K8s components
│   ├── monitoring/               # Observability stack
│   └── storage/                  # Storage solutions
│
├── environments/
│   ├── values-dev.yaml           # Development configuration
│   ├── values-staging.yaml       # Staging configuration
│   ├── values-prod.yaml          # Production configuration
│   ├── secrets-dev.yaml.template # Secret templates
│   └── secrets-prod.yaml.template
│
└── README.md                     # This file
```

## 🔒 Security Baseline Features

### Pod Security Standards
- **Baseline enforcement** for most workloads
- **Restricted enforcement** for sensitive components
- **Privileged exceptions** only for system components that require it

### Security Context Templates
```yaml
# Restricted (most secure)
securityContexts.restricted:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]

# Baseline (moderate security)
securityContexts.baseline:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]

# Networking (for ingress controllers)
securityContexts.networking:
  runAsNonRoot: false
  runAsUser: 101
  runAsGroup: 101
  capabilities:
    drop: [ALL]
    add: [NET_BIND_SERVICE, CHOWN, SETGID, SETUID]
```

### Network Policies
- **Default Deny**: All ingress/egress traffic blocked by default
- **DNS Allow**: Permit DNS resolution
- **Kube API Allow**: Access to Kubernetes API server
- **Custom Policies**: Application-specific network rules

### RBAC Configuration
- **Service Accounts**: Dedicated accounts with minimal privileges
- **Role-based Access**: Granular permissions per component
- **No Token Automount**: Security-first approach to service account tokens

## 🚀 Deployment Hooks

### Pre-deployment Validation
Runs before each deployment to verify:
- Kubernetes cluster connectivity
- Required CRDs existence
- Network policy support
- Storage class availability
- Pod Security Standards compliance
- Environment-specific requirements

### Post-deployment Health Checks
Validates after deployment:
- Pod security contexts
- Network policy enforcement
- RBAC configuration
- Resource limits/requests
- TLS certificate validity
- Monitoring endpoints

### Certificate Rotation
Automated certificate management:
- **Daily checks** at 2 AM for certificate expiry
- **30-day threshold** for automatic rotation
- **Atomic replacement** with zero-downtime
- **Dependent pod restart** after certificate updates
- **Backup and rollback** capabilities

## 🌍 Environment Configuration

### Development
```yaml
podSecurityStandards:
  enforce: "baseline"
  audit: "restricted" 
  warn: "restricted"

resources:
  limits:
    cpu: "1000m"
    memory: "2Gi"
  requests:
    cpu: "100m"
    memory: "128Mi"
```

### Production
```yaml
podSecurityStandards:
  enforce: "restricted"
  audit: "restricted"
  warn: "restricted"

resources:
  limits:
    cpu: "4000m"
    memory: "8Gi"
  requests:
    cpu: "500m"
    memory: "512Mi"
```

## 📋 Usage Guide

### Initial Setup

1. **Copy secret templates**:
```bash
cp environments/secrets-dev.yaml.template environments/secrets-dev.yaml
cp environments/secrets-prod.yaml.template environments/secrets-prod.yaml
```

2. **Populate secrets** (use sealed-secrets for production):
```bash
# Development (basic secrets)
vi environments/secrets-dev.yaml

# Production (use sealed-secrets)
kubectl create secret generic app-secret \
  --from-literal=password=STRONG_PASSWORD \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml
```

3. **Validate configuration**:
```bash
helmfile -e development lint
helmfile -e production lint
```

### Deployment

#### Development Environment
```bash
# Deploy with validation hooks
helmfile -e development sync

# Check deployment status
helmfile -e development status

# View deployment logs
helmfile -e development logs
```

#### Production Environment
```bash
# Plan deployment (dry-run)
helmfile -e production diff

# Deploy with all safety checks
helmfile -e production sync

# Verify security compliance
kubectl get networkpolicies -A
kubectl get podsecuritypolicies -A
```

### Monitoring and Maintenance

#### Certificate Management
```bash
# Check certificate expiry
kubectl get certificates -A
kubectl describe certificate tls-secret -n default

# Manual certificate rotation
kubectl create job --from=cronjob/security-baseline-cert-rotation \
  manual-cert-rotation -n security-system
```

#### Security Validation
```bash
# Run security baseline validation
kubectl create job --from=cronjob/security-baseline-pre-validation \
  manual-validation -n security-system

# Check pod security compliance
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'
```

#### Network Policy Testing
```bash
# List all network policies
kubectl get networkpolicies -A

# Test network connectivity
kubectl run test-pod --image=nicolaka/netshoot -it --rm -- /bin/bash
```

## 🔧 Template Functions

The security baseline provides helper templates for consistent configuration:

### Security Contexts
```yaml
# Use in your templates
securityContext:
  {{- include "security-baseline.securityContext.restricted" . | nindent 2 }}

# Or baseline/networking/privileged variants
securityContext:
  {{- include "security-baseline.securityContext.baseline" . | nindent 2 }}
```

### Resource Limits
```yaml
resources:
  {{- include "security-baseline.resources" (dict "Values" .Values "profile" "standard") | nindent 2 }}

# Available profiles: minimal, standard, high
```

### Health Checks
```yaml
livenessProbe:
  {{- include "security-baseline.livenessProbe" . | nindent 2 }}

readinessProbe:
  {{- include "security-baseline.readinessProbe" . | nindent 2 }}
```

## 🚨 Security Best Practices

### Secret Management
- **Never commit secrets** to version control
- **Use sealed-secrets** or external secret operators in production
- **Rotate secrets regularly** (automated via hooks)
- **Minimal secret scope** (namespace-level when possible)

### Network Security
- **Default deny policies** for all namespaces
- **Explicit allow rules** only for required communication
- **Regular policy audits** via monitoring hooks
- **Egress filtering** to external services

### Container Security
- **Non-root containers** wherever possible
- **Read-only root filesystems** for enhanced security
- **Dropped capabilities** (ALL by default)
- **Resource limits** to prevent resource exhaustion

### RBAC
- **Principle of least privilege** for all service accounts
- **No wildcard permissions** in production
- **Regular access reviews** via automation hooks
- **Service account token restrictions**

## 🔍 Troubleshooting

### Common Issues

1. **Pod Security Policy Violations**:
```bash
kubectl get events --field-selector reason=FailedCreate
kubectl describe pod <failing-pod>
```

2. **Network Policy Blocking Traffic**:
```bash
kubectl get networkpolicies -n <namespace>
kubectl describe networkpolicy <policy-name> -n <namespace>
```

3. **Certificate Issues**:
```bash
kubectl get certificates -A
kubectl describe certificate <cert-name> -n <namespace>
kubectl logs -n cert-manager deployment/cert-manager
```

4. **RBAC Permission Denied**:
```bash
kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<namespace>:<sa-name>
kubectl describe role <role-name> -n <namespace>
```

### Debug Mode
Enable debug logging for troubleshooting:
```bash
HELM_DEBUG=true helmfile -e development sync
```

## 📚 References

- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Cert-Manager Documentation](https://cert-manager.io/docs/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Helmfile Documentation](https://helmfile.readthedocs.io/)

## 🤝 Contributing

When contributing to the Helm charts:

1. **Follow security baselines** - inherit from security-baseline chart
2. **Add appropriate hooks** - include validation and health checks
3. **Document security contexts** - explain any privilege requirements
4. **Test thoroughly** - validate in development environment first
5. **Update this README** - document new features and configurations

## 📄 License

This project is licensed under the MIT License - see the main repository LICENSE file for details.
