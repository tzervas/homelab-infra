#!/bin/bash
# K3s Embedded Database Health Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_embedded_database_pods() {
    start_test "K3s embedded database pods"

    # K3s uses etcd or sqlite3 embedded in the server
    # Check for etcd pods in kube-system namespace
    local etcd_pods
    if etcd_pods=$($KUBECTL_CMD get pods -n kube-system -l component=etcd --no-headers 2>/dev/null); then
        if [[ -n "$etcd_pods" ]]; then
            local running_count=0
            local total_count=0

            while IFS= read -r line; do
                if [[ -n "$line" ]]; then
                    ((total_count++))
                    local pod_status=$(echo "$line" | awk '{print $3}')
                    if [[ "$pod_status" == "Running" ]]; then
                        ((running_count++))
                    fi
                fi
            done <<< "$etcd_pods"

            if [[ $running_count -eq $total_count && $total_count -gt 0 ]]; then
                log_success "etcd pods running: $running_count/$total_count"
            else
                log_error "etcd pods not all running: $running_count/$total_count"
            fi
        else
            log_info "No etcd pods found (may be using embedded SQLite)"
        fi
    else
        log_info "No etcd pods found (likely using embedded SQLite)"
    fi
}

test_kine_deployment() {
    start_test "Kine deployment (external datastore)"

    # Check if kine is being used (external datastore proxy)
    if $KUBECTL_CMD get deployment kine -n kube-system >/dev/null 2>&1; then
        local ready_replicas
        ready_replicas=$($KUBECTL_CMD get deployment kine -n kube-system -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

        if [[ "$ready_replicas" -gt 0 ]]; then
            log_success "Kine deployment is running ($ready_replicas replicas ready)"
        else
            log_error "Kine deployment exists but no replicas are ready"
        fi
    else
        log_info "Kine deployment not found (using embedded datastore)"
    fi
}

test_datastore_connectivity() {
    start_test "Datastore connectivity via API server"

    # Test datastore health by checking API server's ability to read/write
    local test_cm_name="k3s-db-test-$(date +%s)"

    # Create a test configmap to verify write operations
    if $KUBECTL_CMD create configmap "$test_cm_name" --from-literal=test=data -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        log_success "Database write operation successful"

        # Read the configmap back to verify read operations
        if $KUBECTL_CMD get configmap "$test_cm_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
            log_success "Database read operation successful"

            # Clean up test configmap
            $KUBECTL_CMD delete configmap "$test_cm_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1 || true
        else
            log_error "Database read operation failed"
        fi
    else
        log_error "Database write operation failed"
    fi
}

test_k3s_server_metrics() {
    start_test "K3s server database metrics"

    # Check if K3s server exposes metrics endpoint
    local k3s_server_pods
    if k3s_server_pods=$($KUBECTL_CMD get pods -n kube-system -l app=k3s-server --no-headers 2>/dev/null); then
        if [[ -n "$k3s_server_pods" ]]; then
            log_info "K3s server pods found, checking metrics availability"

            # Try to get metrics from the first server pod
            local first_pod=$(echo "$k3s_server_pods" | head -n1 | awk '{print $1}')
            if [[ -n "$first_pod" ]]; then
                # K3s exposes metrics on port 10250 by default
                if $KUBECTL_CMD exec "$first_pod" -n kube-system -- curl -s http://localhost:10250/metrics >/dev/null 2>&1; then
                    log_success "K3s server metrics endpoint accessible"
                else
                    log_info "K3s server metrics endpoint not accessible (may be disabled)"
                fi
            fi
        else
            log_info "No K3s server pods found with label app=k3s-server"
        fi
    else
        log_info "Unable to query for K3s server pods"
    fi
}

test_database_consistency() {
    start_test "Database consistency check"

    # Create multiple resources quickly and verify they're all stored
    local test_prefix="k3s-consistency-test-$(date +%s)"
    local created_resources=()
    local verification_passed=0

    # Create 5 test configmaps rapidly
    for i in {1..5}; do
        local cm_name="${test_prefix}-${i}"
        if $KUBECTL_CMD create configmap "$cm_name" --from-literal=index="$i" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
            created_resources+=("$cm_name")
        fi
    done

    # Wait a moment for consistency
    sleep 2

    # Verify all resources can be read back
    for cm_name in "${created_resources[@]}"; do
        if $KUBECTL_CMD get configmap "$cm_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
            ((verification_passed++))
        fi
    done

    if [[ $verification_passed -eq ${#created_resources[@]} ]] && [[ ${#created_resources[@]} -gt 0 ]]; then
        log_success "Database consistency check passed ($verification_passed/${#created_resources[@]} resources)"
    else
        log_error "Database consistency issues detected ($verification_passed/${#created_resources[@]} resources verified)"
    fi

    # Cleanup test resources
    for cm_name in "${created_resources[@]}"; do
        $KUBECTL_CMD delete configmap "$cm_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1 || true
    done
}

# Main execution
run_embedded_db_health() {
    start_test_module "K3s Embedded Database Health"

    test_embedded_database_pods
    test_kine_deployment
    test_datastore_connectivity
    test_k3s_server_metrics
    test_database_consistency
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_embedded_db_health
    cleanup_framework
fi
