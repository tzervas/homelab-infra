# Security Guide

Comprehensive security guide for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## Security Overview

The orchestrator implements security-first principles:

- **No hardcoded secrets** in configuration files
- **Environment variable-based** secret management
- **Automated certificate management** with Let's Encrypt
- **Pod Security Standards** enforcement
- **Network policies** for traffic control
- **Regular security scanning** in CI/CD

## 🔐 Secret Management

### Automated Secret Generation

Use the provided script to generate all required secrets:

```bash
# Generate secure secrets automatically
./scripts/security/generate-secrets.sh

# This creates a .env file with:
# - OAuth2 client secrets (base64 encoded)
# - Cookie encryption keys (32-byte random)
# - Database passwords
# - TLS certificate email
# - Backup encryption keys
```

### Manual Secret Generation

If you need to generate secrets manually:

```bash
# OAuth2 client secret (base64 encoded)
openssl rand -base64 24

# Cookie encryption secret (32-byte, base64 encoded)
openssl rand -base64 32

# Database password
openssl rand -base64 16 | tr -d "=+/" | cut -c1-16

# API keys
openssl rand -hex 32
```

### Secret Storage Security

```bash
# Secure the .env file
chmod 600 .env
chown $USER:$USER .env

# Verify no secrets in version control
git status --ignored | grep .env

# Create secure backup
cp .env .env.backup-$(date +%Y%m%d)
chmod 600 .env.backup-*
```

### Environment Variable Security

Required security-related environment variables:

```bash
# OAuth2 Authentication
OAUTH2_CLIENT_SECRET=<base64-encoded-random-secret>
OAUTH2_COOKIE_SECRET=<base64-encoded-32-byte-key>
PROMETHEUS_OAUTH2_CLIENT_SECRET=<base64-encoded-secret>
PROMETHEUS_OAUTH2_COOKIE_SECRET=<base64-encoded-32-byte-key>

# TLS/SSL Configuration
TLS_CERT_EMAIL=admin@yourdomain.com  # Required for Let's Encrypt

# Application Passwords
GRAFANA_ADMIN_PASSWORD=<secure-password>

# Storage Encryption
LONGHORN_BACKUP_SECRET=<encryption-key>
```

## 🛡️ Pod Security Standards

### Security Context Configuration

The orchestrator enforces Pod Security Standards:

```yaml
# config/consolidated/security.yaml
security:
  pod_security_standards:
    # Strict security for default namespace
    default: "restricted"
    
    # Baseline for monitoring tools
    monitoring: "baseline"
    
    # Privileged only for system components
    kube-system: "privileged"
    metallb-system: "privileged"
```

### Security Policies

```yaml
security:
  policies:
    # Require security contexts
    require_security_context: true
    
    # Disallow privilege escalation
    disallow_privilege_escalation: true
    
    # Require non-root user
    run_as_non_root: true
    
    # Disallow privileged containers
    disallow_privileged: true
    
    # Require read-only root filesystem
    read_only_root_filesystem: true
```

### Application Security Contexts

```yaml
# Example secure deployment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534  # nobody user
        fsGroup: 65534
      containers:
      - name: app
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
            - ALL
```

## 🔒 Network Security

### Network Policies

Enable network policies for traffic control:

```yaml
# config/consolidated/security.yaml
security:
  network_policies:
    enabled: true
    default_deny: true  # Deny all traffic by default
    
    policies:
      # Allow ingress controller to reach services
      - name: "allow-ingress"
        namespace: "default"
        spec:
          podSelector: {}
          ingress:
          - from:
            - namespaceSelector:
                matchLabels:
                  name: "ingress-nginx"
```

### TLS Everywhere

All services use TLS encryption:

```yaml
services:
  tls:
    # Require TLS for all services
    enforce_tls: true
    
    # Minimum TLS version
    min_tls_version: "1.2"
    
    # Strong cipher suites only
    cipher_suites:
      - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
      - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
```

### Ingress Security

```yaml
# NGINX ingress with security headers
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Strict-Transport-Security: max-age=31536000";
```

## 📜 Certificate Security

### Let's Encrypt Integration

Automated certificate management with security best practices:

```yaml
certificates:
  issuers:
    letsencrypt_prod:
      enabled: true
      # Use production only after testing
      server: "https://acme-v02.api.letsencrypt.org/directory"
      
    letsencrypt_staging:
      enabled: true  # For testing
      server: "https://acme-staging-v02.api.letsencrypt.org/directory"
```

### Certificate Security Features

- **Automatic renewal**: 30 days before expiration
- **Strong key sizes**: RSA 4096-bit or ECDSA P-256
- **HSTS headers**: Force HTTPS connections
- **Certificate transparency**: All certificates logged

### Certificate Monitoring

```bash
# Check certificate expiry
python -m homelab_orchestrator certificates check-expiry

# Monitor certificate health
python -m homelab_orchestrator certificates validate

# Set up alerts for expiring certificates
CERT_EXPIRY_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 🔍 Security Scanning

### Automated Security Scanning

The CI/CD pipeline includes:

```yaml
# .github/workflows/ci-cd.yaml
- name: Security scan - Python dependencies
  run: |
    safety check --json --output safety-report.json
    bandit -r homelab_orchestrator/ scripts/ -f json -o bandit-report.json

- name: Container image scanning
  run: |
    # Scan container images for vulnerabilities
    trivy image --format json --output trivy-report.json nginx:latest
```

### Manual Security Scanning

```bash
# Scan for secrets in code
gitleaks detect --no-git --verbose

# Scan Python code for security issues
bandit -r homelab_orchestrator/ scripts/

# Check dependencies for vulnerabilities
safety check

# Scan container images
trivy image nginx:latest
```

### Security Baseline Validation

```bash
# Run security validation
python -m homelab_orchestrator config validate --security-check

# Check Pod Security Standards compliance
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.securityContext}{"\n"}{end}'
```

## 🛠️ Secure Configuration

### Kubernetes RBAC

```yaml
# Service account with minimal permissions
apiVersion: v1
kind: ServiceAccount
metadata:
  name: homelab-service
  namespace: default

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: homelab-role
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: homelab-binding
subjects:
- kind: ServiceAccount
  name: homelab-service
roleRef:
  kind: Role
  name: homelab-role
  apiGroup: rbac.authorization.k8s.io
```

### Secure Defaults

```yaml
# config/consolidated/security.yaml
security:
  defaults:
    # Always use security contexts
    security_context_required: true
    
    # Drop all capabilities by default
    default_capabilities: []
    
    # Use non-root user
    run_as_non_root: true
    
    # Read-only root filesystem
    read_only_root_filesystem: true
    
    # No privilege escalation
    allow_privilege_escalation: false
```

## 🔒 OAuth2 and SSO Security

### Keycloak Security Configuration

```yaml
keycloak:
  security:
    # Password policy
    password_policy:
      min_length: 12
      require_uppercase: true
      require_lowercase: true
      require_digits: true
      require_special_chars: true
    
    # Session security
    session:
      timeout: 3600  # 1 hour
      remember_me: false
      secure_cookies: true
    
    # TLS configuration
    tls:
      min_version: "TLSv1.2"
      protocols: ["TLSv1.2", "TLSv1.3"]
```

### OAuth2 Proxy Security

```yaml
oauth2_proxy:
  security:
    # Cookie settings
    cookie:
      secure: true
      http_only: true
      same_site: "strict"
      
    # Session encryption
    session:
      encryption_key: "${OAUTH2_COOKIE_SECRET}"
      
    # Upstream validation
    validate_upstream: true
```

## 🔐 Backup Security

### Encrypted Backups

```yaml
storage:
  backup:
    encryption:
      enabled: true
      key: "${LONGHORN_BACKUP_SECRET}"
      algorithm: "AES-256-GCM"
    
    # Secure backup targets
    targets:
      s3:
        endpoint: "s3.amazonaws.com"
        bucket: "homelab-backups"
        encryption: "SSE-S3"
```

### Backup Validation

```bash
# Test backup encryption
python -c "
import os
key = os.environ.get('LONGHORN_BACKUP_SECRET')
print(f'Backup key length: {len(key)} bytes')
print(f'Key entropy: OK' if len(set(key)) > 10 else 'WEAK')
"

# Verify backup integrity
longhorn backup list --verify-checksum
```

## 🚨 Security Monitoring

### Log Security Events

```yaml
logging:
  security_events:
    enabled: true
    events:
      - authentication_failures
      - privilege_escalation_attempts
      - network_policy_violations
      - certificate_validation_failures
    
    destinations:
      - type: "file"
        path: "/var/log/security.log"
      - type: "webhook"
        url: "${SECURITY_WEBHOOK_URL}"
```

### Alerting

```bash
# Set up security alerts
SECURITY_WEBHOOK_URL=https://hooks.slack.com/services/...

# Monitor certificate expiry
python -m homelab_orchestrator certificates check-expiry --alert-days 7

# Monitor failed authentication attempts
kubectl logs -n keycloak -l app=keycloak | grep "Login error"
```

## 🔧 Security Hardening

### System Hardening

```bash
# Disable unnecessary services
sudo systemctl disable cups bluetooth

# Configure firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 6443/tcp  # Kubernetes API

# Secure SSH configuration
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### Kubernetes Hardening

```bash
# Enable audit logging
sudo mkdir -p /var/log/kubernetes/audit/
sudo tee /etc/rancher/k3s/audit-policy.yaml << EOF
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets", "configmaps"]
EOF

# Restart K3s with audit logging
sudo systemctl restart k3s
```

## 🔍 Security Validation

### Security Checklist

Use this checklist to validate your security configuration:

```bash
# 1. No hardcoded secrets
gitleaks detect --no-git

# 2. Secure file permissions
ls -la .env  # Should be 600
ls -la scripts/security/  # Scripts should be executable

# 3. Valid certificates
python -m homelab_orchestrator certificates validate

# 4. Pod security standards
kubectl get podsecuritypolicy

# 5. Network policies active
kubectl get networkpolicy -A

# 6. RBAC configured
kubectl get rolebindings,clusterrolebindings -A

# 7. Security contexts enforced
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.securityContext.runAsNonRoot}{"\n"}{end}'
```

### Penetration Testing

```bash
# Network scanning (authorized testing only)
nmap -sS -O localhost

# Web application testing
nikto -h https://grafana.homelab.local

# TLS/SSL testing
testssl.sh https://grafana.homelab.local
```

## 📋 Security Best Practices

### Development

1. **Never commit secrets**: Use `.gitignore` and pre-commit hooks
2. **Use staging certificates**: Test with Let's Encrypt staging
3. **Regular dependency updates**: `pip install --upgrade -r requirements.txt`
4. **Security scanning**: Run `bandit` and `safety` regularly

### Production

1. **Production certificates**: Use Let's Encrypt production issuer
2. **Strong passwords**: Use generated passwords, no defaults
3. **Network segmentation**: Use network policies and firewalls
4. **Regular backups**: Encrypt and test backup restoration
5. **Monitoring**: Set up security event monitoring and alerting

### Incident Response

1. **Immediate actions**:
   ```bash
   # Isolate compromised pod
   kubectl delete pod <compromised-pod>
   
   # Check for unauthorized access
   kubectl logs -n kube-system kube-apiserver
   
   # Rotate secrets if compromised
   ./scripts/security/generate-secrets.sh
   kubectl rollout restart deployment/<affected-deployment>
   ```

2. **Investigation**: Check logs, network traffic, and system events
3. **Recovery**: Restore from secure backups, patch vulnerabilities
4. **Prevention**: Update security policies, add monitoring

## 🆘 Security Incident Response

### Compromise Detection

```bash
# Check for suspicious activity
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20

# Review authentication logs
kubectl logs -n keycloak deployment/keycloak | grep -i "failed\|error\|unauthorized"

# Check for privilege escalation
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.securityContext.privileged}{"\n"}{end}' | grep -v "false\|null"
```

### Emergency Procedures

```bash
# 1. Isolate affected systems
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets

# 2. Rotate all secrets
rm .env
./scripts/security/generate-secrets.sh

# 3. Update affected deployments
kubectl rollout restart deployment -n <namespace>

# 4. Force certificate renewal
python -m homelab_orchestrator certificates renew --all

# 5. Review and update security policies
python -m homelab_orchestrator config validate --security-audit
```

## 📞 Security Support

- **Security Issues**: Report privately to security@yourdomain.com
- **Vulnerability Reports**: Follow responsible disclosure
- **Security Updates**: Monitor [GitHub Security Advisories](https://github.com/tzervas/homelab-infra/security/advisories)

---

**🔐 Remember**: Security is a continuous process. Regularly review and update your security configuration, monitor for threats, and keep all components up to date.