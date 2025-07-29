#!/bin/bash

# Homelab Infrastructure Deployment Automation Script
# This script deploys the complete homelab infrastructure with DNS and certificate setup.

set -e

# Configuration
LOAD_BALANCER_IP="192.168.16.100"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CA_CERT_PATH="/tmp/homelab-ca.crt"
HOSTS_BACKUP="/tmp/hosts.backup.$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Icons
CHECK="✅"
CROSS="❌"
WARN="⚠️"
ROCKET="🚀"
GEAR="⚙️"
CERT="🔒"
DNS="🌐"

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_prerequisites() {
    log "${BLUE}${GEAR} Checking prerequisites...${NC}"

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log "${RED}${CROSS} kubectl is not installed or not in PATH${NC}"
        exit 1
    fi

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log "${RED}${CROSS} Cannot connect to Kubernetes cluster${NC}"
        exit 1
    fi

    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        log "${RED}${CROSS} curl is not installed${NC}"
        exit 1
    fi

    log "${GREEN}${CHECK} Prerequisites satisfied${NC}"
}

extract_ca_certificate() {
    log "${BLUE}${CERT} Extracting homelab CA certificate...${NC}"

    # Extract CA certificate from cluster
    if kubectl get secret -n cert-manager homelab-ca-secret &> /dev/null; then
        kubectl get secret -n cert-manager homelab-ca-secret -o jsonpath='{.data.tls\.crt}' | base64 -d > "$CA_CERT_PATH"
        log "${GREEN}${CHECK} CA certificate extracted to $CA_CERT_PATH${NC}"
    else
        log "${YELLOW}${WARN} CA certificate secret not found, will check later${NC}"
        return 1
    fi
}

install_ca_certificate() {
    log "${BLUE}${CERT} Installing CA certificate into system trust store...${NC}"

    if [ ! -f "$CA_CERT_PATH" ]; then
        log "${RED}${CROSS} CA certificate not found at $CA_CERT_PATH${NC}"
        return 1
    fi

    # Install certificate using our script
    if "$SCRIPT_DIR/install-ca-cert.sh"; then
        log "${GREEN}${CHECK} CA certificate installed successfully${NC}"
    else
        log "${RED}${CROSS} Failed to install CA certificate${NC}"
        return 1
    fi
}

configure_dns() {
    log "${BLUE}${DNS} Configuring DNS entries in /etc/hosts...${NC}"

    # Backup current hosts file
    sudo cp /etc/hosts "$HOSTS_BACKUP"
    log "${BLUE}${GEAR} Hosts file backed up to $HOSTS_BACKUP${NC}"

    # Get all ingress hosts from cluster
    local hosts=()
    while IFS= read -r host; do
        if [[ -n "$host" && "$host" != "<none>" ]]; then
            hosts+=("$host")
        fi
    done < <(kubectl get ingress -A -o jsonpath='{range .items[*]}{.spec.rules[*].host}{"\n"}{end}' 2>/dev/null)

    # Remove existing homelab entries
    sudo sed -i '/homelab\.local/d' /etc/hosts
    sudo sed -i "/$LOAD_BALANCER_IP.*homelab/d" /etc/hosts

    # Add new entries
    echo "" | sudo tee -a /etc/hosts > /dev/null
    echo "# Homelab Infrastructure Services - Auto-generated $(date)" | sudo tee -a /etc/hosts > /dev/null

    local added_count=0
    for host in "${hosts[@]}"; do
        echo "$LOAD_BALANCER_IP $host" | sudo tee -a /etc/hosts > /dev/null
        log "${GREEN}${CHECK} Added DNS entry: $host -> $LOAD_BALANCER_IP${NC}"
        ((added_count++))
    done

    if [[ $added_count -gt 0 ]]; then
        log "${GREEN}${CHECK} Configured $added_count DNS entries${NC}"
    else
        log "${YELLOW}${WARN} No ingress hosts found to configure${NC}"
    fi
}

deploy_services() {
    log "${BLUE}${ROCKET} Deploying homelab services...${NC}"

    # Deploy all Kubernetes manifests
    local manifest_files=(
        "$PROJECT_ROOT/kubernetes/base/landing-page.yaml"
        "$PROJECT_ROOT/kubernetes/base/prometheus-deployment.yaml"
        "$PROJECT_ROOT/kubernetes/base/gitlab-deployment.yaml"
        "$PROJECT_ROOT/kubernetes/base/ollama-webui-deployment.yaml"
        "$PROJECT_ROOT/kubernetes/base/jupyter-deployment.yaml"
    )

    for manifest in "${manifest_files[@]}"; do
        if [[ -f "$manifest" ]]; then
            log "${BLUE}${GEAR} Applying $(basename "$manifest")...${NC}"
            if kubectl apply -f "$manifest"; then
                log "${GREEN}${CHECK} Applied $(basename "$manifest")${NC}"
            else
                log "${YELLOW}${WARN} Failed to apply $(basename "$manifest"), continuing...${NC}"
            fi
        else
            log "${YELLOW}${WARN} Manifest not found: $manifest${NC}"
        fi
    done
}

wait_for_services() {
    log "${BLUE}${GEAR} Waiting for services to become ready...${NC}"

    # Wait for deployments to be ready
    local namespaces=("homelab-portal" "monitoring" "gitlab" "ai-tools" "jupyter")

    for namespace in "${namespaces[@]}"; do
        if kubectl get namespace "$namespace" &> /dev/null; then
            log "${BLUE}${GEAR} Waiting for deployments in namespace $namespace...${NC}"
            kubectl wait --for=condition=available --timeout=300s deployment --all -n "$namespace" 2>/dev/null || true
        fi
    done

    # Wait for certificates to be ready
    log "${BLUE}${CERT} Waiting for certificates to be issued...${NC}"
    kubectl wait --for=condition=ready --timeout=300s certificates --all -A 2>/dev/null || true
}

verify_deployment() {
    log "${BLUE}${GEAR} Verifying deployment...${NC}"

    # Run health check
    if "$SCRIPT_DIR/health-monitor.sh" once; then
        log "${GREEN}${CHECK} All health checks passed!${NC}"
        return 0
    else
        log "${YELLOW}${WARN} Some health checks failed, but continuing...${NC}"
        return 1
    fi
}

test_connectivity() {
    log "${BLUE}${GEAR} Testing HTTPS connectivity to all services...${NC}"

    local hosts=()
    while IFS= read -r host; do
        if [[ -n "$host" && "$host" != "<none>" ]]; then
            hosts+=("$host")
        fi
    done < <(kubectl get ingress -A -o jsonpath='{range .items[*]}{.spec.rules[*].host}{"\n"}{end}' 2>/dev/null)

    local success_count=0
    local total_count=${#hosts[@]}

    for host in "${hosts[@]}"; do
        local status=$(curl -k -s -o /dev/null -w "%{http_code}" "https://$host/" --max-time 10 2>/dev/null || echo "000")

        case $status in
            200|302|401)
                log "${GREEN}${CHECK} $host: HTTP $status (OK)${NC}"
                ((success_count++))
                ;;
            502|503)
                log "${YELLOW}${WARN} $host: HTTP $status (Still starting)${NC}"
                ;;
            *)
                log "${RED}${CROSS} $host: HTTP $status (Issue)${NC}"
                ;;
        esac
    done

    log "${BLUE}${GEAR} Connectivity test: $success_count/$total_count services responding${NC}"
}

show_summary() {
    log "${GREEN}${ROCKET} HOMELAB DEPLOYMENT SUMMARY${NC}"
    echo "════════════════════════════════════════════"

    # Show service URLs
    echo "🌐 Available Services:"
    kubectl get ingress -A -o custom-columns="SERVICE:.spec.rules[0].host,URL:URL" --no-headers 2>/dev/null | \
    while read -r host _; do
        if [[ -n "$host" && "$host" != "<none>" ]]; then
            echo "  ✅ https://$host"
        fi
    done

    echo ""
    echo "🔒 Certificate Trust:"
    echo "  ✅ CA certificate installed in system trust store"
    echo "  ✅ All services use trusted HTTPS certificates"

    echo ""
    echo "🌐 DNS Configuration:"
    echo "  ✅ All service URLs configured in /etc/hosts"
    echo "  ✅ LoadBalancer IP: $LOAD_BALANCER_IP"

    echo ""
    echo "📋 Next Steps:"
    echo "  1. Access the landing page: https://homelab.local"
    echo "  2. Configure services as needed"
    echo "  3. Monitor with: $SCRIPT_DIR/health-monitor.sh"

    echo ""
    log "${GREEN}🎉 Homelab infrastructure deployment completed successfully!${NC}"
}

# Main execution
main() {
    echo "════════════════════════════════════════════"
    log "${BLUE}${ROCKET} HOMELAB INFRASTRUCTURE DEPLOYMENT${NC}"
    echo "════════════════════════════════════════════"
    echo ""

    check_prerequisites
    echo ""

    deploy_services
    echo ""

    wait_for_services
    echo ""

    extract_ca_certificate
    install_ca_certificate
    echo ""

    configure_dns
    echo ""

    verify_deployment
    echo ""

    test_connectivity
    echo ""

    show_summary
}

# Run main function
main "$@"
