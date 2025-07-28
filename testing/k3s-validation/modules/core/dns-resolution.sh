#!/bin/bash
# Core Kubernetes DNS Resolution Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_coredns_functionality() {
    start_test "CoreDNS functionality"

    # Check if CoreDNS is running
    local coredns_pods
    if coredns_pods=$($KUBECTL_CMD get pods -n kube-system -l k8s-app=kube-dns --no-headers 2>/dev/null); then
        local running_pods=0
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                local pod_status=$(echo "$line" | awk '{print $3}')
                if [[ "$pod_status" == "Running" ]]; then
                    ((running_pods++))
                fi
            fi
        done <<< "$coredns_pods"

        if [[ $running_pods -gt 0 ]]; then
            log_success "CoreDNS is running with $running_pods pod(s)"
        else
            log_error "CoreDNS pods are not in Running state"
            return 1
        fi
    else
        log_error "CoreDNS pods not found"
        return 1
    fi
}

test_cluster_dns_resolution() {
    start_test "Cluster DNS resolution"

    local test_pod="dns-test-pod-$(date +%s)"

    if create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 120"; then
        if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then

            # Test kubernetes service DNS resolution
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup kubernetes.default.svc.cluster.local >/dev/null 2>&1; then
                log_success "Kubernetes service DNS resolution working"
            else
                log_error "Kubernetes service DNS resolution failed"
            fi

            # Test kube-system namespace DNS resolution
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup kube-dns.kube-system.svc.cluster.local >/dev/null 2>&1; then
                log_success "kube-system service DNS resolution working"
            else
                log_warning "kube-dns service DNS resolution failed (may not exist in all clusters)"
            fi

        else
            log_error "DNS test pod failed to become ready"
        fi
    else
        log_error "Failed to create DNS test pod"
    fi
}

test_external_dns_resolution() {
    start_test "External DNS resolution from pods"

    local test_pod="external-dns-test-$(date +%s)"

    if create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 60"; then
        if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then

            # Test external DNS resolution
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup google.com >/dev/null 2>&1; then
                log_success "External DNS resolution working"
            else
                log_error "External DNS resolution failed"
            fi

            # Test specific external DNS server
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup google.com 8.8.8.8 >/dev/null 2>&1; then
                log_success "External DNS server (8.8.8.8) accessible"
            else
                log_warning "External DNS server (8.8.8.8) not accessible (may be network policy)"
            fi

        else
            log_error "External DNS test pod failed to become ready"
        fi
    else
        log_error "Failed to create external DNS test pod"
    fi
}

test_dns_service_endpoints() {
    start_test "DNS service endpoints"

    # Check kube-dns service
    if $KUBECTL_CMD get service kube-dns -n kube-system >/dev/null 2>&1; then
        local cluster_ip
        cluster_ip=$($KUBECTL_CMD get service kube-dns -n kube-system -o jsonpath='{.spec.clusterIP}' 2>/dev/null)

        if [[ -n "$cluster_ip" && "$cluster_ip" != "None" ]]; then
            log_success "kube-dns service has cluster IP: $cluster_ip"

            # Check if service has endpoints
            if wait_for_service_endpoints "kube-dns" "kube-system" 30; then
                log_success "kube-dns service has ready endpoints"
            else
                log_warning "kube-dns service endpoints not ready"
            fi
        else
            log_error "kube-dns service does not have a valid cluster IP"
        fi
    else
        log_info "kube-dns service not found (may use different DNS service name)"
    fi
}

test_dns_config_map() {
    start_test "DNS configuration"

    # Check CoreDNS configmap
    if $KUBECTL_CMD get configmap coredns -n kube-system >/dev/null 2>&1; then
        log_success "CoreDNS configuration found"

        # Get basic info about the config
        local config_data
        if config_data=$($KUBECTL_CMD get configmap coredns -n kube-system -o jsonpath='{.data.Corefile}' 2>/dev/null); then
            if echo "$config_data" | grep -q "kubernetes cluster.local"; then
                log_success "CoreDNS configured for cluster.local domain"
            else
                log_warning "CoreDNS cluster.local configuration not found"
            fi
        else
            log_warning "Could not retrieve CoreDNS configuration"
        fi
    else
        log_warning "CoreDNS configuration not found"
    fi
}

# Main execution
run_dns_resolution() {
    start_test_module "DNS Resolution Validation"

    test_coredns_functionality
    test_cluster_dns_resolution
    test_external_dns_resolution
    test_dns_service_endpoints
    test_dns_config_map
}

# Allow running this module independently
# Main function for orchestrator compatibility
main() {
    run_dns_resolution
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_dns_resolution
    cleanup_framework
fi
