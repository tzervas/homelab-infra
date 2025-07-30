#!/bin/bash

# Comprehensive Homelab Infrastructure Teardown Script
# This script performs a complete teardown of all homelab components including Keycloak SSO
# with thorough validation at each step

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/homelab-teardown-$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="${SCRIPT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case $level in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE" ;;
    esac
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Create logs and backup directories
mkdir -p "${SCRIPT_DIR}/logs" "$BACKUP_DIR"

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up temporary files..."
}

# Signal handlers
trap cleanup EXIT
trap 'log "ERROR" "Teardown interrupted by user"; exit 130' INT TERM

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites for teardown..."

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log "ERROR" "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log "WARN" "Cannot connect to Kubernetes cluster - may already be torn down"
        return 1
    fi

    log "INFO" "Prerequisites check passed"
    return 0
}

# Backup current state before teardown
backup_current_state() {
    log "INFO" "Backing up current state before teardown..."

    if kubectl cluster-info &> /dev/null; then
        # Backup all namespaces and resources
        local namespaces=("keycloak" "oauth2-proxy" "monitoring" "gitlab" "ai-tools" "jupyter" "homelab-portal" "gitlab-runner")

        for namespace in "${namespaces[@]}"; do
            if kubectl get namespace "$namespace" &> /dev/null; then
                log "INFO" "Backing up namespace: $namespace"
                mkdir -p "$BACKUP_DIR/$namespace"
                kubectl get all,secrets,configmaps,ingress,certificates,pvc -n "$namespace" -o yaml > "$BACKUP_DIR/$namespace/${namespace}-resources.yaml" 2>/dev/null || true
            fi
        done

        # Backup cluster-wide resources
        log "INFO" "Backing up cluster-wide resources"
        kubectl get clusterissuers,clusterroles,clusterrolebindings -o yaml > "$BACKUP_DIR/cluster-resources.yaml" 2>/dev/null || true

        # Backup current kubeconfig
        if [[ -f "$HOME/.kube/config" ]]; then
            cp "$HOME/.kube/config" "$BACKUP_DIR/kubeconfig.backup"
        fi

        log "INFO" "State backup completed at: $BACKUP_DIR"
    else
        log "WARN" "Cluster not accessible, skipping state backup"
    fi
}

# Remove application workloads
remove_applications() {
    log "INFO" "Removing application workloads..."

    if ! kubectl cluster-info &> /dev/null; then
        log "WARN" "Cluster not accessible, skipping application removal"
        return 0
    fi

    local namespaces=("homelab-portal" "ai-tools" "jupyter" "gitlab" "gitlab-runner")

    for namespace in "${namespaces[@]}"; do
        if kubectl get namespace "$namespace" &> /dev/null; then
            log "INFO" "Removing applications in namespace: $namespace"

            # Remove deployments first
            kubectl delete deployments --all -n "$namespace" --timeout=60s || true

            # Remove services
            kubectl delete services --all -n "$namespace" --timeout=30s || true

            # Remove ingress
            kubectl delete ingress --all -n "$namespace" --timeout=30s || true

            # Remove certificates
            kubectl delete certificates --all -n "$namespace" --timeout=30s || true

            # Remove PVCs (this will also remove PVs)
            kubectl delete pvc --all -n "$namespace" --timeout=60s || true

            # Wait for pods to terminate
            log "INFO" "Waiting for pods in $namespace to terminate..."
            kubectl wait --for=delete pods --all -n "$namespace" --timeout=120s || true

            # Delete the namespace
            kubectl delete namespace "$namespace" --timeout=60s || true
        fi
    done

    log "INFO" "Application workloads removed"
}

# Remove monitoring stack
remove_monitoring() {
    log "INFO" "Removing monitoring stack..."

    if ! kubectl cluster-info &> /dev/null; then
        log "WARN" "Cluster not accessible, skipping monitoring removal"
        return 0
    fi

    if kubectl get namespace monitoring &> /dev/null; then
        log "INFO" "Removing monitoring namespace resources"

        # Remove monitoring workloads
        kubectl delete deployments --all -n monitoring --timeout=60s || true
        kubectl delete services --all -n monitoring --timeout=30s || true
        kubectl delete ingress --all -n monitoring --timeout=30s || true
        kubectl delete certificates --all -n monitoring --timeout=30s || true
        kubectl delete pvc --all -n monitoring --timeout=60s || true

        # Wait for pods to terminate
        kubectl wait --for=delete pods --all -n monitoring --timeout=120s || true

        kubectl delete namespace monitoring --timeout=60s || true
    fi

    log "INFO" "Monitoring stack removed"
}

# Remove authentication infrastructure
remove_authentication() {
    log "INFO" "Removing authentication infrastructure..."

    if ! kubectl cluster-info &> /dev/null; then
        log "WARN" "Cluster not accessible, skipping authentication removal"
        return 0
    fi

    # Remove OAuth2 Proxy
    if kubectl get namespace oauth2-proxy &> /dev/null; then
        log "INFO" "Removing OAuth2 Proxy"
        kubectl delete deployments --all -n oauth2-proxy --timeout=60s || true
        kubectl delete services --all -n oauth2-proxy --timeout=30s || true
        kubectl delete ingress --all -n oauth2-proxy --timeout=30s || true
        kubectl delete certificates --all -n oauth2-proxy --timeout=30s || true
        kubectl delete configmaps --all -n oauth2-proxy --timeout=30s || true
        kubectl delete secrets --all -n oauth2-proxy --timeout=30s || true
        kubectl wait --for=delete pods --all -n oauth2-proxy --timeout=120s || true
        kubectl delete namespace oauth2-proxy --timeout=60s || true
    fi

    # Remove Keycloak
    if kubectl get namespace keycloak &> /dev/null; then
        log "INFO" "Removing Keycloak and PostgreSQL"
        kubectl delete deployments --all -n keycloak --timeout=60s || true
        kubectl delete services --all -n keycloak --timeout=30s || true
        kubectl delete ingress --all -n keycloak --timeout=30s || true
        kubectl delete certificates --all -n keycloak --timeout=30s || true
        kubectl delete pvc --all -n keycloak --timeout=60s || true
        kubectl delete configmaps --all -n keycloak --timeout=30s || true
        kubectl delete secrets --all -n keycloak --timeout=30s || true
        kubectl wait --for=delete pods --all -n keycloak --timeout=120s || true
        kubectl delete namespace keycloak --timeout=60s || true
    fi

    log "INFO" "Authentication infrastructure removed"
}

# Remove core infrastructure
remove_core_infrastructure() {
    log "INFO" "Removing core infrastructure..."

    if ! kubectl cluster-info &> /dev/null; then
        log "WARN" "Cluster not accessible, skipping core infrastructure removal"
        return 0
    fi

    # Remove cert-manager
    if kubectl get namespace cert-manager &> /dev/null; then
        log "INFO" "Removing cert-manager"

        # Remove cluster issuers first
        kubectl delete clusterissuers --all --timeout=30s || true

        # Remove cert-manager components
        kubectl delete deployments --all -n cert-manager --timeout=60s || true
        kubectl delete services --all -n cert-manager --timeout=30s || true
        kubectl delete validatingwebhookconfigurations cert-manager-webhook || true
        kubectl delete mutatingwebhookconfigurations cert-manager-webhook || true
        kubectl wait --for=delete pods --all -n cert-manager --timeout=120s || true
        kubectl delete namespace cert-manager --timeout=60s || true
    fi

    # Remove ingress-nginx
    if kubectl get namespace ingress-nginx &> /dev/null; then
        log "INFO" "Removing ingress-nginx"
        kubectl delete deployments --all -n ingress-nginx --timeout=60s || true
        kubectl delete services --all -n ingress-nginx --timeout=30s || true
        kubectl delete jobs --all -n ingress-nginx --timeout=30s || true
        kubectl wait --for=delete pods --all -n ingress-nginx --timeout=120s || true
        kubectl delete namespace ingress-nginx --timeout=60s || true
    fi

    # Remove MetalLB
    if kubectl get namespace metallb-system &> /dev/null; then
        log "INFO" "Removing MetalLB"
        kubectl delete daemonsets --all -n metallb-system --timeout=60s || true
        kubectl delete deployments --all -n metallb-system --timeout=60s || true
        kubectl delete services --all -n metallb-system --timeout=30s || true
        kubectl wait --for=delete pods --all -n metallb-system --timeout=120s || true
        kubectl delete namespace metallb-system --timeout=60s || true
    fi

    log "INFO" "Core infrastructure removed"
}

# Remove Kubernetes cluster
remove_k3s_cluster() {
    log "INFO" "Removing K3s cluster..."

    # Check if K3s is installed or if there are K3s-related processes/files
    local k3s_installed=false

    if command -v k3s &> /dev/null; then
        k3s_installed=true
        log "INFO" "K3s binary found"
    elif systemctl list-unit-files | grep -q k3s; then
        k3s_installed=true
        log "INFO" "K3s service found"
    elif [[ -d "/etc/rancher/k3s" ]] || [[ -d "/var/lib/rancher/k3s" ]]; then
        k3s_installed=true
        log "INFO" "K3s directories found"
    fi

    if [[ "$k3s_installed" == false ]]; then
        log "INFO" "No K3s installation found, checking for remaining cluster files..."
    fi

    # Stop K3s service
    if systemctl is-active --quiet k3s 2>/dev/null; then
        log "INFO" "Stopping K3s service"
        sudo systemctl stop k3s || true
        sudo systemctl disable k3s || true
    fi

    # Run K3s uninstall script
    if [[ -f "/usr/local/bin/k3s-uninstall.sh" ]]; then
        log "INFO" "Running K3s uninstall script"
        sudo /usr/local/bin/k3s-uninstall.sh || true
    fi

    # Clean up remaining K3s files
    log "INFO" "Cleaning up K3s files and directories"
    sudo rm -rf /etc/rancher/k3s || true
    sudo rm -rf /var/lib/rancher/k3s || true
    sudo rm -rf /var/lib/kubelet || true
    sudo rm -rf /etc/systemd/system/k3s.service || true
    sudo systemctl daemon-reload || true

    # Clean up Docker containers and networks
    log "INFO" "Cleaning up Docker containers and networks"
    docker ps -a --format "table {{.Names}}\t{{.Image}}" | grep -E "k3s|rancher" | awk '{print $1}' | tail -n +2 | xargs -r docker rm -f || true
    docker network ls | grep -E "k3s|rancher" | awk '{print $1}' | xargs -r docker network rm || true

    # Clean up network interfaces
    log "INFO" "Cleaning up network interfaces"
    sudo ip link delete flannel.1 2>/dev/null || true
    sudo ip link delete cni0 2>/dev/null || true
    sudo ip link delete kube-bridge 2>/dev/null || true

    # Clean up iptables rules
    log "INFO" "Flushing iptables rules"
    sudo iptables -F || true
    sudo iptables -t nat -F || true
    sudo iptables -t mangle -F || true

    # Remove kubeconfig
    if [[ -f "$HOME/.kube/config" ]]; then
        log "INFO" "Removing kubeconfig"
        rm -f "$HOME/.kube/config"
    fi

    log "INFO" "K3s cluster removed"
}

# Validate clean state
validate_clean_state() {
    log "INFO" "Validating clean state after teardown..."

    local issues=0

    # Check if kubectl can connect (should fail)
    if kubectl cluster-info &> /dev/null; then
        log "ERROR" "Kubernetes cluster is still accessible"
        issues=$((issues + 1))
    else
        log "INFO" "✅ Kubernetes cluster is not accessible (expected)"
    fi

    # Check if K3s service is stopped
    if systemctl is-active --quiet k3s 2>/dev/null; then
        log "ERROR" "K3s service is still running"
        issues=$((issues + 1))
    else
        log "INFO" "✅ K3s service is stopped"
    fi

    # Check if K3s processes are running
    if pgrep -f k3s &> /dev/null; then
        log "ERROR" "K3s processes are still running"
        issues=$((issues + 1))
    else
        log "INFO" "✅ No K3s processes running"
    fi

    # Check if Docker containers are running
    local k3s_containers=$(docker ps --format "table {{.Names}}" 2>/dev/null | grep -E "k3s|rancher" | wc -l || echo "0")
    if [[ "$k3s_containers" -gt 0 ]]; then
        log "ERROR" "$k3s_containers K3s-related containers still running"
        issues=$((issues + 1))
    else
        log "INFO" "✅ No K3s-related containers running"
    fi

    # Check network interfaces
    local interfaces=$(ip link show 2>/dev/null | grep -E "flannel|cni0|kube-bridge" | wc -l || echo "0")
    if [[ "$interfaces" -gt 0 ]]; then
        log "ERROR" "$interfaces Kubernetes network interfaces still exist"
        issues=$((issues + 1))
    else
        log "INFO" "✅ No Kubernetes network interfaces found"
    fi

    # Check for remaining files
    local remaining_files=0

    if [[ -d "/etc/rancher/k3s" ]]; then
        log "ERROR" "K3s configuration directory still exists"
        remaining_files=$((remaining_files + 1))
    fi

    if [[ -d "/var/lib/rancher/k3s" ]]; then
        log "ERROR" "K3s data directory still exists"
        remaining_files=$((remaining_files + 1))
    fi

    if [[ -f "$HOME/.kube/config" ]]; then
        log "ERROR" "Kubeconfig file still exists"
        remaining_files=$((remaining_files + 1))
    fi

    if [[ $remaining_files -eq 0 ]]; then
        log "INFO" "✅ No remaining K3s files found"
    else
        issues=$((issues + remaining_files))
    fi

    # Summary
    if [[ $issues -eq 0 ]]; then
        log "INFO" "🎉 Clean state validation passed! System is ready for fresh deployment"
        return 0
    else
        log "ERROR" "❌ Clean state validation failed with $issues issues"
        return 1
    fi
}

# Display teardown summary
display_teardown_summary() {
    log "INFO" "Teardown completed!"

    cat << EOF

🧹 HOMELAB INFRASTRUCTURE TEARDOWN COMPLETE 🧹

📊 Summary:
   • ✅ Application workloads removed
   • ✅ Monitoring stack removed
   • ✅ Authentication infrastructure removed (Keycloak + OAuth2 Proxy)
   • ✅ Core infrastructure removed (cert-manager, ingress-nginx, MetalLB)
   • ✅ K3s cluster completely uninstalled
   • ✅ Network interfaces cleaned up
   • ✅ Docker containers and networks removed
   • ✅ Configuration files removed

💾 Backup Location: ${BACKUP_DIR}
📝 Teardown Log: ${LOG_FILE}

🚀 Next Steps:
   1. System is now ready for fresh deployment
   2. Run: ./deploy-homelab-with-sso.sh to redeploy
   3. Or run: ./clean-and-setup-k3s.sh to setup K3s only

📋 Clean State Validation:
   • Kubernetes cluster: Not accessible ✅
   • K3s service: Stopped ✅
   • K3s processes: None running ✅
   • Docker containers: None found ✅
   • Network interfaces: Cleaned up ✅
   • Configuration files: Removed ✅

EOF
}

# Main teardown function
main() {
    log "INFO" "Starting comprehensive homelab infrastructure teardown"
    log "INFO" "Teardown log: ${LOG_FILE}"
    log "INFO" "Backup location: ${BACKUP_DIR}"

    # Confirm teardown
    echo -e "${YELLOW}⚠️  WARNING: This will completely remove your homelab infrastructure!${NC}"
    echo -e "${YELLOW}   - All applications and data will be removed${NC}"
    echo -e "${YELLOW}   - K3s cluster will be uninstalled${NC}"
    echo -e "${YELLOW}   - All configuration will be backed up to: ${BACKUP_DIR}${NC}"
    echo
    read -p "Are you sure you want to proceed? (yes/NO): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "INFO" "Teardown cancelled by user"
        exit 0
    fi

    check_prerequisites
    backup_current_state
    remove_applications
    remove_monitoring
    remove_authentication
    remove_core_infrastructure
    remove_k3s_cluster

    if validate_clean_state; then
        display_teardown_summary
        log "INFO" "Teardown completed successfully!"
        exit 0
    else
        log "ERROR" "Teardown completed with issues - check validation output above"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
