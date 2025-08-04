# Certificate Management Guide

This guide covers comprehensive certificate management in the Homelab Infrastructure Orchestrator, supporting Let's Encrypt, custom CA, and self-signed certificates.

## Overview

The certificate management system provides:

- **Let's Encrypt Integration**: Automated certificate provisioning via ACME
- **Self-Signed Fallback**: Automatic fallback for development/testing
- **Custom CA Support**: Support for internal certificate authorities
- **Automatic Renewal**: Automated certificate renewal before expiration
- **Health Monitoring**: Continuous monitoring of certificate health
- **Multiple Issuers**: Production, staging, and development certificate sources

## Quick Start

### 1. Deploy cert-manager

```bash
# Deploy cert-manager with all issuers
python -m homelab_orchestrator certificates deploy
```

### 2. Configure Email for Let's Encrypt

Update your `.env` file with a valid email address (required for Let's Encrypt):

```bash
TLS_CERT_EMAIL=admin@yourdomain.com
```

### 3. Validate Certificates

```bash
# Check certificate status and endpoints
python -m homelab_orchestrator certificates validate

# Check certificate expiry dates
python -m homelab_orchestrator certificates check-expiry
```

## Certificate Issuers

### Let's Encrypt (Production)

- **Issuer Name**: `letsencrypt-prod`
- **Server**: <https://acme-v02.api.letsencrypt.org/directory>
- **Rate Limits**: 50 certificates per registered domain per week
- **Validation**: HTTP-01 challenge via NGINX ingress

### Let's Encrypt (Staging)

- **Issuer Name**: `letsencrypt-staging`
- **Server**: <https://acme-staging-v02.api.letsencrypt.org/directory>
- **Rate Limits**: Much higher limits for testing
- **Use Case**: Development and testing environments

### Self-Signed Issuer

- **Issuer Name**: `selfsigned-issuer`
- **Use Case**: Local development, fallback when Let's Encrypt fails
- **CA Generation**: Automatically creates a self-signed CA

### Custom CA Issuer

- **Issuer Name**: `ca-issuer`
- **Use Case**: Internal PKI infrastructure
- **Configuration**: Requires custom CA certificate and key

## Environment Configuration

### Development Environment

```yaml
# Uses Let's Encrypt staging for all certificates
environment: development
certificates:
  issuers:
    letsencrypt_prod:
      enabled: false
    letsencrypt_staging:
      enabled: true
```

### Staging Environment

```yaml
# Uses Let's Encrypt staging for validation
environment: staging
certificates:
  issuers:
    letsencrypt_staging:
      enabled: true
```

### Production Environment

```yaml
# Uses Let's Encrypt production
environment: production
certificates:
  issuers:
    letsencrypt_prod:
      enabled: true
    letsencrypt_staging:
      enabled: false
```

## Certificate Requests

### Wildcard Certificate

Automatically requested for `*.homelab.local`:

```yaml
wildcard_homelab:
  enabled: true
  issuer: "letsencrypt_prod"
  fallback_issuer: "selfsigned"
  secret_name: "homelab-wildcard-tls"
  dns_names:
    - "homelab.local"
    - "*.homelab.local"
```

### Service-Specific Certificates

Individual certificates for each service:

```yaml
grafana:
  enabled: true
  issuer: "letsencrypt_prod"  
  fallback_issuer: "selfsigned"
  secret_name: "grafana-tls"
  dns_names:
    - "grafana.homelab.local"
```

## CLI Commands

### Deploy cert-manager

```bash
# Deploy cert-manager and all configured issuers
python -m homelab_orchestrator certificates deploy
```

### Validate Certificates

```bash
# Validate all HTTPS endpoints
python -m homelab_orchestrator certificates validate

# JSON output for automation
python -m homelab_orchestrator certificates validate --format json
```

### Check Certificate Expiry

```bash
# Check all certificate expiry dates
python -m homelab_orchestrator certificates check-expiry

# JSON output for monitoring integration
python -m homelab_orchestrator certificates check-expiry --format json
```

### Force Certificate Renewal

```bash
# Renew specific certificate
python -m homelab_orchestrator certificates renew homelab-wildcard-tls

# Renew certificate in specific namespace
python -m homelab_orchestrator certificates renew grafana-tls --namespace monitoring
```

## Manual Certificate Operations

### Check cert-manager Status

```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Check certificate status
kubectl get certificates -A

# Check certificate requests
kubectl get certificaterequests -A

# Check ACME orders and challenges
kubectl get orders,challenges -A
```

### Troubleshooting Certificate Issues

```bash
# Describe certificate for detailed status
kubectl describe certificate homelab-wildcard-tls

# Check issuer status
kubectl describe clusterissuer letsencrypt-prod

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

## Configuration Files

### Certificate Configuration

Primary configuration: `config/consolidated/certificates.yaml`

```yaml
certificates:
  issuers:
    letsencrypt_prod:
      enabled: true
      type: "letsencrypt"
      server: "https://acme-v02.api.letsencrypt.org/directory"
      email: "${TLS_CERT_EMAIL}"
      solver:
        type: "http01"
        ingress_class: "nginx"
```

### Environment Variables

Required environment variables in `.env`:

```bash
# Required for Let's Encrypt
TLS_CERT_EMAIL=admin@yourdomain.com

# Optional: Custom ACME server
ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory

# Optional: Webhook for certificate expiry notifications
CERT_EXPIRY_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: Custom CA (for internal PKI)
CUSTOM_CA_CERT=
CUSTOM_CA_KEY=
```

## Monitoring and Alerting

### Certificate Expiry Monitoring

The system automatically monitors certificate expiry and can send alerts:

```yaml
validation:
  monitoring:
    enabled: true
    prometheus_metrics: true
    alert_days_before_expiry: [14, 7, 3, 1]
    webhook_url: "${CERT_EXPIRY_WEBHOOK_URL}"
```

### Prometheus Metrics

cert-manager exposes metrics at `/metrics` endpoint:

- `certmanager_certificate_expiration_timestamp_seconds`
- `certmanager_certificate_ready_status`
- `certmanager_acme_client_request_count`

### Health Checks

Continuous validation of certificate endpoints:

```yaml
health_checks:
  enabled: true
  check_interval: "24h"
  endpoints:
    - "https://grafana.homelab.local/api/health"
    - "https://prometheus.homelab.local/-/healthy"
    - "https://auth.homelab.local/auth/health"
```

## Security Considerations

### Let's Encrypt Rate Limits

- **Certificates per Registered Domain**: 50 per week
- **Duplicate Certificate**: 5 per week
- **Failed Validation**: 5 failures per account per hostname per hour

### Best Practices

1. **Use Staging First**: Always test with staging environment
2. **Monitor Expiry**: Set up alerts for certificate expiration
3. **Backup Certificates**: Store certificates securely
4. **Rotate Regularly**: Use automated renewal
5. **Validate Endpoints**: Regularly check HTTPS endpoints

### Fallback Strategy

The system implements automatic fallback:

1. **Primary**: Let's Encrypt (production/staging)
2. **Fallback**: Self-signed certificates
3. **Manual Override**: Custom CA certificates

## Troubleshooting

### Common Issues

#### Let's Encrypt Challenge Failures

```bash
# Check ingress controller status
kubectl get ingress -A

# Verify DNS resolution
nslookup grafana.homelab.local

# Check cert-manager webhook
kubectl get validatingwebhookconfigurations cert-manager-webhook
```

#### Certificate Not Ready

```bash
# Check certificate status
kubectl describe certificate homelab-wildcard-tls

# Check order status
kubectl describe order <order-name>

# Check challenge status
kubectl describe challenge <challenge-name>
```

#### Rate Limit Exceeded

Switch to staging issuer temporarily:

```bash
# Update certificate to use staging
kubectl patch certificate homelab-wildcard-tls \
  --type='merge' \
  --patch='{"spec":{"issuerRef":{"name":"letsencrypt-staging"}}}'
```

## Integration Examples

### Grafana with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - grafana.homelab.local
    secretName: grafana-tls
  rules:
  - host: grafana.homelab.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
```

### Automatic Certificate with Fallback

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: service-tls
spec:
  secretName: service-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  # Automatic fallback to self-signed if Let's Encrypt fails
  dnsNames:
  - service.homelab.local
```

## Support

For certificate-related issues:

1. Check cert-manager logs: `kubectl logs -n cert-manager deployment/cert-manager`
2. Validate configuration: `python -m homelab_orchestrator config validate`
3. Test certificate endpoints: `python -m homelab_orchestrator certificates validate`
4. Review Let's Encrypt documentation: <https://letsencrypt.org/docs/>

---

**Note**: This certificate management system is designed for homelab environments. For production use, consider additional security measures and monitoring solutions.
