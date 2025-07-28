# Issue Summary Report

**Total Issues Found**: 20
**Deployment Blocking**: 16

## Issues by Severity

- 🚨 **Critical**: 14
- ⚠️ **High**: 2
- ⚡ **Medium**: 4

## Issues by Category

- **Security**: 11
- **Deployment**: 9

## 🚨 Critical Issues (Must Fix)

- **kubernetes_cluster**: Cluster is in critical state
- **service_gitlab**: Service not ready: No pods found
- **service_keycloak**: Service not ready: No pods found
- **service_prometheus**: Service not ready: No pods found
- **service_grafana**: Service not ready: No pods found
- **service_nginx-ingress**: Service not ready: No pods found
- **service_cert-manager**: Service not ready: No pods found
- **service_metallb**: Service not ready: No pods found
- **security_dns**: DNS service discovery failed
- **tls_tls_grafana**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_prometheus**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_longhorn**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_kubernetes-api**: Failed to establish TLS connection or retrieve certificate
- **tls_kubernetes_api**: Failed to establish TLS connection or retrieve certificate

## ⚠️ Deployment Blocking Issues

- **security_cluster_network**: Connectivity issues: Internal DNS resolution failed
- **terraform_infrastructure_state**: Failed to load Terraform state

## Top Issues by Component

### 🚨 kubernetes_cluster (1 issues)

- Cluster is in critical state

### 🚨 service_gitlab (1 issues)

- Service not ready: No pods found

### 🚨 service_keycloak (1 issues)

- Service not ready: No pods found

### 🚨 service_prometheus (1 issues)

- Service not ready: No pods found

### 🚨 service_grafana (1 issues)

- Service not ready: No pods found

### 🚨 service_nginx-ingress (1 issues)

- Service not ready: No pods found

### 🚨 service_cert-manager (1 issues)

- Service not ready: No pods found

### 🚨 service_metallb (1 issues)

- Service not ready: No pods found

### ⚠️ security_cluster_network (1 issues)

- Connectivity issues: Internal DNS resolution failed

### ⚡ security_certificates (1 issues)

- Kubernetes client unavailable

## 🔧 Next Steps

1. **Immediate Action Required**: Fix critical and deployment-blocking issues first
2. **Security Review**: Address high-severity security issues
3. **Configuration**: Review and update configuration-related issues
4. **Validation**: Re-run tests after addressing issues
