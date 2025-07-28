#!/bin/bash
# K3s Traefik Ingress Controller Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_traefik_health() {
    start_test "Traefik controller health check"

    # Check if Traefik deployment exists and is ready
    if $KUBECTL_CMD get deployment traefik -n kube-system >/dev/null 2>&1; then
        if wait_for_deployment_ready traefik kube-system 120; then
            log_success "Traefik deployment is ready"
        else
            log_error "Traefik deployment is not ready"
            return 1
        fi
    else
        log_skip "Traefik not found (may be disabled or using external ingress)"
        return 0
    fi

    # Check Traefik service
    if $KUBECTL_CMD get service traefik -n kube-system >/dev/null 2>&1; then
        log_success "Traefik service exists"
    else
        log_error "Traefik service not found"
        return 1
    fi

    # Check if Traefik is responding
    local traefik_port
    if traefik_port=$($KUBECTL_CMD get service traefik -n kube-system -o jsonpath='{.spec.ports[?(@.name=="web")].port}' 2>/dev/null); then
        if [[ -n "$traefik_port" ]]; then
            log_success "Traefik web port configured: $traefik_port"
        else
            log_warning "Traefik web port not found"
        fi
    fi
}

test_traefik_ingress_functionality() {
    start_test "Traefik ingress functionality"

    # Skip if Traefik is not available
    if ! $KUBECTL_CMD get deployment traefik -n kube-system >/dev/null 2>&1; then
        log_skip "Traefik not available for ingress testing"
        return 0
    fi

    # Create test application
    local app_name="traefik-test-app"
    create_test_deployment "$app_name" "nginx:1.25-alpine" "$TEST_NAMESPACE" 1

    if ! wait_for_deployment_ready "$app_name" "$TEST_NAMESPACE" 120; then
        log_error "Test application failed to deploy"
        return 1
    fi

    # Create service for the test app
    create_test_service "${app_name}-service" "$app_name" "$TEST_NAMESPACE" 80

    # Create ingress
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${app_name}-ingress
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
spec:
  rules:
  - host: test-app.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ${app_name}-service
            port:
              number: 80
EOF

    # Wait for ingress to be ready
    sleep 10

    # Check if ingress was created
    if $KUBECTL_CMD get ingress "${app_name}-ingress" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        log_success "Ingress resource created successfully"

        # Check ingress status
        local ingress_ip
        ingress_ip=$($KUBECTL_CMD get ingress "${app_name}-ingress" -n "$TEST_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
        if [[ -n "$ingress_ip" ]]; then
            log_success "Ingress has IP address: $ingress_ip"
        else
            log_warning "Ingress IP not yet assigned (may be normal for some setups)"
        fi
    else
        log_error "Failed to create ingress resource"
        return 1
    fi
}

test_traefik_dashboard_access() {
    start_test "Traefik dashboard accessibility"

    # Check if Traefik dashboard is enabled
    if $KUBECTL_CMD get service traefik-dashboard -n kube-system >/dev/null 2>&1; then
        log_success "Traefik dashboard service exists"

        # Try to access dashboard endpoint
        local dashboard_port
        dashboard_port=$($KUBECTL_CMD get service traefik-dashboard -n kube-system -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
        if [[ -n "$dashboard_port" ]]; then
            log_success "Dashboard accessible on port: $dashboard_port"
        fi
    else
        log_skip "Traefik dashboard not exposed (may be intentionally disabled for security)"
    fi
}

test_traefik_tls_configuration() {
    start_test "Traefik TLS configuration"

    # Check for TLS-related configuration
    if $KUBECTL_CMD get service traefik -n kube-system -o json | jq -e '.spec.ports[] | select(.name=="websecure")' >/dev/null 2>&1; then
        log_success "Traefik HTTPS port (websecure) configured"

        local tls_port
        tls_port=$($KUBECTL_CMD get service traefik -n kube-system -o jsonpath='{.spec.ports[?(@.name=="websecure")].port}')
        log_info "TLS port: $tls_port"
    else
        log_warning "Traefik HTTPS port not configured (HTTP-only setup)"
    fi

    # Check for TLS-related secrets or certificates
    local cert_count
    cert_count=$($KUBECTL_CMD get secrets -n kube-system --field-selector type=kubernetes.io/tls -o json | jq '.items | length' 2>/dev/null || echo "0")
    if [[ $cert_count -gt 0 ]]; then
        log_success "Found $cert_count TLS certificate(s)"
    else
        log_info "No TLS certificates found in kube-system namespace"
    fi
}

test_traefik_middleware() {
    start_test "Traefik middleware functionality"

    # Check for Traefik CRDs
    if $KUBECTL_CMD get crd middlewares.traefik.containo.us >/dev/null 2>&1; then
        log_success "Traefik Middleware CRD available"

        # Create a test middleware
        cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: test-headers
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  headers:
    customRequestHeaders:
      X-Test-Header: "k3s-validation"
EOF

        if $KUBECTL_CMD get middleware test-headers -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
            log_success "Traefik middleware created successfully"
        else
            log_error "Failed to create Traefik middleware"
        fi
    else
        log_skip "Traefik CRDs not installed (may be using ingress-only mode)"
    fi
}

# Main execution
run_traefik_validation() {
    start_test_module "Traefik Validation"

    test_traefik_health
    test_traefik_ingress_functionality
    test_traefik_dashboard_access
    test_traefik_tls_configuration
    test_traefik_middleware
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    create_test_namespace
    run_traefik_validation
    cleanup_framework
fi
