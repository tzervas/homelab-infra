#!/bin/bash
set -euo pipefail

# Script to check K3s cluster status and return JSON output
# Used by Terraform external data source

# Initialize output object
output="{}"

# Function to add key-value pair to JSON output
add_to_output() {
    local key="$1"
    local value="$2"
    output=$(echo "$output" | jq --arg k "$key" --arg v "$value" '. + {($k): $v}')
}

# Check if K3s is installed
if ! command -v k3s &> /dev/null; then
    add_to_output "status" "not_installed"
    echo "$output"
    exit 0
fi

# Check if K3s service is running
if ! systemctl is-active --quiet k3s 2>/dev/null; then
    add_to_output "status" "not_running"
    echo "$output"
    exit 0
fi

# Check if kubectl is responding
if ! sudo k3s kubectl get nodes &> /dev/null; then
    add_to_output "status" "unhealthy"
    echo "$output"
    exit 0
fi

# K3s is running and healthy
add_to_output "status" "running"

# Get cluster token if available
if [[ -f /var/lib/rancher/k3s/server/token ]]; then
    token=$(sudo cat /var/lib/rancher/k3s/server/token 2>/dev/null || echo "")
    if [[ -n "$token" ]]; then
        add_to_output "token" "$token"
    fi
fi

# Get CA certificate if available
if [[ -f /var/lib/rancher/k3s/server/tls/server-ca.crt ]]; then
    ca_cert=$(sudo base64 -w 0 /var/lib/rancher/k3s/server/tls/server-ca.crt 2>/dev/null || echo "")
    if [[ -n "$ca_cert" ]]; then
        add_to_output "ca_cert" "$ca_cert"
    fi
fi

# Get node count
node_count=$(sudo k3s kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0")
add_to_output "node_count" "$node_count"

# Get K3s version
k3s_version=$(k3s --version | head -n1 | cut -d' ' -f3 || echo "unknown")
add_to_output "k3s_version" "$k3s_version"

# Get cluster info
cluster_info=$(sudo k3s kubectl cluster-info 2>/dev/null | head -n1 || echo "unknown")
add_to_output "cluster_info" "$cluster_info"

# Output final JSON
echo "$output"
