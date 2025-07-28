# TLS/mTLS Security Guide

**Version:** 2.0  
**Date:** December 2024  
**Author:** Security Team  

## Overview

This guide provides detailed implementation steps for TLS and mTLS within the homelab infrastructure. Security is enhanced by using Let's Encrypt certificates for external services and a custom CA for internal communications.

## Implementation Strategy

### External TLS Certificates

- **Let's Encrypt**: Automated certificate issuance and renewal
- **Cert-manager**: Manages TLS lifecycle with Kubernetes
- **Ingress NGINX**: SSL termination

### Internal mTLS Configuration

- **Custom CA**: Hierarchy with root and intermediate CAs
- **Internal Services**: Service-to-service authentication with mTLS
- **Service Mesh**: Optional Istio integration for service identity

## Prerequisites

- **Kubernetes Cluster**: Running with kubectl access
- **Cert-manager Installed**: Deployed in Kubernetes

## TLS Certificate Management with Cert-Manager

### Install Cert-Manager

```bash
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.6.0/cert-manager.yaml

kubectl get pods --namespace cert-manager
```

### Set Up Let's Encrypt Issuer

- **ClusterIssuer (Production)**:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    email: tz-dev@vectorweight.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

- **ClusterIssuer (Staging)**:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    email: tz-dev@vectorweight.com
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Configure Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - example.homelab.local
    secretName: example-cert
  rules:
  - host: example.homelab.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

### Automated Certificate Rotation

- Cert-manager automatically checks and renews certificates 30 days before expiration.

## Implementing mTLS

### Steps to Set Up mTLS with Istio

#### Install Istio

```bash
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.14.1 sh -
cd istio-1.14.1
export PATH=$PWD/bin:$PATH

istioctl install --set profile=demo -y

kubectl get pods -n istio-system
```

#### Enable Strict mTLS Mode

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT
```

#### Apply Destination Rules

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: example-destination-rule
  namespace: default
spec:
  host: "*.example.com"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

#### Verify mTLS

1. **Test Service to Service Communication**:
   Use client-side tracing or logging to verify mTLS authentication.

2. **Check Istio Metrics**:
   View metrics and logs in Prometheus or Grafana for mTLS statistics and insights.

3. **Validate TLS Connections**:
   Confirm with: `openssl s_client -connect service.example.svc.cluster.local:80 -tls1_2`

#### mTLS for Non-Istio Environments

- **Manual Certificate Management**: Manage and rotate secrets manually within Kubernetes.
- **Seal Secrets**: Use Sealed Secrets to store and encrypt TLS certificates.

## Security Best Practices

### Certificate Management

- **Use ECDSA Certificates**: Higher security and performance.
- **Automate Renewal**: Use cert-manager to avoid manual renewal headaches.

### Network Security

- **Default Deny-All Policies**: Ensure no unintended access.
- **Principle of Least Privilege**: Only allow necessary network paths.
- **Regular Audits**: Review security policies regularly.

### Secret Management

- **Sealed Secrets**: Use for encrypting Kubernetes secrets.
- **Regular Rotation**: Rotate secrets according to your security policy.

## Troubleshooting Tips

1. **Certificate Not Issued**:
   - Check cert-manager logs for errors.
   - Verify DNS or HTTP challenge is correctly configured.

2. **Ingress Not Loading**:
   - Confirm that Ingress controller is running.
   - Check TLS secret existence and validity.

3. **mTLS Connection Errors**:
   - Validate service communication with sidecar logs.
   - Ensure DestinationRules align with mTLS configurations.

## Monitoring and Alerting

- **Prometheus Metrics**: Track certificate metrics, expiry, rotation.
- **Alertmanager Configurations**: Set alerts for soon-to-expire certificates.
- **Grafana Dashboards**: Visualize mTLS performance and issues.

## Conclusion

Integrating TLS and mTLS into the homelab provides a robust security layer. Automating certificate management with cert-manager and implementing mTLS with Istio can vastly improve the security posture of your infrastructure.

**Contact:** <tz-dev@vectorweight.com>  
**Last Updated:** December 2024  
**Next Review:** Bi-annually
