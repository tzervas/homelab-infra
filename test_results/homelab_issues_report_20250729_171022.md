# Issue Summary Report

**Total Issues Found**: 30
**Deployment Blocking**: 23

## Issues by Severity

- 🚨 **Critical**: 17
- ⚠️ **High**: 6
- ⚡ **Medium**: 7

## Issues by Category

- **Security**: 19
- **Configuration**: 7
- **Deployment**: 4

## 🚨 Critical Issues (Must Fix)

- **kubernetes_cluster**: Cluster is in critical state
- **service_gitlab**: Service not ready: No pods found
- **security_dns**: DNS service discovery failed
- **kubernetes_security_contexts**: Missing privileged container: ingress-nginx/ingress-nginx-controller:controller
- **tls_tls_grafana**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_prometheus**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_longhorn**: Failed to establish TLS connection or retrieve certificate
- **tls_tls_kubernetes-api**: Failed to establish TLS connection or retrieve certificate
- **tls_kubernetes_api**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate
- **tls_ingress_tls**: Failed to establish TLS connection or retrieve certificate

## ⚠️ Deployment Blocking Issues

- **service_nginx-ingress**: Service not ready: 1/3 pods ready
- **security_cluster_network**: Connectivity issues: Internal DNS resolution failed
- **security_network_security**: Missing critical policies: default-deny-all, allow-dns, monitoring-ingress
- **kubernetes_security_contexts**: Missing 5 security context(s): monitoring/grafana (pod level), monitoring/grafana:grafana, monitoring/prometheus (pod level) ... and 2 more
- **kubernetes_security_contexts**: Total of 21 missing security contexts (showing 5)
- **terraform_infrastructure_state**: Failed to load Terraform state

## Top Issues by Component

### 🚨 tls_ingress_tls (8 issues)

- Failed to establish TLS connection or retrieve certificate
- Failed to establish TLS connection or retrieve certificate
- Failed to establish TLS connection or retrieve certificate
- ... and 5 more issues

### ⚡ config_environment_config (4 issues)

- Schema validation error: 'environment' is a required property
- Schema validation error: 'environment' is a required property
- Schema validation error: 'environment' is a required property
- ... and 1 more issues

### ⚡ config_generic (3 issues)

- Failed to load file
- Failed to load file
- Failed to load file

### 🚨 kubernetes_security_contexts (3 issues)

- Missing privileged container: ingress-nginx/ingress-nginx-controller:controller
- Missing 5 security context(s): monitoring/grafana (pod level), monitoring/grafana:grafana, monitoring/prometheus (pod level) ... and 2 more
- Total of 21 missing security contexts (showing 5)

### 🚨 kubernetes_cluster (1 issues)

- Cluster is in critical state

### 🚨 service_gitlab (1 issues)

- Service not ready: No pods found

### ⚠️ service_nginx-ingress (1 issues)

- Service not ready: 1/3 pods ready

### ⚠️ security_cluster_network (1 issues)

- Connectivity issues: Internal DNS resolution failed

### ⚠️ security_network_security (1 issues)

- Missing critical policies: default-deny-all, allow-dns, monitoring-ingress

### 🚨 security_dns (1 issues)

- DNS service discovery failed

## 🔧 Next Steps

1. **Immediate Action Required**: Fix critical and deployment-blocking issues first
2. **Security Review**: Address high-severity security issues
3. **Configuration**: Review and update configuration-related issues
4. **Validation**: Re-run tests after addressing issues
