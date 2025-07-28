#!/bin/bash
# Core Kubernetes System Pods Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_kube_system_pods() {
    start_test "kube-system pods status"

    local failed_pods=0
    local total_pods=0

    # Get all pods in kube-system namespace
    local pods_output
    if pods_output=$($KUBECTL_CMD get pods -n kube-system --no-headers 2>/dev/null); then
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((total_pods++))
                local pod_name=$(echo "$line" | awk '{print $1}')
                local pod_status=$(echo "$line" | awk '{print $3}')

                if [[ "$pod_status" != "Running" && "$pod_status" != "Completed" ]]; then
                    log_error "Pod $pod_name is in $pod_status state"
                    ((failed_pods++))
                else
                    log_debug "Pod $pod_name is $pod_status"
                fi
            fi
        done <<< "$pods_output"

        if [[ $failed_pods -eq 0 ]]; then
            log_success "All $total_pods kube-system pods are running correctly"
        else
            log_error "$failed_pods out of $total_pods kube-system pods are not running"
        fi
    else
        log_error "Failed to get kube-system pods"
        return 1
    fi
}

test_coredns_pods() {
    start_test "CoreDNS pods availability"

    local coredns_pods
    if coredns_pods=$($KUBECTL_CMD get pods -n kube-system -l k8s-app=kube-dns --no-headers 2>/dev/null); then
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
        done <<< "$coredns_pods"

        if [[ $running_count -gt 0 ]]; then
            log_success "CoreDNS pods running: $running_count/$total_count"
        else
            log_error "No CoreDNS pods are running"
        fi
    else
        log_warning "CoreDNS pods not found or not accessible"
    fi
}

test_metrics_server() {
    start_test "Metrics server availability"

    if $KUBECTL_CMD get deployment metrics-server -n kube-system >/dev/null 2>&1; then
        local ready_replicas
        ready_replicas=$($KUBECTL_CMD get deployment metrics-server -n kube-system -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

        if [[ "$ready_replicas" -gt 0 ]]; then
            log_success "Metrics server is running ($ready_replicas replicas ready)"
        else
            log_warning "Metrics server deployment exists but no replicas are ready"
        fi
    else
        log_info "Metrics server not found (optional component)"
    fi
}

# Main execution
run_system_pods() {
    start_test_module "Core System Pods Validation"

    test_kube_system_pods
    test_coredns_pods
    test_metrics_server
}

# Allow running this module independently
# Main function for orchestrator compatibility
main() {
    run_system_pods
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_system_pods
    cleanup_framework
fi
