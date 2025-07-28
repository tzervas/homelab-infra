#!/bin/bash
# K3s Performance Benchmarking Module - Startup and Response Times

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_pod_startup_time() {
    start_test "Pod startup time benchmarking"

    local test_iterations=5
    local total_time=0
    local successful_starts=0

    for ((i=1; i<=test_iterations; i++)); do
        local pod_name="startup-test-$i"
        log_debug "Testing pod startup iteration $i"

        # Measure pod creation to running time
        local start_time=$(date +%s.%N)

        create_test_pod "$pod_name" "busybox:1.35" "$TEST_NAMESPACE" "sleep 60"

        if wait_for_pod_ready "$pod_name" "$TEST_NAMESPACE" 60; then
            local end_time=$(date +%s.%N)
            local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")

            log_debug "Pod $pod_name startup time: ${duration}s"
            total_time=$(echo "$total_time + $duration" | bc -l 2>/dev/null || echo "$total_time")
            ((successful_starts++))
        else
            log_warning "Pod $pod_name failed to start within timeout"
        fi

        # Cleanup pod
        $KUBECTL_CMD delete pod "$pod_name" -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
        sleep 2
    done

    if [[ $successful_starts -gt 0 ]]; then
        local avg_time=$(echo "scale=2; $total_time / $successful_starts" | bc -l 2>/dev/null || echo "0")
        log_success "Average pod startup time: ${avg_time}s ($successful_starts/$test_iterations successful)"

        # Performance thresholds
        if (( $(echo "$avg_time < 10" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Pod startup performance: Excellent (< 10s)"
        elif (( $(echo "$avg_time < 30" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Pod startup performance: Good (< 30s)"
        elif (( $(echo "$avg_time < 60" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Pod startup performance: Acceptable (< 60s)"
        else
            log_error "Pod startup performance: Poor (>= 60s)"
        fi
    else
        log_error "No pods started successfully"
    fi
}

test_deployment_scaling_time() {
    start_test "Deployment scaling performance"

    local deployment_name="scaling-test-deployment"

    # Create initial deployment
    create_test_deployment "$deployment_name" "nginx:1.25-alpine" "$TEST_NAMESPACE" 1

    if ! wait_for_deployment_ready "$deployment_name" "$TEST_NAMESPACE" 120; then
        log_error "Initial deployment failed to become ready"
        return 1
    fi

    # Test scaling up
    local scale_start_time=$(date +%s.%N)

    $KUBECTL_CMD scale deployment "$deployment_name" -n "$TEST_NAMESPACE" --replicas=5 >/dev/null 2>&1

    if wait_for_deployment_ready "$deployment_name" "$TEST_NAMESPACE" 180; then
        local scale_end_time=$(date +%s.%N)
        local scale_duration=$(echo "$scale_end_time - $scale_start_time" | bc -l 2>/dev/null || echo "0")

        log_success "Deployment scaled from 1 to 5 replicas in ${scale_duration}s"

        # Performance evaluation
        if (( $(echo "$scale_duration < 30" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Scaling performance: Excellent (< 30s)"
        elif (( $(echo "$scale_duration < 60" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Scaling performance: Good (< 60s)"
        elif (( $(echo "$scale_duration < 120" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Scaling performance: Acceptable (< 120s)"
        else
            log_error "Scaling performance: Poor (>= 120s)"
        fi
    else
        log_error "Deployment scaling failed to complete within timeout"
    fi

    # Test scaling down
    local scale_down_start=$(date +%s.%N)

    $KUBECTL_CMD scale deployment "$deployment_name" -n "$TEST_NAMESPACE" --replicas=1 >/dev/null 2>&1

    # Wait for scale down (should be faster)
    sleep 10
    local ready_replicas
    ready_replicas=$($KUBECTL_CMD get deployment "$deployment_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

    if [[ $ready_replicas -eq 1 ]]; then
        local scale_down_end=$(date +%s.%N)
        local scale_down_duration=$(echo "$scale_down_end - $scale_down_start" | bc -l 2>/dev/null || echo "0")
        log_success "Deployment scaled down from 5 to 1 replica in ${scale_down_duration}s"
    else
        log_warning "Scale down verification incomplete"
    fi
}

test_service_response_time() {
    start_test "Service response time benchmarking"

    # Use existing deployment or create new one
    local deployment_name="response-time-test"
    local service_name="${deployment_name}-service"

    # Create deployment and service
    create_test_deployment "$deployment_name" "nginx:1.25-alpine" "$TEST_NAMESPACE" 2

    if ! wait_for_deployment_ready "$deployment_name" "$TEST_NAMESPACE" 120; then
        log_error "Response time test deployment failed"
        return 1
    fi

    create_test_service "$service_name" "$deployment_name" "$TEST_NAMESPACE" 80

    if ! wait_for_service_endpoints "$service_name" "$TEST_NAMESPACE" 60; then
        log_error "Service endpoints not ready for response time test"
        return 1
    fi

    # Create test client pod
    create_test_pod "response-test-client" "curlimages/curl:8.1.0" "$TEST_NAMESPACE" "sleep 300"

    if ! wait_for_pod_ready "response-test-client" "$TEST_NAMESPACE" 60; then
        log_error "Response test client pod failed to start"
        return 1
    fi

    # Measure response times
    local test_iterations=10
    local total_response_time=0
    local successful_requests=0

    for ((i=1; i<=test_iterations; i++)); do
        # Measure response time using curl
        local response_time
        response_time=$($KUBECTL_CMD exec response-test-client -n "$TEST_NAMESPACE" -- curl -w "%{time_total}" -s -o /dev/null "http://$service_name" 2>/dev/null)

        if [[ -n "$response_time" ]] && (( $(echo "$response_time > 0" | bc -l 2>/dev/null || echo "0") )); then
            total_response_time=$(echo "$total_response_time + $response_time" | bc -l 2>/dev/null || echo "$total_response_time")
            ((successful_requests++))
            log_debug "Request $i response time: ${response_time}s"
        else
            log_debug "Request $i failed"
        fi

        sleep 1
    done

    if [[ $successful_requests -gt 0 ]]; then
        local avg_response_time=$(echo "scale=3; $total_response_time / $successful_requests" | bc -l 2>/dev/null || echo "0")
        log_success "Average service response time: ${avg_response_time}s ($successful_requests/$test_iterations successful)"

        # Performance thresholds
        if (( $(echo "$avg_response_time < 0.1" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Service response performance: Excellent (< 100ms)"
        elif (( $(echo "$avg_response_time < 0.5" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Service response performance: Good (< 500ms)"
        elif (( $(echo "$avg_response_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Service response performance: Acceptable (< 1s)"
        else
            log_error "Service response performance: Poor (>= 1s)"
        fi

        # Calculate success rate
        local success_rate=$((successful_requests * 100 / test_iterations))
        if [[ $success_rate -ge 95 ]]; then
            log_success "Service reliability: Excellent (${success_rate}%)"
        elif [[ $success_rate -ge 90 ]]; then
            log_success "Service reliability: Good (${success_rate}%)"
        elif [[ $success_rate -ge 80 ]]; then
            log_warning "Service reliability: Acceptable (${success_rate}%)"
        else
            log_error "Service reliability: Poor (${success_rate}%)"
        fi
    else
        log_error "No successful service requests"
    fi
}

test_dns_resolution_performance() {
    start_test "DNS resolution performance"

    create_test_pod "dns-perf-test" "busybox:1.35" "$TEST_NAMESPACE" "sleep 300"

    if ! wait_for_pod_ready "dns-perf-test" "$TEST_NAMESPACE" 60; then
        log_error "DNS performance test pod failed to start"
        return 1
    fi

    # Test DNS resolution times
    local dns_targets=("kubernetes.default.svc.cluster.local" "kube-dns.kube-system.svc.cluster.local")

    for target in "${dns_targets[@]}"; do
        local test_iterations=5
        local total_dns_time=0
        local successful_lookups=0

        for ((i=1; i<=test_iterations; i++)); do
            local start_time=$(date +%s.%N)

            if $KUBECTL_CMD exec dns-perf-test -n "$TEST_NAMESPACE" -- nslookup "$target" >/dev/null 2>&1; then
                local end_time=$(date +%s.%N)
                local dns_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")

                total_dns_time=$(echo "$total_dns_time + $dns_time" | bc -l 2>/dev/null || echo "$total_dns_time")
                ((successful_lookups++))
            fi

            sleep 0.5
        done

        if [[ $successful_lookups -gt 0 ]]; then
            local avg_dns_time=$(echo "scale=3; $total_dns_time / $successful_lookups" | bc -l 2>/dev/null || echo "0")
            log_success "DNS resolution time for $target: ${avg_dns_time}s"

            if (( $(echo "$avg_dns_time < 0.1" | bc -l 2>/dev/null || echo "0") )); then
                log_success "DNS performance for $target: Excellent (< 100ms)"
            elif (( $(echo "$avg_dns_time < 0.5" | bc -l 2>/dev/null || echo "0") )); then
                log_success "DNS performance for $target: Good (< 500ms)"
            elif (( $(echo "$avg_dns_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "DNS performance for $target: Acceptable (< 1s)"
            else
                log_error "DNS performance for $target: Poor (>= 1s)"
            fi
        else
            log_error "DNS resolution failed for $target"
        fi
    done
}

test_image_pull_performance() {
    start_test "Container image pull performance"

    # Test pulling a new image that's likely not cached
    local test_image="hello-world:latest"
    local pod_name="image-pull-test"

    # First, try to remove the image from nodes (best effort)
    log_info "Testing image pull performance with $test_image"

    local pull_start_time=$(date +%s.%N)

    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  containers:
  - name: test-container
    image: $test_image
    imagePullPolicy: Always
    command: ["/hello"]
  restartPolicy: Never
EOF

    # Wait for pod to complete or fail
    local timeout=300  # 5 minutes for image pull
    local elapsed=0
    local pod_phase=""

    while [[ $elapsed -lt $timeout ]]; do
        pod_phase=$($KUBECTL_CMD get pod "$pod_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)

        if [[ "$pod_phase" == "Succeeded" || "$pod_phase" == "Failed" ]]; then
            break
        fi

        sleep 2
        ((elapsed += 2))
    done

    local pull_end_time=$(date +%s.%N)
    local pull_duration=$(echo "$pull_end_time - $pull_start_time" | bc -l 2>/dev/null || echo "0")

    if [[ "$pod_phase" == "Succeeded" ]]; then
        log_success "Image pull and execution completed in ${pull_duration}s"

        # Performance evaluation
        if (( $(echo "$pull_duration < 30" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Image pull performance: Excellent (< 30s)"
        elif (( $(echo "$pull_duration < 60" | bc -l 2>/dev/null || echo "0") )); then
            log_success "Image pull performance: Good (< 60s)"
        elif (( $(echo "$pull_duration < 120" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Image pull performance: Acceptable (< 120s)"
        else
            log_error "Image pull performance: Poor (>= 120s)"
        fi
    else
        log_error "Image pull test failed or timed out (phase: $pod_phase)"
    fi
}

# Main execution
run_startup_benchmarks() {
    start_test_module "Startup and Performance Benchmarks"

    test_pod_startup_time
    test_deployment_scaling_time
    test_service_response_time
    test_dns_resolution_performance
    test_image_pull_performance
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    create_test_namespace
    run_startup_benchmarks
    cleanup_framework
fi
