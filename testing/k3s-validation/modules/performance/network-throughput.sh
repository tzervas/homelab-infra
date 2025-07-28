#!/bin/bash
# K3s Network Throughput Performance Testing Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_pod_to_pod_throughput() {
    start_test "Pod-to-pod network throughput"

    local server_pod="throughput-server-$(date +%s)"
    local client_pod="throughput-client-$(date +%s)"

    # Create server pod with iperf3
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $server_pod
  namespace: $TEST_NAMESPACE
  labels:
    app: throughput-server
spec:
  containers:
  - name: iperf3-server
    image: networkstatic/iperf3:latest
    command: ["iperf3", "-s"]
    ports:
    - containerPort: 5201
  restartPolicy: Never
EOF

    if [[ $? -eq 0 ]]; then
        # Create service for server
        $KUBECTL_CMD expose pod "$server_pod" --port=5201 --target-port=5201 -n "$TEST_NAMESPACE" >/dev/null 2>&1

        # Wait for server pod to be ready
        if wait_for_pod_ready "$server_pod" "$TEST_NAMESPACE" 60; then
            local server_ip
            server_ip=$($KUBECTL_CMD get pod "$server_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)

            if [[ -n "$server_ip" ]]; then
                log_info "Server pod ready at $server_ip"

                # Create client pod
                cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $client_pod
  namespace: $TEST_NAMESPACE
spec:
  containers:
  - name: iperf3-client
    image: networkstatic/iperf3:latest
    command: ["sleep", "300"]
  restartPolicy: Never
EOF

                if wait_for_pod_ready "$client_pod" "$TEST_NAMESPACE" 60; then
                    # Run throughput test
                    local throughput_result
                    if throughput_result=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- iperf3 -c "$server_ip" -t 10 -f M 2>/dev/null | grep "receiver" | tail -n1); then
                        local throughput=$(echo "$throughput_result" | awk '{print $(NF-1), $NF}')
                        log_success "Pod-to-pod throughput: $throughput"

                        # Extract numeric value for comparison
                        local throughput_mbps=$(echo "$throughput_result" | awk '{print $(NF-1)}' | sed 's/[^0-9.]//g')
                        if [[ -n "$throughput_mbps" ]]; then
                            if (( $(echo "$throughput_mbps > 100" | bc -l 2>/dev/null || echo "0") )); then
                                log_success "Network performance: Excellent (>100 Mbps)"
                            elif (( $(echo "$throughput_mbps > 50" | bc -l 2>/dev/null || echo "0") )); then
                                log_success "Network performance: Good (>50 Mbps)"
                            elif (( $(echo "$throughput_mbps > 10" | bc -l 2>/dev/null || echo "0") )); then
                                log_warning "Network performance: Acceptable (>10 Mbps)"
                            else
                                log_error "Network performance: Poor (<10 Mbps)"
                            fi
                        fi
                    else
                        log_error "Failed to run throughput test"
                    fi
                else
                    log_error "Client pod failed to become ready"
                fi
            else
                log_error "Could not get server pod IP"
            fi
        else
            log_error "Server pod failed to become ready"
        fi
    else
        log_error "Failed to create throughput test server"
    fi
}

test_service_throughput() {
    start_test "Service-based network throughput"

    local service_name="throughput-service-$(date +%s)"
    local deployment_name="throughput-deploy-$(date +%s)"
    local client_pod="service-client-$(date +%s)"

    # Create deployment with iperf3 server
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $deployment_name
  namespace: $TEST_NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: throughput-service-test
  template:
    metadata:
      labels:
        app: throughput-service-test
    spec:
      containers:
      - name: iperf3-server
        image: networkstatic/iperf3:latest
        command: ["iperf3", "-s"]
        ports:
        - containerPort: 5201
---
apiVersion: v1
kind: Service
metadata:
  name: $service_name
  namespace: $TEST_NAMESPACE
spec:
  selector:
    app: throughput-service-test
  ports:
  - port: 5201
    targetPort: 5201
EOF

    if [[ $? -eq 0 ]]; then
        # Wait for deployment to be ready
        if wait_for_deployment_ready "$deployment_name" "$TEST_NAMESPACE" 60; then
            # Create client pod
            create_test_pod "$client_pod" "networkstatic/iperf3:latest" "$TEST_NAMESPACE" "sleep 300"

            if wait_for_pod_ready "$client_pod" "$TEST_NAMESPACE" 60; then
                # Test service throughput
                local service_result
                if service_result=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- iperf3 -c "$service_name.$TEST_NAMESPACE.svc.cluster.local" -t 5 -f M 2>/dev/null | grep "receiver" | tail -n1); then
                    local service_throughput=$(echo "$service_result" | awk '{print $(NF-1), $NF}')
                    log_success "Service throughput: $service_throughput"
                else
                    log_error "Failed to test service throughput"
                fi
            else
                log_error "Service client pod failed to become ready"
            fi
        else
            log_error "Throughput service deployment failed to become ready"
        fi
    else
        log_error "Failed to create throughput service test"
    fi
}

test_cross_node_throughput() {
    start_test "Cross-node network throughput"

    # Get list of nodes
    local nodes_array=()
    while IFS= read -r node; do
        if [[ -n "$node" ]]; then
            nodes_array+=("$node")
        fi
    done < <($KUBECTL_CMD get nodes --no-headers -o custom-columns=":metadata.name" 2>/dev/null)

    if [[ ${#nodes_array[@]} -ge 2 ]]; then
        local server_pod="cross-node-server-$(date +%s)"
        local client_pod="cross-node-client-$(date +%s)"

        log_info "Testing cross-node throughput between ${nodes_array[0]} and ${nodes_array[1]}"

        # Create server pod on first node
        cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $server_pod
  namespace: $TEST_NAMESPACE
spec:
  nodeName: ${nodes_array[0]}
  containers:
  - name: iperf3-server
    image: networkstatic/iperf3:latest
    command: ["iperf3", "-s"]
  restartPolicy: Never
EOF

        # Create client pod on second node
        cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $client_pod
  namespace: $TEST_NAMESPACE
spec:
  nodeName: ${nodes_array[1]}
  containers:
  - name: iperf3-client
    image: networkstatic/iperf3:latest
    command: ["sleep", "300"]
  restartPolicy: Never
EOF

        if wait_for_pod_ready "$server_pod" "$TEST_NAMESPACE" 60 && wait_for_pod_ready "$client_pod" "$TEST_NAMESPACE" 60; then
            local server_ip
            server_ip=$($KUBECTL_CMD get pod "$server_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)

            if [[ -n "$server_ip" ]]; then
                local cross_node_result
                if cross_node_result=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- iperf3 -c "$server_ip" -t 10 -f M 2>/dev/null | grep "receiver" | tail -n1); then
                    local cross_throughput=$(echo "$cross_node_result" | awk '{print $(NF-1), $NF}')
                    log_success "Cross-node throughput: $cross_throughput"
                else
                    log_error "Failed to test cross-node throughput"
                fi
            else
                log_error "Could not get cross-node server IP"
            fi
        else
            log_error "Cross-node test pods failed to become ready"
        fi
    else
        log_info "Single node cluster - skipping cross-node throughput test"
    fi
}

test_concurrent_connections() {
    start_test "Concurrent connection performance"

    local server_pod="concurrent-server-$(date +%s)"
    local num_clients=5

    # Create server pod
    create_test_pod "$server_pod" "networkstatic/iperf3:latest" "$TEST_NAMESPACE" "iperf3 -s"

    if wait_for_pod_ready "$server_pod" "$TEST_NAMESPACE" 60; then
        local server_ip
        server_ip=$($KUBECTL_CMD get pod "$server_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)

        if [[ -n "$server_ip" ]]; then
            local client_pids=()
            local total_throughput=0
            local successful_clients=0

            # Start multiple client pods
            for i in $(seq 1 $num_clients); do
                local client_pod="concurrent-client-${i}-$(date +%s)"
                create_test_pod "$client_pod" "networkstatic/iperf3:latest" "$TEST_NAMESPACE" "sleep 300" &
            done
            wait  # Wait for all client pods to be created

            # Run concurrent tests
            for i in $(seq 1 $num_clients); do
                local client_pod="concurrent-client-${i}-$(date +%s)"
                if wait_for_pod_ready "$client_pod" "$TEST_NAMESPACE" 30; then
                    local client_result
                    if client_result=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- iperf3 -c "$server_ip" -t 5 -f M -P 1 2>/dev/null | grep "receiver" | tail -n1); then
                        local client_throughput=$(echo "$client_result" | awk '{print $(NF-1)}' | sed 's/[^0-9.]//g')
                        if [[ -n "$client_throughput" ]]; then
                            total_throughput=$(echo "$total_throughput + $client_throughput" | bc -l 2>/dev/null || echo "$total_throughput")
                            ((successful_clients++))
                        fi
                    fi
                fi
            done

            if [[ $successful_clients -gt 0 ]]; then
                log_success "Concurrent connections: $successful_clients/$num_clients successful"
                local avg_throughput=$(echo "scale=2; $total_throughput / $successful_clients" | bc -l 2>/dev/null || echo "0")
                log_success "Average concurrent throughput: ${avg_throughput} Mbps"
            else
                log_error "No concurrent connections succeeded"
            fi
        else
            log_error "Could not get concurrent test server IP"
        fi
    else
        log_error "Concurrent test server failed to become ready"
    fi
}

test_dns_resolution_performance() {
    start_test "DNS resolution performance"

    local test_pod="dns-perf-$(date +%s)"

    create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 300"

    if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then
        # Test DNS resolution time for cluster services
        local dns_targets=("kubernetes.default.svc.cluster.local" "kube-dns.kube-system.svc.cluster.local")
        local successful_resolutions=0
        local total_time=0

        for target in "${dns_targets[@]}"; do
            local start_time=$(date +%s.%N)
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- nslookup "$target" >/dev/null 2>&1; then
                local end_time=$(date +%s.%N)
                local resolution_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
                total_time=$(echo "$total_time + $resolution_time" | bc -l 2>/dev/null || echo "$total_time")
                ((successful_resolutions++))
                log_debug "DNS resolution for $target: ${resolution_time}s"
            fi
        done

        if [[ $successful_resolutions -gt 0 ]]; then
            local avg_dns_time=$(echo "scale=3; $total_time / $successful_resolutions" | bc -l 2>/dev/null || echo "0")
            log_success "Average DNS resolution time: ${avg_dns_time}s"

            if (( $(echo "$avg_dns_time < 0.1" | bc -l 2>/dev/null || echo "0") )); then
                log_success "DNS performance: Excellent (<100ms)"
            elif (( $(echo "$avg_dns_time < 0.5" | bc -l 2>/dev/null || echo "0") )); then
                log_success "DNS performance: Good (<500ms)"
            elif (( $(echo "$avg_dns_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "DNS performance: Acceptable (<1s)"
            else
                log_error "DNS performance: Poor (>=1s)"
            fi
        else
            log_error "No DNS resolutions succeeded"
        fi
    else
        log_error "DNS performance test pod failed to become ready"
    fi
}

# Main execution
run_network_throughput() {
    start_test_module "Network Throughput Performance"

    test_pod_to_pod_throughput
    test_service_throughput
    test_cross_node_throughput
    test_concurrent_connections
    test_dns_resolution_performance
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_network_throughput
    cleanup_framework
fi
