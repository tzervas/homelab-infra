#!/bin/bash

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_WAIT_TIME=300  # 5 minutes
CHECK_INTERVAL=10  # Check every 10 seconds
CLUSTER_IP="${K3S_MASTER_IP:-192.168.16.26}"
CLUSTER_PORT="${K3S_PORT:-6443}"  # K3s default port
VM_HOST_IP="${VM_HOST_IP:-192.168.1.100}"  # Adjust to your VM host IP
HOMELAB_SERVER="${HOMELAB_SERVER:-homelab}"  # Your homelab server hostname/IP

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}K3s Deployment Stabilization & Setup${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to setup SSH port forwarding
setup_port_forwarding() {
    echo -e "\n${YELLOW}Setting up port forwarding...${NC}"

    # Check if we need to set up SSH tunnel to homelab server
    if [[ -n "${SSH_TUNNEL_NEEDED:-}" ]]; then
        echo "Setting up SSH tunnel to homelab server..."

        # Kill any existing SSH tunnels for the same port
        existing_tunnel=$(ps aux | grep "ssh.*-L.*:${CLUSTER_PORT}:${CLUSTER_IP}:${CLUSTER_PORT}" | grep -v grep | awk '{print $2}' || true)
        if [[ -n "$existing_tunnel" ]]; then
            echo "Killing existing SSH tunnel (PID: $existing_tunnel)"
            kill $existing_tunnel 2>/dev/null || true
            sleep 2
        fi

        # Create SSH tunnel
        ssh -f -N -L ${CLUSTER_PORT}:${CLUSTER_IP}:${CLUSTER_PORT} ${HOMELAB_SERVER} \
            -o ServerAliveInterval=60 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes

        echo -e "${GREEN}SSH tunnel established${NC}"
        echo "Local port ${CLUSTER_PORT} -> ${HOMELAB_SERVER} -> ${CLUSTER_IP}:${CLUSTER_PORT}"

        # Update kubeconfig to use localhost
        if [[ -f "$HOME/.kube/config" ]]; then
            echo "Updating kubeconfig to use localhost:${CLUSTER_PORT}..."
            sed -i.bak "s|https://${CLUSTER_IP}:${CLUSTER_PORT}|https://localhost:${CLUSTER_PORT}|g" "$HOME/.kube/config"
        fi
    fi

    # Setup any additional port forwards for services
    echo -e "\n${YELLOW}Port forwarding setup:${NC}"
    echo "- K3s API Server: ${CLUSTER_IP}:${CLUSTER_PORT}"
    if [[ -n "${SSH_TUNNEL_NEEDED:-}" ]]; then
        echo "- Local access via: localhost:${CLUSTER_PORT}"
    fi
}

# Function to check if cluster is accessible
check_cluster_api() {
    kubectl get nodes &>/dev/null
}

# Function to wait for cluster
wait_for_cluster() {
    echo -e "\n${YELLOW}Waiting for K3s cluster to become ready...${NC}"
    echo "Cluster endpoint: https://${CLUSTER_IP}:${CLUSTER_PORT}"

    start_time=$(date +%s)
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))

        if [ $elapsed -gt $MAX_WAIT_TIME ]; then
            echo -e "${RED}Timeout: Cluster did not become ready within ${MAX_WAIT_TIME} seconds${NC}"

            # Try to diagnose the issue
            echo -e "\n${YELLOW}Diagnostic information:${NC}"
            echo "1. Testing network connectivity to ${CLUSTER_IP}..."
            if ping -c 1 -W 2 ${CLUSTER_IP} &>/dev/null; then
                echo -e "   ${GREEN}Host is reachable${NC}"
            else
                echo -e "   ${RED}Host is not reachable${NC}"
            fi

            echo "2. Testing port ${CLUSTER_PORT}..."
            if nc -zv -w 2 ${CLUSTER_IP} ${CLUSTER_PORT} &>/dev/null; then
                echo -e "   ${GREEN}Port is open${NC}"
            else
                echo -e "   ${RED}Port is closed or filtered${NC}"
            fi

            echo "3. Checking kubeconfig..."
            echo "   KUBECONFIG=${KUBECONFIG:-$HOME/.kube/config}"

            return 1
        fi

        if check_cluster_api; then
            echo -e "${GREEN}Cluster API is accessible!${NC}"
            break
        else
            echo "Waiting for cluster API... (${elapsed}s elapsed)"
            sleep $CHECK_INTERVAL
        fi
    done
}

# Function to run smoke tests
run_smoke_tests() {
    echo -e "\n${YELLOW}Running smoke tests...${NC}"

    # Test 1: Check node status
    echo -e "\n1. Checking node status... "
    if kubectl get nodes | grep -q "Ready"; then
        echo -e "${GREEN}PASS${NC}"
        kubectl get nodes
    else
        echo -e "${RED}FAIL${NC}"
        echo "Node status:"
        kubectl get nodes
    fi

    # Test 2: Check core namespaces
    echo -e "\n2. Checking core namespaces... "
    CORE_NAMESPACES=("default" "kube-system" "kube-public" "kube-node-lease")
    all_ns_exist=true

    for ns in "${CORE_NAMESPACES[@]}"; do
        if kubectl get namespace "$ns" &>/dev/null; then
            echo -e "   - $ns: ${GREEN}EXISTS${NC}"
        else
            echo -e "   - $ns: ${RED}MISSING${NC}"
            all_ns_exist=false
        fi
    done

    # Test 3: Check system pods
    echo -e "\n3. Checking system pods in kube-system... "
    kubectl get pods -n kube-system

    # Wait for all system pods to be ready
    echo -e "\n4. Waiting for all system pods to be ready... "
    if kubectl wait --for=condition=ready pods --all -n kube-system --timeout=120s; then
        echo -e "${GREEN}All system pods are ready${NC}"
    else
        echo -e "${YELLOW}Some system pods may not be ready yet${NC}"
        echo "Current pod status:"
        kubectl get pods -n kube-system --no-headers | grep -v "Running\|Completed" || true
    fi

    # Test 4: Check DNS resolution
    echo -e "\n5. Testing DNS resolution... "
    # Clean up any existing test pod
    kubectl delete pod dns-test --ignore-not-found=true &>/dev/null

    if kubectl run dns-test --image=busybox:1.28 --rm -i --restart=Never -- nslookup kubernetes.default 2>&1 | grep -q "Address"; then
        echo -e "${GREEN}DNS resolution is working${NC}"
    else
        echo -e "${YELLOW}DNS test failed or is still initializing${NC}"
    fi

    # Test 5: Check API server responsiveness
    echo -e "\n6. Testing API server responsiveness... "
    start_api_test=$(date +%s%N)
    kubectl version --short 2>/dev/null || kubectl version
    end_api_test=$(date +%s%N)
    api_response_time=$(( (end_api_test - start_api_test) / 1000000 ))
    echo -e "API response time: ${api_response_time}ms"

    # Test 6: Check cluster info
    echo -e "\n7. Cluster information:"
    kubectl cluster-info

    # Test 7: Check storage classes (for K3s local-path)
    echo -e "\n8. Checking storage classes..."
    kubectl get storageclass
}

# Function to setup useful aliases and functions
setup_helpers() {
    echo -e "\n${YELLOW}Setting up helpful commands...${NC}"

    # Create a helper script
    cat > "$HOME/.k3s-helpers.sh" << 'EOF'
# K3s helper functions

# Quick cluster status
k3s-status() {
    echo "=== Nodes ==="
    kubectl get nodes
    echo -e "\n=== System Pods ==="
    kubectl get pods -n kube-system
    echo -e "\n=== All Namespaces ==="
    kubectl get namespaces
}

# Port forward to a service
k3s-forward() {
    if [ $# -lt 3 ]; then
        echo "Usage: k3s-forward <namespace> <service> <port>"
        return 1
    fi
    kubectl port-forward -n "$1" "svc/$2" "$3"
}

# Get logs from a pod
k3s-logs() {
    if [ $# -lt 2 ]; then
        echo "Usage: k3s-logs <namespace> <pod-name-pattern>"
        return 1
    fi
    pod=$(kubectl get pods -n "$1" --no-headers | grep "$2" | head -1 | awk '{print $1}')
    kubectl logs -n "$1" "$pod" "${@:3}"
}

# Execute command in pod
k3s-exec() {
    if [ $# -lt 2 ]; then
        echo "Usage: k3s-exec <namespace> <pod-name-pattern> [command]"
        return 1
    fi
    pod=$(kubectl get pods -n "$1" --no-headers | grep "$2" | head -1 | awk '{print $1}')
    shift 2
    kubectl exec -it -n "$1" "$pod" -- "${@:-/bin/sh}"
}
EOF

    echo -e "${GREEN}Helper functions created in ~/.k3s-helpers.sh${NC}"
    echo "Add 'source ~/.k3s-helpers.sh' to your shell profile to use:"
    echo "  - k3s-status: Quick cluster status"
    echo "  - k3s-forward: Port forward to a service"
    echo "  - k3s-logs: Get logs from a pod"
    echo "  - k3s-exec: Execute command in a pod"
}

# Main execution
main() {
    # Check if we need SSH tunnel (if not on the same network as cluster)
    if ! ping -c 1 -W 2 ${CLUSTER_IP} &>/dev/null; then
        echo -e "${YELLOW}Direct connection to ${CLUSTER_IP} not available${NC}"
        echo "SSH tunnel may be required. Set SSH_TUNNEL_NEEDED=1 to enable."
    fi

    # Setup port forwarding if needed
    setup_port_forwarding

    # Wait for cluster to be ready
    if ! wait_for_cluster; then
        echo -e "${RED}Failed to connect to cluster${NC}"
        exit 1
    fi

    # Run smoke tests
    run_smoke_tests

    # Setup helper functions
    setup_helpers

    # Summary
    echo -e "\n${GREEN}======================================${NC}"
    echo -e "${GREEN}Deployment stabilization complete!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo -e "\nCluster Summary:"
    echo "- API Server: https://${CLUSTER_IP}:${CLUSTER_PORT}"
    if [[ -n "${SSH_TUNNEL_NEEDED:-}" ]]; then
        echo "- Local access: https://localhost:${CLUSTER_PORT}"
    fi
    echo "- Kubeconfig: ${KUBECONFIG:-$HOME/.kube/config}"
    echo -e "\nUseful commands:"
    echo "- kubectl get nodes"
    echo "- kubectl get pods --all-namespaces"
    echo "- kubectl get svc --all-namespaces"
    echo -e "\nNext steps:"
    echo "1. Deploy your applications"
    echo "2. Set up monitoring (Prometheus, Grafana)"
    echo "3. Configure ingress controller"
    echo "4. Set up cert-manager for TLS"
}

# Run main function
main "$@"
