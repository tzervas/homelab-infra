#!/bin/bash

# MIT License
#
# Copyright (c) 2025 Tyler Zervas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Enhanced K3s Infrastructure Cleanup and Setup Script
# Optimized for homelab environments with comprehensive error handling

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/.homelab/logs"
BACKUP_DIR="${HOME}/.homelab/backups/$(date +%Y%m%d_%H%M%S)"
KUBECONFIG_PATH="${HOME}/.kube/config"
K3S_CONFIG_DIR="/etc/rancher/k3s"
K3S_CONFIG_FILE="${K3S_CONFIG_DIR}/k3s.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    mkdir -p "${LOG_DIR}" 2>/dev/null || true
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "${LOG_DIR}/k3s-setup.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "${LOG_DIR}/k3s-setup.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "${LOG_DIR}/k3s-setup.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "${LOG_DIR}/k3s-setup.log"
}

# Error handling
cleanup_on_error() {
    local exit_code=$?
    log_error "Script failed with exit code ${exit_code}"
    if [[ -f "${BACKUP_DIR}/kubeconfig.backup" ]]; then
        log_info "Restoring kubeconfig backup"
        cp "${BACKUP_DIR}/kubeconfig.backup" "${KUBECONFIG_PATH}" || true
    fi
    exit $exit_code
}

trap cleanup_on_error ERR

# Initialize directories
initialize_directories() {
    log_info "Initializing directories"
    mkdir -p "${LOG_DIR}" "${BACKUP_DIR}" "${HOME}/.kube"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites"

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi

    # Check required commands
    local required_commands=("curl" "systemctl" "docker")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '${cmd}' not found"
            exit 1
        fi
    done

    # Check system resources
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [[ $available_memory -lt 2048 ]]; then
        log_warning "Low available memory: ${available_memory}MB (recommended: 2GB+)"
    fi
}

# Backup existing configuration
backup_configuration() {
    log_info "Backing up existing configuration"

    if [[ -f "${KUBECONFIG_PATH}" ]]; then
        cp "${KUBECONFIG_PATH}" "${BACKUP_DIR}/kubeconfig.backup"
        log_info "Kubeconfig backed up to ${BACKUP_DIR}/kubeconfig.backup"
    fi
}

# Clean up existing K3s installation
cleanup_k3s() {
    log_info "Cleaning up existing K3s installation"

    # Stop K3s service if running
    if systemctl is-active --quiet k3s 2>/dev/null; then
        log_info "Stopping K3s service"
        sudo systemctl stop k3s || true
    fi

    # Run K3s uninstall script if it exists
    if [[ -f "/usr/local/bin/k3s-uninstall.sh" ]]; then
        log_info "Running K3s uninstall script"
        sudo /usr/local/bin/k3s-uninstall.sh || true
    fi

    # Clean up Docker containers
    log_info "Cleaning up Docker containers"
    docker ps -a --format "table {{.Names}}\t{{.Image}}" | grep -E "k3s|k3d|rancher" | awk '{print $1}' | tail -n +2 | xargs -r docker rm -f || true

    # Clean up network interfaces
    sudo ip link delete flannel.1 2>/dev/null || true
    sudo ip link delete cni0 2>/dev/null || true
}

# Check and configure firewall
configure_firewall() {
    log_info "Configuring firewall"

    if command -v ufw &> /dev/null; then
        if sudo ufw status | grep -q "Status: active"; then
            log_warning "UFW firewall is active, disabling for K3s setup"
            sudo ufw disable
        fi
    fi
}

# Install K3s
install_k3s() {
    log_info "Installing K3s"

    if command -v k3s &> /dev/null; then
        log_info "K3s already installed, skipping installation"
        return 0
    fi

    # Install K3s with homelab-optimized settings
    curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --disable traefik --disable servicelb" sh -

    # Wait for K3s to start
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if systemctl is-active --quiet k3s; then
            log_success "K3s service is running"
            break
        fi
        log_info "Waiting for K3s service to start (attempt ${attempt}/${max_attempts})"
        sleep 2
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        log_error "K3s service failed to start after ${max_attempts} attempts"
        exit 1
    fi
}

# Configure kubeconfig
configure_kubeconfig() {
    log_info "Configuring kubeconfig"

    if [[ ! -f "${K3S_CONFIG_FILE}" ]]; then
        log_error "K3s config file not found at ${K3S_CONFIG_FILE}"
        exit 1
    fi

    # Copy K3s config to user directory
    sudo cp "${K3S_CONFIG_FILE}" "${KUBECONFIG_PATH}"
    sudo chown "$(id -u):$(id -g)" "${KUBECONFIG_PATH}"
    chmod 600 "${KUBECONFIG_PATH}"

    log_success "Kubeconfig configured at ${KUBECONFIG_PATH}"
}

# Verify cluster health
verify_cluster_health() {
    log_info "Verifying cluster health"

    # Test 1: Wait for nodes to appear and become ready
    log_info "Waiting for nodes to become ready"
    local max_wait=300  # 5 minutes
    local check_interval=10
    local elapsed=0

    while [[ $elapsed -lt $max_wait ]]; do
        # Check if any nodes exist first
        local node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo 0)

        if [[ $node_count -eq 0 ]]; then
            log_info "No nodes found yet, waiting for K3s to initialize... (${elapsed}s/${max_wait}s)"
            sleep $check_interval
            elapsed=$((elapsed + check_interval))
            continue
        fi

        # Check node readiness
        local ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo 0)

        if [[ $ready_nodes -gt 0 ]]; then
            log_success "Cluster has ${ready_nodes}/${node_count} node(s) in Ready state"
            break
        fi

        log_info "Waiting for nodes to become ready... (${elapsed}s/${max_wait}s)"
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
    done

    if [[ $elapsed -ge $max_wait ]]; then
        log_error "Nodes did not become ready within ${max_wait}s"
        kubectl get nodes 2>/dev/null || echo "Cannot access cluster"
        exit 1
    fi

    # Test 2: Check system pods
    log_info "Checking system pods"
    local max_wait=120
    local elapsed=0

    while [[ $elapsed -lt $max_wait ]]; do
        local pending_pods=$(kubectl get pods -n kube-system --no-headers | grep -v "Running\|Completed" | wc -l)
        if [[ $pending_pods -eq 0 ]]; then
            log_success "All system pods are running"
            break
        fi
        log_info "Waiting for ${pending_pods} system pods to be ready (${elapsed}s/${max_wait}s)"
        sleep 5
        ((elapsed += 5))
    done

    if [[ $elapsed -ge $max_wait ]]; then
        log_warning "Some system pods may still be starting"
        kubectl get pods -n kube-system --no-headers | grep -v "Running\|Completed" || true
    fi

    # Test 3: Check DNS resolution
    log_info "Testing DNS resolution"
    if kubectl run dns-test --image=busybox:1.28 --rm -i --restart=Never -- nslookup kubernetes.default 2>/dev/null | grep -q "Address"; then
        log_success "DNS resolution is working"
    else
        log_warning "DNS resolution test inconclusive"
    fi

    # Test 4: Check storage class
    log_info "Checking storage classes"
    if kubectl get storageclass --no-headers | grep -q "local-path"; then
        log_success "Local storage class is available"
    else
        log_warning "No storage classes found"
    fi

    # Test 5: Check resource usage
    log_info "Checking resource usage"
    kubectl top nodes 2>/dev/null || log_warning "Metrics server not ready yet"
}

# Display deployment summary
display_summary() {
    log_success "K3s deployment completed successfully!"

    echo -e "\n${GREEN}=== Deployment Summary ===${NC}"
    echo -e "Cluster Information:"
    kubectl cluster-info 2>/dev/null || echo "  Cluster info temporarily unavailable"

    echo -e "\nNodes:"
    kubectl get nodes 2>/dev/null || echo "  Node information temporarily unavailable"

    echo -e "\nStorage Classes:"
    kubectl get storageclass 2>/dev/null || echo "  Storage class information temporarily unavailable"

    echo -e "\n${BLUE}Configuration Files:${NC}"
    echo -e "  Kubeconfig: ${KUBECONFIG_PATH}"
    echo -e "  K3s Config: ${K3S_CONFIG_FILE}"
    echo -e "  Logs: ${LOG_DIR}/k3s-setup.log"
    echo -e "  Backup: ${BACKUP_DIR}"

    echo -e "\n${BLUE}Next Steps:${NC}"
    echo -e "  1. Deploy applications with: helmfile sync"
    echo -e "  2. Check cluster status: kubectl get all --all-namespaces"
    echo -e "  3. Monitor logs: tail -f ${LOG_DIR}/k3s-setup.log"
}

# Main execution
main() {
    log_info "Starting K3s infrastructure cleanup and setup"

    initialize_directories
    check_prerequisites
    backup_configuration
    cleanup_k3s
    configure_firewall
    install_k3s
    configure_kubeconfig
    verify_cluster_health
    display_summary

    log_success "K3s infrastructure setup completed successfully!"
}

# Run main function
main "$@"
