#!/bin/bash
# Core Kubernetes Node Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_node_readiness() {
    start_test "Node readiness status"

    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        local ready_nodes
        ready_nodes=$(echo "$nodes_output" | jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status=="True")) | .metadata.name' | wc -l)
        local total_nodes
        total_nodes=$(echo "$nodes_output" | jq -r '.items | length')

        if [[ $ready_nodes -eq $total_nodes ]] && [[ $total_nodes -gt 0 ]]; then
            log_success "All $total_nodes nodes are ready"

            # List node names and roles
            echo "$nodes_output" | jq -r '.items[] | "\(.metadata.name): \(.metadata.labels."kubernetes.io/role" // "worker")"' | while read -r line; do
                log_info "Node: $line"
            done
        else
            log_error "Only $ready_nodes out of $total_nodes nodes are ready"

            # Show which nodes are not ready
            echo "$nodes_output" | jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status!="True")) | .metadata.name' | while read -r node; do
                log_error "Node not ready: $node"
            done
        fi
    else
        log_error "Cannot retrieve node status"
        return 1
    fi
}

test_node_resources() {
    start_test "Node resource capacity and allocation"

    local nodes_capacity
    if nodes_capacity=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        # Calculate total cluster capacity
        local total_cpu total_memory_kb
        total_cpu=$(echo "$nodes_capacity" | jq -r '.items[].status.capacity.cpu' | awk '{sum += $1} END {print sum}')
        total_memory_kb=$(echo "$nodes_capacity" | jq -r '.items[].status.capacity.memory' | sed 's/Ki$//' | awk '{sum += $1} END {print sum}')
        local total_memory_gb=$(echo "scale=2; $total_memory_kb / 1024 / 1024" | bc -l 2>/dev/null || echo "0")

        log_success "Cluster total capacity - CPU: $total_cpu cores, Memory: ${total_memory_gb}GB"

        # Show per-node capacity
        echo "$nodes_capacity" | jq -r '.items[] | "\(.metadata.name): CPU=\(.status.capacity.cpu), Memory=\(.status.capacity.memory)"' | while read -r line; do
            log_info "$line"
        done

        # Check for resource pressure
        local pressure_nodes
        pressure_nodes=$(echo "$nodes_capacity" | jq -r '.items[] | select(.status.conditions[] | select(.type=="MemoryPressure" and .status=="True")) | .metadata.name' | wc -l)

        if [[ $pressure_nodes -eq 0 ]]; then
            log_success "No nodes under memory pressure"
        else
            log_warning "$pressure_nodes node(s) under memory pressure"
        fi

        pressure_nodes=$(echo "$nodes_capacity" | jq -r '.items[] | select(.status.conditions[] | select(.type=="DiskPressure" and .status=="True")) | .metadata.name' | wc -l)

        if [[ $pressure_nodes -eq 0 ]]; then
            log_success "No nodes under disk pressure"
        else
            log_error "$pressure_nodes node(s) under disk pressure"
        fi
    else
        log_error "Cannot retrieve node capacity information"
    fi
}

test_node_kubelet_health() {
    start_test "Kubelet health on nodes"

    # Check kubelet readiness
    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        local kubelet_ready_count=0
        local total_nodes
        total_nodes=$(echo "$nodes_output" | jq -r '.items | length')

        # Check KubeletReady condition
        while IFS= read -r node_name; do
            local kubelet_ready
            kubelet_ready=$(echo "$nodes_output" | jq -r --arg node "$node_name" '.items[] | select(.metadata.name==$node) | .status.conditions[] | select(.type=="KubeletReady") | .status')

            if [[ "$kubelet_ready" == "True" ]]; then
                ((kubelet_ready_count++))
                log_debug "Kubelet ready on node: $node_name"
            else
                log_warning "Kubelet not ready on node: $node_name"
            fi
        done < <(echo "$nodes_output" | jq -r '.items[].metadata.name')

        if [[ $kubelet_ready_count -eq $total_nodes ]]; then
            log_success "Kubelet is healthy on all $total_nodes nodes"
        else
            log_error "Kubelet issues detected: $kubelet_ready_count/$total_nodes nodes healthy"
        fi
    else
        log_error "Cannot check kubelet health"
    fi
}

test_node_labels_and_taints() {
    start_test "Node labels and taints configuration"

    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        # Check for master/control-plane nodes
        local master_nodes
        master_nodes=$(echo "$nodes_output" | jq -r '.items[] | select(.metadata.labels."kubernetes.io/role"=="master" or .metadata.labels."node-role.kubernetes.io/control-plane"=="true") | .metadata.name' | wc -l)

        if [[ $master_nodes -gt 0 ]]; then
            log_success "Found $master_nodes control-plane node(s)"
        else
            log_info "No dedicated control-plane nodes (single-node or worker-only cluster)"
        fi

        # Check for worker nodes
        local worker_nodes
        worker_nodes=$(echo "$nodes_output" | jq -r '.items[] | select(.metadata.labels."kubernetes.io/role"=="worker" or (.metadata.labels."kubernetes.io/role" | not))' | wc -l)

        if [[ $worker_nodes -gt 0 ]]; then
            log_success "Found $worker_nodes worker node(s)"
        fi

        # Check for taints on control-plane nodes
        local tainted_nodes
        tainted_nodes=$(echo "$nodes_output" | jq -r '.items[] | select(.spec.taints) | .metadata.name' | wc -l)

        if [[ $tainted_nodes -gt 0 ]]; then
            log_info "$tainted_nodes node(s) have taints configured"

            # Show taint details
            echo "$nodes_output" | jq -r '.items[] | select(.spec.taints) | "\(.metadata.name): \(.spec.taints[].key)=\(.spec.taints[].value):\(.spec.taints[].effect)"' | while read -r line; do
                log_debug "Taint: $line"
            done
        else
            log_info "No node taints configured"
        fi
    else
        log_error "Cannot retrieve node labels and taints"
    fi
}

test_node_system_info() {
    start_test "Node system information"

    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        # Get system information for each node
        echo "$nodes_output" | jq -r '.items[] | "\(.metadata.name)|\(.status.nodeInfo.osImage)|\(.status.nodeInfo.kernelVersion)|\(.status.nodeInfo.containerRuntimeVersion)"' | while IFS='|' read -r node_name os_image kernel_version runtime_version; do
            log_info "Node $node_name:"
            log_info "  OS: $os_image"
            log_info "  Kernel: $kernel_version"
            log_info "  Runtime: $runtime_version"
        done

        # Check for consistent runtime across nodes
        local runtime_versions
        runtime_versions=$(echo "$nodes_output" | jq -r '.items[].status.nodeInfo.containerRuntimeVersion' | sort -u | wc -l)

        if [[ $runtime_versions -eq 1 ]]; then
            log_success "Consistent container runtime across all nodes"
        else
            log_warning "Multiple container runtime versions detected"
        fi

        # Check Kubernetes version consistency
        local kubelet_versions
        kubelet_versions=$(echo "$nodes_output" | jq -r '.items[].status.nodeInfo.kubeletVersion' | sort -u | wc -l)

        if [[ $kubelet_versions -eq 1 ]]; then
            log_success "Consistent Kubernetes version across all nodes"
        else
            log_warning "Multiple Kubernetes versions detected (upgrade in progress?)"
        fi
    else
        log_error "Cannot retrieve node system information"
    fi
}

# Main execution
run_node_validation() {
    start_test_module "Node Validation"

    test_node_readiness
    test_node_resources
    test_node_kubelet_health
    test_node_labels_and_taints
    test_node_system_info
}

# Allow running this module independently
# Main function for orchestrator compatibility
main() {
    run_node_validation
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_node_validation
    cleanup_framework
fi
