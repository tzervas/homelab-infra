#!/bin/bash
# K3s Agent-Server Communication Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_server_agent_connectivity() {
    start_test "K3s server-agent connectivity"

    # Get all nodes and check their roles
    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes --no-headers 2>/dev/null); then
        local server_nodes=0
        local agent_nodes=0
        local total_nodes=0

        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((total_nodes++))
                local node_name=$(echo "$line" | awk '{print $1}')
                local node_roles=$(echo "$line" | awk '{print $3}')

                if [[ "$node_roles" == *"control-plane"* ]] || [[ "$node_roles" == *"master"* ]]; then
                    ((server_nodes++))
                    log_debug "Server node: $node_name"
                else
                    ((agent_nodes++))
                    log_debug "Agent node: $node_name"
                fi
            fi
        done <<< "$nodes_output"

        log_success "Node inventory: $server_nodes server(s), $agent_nodes agent(s), $total_nodes total"

        if [[ $server_nodes -gt 0 && $agent_nodes -gt 0 ]]; then
            log_success "Mixed server-agent topology detected"
        elif [[ $server_nodes -gt 0 && $agent_nodes -eq 0 ]]; then
            log_info "Server-only topology (no separate agents)"
        else
            log_warning "Unusual node topology detected"
        fi
    else
        log_error "Unable to retrieve node information"
    fi
}

test_node_registration() {
    start_test "Node registration status"

    # Check that all nodes are in Ready state
    local ready_nodes=0
    local total_nodes=0
    local not_ready_nodes=()

    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes --no-headers 2>/dev/null); then
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((total_nodes++))
                local node_name=$(echo "$line" | awk '{print $1}')
                local node_status=$(echo "$line" | awk '{print $2}')

                if [[ "$node_status" == "Ready" ]]; then
                    ((ready_nodes++))
                else
                    not_ready_nodes+=("$node_name ($node_status)")
                fi
            fi
        done <<< "$nodes_output"

        if [[ $ready_nodes -eq $total_nodes ]]; then
            log_success "All nodes are Ready ($ready_nodes/$total_nodes)"
        else
            log_error "Some nodes are not Ready ($ready_nodes/$total_nodes)"
            for node in "${not_ready_nodes[@]}"; do
                log_error "Not ready: $node"
            done
        fi
    else
        log_error "Unable to check node registration status"
    fi
}

test_k3s_token_validation() {
    start_test "K3s token and certificate validation"

    # Check for K3s specific secrets that indicate proper agent-server auth
    local k3s_secrets=0

    # Look for K3s serving certificates
    if $KUBECTL_CMD get secret k3s-serving -n kube-system >/dev/null 2>&1; then
        ((k3s_secrets++))
        log_success "K3s serving certificate found"
    else
        log_info "K3s serving certificate not found (may use different naming)"
    fi

    # Look for service account token
    if $KUBECTL_CMD get secret -n kube-system | grep -q "k3s.*token" 2>/dev/null; then
        ((k3s_secrets++))
        log_success "K3s service account tokens found"
    else
        log_info "K3s specific service account tokens not found"
    fi

    # Check for node client certificates
    local node_certs=0
    if $KUBECTL_CMD get csr 2>/dev/null | grep -q "node-csr" || \
       $KUBECTL_CMD get secrets -A | grep -q "kubelet-client" 2>/dev/null; then
        ((node_certs++))
        log_success "Node client certificates found"
    else
        log_info "Node client certificates not visible (expected in K3s)"
    fi

    if [[ $k3s_secrets -gt 0 || $node_certs -gt 0 ]]; then
        log_success "K3s authentication components present"
    else
        log_warning "Unable to verify K3s authentication setup"
    fi
}

test_cluster_communication() {
    start_test "Inter-node cluster communication"

    # Create a daemonset to test communication across all nodes
    local ds_name="k3s-comm-test-$(date +%s)"

    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: $ds_name
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  selector:
    matchLabels:
      app: k3s-comm-test
  template:
    metadata:
      labels:
        app: k3s-comm-test
    spec:
      containers:
      - name: test-container
        image: busybox:1.35
        command: ["/bin/sh", "-c", "while true; do echo 'Node communication test'; sleep 30; done"]
      tolerations:
      - operator: Exists
      restartPolicy: Always
EOF

    if [[ $? -eq 0 ]]; then
        log_info "Created test DaemonSet to verify node communication"

        # Wait for daemonset to be scheduled
        sleep 10

        # Check if pods are running on multiple nodes
        local running_pods=0
        local nodes_with_pods=()

        local pods_output
        if pods_output=$($KUBECTL_CMD get pods -n "$TEST_NAMESPACE" -l app=k3s-comm-test -o wide --no-headers 2>/dev/null); then
            while IFS= read -r line; do
                if [[ -n "$line" ]]; then
                    local pod_status=$(echo "$line" | awk '{print $3}')
                    local node_name=$(echo "$line" | awk '{print $7}')

                    if [[ "$pod_status" == "Running" ]]; then
                        ((running_pods++))
                        if [[ ! " ${nodes_with_pods[@]} " =~ " ${node_name} " ]]; then
                            nodes_with_pods+=("$node_name")
                        fi
                    fi
                fi
            done <<< "$pods_output"

            if [[ $running_pods -gt 0 ]]; then
                log_success "Communication test pods running on ${#nodes_with_pods[@]} node(s): $running_pods pods total"
            else
                log_error "No communication test pods are running"
            fi
        else
            log_warning "Unable to verify test pod distribution"
        fi

        # Cleanup
        $KUBECTL_CMD delete daemonset "$ds_name" -n "$TEST_NAMESPACE" >/dev/null 2>&1 || true
    else
        log_error "Failed to create test DaemonSet"
    fi
}

test_k3s_agent_logs() {
    start_test "K3s agent process health"

    # Try to check K3s agent/server processes on nodes
    # This is limited since we're running from within the cluster

    # Check for K3s related pods in kube-system
    local k3s_system_pods=0

    # Look for K3s server pods (may not exist in all setups)
    if $KUBECTL_CMD get pods -n kube-system -l app=k3s-server --no-headers 2>/dev/null | grep -q "Running"; then
        ((k3s_system_pods++))
        log_success "K3s server pods are running"
    fi

    # Look for K3s agent pods (may not exist in all setups)
    if $KUBECTL_CMD get pods -n kube-system -l app=k3s-agent --no-headers 2>/dev/null | grep -q "Running"; then
        ((k3s_system_pods++))
        log_success "K3s agent pods are running"
    fi

    # Check kubelet readiness across all nodes
    local kubelet_ready_nodes=0
    if $KUBECTL_CMD get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -q "True"; then
        kubelet_ready_nodes=$(kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | tr ' ' '\n' | grep -c "True" || echo "0")
        log_success "Kubelet ready on $kubelet_ready_nodes node(s)"
    else
        log_error "Unable to verify kubelet readiness"
    fi

    if [[ $k3s_system_pods -gt 0 || $kubelet_ready_nodes -gt 0 ]]; then
        log_success "K3s agent/server processes appear healthy"
    else
        log_info "K3s processes health cannot be fully verified from cluster"
    fi
}

test_cluster_networking() {
    start_test "Cross-node networking in K3s"

    # Create pods on different nodes and test connectivity
    local test_pod1="net-test-1-$(date +%s)"
    local test_pod2="net-test-2-$(date +%s)"

    # Get list of nodes for pod placement
    local nodes_array=()
    while IFS= read -r node; do
        if [[ -n "$node" ]]; then
            nodes_array+=("$node")
        fi
    done < <($KUBECTL_CMD get nodes --no-headers -o custom-columns=":metadata.name" 2>/dev/null)

    if [[ ${#nodes_array[@]} -ge 2 ]]; then
        # Create pods on different nodes
        log_info "Testing cross-node communication between ${nodes_array[0]} and ${nodes_array[1]}"

        # Create first pod on first node
        cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $test_pod1
  namespace: $TEST_NAMESPACE
spec:
  nodeName: ${nodes_array[0]}
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["/bin/sh", "-c", "sleep 120"]
  restartPolicy: Never
EOF

        # Create second pod on second node
        cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $test_pod2
  namespace: $TEST_NAMESPACE
spec:
  nodeName: ${nodes_array[1]}
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["/bin/sh", "-c", "sleep 120"]
  restartPolicy: Never
EOF

        # Wait for pods to be ready
        if wait_for_pod_ready "$test_pod1" "$TEST_NAMESPACE" 60 && wait_for_pod_ready "$test_pod2" "$TEST_NAMESPACE" 60; then
            # Get pod IPs
            local pod1_ip
            local pod2_ip
            pod1_ip=$($KUBECTL_CMD get pod "$test_pod1" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)
            pod2_ip=$($KUBECTL_CMD get pod "$test_pod2" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null)

            if [[ -n "$pod1_ip" && -n "$pod2_ip" ]]; then
                # Test connectivity from pod1 to pod2
                if $KUBECTL_CMD exec "$test_pod1" -n "$TEST_NAMESPACE" -- ping -c 3 "$pod2_ip" >/dev/null 2>&1; then
                    log_success "Cross-node pod communication successful ($pod1_ip -> $pod2_ip)"
                else
                    log_error "Cross-node pod communication failed"
                fi
            else
                log_error "Unable to get pod IP addresses"
            fi
        else
            log_error "Test pods failed to become ready"
        fi
    else
        log_info "Single node cluster - skipping cross-node communication test"
    fi
}

# Main execution
run_agent_server_comm() {
    start_test_module "K3s Agent-Server Communication"

    test_server_agent_connectivity
    test_node_registration
    test_k3s_token_validation
    test_cluster_communication
    test_k3s_agent_logs
    test_cluster_networking
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_agent_server_comm
    cleanup_framework
fi
