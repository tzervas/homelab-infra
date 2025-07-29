#!/bin/bash

# Complete Homelab Deployment Suite
# Integrated deployment, teardown, and local configuration automation
# Author: Homelab Infrastructure Team
# Version: 2.0

set -euo pipefail

# Include centralized environment configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PROJECT_ROOT/scripts/common/environment.sh"
load_environment

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
CA_CERT_PATH="/tmp/homelab-ca.crt"
BACKUP_BASE_DIR="/tmp/homelab-backups"
ANSIBLE_INVENTORY="${SCRIPT_DIR}/ansible/inventory/hosts.yml"

# Service definitions - Extended with SSO services
SERVICES=("auth" "homelab" "grafana" "prometheus" "ollama" "jupyter" "gitlab")
SSO_SERVICES=("keycloak" "oauth2-proxy")

show_banner() {
    echo -e "${BOLD}${BLUE}"
    cat << 'EOF'
╔══════════════════════════════════════════════╗
║           HOMELAB AUTOMATION SUITE           ║
║         Complete Infrastructure Stack        ║
╚══════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

show_usage() {
    show_banner
    echo ""
    echo -e "${BOLD}Usage:${NC} $0 [command] [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo "  ${GREEN}deploy${NC}         Complete infrastructure deployment"
    echo "  ${RED}teardown${NC}       Complete infrastructure teardown"
    echo "  ${BLUE}setup-local${NC}    Configure local workstation access"
    echo "  ${YELLOW}status${NC}         Show deployment status"
    echo "  ${BLUE}backup${NC}         Backup current deployment"
    echo "  ${BLUE}restore${NC}        Restore from backup"
    echo "  ${YELLOW}test${NC}           Run connectivity tests"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --skip-local      Skip local workstation configuration"
    echo "  --backup-first    Create backup before operations"
    echo "  --force           Force operations without confirmation"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 deploy                    # Full deployment with local setup"
    echo "  $0 deploy --skip-local       # Deploy without local config"
    echo "  $0 teardown --backup-first   # Backup then teardown"
    echo "  $0 status                    # Check current status"
}

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

confirm_action() {
    if [[ "$FORCE" != "true" ]]; then
        echo -e "${YELLOW}$1${NC}"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation cancelled."
            exit 0
        fi
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check required tools
    tools=("kubectl" "ansible" "helm" "openssl" "curl")
    missing_tools=()

    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
    fi

    # Check ansible inventory
    if [[ ! -f "$ANSIBLE_INVENTORY" ]]; then
        error "Ansible inventory not found: $ANSIBLE_INVENTORY"
    fi

    # Check network connectivity
    if ! ping -c 1 -W 3 "$HOMELAB_SERVER_IP" &>/dev/null; then
        error "Cannot reach homelab server: $HOMELAB_SERVER_IP"
    fi

    success "Prerequisites check passed"
}

create_backup() {
    log "Creating deployment backup..."

    local backup_dir="$BACKUP_BASE_DIR/backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup Kubernetes resources
    if kubectl get nodes &>/dev/null; then
        log "Backing up Kubernetes resources..."

        # Create namespace-specific backups
        namespaces=($(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo ""))
        for ns in "${namespaces[@]}"; do
            if [[ "$ns" =~ ^(kube-|default|cert-manager|monitoring|longhorn|metallb|ingress) ]]; then
                mkdir -p "$backup_dir/namespaces/$ns"
                kubectl get all -n "$ns" -o yaml > "$backup_dir/namespaces/$ns/resources.yaml" 2>/dev/null || true
                kubectl get secrets -n "$ns" -o yaml > "$backup_dir/namespaces/$ns/secrets.yaml" 2>/dev/null || true
                kubectl get configmaps -n "$ns" -o yaml > "$backup_dir/namespaces/$ns/configmaps.yaml" 2>/dev/null || true
            fi
        done

        # Backup cluster-wide resources
        kubectl get clusterissuers -o yaml > "$backup_dir/clusterissuers.yaml" 2>/dev/null || true
        kubectl get storageclass -o yaml > "$backup_dir/storageclasses.yaml" 2>/dev/null || true
        kubectl get pv -o yaml > "$backup_dir/persistentvolumes.yaml" 2>/dev/null || true

        # Backup certificates
        kubectl get secret homelab-ca-secret -n cert-manager -o yaml > "$backup_dir/ca-secret.yaml" 2>/dev/null || true
        kubectl get secret homelab-ca-secret -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d > "$backup_dir/homelab-ca.crt" 2>/dev/null || true
    fi

    # Backup configuration files
    cp -r "$SCRIPT_DIR/kubernetes" "$backup_dir/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/ansible" "$backup_dir/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/helm" "$backup_dir/" 2>/dev/null || true

    # Create backup summary
    cat > "$backup_dir/backup-info.md" << EOF
# Homelab Backup Summary

**Created**: $(date)
**Backup Directory**: $backup_dir
**Homelab Server**: $HOMELAB_SERVER_IP
**MetalLB IP**: $METALLB_IP

## Backup Contents

$(if kubectl get nodes &>/dev/null; then
    echo "### Kubernetes Cluster"
    echo "- **Nodes**: $(kubectl get nodes --no-headers | wc -l)"
    echo "- **Pods**: $(kubectl get pods --all-namespaces --no-headers | wc -l)"
    echo "- **Services**: $(kubectl get services --all-namespaces --no-headers | wc -l)"
    echo "- **Certificates**: $(kubectl get certificates --all-namespaces --no-headers | wc -l)"
else
    echo "### No Kubernetes Cluster Connected"
fi)

### Files Backed Up
$(find "$backup_dir" -type f | wc -l) files backed up

### Restoration
To restore this backup, use:
\`\`\`bash
$0 restore $backup_dir
\`\`\`
EOF

    success "Backup created: $backup_dir"
    echo "$backup_dir"
}

complete_teardown() {
    log "Starting complete teardown..."

    confirm_action "This will completely destroy the homelab infrastructure!"

    # Create backup if requested
    if [[ "$BACKUP_FIRST" == "true" ]]; then
        create_backup
    fi

    # Delete all custom resources
    log "Removing custom resources..."
    kubectl delete certificates --all --all-namespaces --timeout=60s 2>/dev/null || true
    kubectl delete clusterissuers --all --timeout=60s 2>/dev/null || true
    kubectl delete ingress --all --all-namespaces --timeout=60s 2>/dev/null || true
    kubectl delete pvc --all --all-namespaces --timeout=60s 2>/dev/null || true

    # Delete application namespaces
    log "Removing application namespaces..."
    namespaces=("monitoring" "longhorn-system" "cert-manager" "metallb-system" "ingress-nginx")
    for ns in "${namespaces[@]}"; do
        log "Deleting namespace: $ns"
        kubectl delete namespace "$ns" --timeout=120s 2>/dev/null || true
    done

    # Uninstall K3s
    log "Uninstalling K3s from remote server..."
    ansible homelab-server -i "$ANSIBLE_INVENTORY" -m shell -a "sudo systemctl stop k3s" 2>/dev/null || true
    ansible homelab-server -i "$ANSIBLE_INVENTORY" -m shell -a "sudo /usr/local/bin/k3s-uninstall.sh" 2>/dev/null || true

    # Clean local kubectl config
    log "Cleaning local configuration..."
    cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    kubectl config delete-context default 2>/dev/null || true

    # Clean local hosts file
    log "Cleaning local /etc/hosts entries..."
    if sudo -n true 2>/dev/null; then
        sudo sed -i '/homelab.local/d' /etc/hosts 2>/dev/null || true
        success "Local hosts entries cleaned"
    else
        warning "Could not clean /etc/hosts (sudo required)"
        echo "Manual cleanup needed: sudo sed -i '/homelab.local/d' /etc/hosts"
    fi

    success "Complete teardown finished"
}

deploy_infrastructure() {
    log "Starting complete infrastructure deployment..."

    # Check if cluster already exists and is accessible
    if kubectl get nodes &>/dev/null; then
        log "Kubernetes cluster already exists and is accessible"
        local node_count=$(kubectl get nodes --no-headers | wc -l)
        success "Found existing K3s cluster with $node_count node(s)"

        # Skip to infrastructure components deployment
        deploy_infrastructure_components
        return $?
    fi

    # Synchronize and pull the latest configuration files
    git pull origin main
    success "Configuration synchronized."

    confirm_action "This will deploy the complete homelab infrastructure."

    # Step 1: Deploy K3s
    log "Deploying K3s cluster..."
    ansible-playbook -i "$ANSIBLE_INVENTORY" ansible/playbooks/install-missing-tools.yml

    # Get kubeconfig
    log "Configuring kubectl access..."
    ansible homelab-server -i "$ANSIBLE_INVENTORY" -m fetch -a "src=/home/kang/.kube/config dest=/tmp/k3s-config flat=yes"
    cp /tmp/k3s-config ~/.kube/config

    # Verify cluster
    kubectl get nodes || error "Failed to connect to K3s cluster"
    success "K3s cluster deployed and accessible"

    # Step 2: Install dependencies
    log "Installing system dependencies..."
    ansible-playbook -i "$ANSIBLE_INVENTORY" ansible/playbooks/install-longhorn-requirements.yml
    success "System dependencies installed"

    # Step 3: Deploy infrastructure components
    log "Deploying infrastructure components..."

    # Deploy MetalLB
    if ! kubectl get namespace metallb-system &>/dev/null; then
        log "Installing MetalLB..."
        helm repo add metallb https://metallb.github.io/metallb --force-update 2>/dev/null || true
        helm repo update

        # Try helm install, fallback to kubectl if it fails
        if ! helm install metallb metallb/metallb --namespace metallb-system --create-namespace --wait --timeout=300s; then
            warning "Helm install failed, trying direct kubectl apply..."
            kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
            kubectl wait --namespace metallb-system --for=condition=ready pod --selector=app=metallb --timeout=300s
        fi
        success "MetalLB installed"
    fi

    # Configure MetalLB
    log "Configuring MetalLB..."
    kubectl apply -f kubernetes/base/metallb-config.yaml
    success "MetalLB configured"

    # Deploy cert-manager
    if ! kubectl get namespace cert-manager &>/dev/null; then
        log "Installing cert-manager..."
        helm repo add jetstack https://charts.jetstack.io --force-update 2>/dev/null || true
        helm repo update
        helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true --wait --timeout=300s
        success "cert-manager installed"
    fi

    # Deploy nginx-ingress
    if ! kubectl get namespace ingress-nginx &>/dev/null; then
        log "Installing nginx-ingress..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
        kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=300s
        success "nginx-ingress installed"
    fi

    # Step 4: Configure certificates
    log "Configuring certificate infrastructure..."

    # Create CA issuer configuration if it doesn't exist
    if [[ ! -f "/tmp/homelab-ca-issuer.yaml" ]]; then
        cat > /tmp/homelab-ca-issuer.yaml << 'EOF'
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: homelab-ca-issuer
spec:
  ca:
    secretName: homelab-ca-secret
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: homelab-ca-cert
  namespace: cert-manager
spec:
  isCA: true
  commonName: Homelab CA
  secretName: homelab-ca-secret
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: selfsigned-issuer
    kind: ClusterIssuer
    group: cert-manager.io
  subject:
    organizationalUnits:
      - Homelab Infrastructure
    organizations:
      - Homelab
    countries:
      - US
    provinces:
      - "Home"
    localities:
      - "Lab"
EOF
    fi

    kubectl apply -f /tmp/homelab-ca-issuer.yaml

    # Wait for CA certificate
    log "Waiting for CA certificate generation..."
    kubectl wait --for=condition=ready certificate homelab-ca-cert -n cert-manager --timeout=300s
    success "CA certificate ready"

    # Step 5: Deploy all homelab services
    log "Deploying complete homelab service stack..."

    # Deploy Keycloak (SSO Provider)
    log "Deploying Keycloak SSO..."
    kubectl apply -f kubernetes/base/keycloak-deployment.yaml
    kubectl apply -f kubernetes/base/keycloak-realm-enhanced.yaml
    success "Keycloak deployed"

    # Deploy OAuth2 Proxy (Authentication Gateway)
    log "Deploying OAuth2 Proxy..."
    kubectl apply -f kubernetes/base/oauth2-proxy.yaml
    success "OAuth2 Proxy deployed"

    # Deploy monitoring stack
    log "Deploying monitoring services..."
    if [[ -f "helm/charts/monitoring/Chart.yaml" ]]; then
        helm upgrade --install monitoring ./helm/charts/monitoring \
            --namespace monitoring --create-namespace \
            --values helm/environments/values-default.yaml \
            --wait --timeout=300s
    else
        # Fallback to direct manifests
        kubectl apply -f kubernetes/monitoring/
    fi
    success "Monitoring stack deployed"

    # Deploy GitLab
    log "Deploying GitLab..."
    if [[ -f "kubernetes/gitlab/gitlab-deployment.yaml" ]]; then
        kubectl apply -f kubernetes/gitlab/
    fi
    success "GitLab deployed"

    # Deploy AI/ML Tools (Ollama)
    log "Deploying AI/ML tools..."
    if [[ -f "kubernetes/ai-tools/ollama-deployment.yaml" ]]; then
        kubectl apply -f kubernetes/ai-tools/
    fi
    success "AI/ML tools deployed"

    # Deploy JupyterLab
    log "Deploying JupyterLab..."
    if [[ -f "kubernetes/jupyter/jupyter-deployment.yaml" ]]; then
        kubectl apply -f kubernetes/jupyter/
    fi
    success "JupyterLab deployed"

    # Deploy Landing Portal
    log "Deploying homelab portal..."
    if [[ -f "kubernetes/homelab-portal/portal-deployment.yaml" ]]; then
        kubectl apply -f kubernetes/homelab-portal/
    fi
    success "Homelab portal deployed"

    # Wait for all certificates to be ready
    log "Waiting for all service certificates..."
    local cert_namespaces=("monitoring" "gitlab" "ai-tools" "jupyter" "homelab-portal" "keycloak" "oauth2-proxy")
    for ns in "${cert_namespaces[@]}"; do
        if kubectl get namespace "$ns" &>/dev/null; then
            local certs=$(kubectl get certificates -n "$ns" -o name 2>/dev/null || echo "")
            if [[ -n "$certs" ]]; then
                for cert in $certs; do
                    kubectl wait --for=condition=ready "$cert" -n "$ns" --timeout=300s || warning "Certificate $cert in $ns timed out"
                done
            fi
        fi
    done
    success "All certificates processed"

    # Step 6: Verify MetalLB IP assignment
    log "Verifying MetalLB configuration..."
    local max_attempts=30
    local attempt=1
    local external_ip=""

    while [[ $attempt -le $max_attempts ]]; do
        external_ip=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        if [[ "$external_ip" == "$METALLB_IP" ]]; then
            success "MetalLB assigned correct IP: $external_ip"
            break
        else
            log "Waiting for MetalLB IP assignment... (attempt $attempt/$max_attempts)"
            sleep 10
            ((attempt++))
        fi
    done

    if [[ "$external_ip" != "$METALLB_IP" ]]; then
        warning "MetalLB IP assignment issue. Expected: $METALLB_IP, Got: $external_ip"
    fi

    success "Infrastructure deployment complete"

    # Step 7: Run comprehensive health monitoring
    log "Running comprehensive health monitoring..."
    if [[ -f "scripts/health-monitor.sh" ]]; then
        bash scripts/health-monitor.sh continuous 30
        if [[ $? -eq 0 ]]; then
            success "All services are healthy and operational"
        else
            warning "Some services may still be initializing"
        fi
    else
        warning "Health monitor script not found, running basic verification"
        sleep 30  # Give services time to start
    fi

    # Automatically configure local access unless skipped
    if [[ "$SKIP_LOCAL" != "true" ]]; then
        setup_local_access
    else
        log "Local configuration skipped (use --skip-local flag removed to enable)"
        show_manual_setup_instructions
    fi
}

setup_local_access() {
    log "Configuring local workstation for homelab access..."

    # Extract CA certificate
    log "Extracting CA certificate..."
    kubectl get secret homelab-ca-secret -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d > "$CA_CERT_PATH"
    if [[ -s "$CA_CERT_PATH" ]]; then
        success "CA certificate extracted"
    else
        error "Failed to extract CA certificate"
    fi

    # Update /etc/hosts
    log "Configuring DNS resolution..."

    # Create hosts entries file
    cat > /tmp/homelab-hosts-entries.txt << EOF
# Homelab Services (via MetalLB LoadBalancer)
EOF
    for service in "${SERVICES[@]}"; do
        echo "$METALLB_IP ${service}.homelab.local" >> /tmp/homelab-hosts-entries.txt
    done

    # Try to update hosts file
    if sudo -n true 2>/dev/null; then
        # Backup existing hosts file
        sudo cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d_%H%M%S)

        # Remove existing homelab entries
        sudo sed -i '/homelab.local/d' /etc/hosts 2>/dev/null || true

        # Add new entries
        echo "" | sudo tee -a /etc/hosts > /dev/null
        cat /tmp/homelab-hosts-entries.txt | sudo tee -a /etc/hosts > /dev/null

        success "DNS resolution configured"
    else
        warning "Cannot update /etc/hosts automatically (sudo required)"
        show_manual_setup_instructions
        return
    fi

    # Install CA certificate system-wide
    log "Installing CA certificate system-wide..."

    if [[ -f /etc/debian_version ]] && sudo -n true 2>/dev/null; then
        sudo cp "$CA_CERT_PATH" /usr/local/share/ca-certificates/homelab-ca.crt
        sudo update-ca-certificates > /dev/null
        success "CA certificate installed system-wide"
    elif [[ -f /etc/redhat-release ]] && sudo -n true 2>/dev/null; then
        sudo cp "$CA_CERT_PATH" /etc/pki/ca-trust/source/anchors/homelab-ca.crt
        sudo update-ca-trust
        success "CA certificate installed system-wide"
    else
        warning "Automatic certificate installation not supported or requires sudo"
        show_manual_setup_instructions
        return
    fi

    # Test configuration
    test_local_configuration

    success "Local workstation configuration complete"
    show_access_information
}

test_local_configuration() {
    log "Testing local configuration..."

    # Test DNS resolution
    local dns_failures=0
    for service in "${SERVICES[@]}"; do
        local resolved_ip=$(getent hosts ${service}.homelab.local | awk '{print $1}' 2>/dev/null || echo "")
        if [[ "$resolved_ip" == "$METALLB_IP" ]]; then
            success "${service}.homelab.local → $resolved_ip"
        else
            warning "${service}.homelab.local → Resolution failed"
            ((dns_failures++))
        fi
    done

    # Test connectivity
    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/80" 2>/dev/null; then
        success "HTTP connectivity to $METALLB_IP"
    else
        warning "Cannot reach $METALLB_IP:80"
    fi

    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/443" 2>/dev/null; then
        success "HTTPS connectivity to $METALLB_IP"
    else
        warning "Cannot reach $METALLB_IP:443"
    fi

    # Test HTTPS certificate
    local cert_test=$(echo | openssl s_client -servername grafana.homelab.local -connect $METALLB_IP:443 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null || echo "")
    if echo "$cert_test" | grep -q "Homelab CA"; then
        success "HTTPS certificate issued by Homelab CA"
    else
        warning "HTTPS certificate validation failed"
    fi

    if [[ $dns_failures -eq 0 ]]; then
        success "All DNS resolution tests passed"
    else
        warning "$dns_failures DNS resolution failures detected"
    fi
}

show_manual_setup_instructions() {
    echo ""
    echo -e "${BOLD}🔧 MANUAL SETUP REQUIRED${NC}"
    echo "========================="
    echo ""
    echo -e "${YELLOW}Run these commands to complete workstation setup:${NC}"
    echo ""
    echo "1️⃣  Add DNS entries to /etc/hosts:"
    echo "sudo bash -c 'cat >> /etc/hosts << \"EOF\""
    echo ""
    echo "# Homelab Services (via MetalLB LoadBalancer)"
    for service in "${SERVICES[@]}"; do
        echo "$METALLB_IP ${service}.homelab.local"
    done
    echo "EOF'"
    echo ""
    echo "2️⃣  Install CA certificate:"
    echo "sudo cp $CA_CERT_PATH /usr/local/share/ca-certificates/homelab-ca.crt"
    echo "sudo update-ca-certificates"
    echo ""
}

show_status() {
    log "Checking homelab deployment status..."
    echo ""

    # Check cluster connectivity
    if kubectl get nodes &>/dev/null; then
        success "Kubernetes cluster: Connected"

        # Show cluster info
        local nodes=$(kubectl get nodes --no-headers | wc -l)
        local pods=$(kubectl get pods --all-namespaces --no-headers | grep Running | wc -l)
        local services=$(kubectl get services --all-namespaces --no-headers | wc -l)

        echo "   📊 Cluster: $nodes nodes, $pods running pods, $services services"

        # Show namespace status
        local namespaces=("kube-system" "metallb-system" "cert-manager" "ingress-nginx" "monitoring" "longhorn-system")
        for ns in "${namespaces[@]}"; do
            local pod_count=$(kubectl get pods -n "$ns" --no-headers 2>/dev/null | grep Running | wc -l)
            if [[ $pod_count -gt 0 ]]; then
                echo "   📦 $ns: $pod_count running pods"
            fi
        done

        # Check MetalLB status
        local external_ip=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "None")
        if [[ "$external_ip" == "$METALLB_IP" ]]; then
            success "MetalLB LoadBalancer: $external_ip"
        else
            warning "MetalLB LoadBalancer: $external_ip (expected: $METALLB_IP)"
        fi

        # Check certificates
        local cert_count=$(kubectl get certificates --all-namespaces --no-headers 2>/dev/null | grep True | wc -l)
        echo "   🔐 Ready certificates: $cert_count"

    else
        warning "Kubernetes cluster: Not connected"
        echo "   Use '$0 deploy' to deploy the cluster"
    fi

    # Check local configuration
    echo ""
    log "Checking local workstation configuration..."

    # Check DNS resolution
    local dns_ok=0
    for service in "${SERVICES[@]}"; do
        local resolved_ip=$(getent hosts ${service}.homelab.local | awk '{print $1}' 2>/dev/null || echo "")
        if [[ "$resolved_ip" == "$METALLB_IP" ]]; then
            success "${service}.homelab.local → $resolved_ip"
            ((dns_ok++))
        else
            warning "${service}.homelab.local → Not resolved"
        fi
    done

    if [[ $dns_ok -eq ${#SERVICES[@]} ]]; then
        success "DNS configuration: All services resolve correctly"
    else
        warning "DNS configuration: $((${#SERVICES[@]} - dns_ok)) services not resolving"
    fi

    # Check connectivity
    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/80" 2>/dev/null; then
        success "Network connectivity: HTTP reachable"
    else
        warning "Network connectivity: Cannot reach HTTP port"
    fi

    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/443" 2>/dev/null; then
        success "Network connectivity: HTTPS reachable"
    else
        warning "Network connectivity: Cannot reach HTTPS port"
    fi

    # Check CA certificate
    if [[ -f "$CA_CERT_PATH" ]]; then
        success "CA certificate: Available at $CA_CERT_PATH"
        local ca_expiry=$(openssl x509 -in "$CA_CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2)
        echo "   📅 Expires: $ca_expiry"
    else
        warning "CA certificate: Not found"
    fi
}

run_connectivity_tests() {
    log "Running comprehensive connectivity tests..."
    echo ""

    # Basic network tests
    echo -e "${BLUE}🌐 Network Connectivity Tests${NC}"
    echo "=============================="

    if ping -c 1 -W 3 "$HOMELAB_SERVER_IP" &>/dev/null; then
        success "Homelab server ($HOMELAB_SERVER_IP) reachable"
    else
        error "Cannot reach homelab server ($HOMELAB_SERVER_IP)"
    fi

    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/80" 2>/dev/null; then
        success "MetalLB HTTP port accessible"
    else
        warning "MetalLB HTTP port not accessible"
    fi

    if timeout 3 bash -c "echo > /dev/tcp/$METALLB_IP/443" 2>/dev/null; then
        success "MetalLB HTTPS port accessible"
    else
        warning "MetalLB HTTPS port not accessible"
    fi

    # DNS resolution tests
    echo ""
    echo -e "${BLUE}🔍 DNS Resolution Tests${NC}"
    echo "======================="

    for service in "${SERVICES[@]}"; do
        local resolved_ip=$(getent hosts ${service}.homelab.local | awk '{print $1}' 2>/dev/null || echo "")
        if [[ "$resolved_ip" == "$METALLB_IP" ]]; then
            success "${service}.homelab.local → $resolved_ip"
        else
            warning "${service}.homelab.local → Failed to resolve"
        fi
    done

    # HTTPS certificate tests
    echo ""
    echo -e "${BLUE}🔐 HTTPS Certificate Tests${NC}"
    echo "=========================="

    for service in "${SERVICES[@]}"; do
        local cert_info=$(echo | openssl s_client -servername ${service}.homelab.local -connect $METALLB_IP:443 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null || echo "")
        if echo "$cert_info" | grep -q "Homelab CA"; then
            success "${service}.homelab.local certificate issued by Homelab CA"
        else
            warning "${service}.homelab.local certificate validation failed"
        fi

        local https_code=$(curl -k -s -w "%{http_code}" -o /dev/null https://${service}.homelab.local/ 2>/dev/null || echo "000")
        if [[ "$https_code" =~ ^[23] ]]; then
            success "${service}.homelab.local HTTPS responding (HTTP $https_code)"
        elif [[ "$https_code" == "404" ]]; then
            warning "${service}.homelab.local service not deployed (HTTP 404)"
        else
            warning "${service}.homelab.local HTTPS issue (HTTP $https_code)"
        fi
    done

    echo ""
    success "Connectivity tests completed"
}

show_access_information() {
    echo ""
    echo -e "${BOLD}🌐 HOMELAB ACCESS INFORMATION${NC}"
    echo "=============================="
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    for service in "${SERVICES[@]}"; do
        local status="🔹"
        if [[ "$service" == "grafana" ]]; then
            status="✅"
        else
            status="🔹"
        fi
        echo "   $status $(echo ${service^}): https://${service}.homelab.local"
    done
    echo ""
    echo -e "${BLUE}Default Credentials:${NC}"
    echo "   🔐 Grafana: admin/admin"
    echo ""
    echo -e "${YELLOW}Browser Configuration:${NC}"
    echo "   📋 Import CA certificate for trusted HTTPS:"
    echo "   📁 Certificate: $CA_CERT_PATH"
    echo ""
    echo -e "${GREEN}Chrome/Chromium:${NC} Settings → Privacy → Security → Certificates → Authorities → Import"
    echo -e "${GREEN}Firefox:${NC} Settings → Privacy → Certificates → Authorities → Import"
    echo ""
    echo -e "${BLUE}Quick Test:${NC}"
    echo "   curl -I https://grafana.homelab.local"
    echo ""
}

# Parse command line arguments
COMMAND=""
SKIP_LOCAL="false"
BACKUP_FIRST="false"
FORCE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        deploy|teardown|setup-local|status|backup|restore|test)
            COMMAND="$1"
            shift
            ;;
        --skip-local)
            SKIP_LOCAL="true"
            shift
            ;;
        --backup-first)
            BACKUP_FIRST="true"
            shift
            ;;
        --force)
            FORCE="true"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main script execution
cd "$SCRIPT_DIR"

case "$COMMAND" in
    "deploy")
        show_banner
        echo -e "${BOLD}🚀 COMPLETE HOMELAB DEPLOYMENT${NC}"
        echo "================================"
        check_prerequisites
deploy_infrastructure || error "Initial deployment check failed or infrastructure already exists"
        echo ""
        success "Deployment completed successfully or already in place!"
        ;;
    "teardown")
        show_banner
        echo -e "${BOLD}💥 COMPLETE HOMELAB TEARDOWN${NC}"
        echo "=============================="
        complete_teardown
        echo ""
        success "Teardown completed successfully!"
        ;;
    "setup-local")
        show_banner
        echo -e "${BOLD}🌐 LOCAL WORKSTATION SETUP${NC}"
        echo "=========================="
        setup_local_access
        ;;
    "status")
        show_banner
        echo -e "${BOLD}📊 DEPLOYMENT STATUS${NC}"
        echo "===================="
        show_status
        ;;
    "backup")
        show_banner
        echo -e "${BOLD}📦 BACKUP DEPLOYMENT${NC}"
        echo "==================="
        backup_path=$(create_backup)
        echo ""
        success "Backup completed: $backup_path"
        ;;
    "test")
        show_banner
        echo -e "${BOLD}🧪 CONNECTIVITY TESTS${NC}"
        echo "====================="
        run_connectivity_tests
        ;;
    *)
        show_usage
        ;;
esac
