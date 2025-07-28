# Homelab Infrastructure Test Report

**Generated:** 2025-07-28T20:35:57.461398+00:00
**Duration:** 2.28 seconds
**Overall Status:** FAIL

## Summary

- **Overall Status:** fail
- **Test Duration:** 2.2751526832580566
- **Modules Run:** 4
- **Total Recommendations:** 3

## Issue Summary

**Total Issues**: 20
**Deployment Blocking**: 16

### 🚨 Critical Issues (Must Fix)

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

### Issues by Severity

- 🚨 **Critical**: 14
- ⚠️ **High**: 2
- ⚡ **Medium**: 4

### Top Issues by Component

**🚨 kubernetes_cluster** (1 issues)
  - Cluster is in critical state

**🚨 service_gitlab** (1 issues)
  - Service not ready: No pods found

**🚨 service_keycloak** (1 issues)
  - Service not ready: No pods found

**🚨 service_prometheus** (1 issues)
  - Service not ready: No pods found

**🚨 service_grafana** (1 issues)
  - Service not ready: No pods found

**🚨 service_nginx-ingress** (1 issues)
  - Service not ready: No pods found

**🚨 service_cert-manager** (1 issues)
  - Service not ready: No pods found

**🚨 service_metallb** (1 issues)
  - Service not ready: No pods found

**⚠️ security_cluster_network** (1 issues)
  - Connectivity issues: Internal DNS resolution failed

**⚡ security_certificates** (1 issues)
  - Kubernetes client unavailable

## Metrics

### Infrastructure Health

- **Health Percentage:** 0.0
- **Total Checks:** 5
- **Healthy Checks:** 0

### Service Deployment

- **Total Services:** 7
- **Ready Services:** 0
- **Readiness Rate:** 0.0

### Network Security

- **Total Checks:** 6
- **Secure Checks:** 0
- **Security Score:** 0.0

## Recommendations

1. Address infrastructure health issues before proceeding
2. Investigate unready services: gitlab, keycloak, prometheus, grafana, nginx-ingress, cert-manager, metallb
3. Review and address security warnings

## Infrastructure Health

**Overall Status:** CRITICAL
**Health Score:** 0.0%

## Service Deployment

- ❌ **gitlab:** No pods found
- ❌ **keycloak:** No pods found
- ❌ **prometheus:** No pods found
- ❌ **grafana:** No pods found
- ❌ **nginx-ingress:** No pods found
- ❌ **cert-manager:** No pods found
- ❌ **metallb:** No pods found

## Network & Security

- ⚠️ **Network Connectivity:** Connectivity issues: Internal DNS resolution failed
- 🚨 **Tls Certificates:** Kubernetes client unavailable
- 🚨 **Network Policies:** Kubernetes client unavailable
- 🚨 **Metallb Loadbalancer:** Kubernetes client unavailable
- 🚨 **Dns Service Discovery:** DNS service discovery failed
- 🚨 **Rbac Security:** Kubernetes client unavailable

