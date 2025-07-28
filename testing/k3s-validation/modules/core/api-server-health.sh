#!/bin/bash
# Core Kubernetes API Server Health Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_api_server_connectivity() {
    start_test "API server connectivity"

    if $KUBECTL_CMD cluster-info >/dev/null 2>&1; then
        log_success "API server is accessible"

        # Get API server version
        local api_version
        api_version=$($KUBECTL_CMD version --short 2>/dev/null | grep "Server Version" | cut -d':' -f2 | tr -d ' ' || echo "unknown")
        log_info "API server version: $api_version"
    else
        log_error "API server is not accessible"
        return 1
    fi
}

test_api_server_health_endpoints() {
    start_test "API server health endpoints"

    # Test /healthz endpoint
    if $KUBECTL_CMD get --raw /healthz >/dev/null 2>&1; then
        log_success "API server /healthz endpoint responding"
    else
        log_error "API server /healthz endpoint not responding"
    fi

    # Test /readyz endpoint
    if $KUBECTL_CMD get --raw /readyz >/dev/null 2>&1; then
        log_success "API server /readyz endpoint responding"
    else
        log_warning "API server /readyz endpoint not responding (may not be available in all versions)"
    fi

    # Test /livez endpoint
    if $KUBECTL_CMD get --raw /livez >/dev/null 2>&1; then
        log_success "API server /livez endpoint responding"
    else
        log_warning "API server /livez endpoint not responding (may not be available in all versions)"
    fi
}

test_api_server_performance() {
    start_test "API server response performance"

    local total_time=0
    local iterations=5
    local successful_requests=0

    for ((i=1; i<=iterations; i++)); do
        local start_time=$(date +%s.%N)

        if $KUBECTL_CMD get namespaces >/dev/null 2>&1; then
            local end_time=$(date +%s.%N)
            local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")

            total_time=$(echo "$total_time + $duration" | bc -l 2>/dev/null || echo "$total_time")
            ((successful_requests++))
        fi

        sleep 0.5
    done

    if [[ $successful_requests -gt 0 ]]; then
        local avg_time=$(echo "scale=3; $total_time / $successful_requests" | bc -l 2>/dev/null || echo "0")
        log_success "Average API response time: ${avg_time}s"

        if (( $(echo "$avg_time < 0.5" | bc -l 2>/dev/null || echo "0") )); then
            log_success "API server performance: Excellent (< 500ms)"
        elif (( $(echo "$avg_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
            log_success "API server performance: Good (< 1s)"
        elif (( $(echo "$avg_time < 2.0" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "API server performance: Acceptable (< 2s)"
        else
            log_error "API server performance: Poor (>= 2s)"
        fi
    else
        log_error "No successful API requests"
    fi
}

test_api_server_resources() {
    start_test "API server resource discovery"

    # Test core API resources
    if $KUBECTL_CMD api-resources --api-group="" >/dev/null 2>&1; then
        log_success "Core API resources accessible"
    else
        log_error "Cannot access core API resources"
    fi

    # Test apps API resources
    if $KUBECTL_CMD api-resources --api-group="apps" >/dev/null 2>&1; then
        log_success "Apps API group accessible"
    else
        log_error "Cannot access apps API group"
    fi

    # Count total API resources
    local resource_count
    resource_count=$($KUBECTL_CMD api-resources --no-headers 2>/dev/null | wc -l || echo "0")

    if [[ $resource_count -gt 0 ]]; then
        log_success "Total API resources available: $resource_count"
    else
        log_error "No API resources found"
    fi
}

# Main execution
run_api_server_health() {
    start_test_module "API Server Health"

    test_api_server_connectivity
    test_api_server_health_endpoints
    test_api_server_performance
    test_api_server_resources
}

# Main function for orchestrator compatibility
main() {
    run_api_server_health
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    create_test_namespace
    main
    cleanup_test_namespace
fi
