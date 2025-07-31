# Homelab Infrastructure Test Report

**Generated:** 2025-07-29T17:09:18.842143+00:00
**Duration:** 63.17 seconds
**Overall Status:** FAIL

## Summary

- **Overall Status:** fail
- **Test Duration:** 63.1713182926178
- **Modules Run:** 4
- **Total Recommendations:** 11

## Issue Summary

**Total Issues**: 30
**Deployment Blocking**: 23

### 🚨 Critical Issues (Must Fix)

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

### Issues by Severity

- 🚨 **Critical**: 17
- ⚠️ **High**: 6
- ⚡ **Medium**: 7

### Top Issues by Component

**🚨 tls_ingress_tls** (8 issues)

- Failed to establish TLS connection or retrieve certificate
- Failed to establish TLS connection or retrieve certificate
- ... and 6 more issues

**⚡ config_environment_config** (4 issues)

- Schema validation error: 'environment' is a required property
- Schema validation error: 'environment' is a required property
- ... and 2 more issues

**⚡ config_generic** (3 issues)

- Failed to load file
- Failed to load file
- ... and 1 more issues

**🚨 kubernetes_security_contexts** (3 issues)

- Missing privileged container: ingress-nginx/ingress-nginx-controller:controller
- Missing 5 security context(s): monitoring/grafana (pod level), monitoring/grafana:grafana, monitoring/prometheus (pod level) ... and 2 more
- ... and 1 more issues

**🚨 kubernetes_cluster** (1 issues)

- Cluster is in critical state

**🚨 service_gitlab** (1 issues)

- Service not ready: No pods found

**⚠️ service_nginx-ingress** (1 issues)

- Service not ready: 1/3 pods ready

**⚠️ security_cluster_network** (1 issues)

- Connectivity issues: Internal DNS resolution failed

**⚠️ security_network_security** (1 issues)

- Missing critical policies: default-deny-all, allow-dns, monitoring-ingress

**🚨 security_dns** (1 issues)

- DNS service discovery failed

## Metrics

### Config Validation

- **Total Files:** 22
- **Valid Files:** 15
- **Validation Rate:** 68.18181818181817

### Infrastructure Health

- **Health Percentage:** 60.0
- **Total Checks:** 5
- **Healthy Checks:** 3

### Service Deployment

- **Total Services:** 7
- **Ready Services:** 5
- **Readiness Rate:** 71.42857142857143

### Network Security

- **Total Checks:** 6
- **Secure Checks:** 2
- **Security Score:** 33.33333333333333

## Recommendations

1. Fix 7 invalid configuration files
2. Address infrastructure health issues before proceeding
3. Investigate unready services: gitlab, nginx-ingress
4. Review and address security warnings
5. Review policy effectiveness
6. Fix 1 privileged containers
7. Set runAsNonRoot: true and remove privileged access
8. Add security contexts to 21 containers/pods
9. Implement comprehensive security context policy
10. Configure Pod Security Standards for 14 namespaces
11. Use 'restricted' profile for production workloads

## Configuration Validation

**Status:** 15/22 files valid

## Infrastructure Health

**Overall Status:** CRITICAL
**Health Score:** 60.0%

## Service Deployment

- ❌ **gitlab:** No pods found
- ✅ **keycloak:** All 2 pods ready, endpoints healthy
- ✅ **prometheus:** All 2 pods ready, endpoints healthy
- ✅ **grafana:** All 2 pods ready, endpoints healthy
- ❌ **nginx-ingress:** 1/3 pods ready
- ✅ **cert-manager:** All 3 pods ready, endpoints healthy
- ✅ **metallb:** All 2 pods ready, endpoints healthy

## Network & Security

- ⚠️ **Network Connectivity:** Connectivity issues: Internal DNS resolution failed
- 🔒 **Tls Certificates:** Found 11 TLS certificates
- ⚠️ **Network Policies:** Missing critical policies: default-deny-all, allow-dns, monitoring-ingress
- 🔒 **Metallb Loadbalancer:** MetalLB operational: 1 LoadBalancers active
- 🚨 **Dns Service Discovery:** DNS service discovery failed
- ⚠️ **Rbac Security:** Security issues: 1 privileged containers, 21 missing contexts, 14 PSS violations
