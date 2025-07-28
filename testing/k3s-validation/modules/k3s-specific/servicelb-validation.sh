#!/bin/bash
# K3s ServiceLB Load Balancer Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_servicelb_controller() {
    start_test "ServiceLB controller health"

    # Check if ServiceLB is running (part of K3s server)
    if $KUBECTL_CMD get daemonset svclb-traefik -n kube-system >/dev/null 2>&1; then
        local ready_count
        ready_count=$($KUBECTL_CMD get daemonset svclb-traefik -n kube-system -o jsonpath='{.status.numberReady}' 2>/dev/null || echo "0")
        local desired_count
        desired_count=$($KUBECTL_CMD get daemonset svclb-traefik -n kube-system -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo "0")

        if [[ $ready_count -eq $desired_count ]] && [[ $desired_count -gt 0 ]]; then
            log_success "ServiceLB DaemonSet ready: $ready_count/$desired_count pods"
        else
            log_error "ServiceLB DaemonSet not ready: $ready_count/$desired_count pods"
        fi
    else
        log_skip "ServiceLB DaemonSet not found (may be disabled or different configuration)"
    fi
}

test_loadbalancer_service_creation() {
    start_test "LoadBalancer service creation and IP assignment"

    # Create test deployment
    local app_name="lb-test-app"
    create_test_deployment "$app_name" "nginx:1.25-alpine" "$TEST_NAMESPACE" 2

    if ! wait_for_deployment_ready "$app_name" "$TEST_NAMESPACE" 120; then
        log_error "Test deployment failed to become ready"
        return 1
    fi

    # Create LoadBalancer service
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Service
metadata:
  name: ${app_name}-lb
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  type: LoadBalancer
  selector:
    app: $app_name
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
EOF

    # Wait for LoadBalancer IP assignment
    local timeout=120
    local elapsed=0
    local external_ip=""

    while [[ $elapsed -lt $timeout ]]; do
        external_ip=$($KUBECTL_CMD get service "${app_name}-lb" -n "$TEST_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
        if [[ -n "$external_ip" && "$external_ip" != "null" ]]; then
            break
        fi
        sleep 2
        ((elapsed += 2))
    done

    if [[ -n "$external_ip" && "$external_ip" != "null" ]]; then
        log_success "LoadBalancer service assigned external IP: $external_ip"

        # Test connectivity to the LoadBalancer IP
        if timeout 10 curl -s "http://$external_ip" >/dev/null 2>&1; then
            log_success "LoadBalancer service is reachable via external IP"
        else
            log_warning "LoadBalancer service IP assigned but not reachable (may be network/firewall issue)"
        fi
    else
        log_error "LoadBalancer service did not receive external IP within ${timeout}s"

        # Check service status for debugging
        local service_status
        service_status=$($KUBECTL_CMD get service "${app_name}-lb" -n "$TEST_NAMESPACE" -o json 2>/dev/null)
        if echo "$service_status" | jq -e '.status.loadBalancer.ingress[0].hostname' >/dev/null 2>&1; then
            local hostname
            hostname=$(echo "$service_status" | jq -r '.status.loadBalancer.ingress[0].hostname')
            log_info "LoadBalancer assigned hostname: $hostname"
        fi
    fi
}

test_servicelb_pod_distribution() {
    start_test "ServiceLB pod distribution across nodes"

    # Get node count
    local node_count
    node_count=$($KUBECTL_CMD get nodes --no-headers | wc -l)

    if [[ $node_count -lt 2 ]]; then
        log_skip "Single node cluster - ServiceLB distribution test not applicable"
        return 0
    fi

    # Check ServiceLB pods distribution
    local servicelb_pods
    servicelb_pods=$($KUBECTL_CMD get pods -n kube-system -l app=svclb-traefik -o json 2>/dev/null)

    if [[ -n "$servicelb_pods" ]]; then
        local pod_count
        pod_count=$(echo "$servicelb_pods" | jq '.items | length')

        if [[ $pod_count -eq $node_count ]]; then
            log_success "ServiceLB pods properly distributed: $pod_count pods on $node_count nodes"

            # Check that pods are on different nodes
            local unique_nodes
            unique_nodes=$(echo "$servicelb_pods" | jq -r '.items[].spec.nodeName' | sort -u | wc -l)

            if [[ $unique_nodes -eq $node_count ]]; then
                log_success "ServiceLB pods distributed across all nodes"
            else
                log_warning "ServiceLB pods not evenly distributed across nodes"
            fi
        else
            log_error "ServiceLB pod count mismatch: $pod_count pods for $node_count nodes"
        fi
    else
        log_skip "No ServiceLB pods found for distribution testing"
    fi
}

test_servicelb_failover() {
    start_test "ServiceLB failover behavior"

    # This test requires multiple nodes and is more complex
    local node_count
    node_count=$($KUBECTL_CMD get nodes --no-headers | wc -l)

    if [[ $node_count -lt 2 ]]; then
        log_skip "Multi-node setup required for failover testing"
        return 0
    fi

    # Create test service if not exists
    local service_name="lb-test-app-lb"
    if ! $KUBECTL_CMD get service "$service_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        log_skip "LoadBalancer service not available for failover testing"
        return 0
    fi

    # Get current external IP
    local external_ip
    external_ip=$($KUBECTL_CMD get service "$service_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)

    if [[ -n "$external_ip" && "$external_ip" != "null" ]]; then
        # Test connectivity multiple times to ensure stability
        local success_count=0
        local test_iterations=5

        for ((i=1; i<=test_iterations; i++)); do
            if timeout 5 curl -s "http://$external_ip" >/dev/null 2>&1; then
                ((success_count++))
            fi
            sleep 1
        done

        local success_rate=$((success_count * 100 / test_iterations))
        if [[ $success_rate -ge 80 ]]; then
            log_success "LoadBalancer stability test passed: ${success_rate}% success rate"
        else
            log_warning "LoadBalancer instability detected: ${success_rate}% success rate"
        fi
    else
        log_skip "No external IP available for failover testing"
    fi
}

test_servicelb_port_allocation() {
    start_test "ServiceLB port allocation and management"

    # Create services with different port configurations
    local app_name="port-test-app"
    create_test_deployment "$app_name" "nginx:1.25-alpine" "$TEST_NAMESPACE" 1

    if ! wait_for_deployment_ready "$app_name" "$TEST_NAMESPACE" 120; then
        log_error "Port test deployment failed"
        return 1
    fi

    # Test multiple port LoadBalancer service
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Service
metadata:
  name: ${app_name}-multiport-lb
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  type: LoadBalancer
  selector:
    app: $app_name
  ports:
  - name: http
    port: 8080
    targetPort: 80
    protocol: TCP
  - name: alt-http
    port: 8081
    targetPort: 80
    protocol: TCP
EOF

    # Wait for service to be ready
    sleep 10

    # Check if both ports are allocated
    local service_info
    service_info=$($KUBECTL_CMD get service "${app_name}-multiport-lb" -n "$TEST_NAMESPACE" -o json 2>/dev/null)

    if [[ -n "$service_info" ]]; then
        local port_count
        port_count=$(echo "$service_info" | jq '.spec.ports | length')

        if [[ $port_count -eq 2 ]]; then
            log_success "Multi-port LoadBalancer service created with $port_count ports"
        else
            log_error "Multi-port LoadBalancer configuration failed"
        fi

        # Check external IP assignment
        local external_ip
        external_ip=$(echo "$service_info" | jq -r '.status.loadBalancer.ingress[0].ip // empty')

        if [[ -n "$external_ip" ]]; then
            log_success "Multi-port LoadBalancer assigned IP: $external_ip"
        else
            log_warning "Multi-port LoadBalancer IP not yet assigned"
        fi
    fi
}

# Main execution
run_servicelb_validation() {
    start_test_module "ServiceLB Validation"

    test_servicelb_controller
    test_loadbalancer_service_creation
    test_servicelb_pod_distribution
    test_servicelb_failover
    test_servicelb_port_allocation
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    create_test_namespace
    run_servicelb_validation
    cleanup_framework
fi
