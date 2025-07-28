#!/bin/bash
# Core Kubernetes Basic Networking Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_pod_to_pod_communication() {
    start_test "Pod-to-pod communication"

    # Create test pods
    local test_pod1="network-test-pod1-$(date +%s)"
    local test_pod2="network-test-pod2-$(date +%s)"

    log_info "Creating test pods for network communication test"

    if create_test_pod "$test_pod1" "busybox:1.35" "$TEST_NAMESPACE" "sleep 120"; then
        if create_test_pod "$test_pod2" "busybox:1.35" "$TEST_NAMESPACE" "sleep 120"; then

            # Wait for pods to be ready
            if wait_for_pod_ready "$test_pod1" "$TEST_NAMESPACE" 60 && wait_for_pod_ready "$test_pod2" "$TEST_NAMESPACE" 60; then

                # Get pod IPs
                local pod1_ip
                local pod2_ip
                pod1_ip=$($KUBECTL_CMD get pod "$test_pod1" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)
                pod2_ip=$($KUBECTL_CMD get pod "$test_pod2" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)

                if [[ -n "$pod1_ip" && -n "$pod2_ip" ]]; then
                    log_info "Pod IPs: $test_pod1($pod1_ip), $test_pod2($pod2_ip)"

                    # Test connectivity from pod1 to pod2
                    if $KUBECTL_CMD exec "$test_pod1" -n "$TEST_NAMESPACE" -- ping -c 3 "$pod2_ip" >/dev/null 2>&1; then
                        log_success "Pod-to-pod communication successful"
                    else
                        log_error "Pod-to-pod communication failed"
                    fi
                else
                    log_error "Failed to get pod IP addresses"
                fi
            else
                log_error "Test pods failed to become ready"
            fi
        else
            log_error "Failed to create second test pod"
        fi
    else
        log_error "Failed to create first test pod"
    fi

    # Cleanup is handled by framework cleanup
}

test_service_discovery() {
    start_test "Service discovery and communication"

    local test_deployment="network-test-deploy-$(date +%s)"
    local test_service="network-test-svc-$(date +%s)"
    local test_client="network-test-client-$(date +%s)"

    log_info "Creating test deployment and service"

    if create_test_deployment "$test_deployment" "nginx:1.25-alpine" "$TEST_NAMESPACE" 1; then
        if create_test_service "$test_service" "$test_deployment" "$TEST_NAMESPACE" 80; then

            # Wait for deployment to be ready
            if wait_for_deployment_ready "$test_deployment" "$TEST_NAMESPACE" 60; then

                # Create client pod to test service access
                if create_test_pod "$test_client" "busybox:1.35" "$TEST_NAMESPACE" "sleep 120"; then
                    if wait_for_pod_ready "$test_client" "$TEST_NAMESPACE" 60; then

                        # Test service connectivity by name
                        if $KUBECTL_CMD exec "$test_client" -n "$TEST_NAMESPACE" -- wget -q -O- "$test_service" >/dev/null 2>&1; then
                            log_success "Service discovery and connectivity working"
                        else
                            log_error "Service connectivity test failed"
                        fi
                    else
                        log_error "Client pod failed to become ready"
                    fi
                else
                    log_error "Failed to create client pod"
                fi
            else
                log_error "Test deployment failed to become ready"
            fi
        else
            log_error "Failed to create test service"
        fi
    else
        log_error "Failed to create test deployment"
    fi
}

test_external_connectivity() {
    start_test "External connectivity from pods"

    local test_pod="external-test-pod-$(date +%s)"

    if create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 60"; then
        if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then

            # Test external DNS resolution and connectivity
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup google.com >/dev/null 2>&1; then
                log_success "External DNS resolution working"

                # Test external connectivity
                if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- wget -q -O- --timeout=10 http://httpbin.org/ip >/dev/null 2>&1; then
                    log_success "External connectivity working"
                else
                    log_warning "External HTTP connectivity test failed (may be network policy or firewall)"
                fi
            else
                log_error "External DNS resolution failed"
            fi
        else
            log_error "External connectivity test pod failed to become ready"
        fi
    else
        log_error "Failed to create external connectivity test pod"
    fi
}

# Main execution
run_basic_networking() {
    start_test_module "Basic Networking Validation"

    test_pod_to_pod_communication
    test_service_discovery
    test_external_connectivity
}

# Allow running this module independently
# Main function for orchestrator compatibility
main() {
    run_basic_networking
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_basic_networking
    cleanup_framework
fi
