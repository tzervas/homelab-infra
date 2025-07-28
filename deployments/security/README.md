# Comprehensive Security Layer

This directory contains comprehensive security configurations and policies for the homelab infrastructure, implementing defense-in-depth security principles.

## Overview

The security layer provides:

- **TLS Certificate Management**: Automated certificate lifecycle management with cert-manager
- **mTLS Configuration**: Service-to-service mutual TLS authentication
- **Network Policy Templates**: Reusable network security policies
- **Secret Rotation Mechanisms**: Automated secret rotation and management
- **Sealed Secrets Patterns**: Secure secret storage and distribution
- **Security Validation Scripts**: Automated security compliance checking

## Architecture

```
deployments/security/
├── README.md                           # This documentation
├── tls-certificate-management.yaml    # Certificate management workflows
├── mtls-configuration.yaml           # mTLS service mesh configuration
├── network-policy-templates.yaml     # Network security policy templates
├── secret-rotation-mechanisms.yaml   # Automated secret rotation
└── sealed-secrets-patterns.yaml      # Sealed secrets templates
```

## Components

### 1. TLS Certificate Management

**File**: `tls-certificate-management.yaml`

Implements comprehensive certificate lifecycle management:

- **Let's Encrypt Integration**: Automated public certificate provisioning
- **Internal CA Hierarchy**: Root and intermediate CAs for internal services
- **Certificate Templates**: Reusable certificate configurations
- **Rotation Policies**: Automated certificate renewal and rotation

**Key Features**:
- ECDSA P-256 keys for performance and security
- Automated renewal 30 days before expiry
- Backup and monitoring integration
- Multi-tier CA structure for security isolation

### 2. mTLS Configuration

**File**: `mtls-configuration.yaml`

Configures mutual TLS for service-to-service communication:

- **Istio Integration**: Service mesh mTLS policies
- **Certificate Provisioning**: Automated service certificate management
- **Policy Enforcement**: Strict, permissive, and disabled modes
- **Security Enhancement**: EnvoyFilters for advanced TLS configuration

**Security Levels**:
- **Strict**: mTLS required for all communication
- **Permissive**: mTLS preferred but not required
- **Disabled**: No mTLS enforcement (development only)

### 3. Network Policy Templates

**File**: `network-policy-templates.yaml`

Provides reusable network security policies:

- **Default Deny**: Deny-all baseline security posture
- **Service-Specific**: Tailored policies for GitLab, Keycloak, monitoring
- **Environment-Based**: Development vs production policy templates
- **Cross-Namespace**: Controlled inter-namespace communication

**Policy Types**:
- DNS resolution policies
- Web application ingress policies
- Database access policies
- Monitoring access policies
- Service mesh sidecar policies

### 4. Secret Rotation Mechanisms

**File**: `secret-rotation-mechanisms.yaml`

Automated secret lifecycle management:

- **Rotation Schedules**: Configurable rotation intervals by secret type
- **Template Scripts**: Database, API key, and SSH key rotation
- **Backup Integration**: Encrypted secret backups with retention
- **Monitoring**: Certificate expiry and rotation failure alerts

**Rotation Intervals**:
- Certificates: 30 days
- Database passwords: 30 days
- API keys: 90 days
- SSH keys: 365 days
- Admin tokens: 7 days

### 5. Sealed Secrets Patterns

**File**: `sealed-secrets-patterns.yaml`

Secure secret distribution using Bitnami Sealed Secrets:

- **Controller Configuration**: Enhanced sealed secrets controller
- **Secret Templates**: Pre-configured sealed secret patterns
- **Backup Strategies**: Automated key backup and rotation
- **Usage Guidelines**: Best practices and troubleshooting

**Secret Scopes**:
- **Strict**: Same name and namespace only
- **Namespace-wide**: Any name within namespace
- **Cluster-wide**: Any name in any namespace

## Security Validation Scripts

Located in `scripts/security/`, these Python scripts provide automated security validation:

### Certificate Expiry Monitoring

**Script**: `certificate-expiry-monitoring.py`

Monitors certificate expiration across:
- Kubernetes cert-manager certificates
- File system certificates
- Remote endpoint certificates

**Features**:
- Email and webhook alerts
- Configurable warning thresholds
- HTML email reports
- Prometheus metrics integration

### TLS Configuration Validation

**Script**: `tls-configuration-validation.py`

Validates TLS configurations for:
- Kubernetes ingresses and services
- External endpoints
- Security headers and policies

**Checks**:
- TLS version compliance (minimum TLSv1.2)
- Cipher suite security
- Forward secrecy support
- Certificate validation
- Common vulnerability scanning

### Security Policy Compliance

**Script**: `security-policy-compliance-checks.py`

Validates security policy compliance:
- Configurable policy definitions
- Automated compliance checking
- Detailed compliance reporting
- Integration with monitoring

## Deployment

### Prerequisites

1. **cert-manager**: Install cert-manager in the cluster
2. **Sealed Secrets Controller**: Deploy sealed secrets controller
3. **Network Policies**: Ensure CNI supports network policies
4. **Monitoring**: Prometheus for metrics collection

### Installation Steps

1. **Deploy Certificate Management**:
   ```bash
   kubectl apply -f deployments/security/tls-certificate-management.yaml
   ```

2. **Configure mTLS** (if using Istio):
   ```bash
   kubectl apply -f deployments/security/mtls-configuration.yaml
   ```

3. **Apply Network Policies**:
   ```bash
   kubectl apply -f deployments/security/network-policy-templates.yaml
   ```

4. **Setup Secret Rotation**:
   ```bash
   kubectl apply -f deployments/security/secret-rotation-mechanisms.yaml
   ```

5. **Deploy Sealed Secrets**:
   ```bash
   kubectl apply -f deployments/security/sealed-secrets-patterns.yaml
   ```

### Configuration

#### Certificate Management

Configure Let's Encrypt email and domains:

```yaml
# In tls-certificate-management.yaml
email: tz-dev@vectorweight.com
dnsNames:
  - "homelab.local"
  - "*.homelab.local"
  - "*.apps.homelab.local"
```

#### Network Policies

Customize network policies for your environment:

```yaml
# Add custom policies to network-policy-templates.yaml
spec:
  podSelector:
    matchLabels:
      app: your-app
  policyTypes:
  - Ingress
  - Egress
```

#### Secret Rotation

Configure rotation intervals and notification:

```yaml
# In secret-rotation-mechanisms.yaml
rotation:
  intervals:
    certificates: "30d"
    api_keys: "90d"
  notifications:
    email: "tz-dev@vectorweight.com"
```

## Monitoring and Alerting

### Metrics

The security layer exposes metrics for:
- Certificate expiry dates
- Secret rotation status
- Network policy violations
- TLS configuration compliance

### Alerts

Configure alerts in Prometheus for:
- Certificates expiring within 30 days
- Failed secret rotations
- TLS configuration non-compliance
- Network policy violations

### Dashboards

Grafana dashboards for:
- Certificate lifecycle monitoring
- Security policy compliance
- Network traffic analysis
- Secret rotation status

## Security Best Practices

### Certificate Management

1. **Use ECDSA keys** for better performance
2. **Implement certificate pinning** for critical services
3. **Monitor certificate transparency logs**
4. **Automate certificate renewal** to prevent outages

### Network Security

1. **Default deny-all policies** as baseline
2. **Principle of least privilege** for network access
3. **Regular policy audits** and updates
4. **Monitor network traffic** for anomalies

### Secret Management

1. **Regular secret rotation** based on sensitivity
2. **Encrypted secret storage** using sealed secrets
3. **Access logging** for secret usage
4. **Backup and recovery** procedures

### mTLS Implementation

1. **Start with permissive mode** for gradual rollout
2. **Monitor service dependencies** before enforcing strict mode
3. **Certificate lifecycle automation** for service certificates
4. **Performance monitoring** for mTLS overhead

## Troubleshooting

### Common Issues

1. **Certificate Renewal Failures**:
   - Check cert-manager logs
   - Verify DNS/HTTP challenge configuration
   - Ensure RBAC permissions

2. **Network Policy Blocking Traffic**:
   - Use `kubectl describe networkpolicy`
   - Check pod labels and selectors
   - Verify namespace labels

3. **Sealed Secrets Decryption Issues**:
   - Verify controller key validity
   - Check secret scope configuration
   - Ensure correct namespace

4. **mTLS Connection Failures**:
   - Verify certificate validity
   - Check Istio sidecar injection
   - Review destination rules

### Debugging Commands

```bash
# Check certificate status
kubectl get certificates -A
kubectl describe certificate <name> -n <namespace>

# Verify network policies
kubectl get networkpolicies -A
kubectl describe networkpolicy <name> -n <namespace>

# Check sealed secrets
kubectl get sealedsecrets -A
kubectl logs -n kube-system -l app.kubernetes.io/name=sealed-secrets

# Validate mTLS configuration
istioctl proxy-config cluster <pod-name> -n <namespace>
istioctl authn tls-check <pod-name>.<namespace>
```

## Contributing

When adding new security configurations:

1. **Follow the principle of least privilege**
2. **Document all security decisions**
3. **Test in development environment first**
4. **Update monitoring and alerting**
5. **Review with security team**

## Security Contacts

- **Security Team**: tz-dev@vectorweight.com
- **Incident Response**: Available 24/7
- **Vulnerability Reports**: Follow responsible disclosure

## Compliance

This security layer helps achieve compliance with:

- **CIS Kubernetes Benchmark**
- **NIST Cybersecurity Framework**
- **OWASP Security Guidelines**
- **Industry-specific requirements**

## Regular Reviews

Security configurations should be reviewed:

- **Monthly**: Certificate expiry and rotation
- **Quarterly**: Network policy effectiveness
- **Bi-annually**: Overall security posture
- **Annually**: Compliance audit and certification

---

**Note**: This security layer is designed for homelab environments. For production deployments, additional security measures may be required based on specific compliance and regulatory requirements.
