#!/bin/bash
# Optimized Homelab Deployment Script
# Combines validation, deployment, and monitoring for reliable homelab infrastructure deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
ENVIRONMENT="${1:-development}"
LOG_DIR="${HOME}/.local/log/homelab-deployment"
LOG_FILE="${LOG_DIR}/deployment-$(date +%Y%m%d-%H%M%S).log"
VALIDATION_TIMEOUT=600  # 10 minutes
DEPLOYMENT_TIMEOUT=1200  # 20 minutes

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    mkdir -p "$LOG_DIR"
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    
    case "$level" in
        ERROR) echo -e "${RED}[$level]${NC} $message" >&2 ;;
        WARN)  echo -e "${YELLOW}[$level]${NC} $message" ;;
        INFO)  echo -e "${GREEN}[$level]${NC} $message" ;;
        DEBUG) [[ ${DEBUG:-false} == "true" ]] && echo -e "${BLUE}[$level]${NC} $message" ;;
    esac
}

log_header() {
    echo -e "${PURPLE}$1${NC}"
    log "INFO" "$1"
}

# Validation tracking
VALIDATION_RESULTS=()
FAILED_CHECKS=()
TOTAL_CHECKS=0
PASSED_CHECKS=0

add_result() {
    local check_name="$1"
    local status="$2"
    local details="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [[ $status == "PASS" ]]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log "INFO" "✅ $check_name: $details"
        VALIDATION_RESULTS+=("✅ $check_name: $details")
    else
        log "ERROR" "❌ $check_name: $details"
        VALIDATION_RESULTS+=("❌ $check_name: $details")
        FAILED_CHECKS+=("$check_name")
    fi
}

show_usage() {
    cat <<EOF
Optimized Homelab Deployment Script

USAGE:
    $0 [ENVIRONMENT] [OPTIONS]

ENVIRONMENTS:
    development    Deploy to development environment (default)
    staging        Deploy to staging environment  
    production     Deploy to production environment

OPTIONS:
    --dry-run     Perform validation and dry-run without deployment
    --debug       Enable debug logging
    --help        Show this help message

EXAMPLES:
    $0 development
    $0 production --dry-run
    DEBUG=true $0 staging

EOF
}

# Parse arguments
DRY_RUN=false
while [[ $# -gt 1 ]]; do
    case $2 in
        --dry-run) DRY_RUN=true; shift ;;
        --debug) export DEBUG=true; shift ;;
        --help) show_usage; exit 0 ;;
        *) log "ERROR" "Unknown option: $2"; show_usage; exit 1 ;;
    esac
done

if [[ $1 == "--help" ]]; then
    show_usage
    exit 0
fi

# Validate environment
if [[ ! $ENVIRONMENT =~ ^(development|staging|production)$ ]]; then
    log "ERROR" "Invalid environment: $ENVIRONMENT"
    log "INFO" "Valid environments: development, staging, production"
    exit 1
fi

log_header "🚀 Optimized Homelab Deployment Started"
log "INFO" "Environment: $ENVIRONMENT"
log "INFO" "Dry Run: $DRY_RUN"
log "INFO" "Log File: $LOG_FILE"

# Wait for nodes to become ready with retry logic
wait_for_nodes_ready() {
    log "INFO" "Waiting for K3s nodes to become ready..."
    
    local max_wait=300  # 5 minutes
    local check_interval=10
    local elapsed=0
    local min_nodes=1
    
    while [[ $elapsed -lt $max_wait ]]; do
        # Check if any nodes exist first
        local node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo 0)
        
        if [[ $node_count -eq 0 ]]; then
            log "DEBUG" "No nodes found yet, waiting for K3s to initialize..."
            sleep $check_interval
            elapsed=$((elapsed + check_interval))
            continue
        fi
        
        # Check node readiness
        local ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo 0)
        local total_nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo 0)
        
        log "DEBUG" "Node status: $ready_nodes/$total_nodes ready"
        
        if [[ $ready_nodes -ge $min_nodes && $ready_nodes -eq $total_nodes ]]; then
            log "INFO" "All $total_nodes node(s) are ready"
            return 0
        fi
        
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
    done
    
    log "ERROR" "Nodes did not become ready within ${max_wait}s"
    kubectl get nodes --no-headers 2>/dev/null || echo "Cannot access cluster"
    return 1
}

# Prerequisite validation
validate_prerequisites() {
    log_header "🔍 Validating Prerequisites"
    
    local required_tools=("helm" "helmfile" "kubectl" "yq" "curl")
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &>/dev/null; then
            add_result "Tool: $tool" "PASS" "Available"
        else
            add_result "Tool: $tool" "FAIL" "Not found"
        fi
    done
    
    # Check Kubernetes connectivity and wait for nodes
    if kubectl cluster-info &>/dev/null; then
        if wait_for_nodes_ready; then
            local node_count=$(kubectl get nodes --no-headers | wc -l)
            local ready_nodes=$(kubectl get nodes --no-headers | grep -c " Ready ")
            add_result "Kubernetes Cluster" "PASS" "$ready_nodes/$node_count node(s) ready"
        else
            add_result "Kubernetes Cluster" "FAIL" "Nodes not ready within timeout"
            return 1
        fi
    else
        add_result "Kubernetes Cluster" "FAIL" "Cannot connect to cluster"
        return 1
    fi
    
    # Check Helm repositories
    if helm repo list | grep -q "prometheus-community\|grafana\|ingress-nginx"; then
        add_result "Helm Repositories" "PASS" "Required repositories available"
    else
        log "INFO" "Adding required Helm repositories..."
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo add grafana https://grafana.github.io/helm-charts
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
        helm repo add jetstack https://charts.jetstack.io
        helm repo add metallb https://metallb.github.io/metallb
        helm repo add longhorn https://charts.longhorn.io
        helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
        helm repo update
        add_result "Helm Repositories" "PASS" "Repositories updated"
    fi
}

# Enhanced chart validation
validate_charts() {
    log_header "📋 Validating Helm Charts"
    
    # Run chart validation script
    if ./validate-charts.sh &>>"$LOG_FILE"; then
        add_result "Chart Validation" "PASS" "All charts valid"
    else
        add_result "Chart Validation" "FAIL" "Chart validation failed - check logs"
        return 1
    fi
}

# Template validation
validate_templates() {
    log_header "🔧 Validating Templates"
    
    # Run template validation
    if ./validate-templates.sh "$ENVIRONMENT" &>>"$LOG_FILE"; then
        add_result "Template Validation" "PASS" "Templates render correctly"
    else
        add_result "Template Validation" "FAIL" "Template validation failed - check logs"
        return 1
    fi
}

# Deploy infrastructure with retry logic
deploy_infrastructure() {
    if [[ $DRY_RUN == true ]]; then
        log_header "🏗️ Dry Run - Infrastructure Deployment"
        
        if helmfile -e "$ENVIRONMENT" diff 2>>"$LOG_FILE"; then
            add_result "Deployment Dry Run" "PASS" "No deployment errors in dry run"
        else
            add_result "Deployment Dry Run" "FAIL" "Dry run failed - check configuration"
            return 1
        fi
        return 0
    fi
    
    log_header "🏗️ Deploying Infrastructure"
    
    local max_retries=3
    local retry_count=0
    
    while [[ $retry_count -lt $max_retries ]]; do
        log "INFO" "Deployment attempt $((retry_count + 1))/$max_retries"
        
        if timeout $DEPLOYMENT_TIMEOUT helmfile -e "$ENVIRONMENT" sync --wait --timeout 600 2>>"$LOG_FILE"; then
            add_result "Infrastructure Deployment" "PASS" "All releases deployed successfully"
            return 0
        else
            retry_count=$((retry_count + 1))
            if [[ $retry_count -lt $max_retries ]]; then
                log "WARN" "Deployment failed, retrying in 30 seconds..."
                sleep 30
            fi
        fi
    done
    
    add_result "Infrastructure Deployment" "FAIL" "Deployment failed after $max_retries attempts"
    return 1
}

# Wait for deployment stabilization
wait_for_stabilization() {
    log_header "⏳ Waiting for Deployment Stabilization"
    
    local max_wait=$VALIDATION_TIMEOUT
    local check_interval=15
    local elapsed=0
    
    while [[ $elapsed -lt $max_wait ]]; do
        local total_pods=$(kubectl get pods -A --no-headers | wc -l)
        local running_pods=$(kubectl get pods -A --no-headers | grep -c "Running" || echo 0)
        local failed_pods=$(kubectl get pods -A --no-headers | grep -cE "(Error|CrashLoopBackOff|ImagePullBackOff)" || echo 0)
        
        log "DEBUG" "Pod status: $running_pods/$total_pods running, $failed_pods failed"
        
        if [[ $failed_pods -eq 0 && $running_pods -gt $((total_pods * 80 / 100)) ]]; then
            add_result "Deployment Stabilization" "PASS" "$running_pods/$total_pods pods running"
            return 0
        fi
        
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
        echo -n "."
    done
    
    echo
    add_result "Deployment Stabilization" "FAIL" "Deployment did not stabilize within ${max_wait}s"
    return 1
}

# Comprehensive health checks
run_health_checks() {
    log_header "🏥 Running Health Checks"
    
    # Check critical namespaces
    local critical_namespaces=("metallb-system" "cert-manager" "ingress-nginx" "longhorn-system" "monitoring")
    for ns in "${critical_namespaces[@]}"; do
        if kubectl get namespace "$ns" &>/dev/null; then
            local ready_pods=$(kubectl get pods -n "$ns" --no-headers | grep -c "Running" || echo 0)
            local total_pods=$(kubectl get pods -n "$ns" --no-headers | wc -l)
            
            if [[ $total_pods -gt 0 && $ready_pods -eq $total_pods ]]; then
                add_result "Namespace: $ns" "PASS" "$ready_pods/$total_pods pods ready"
            else
                add_result "Namespace: $ns" "FAIL" "Only $ready_pods/$total_pods pods ready"
            fi
        else
            add_result "Namespace: $ns" "FAIL" "Namespace not found"
        fi
    done
    
    # Check ingress controller
    if kubectl get svc -n ingress-nginx ingress-nginx-controller &>/dev/null; then
        local external_ip=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [[ -n $external_ip && $external_ip != "null" ]]; then
            add_result "Ingress External IP" "PASS" "IP assigned: $external_ip"
        else
            add_result "Ingress External IP" "FAIL" "No external IP assigned"
        fi
    else
        add_result "Ingress Controller" "FAIL" "Service not found"
    fi
    
    # Check certificate issuers
    if kubectl get clusterissuer &>/dev/null; then
        local ready_issuers=$(kubectl get clusterissuer --no-headers | grep -c "True" || echo 0)
        local total_issuers=$(kubectl get clusterissuer --no-headers | wc -l)
        
        if [[ $total_issuers -gt 0 && $ready_issuers -eq $total_issuers ]]; then
            add_result "Certificate Issuers" "PASS" "$ready_issuers/$total_issuers issuers ready"
        else
            add_result "Certificate Issuers" "FAIL" "Only $ready_issuers/$total_issuers issuers ready"
        fi
    else
        add_result "Certificate Issuers" "FAIL" "No cluster issuers found"
    fi
    
    # Check storage
    if kubectl get storageclass --no-headers | grep -q "(default)"; then
        local default_sc=$(kubectl get storageclass --no-headers | grep "(default)" | awk '{print $1}')
        add_result "Default Storage Class" "PASS" "Default: $default_sc"
    else
        add_result "Default Storage Class" "FAIL" "No default storage class"
    fi
}

# Connectivity tests
run_connectivity_tests() {
    log_header "🔗 Running Connectivity Tests"
    
    local test_pod="connectivity-test-$(date +%s)"
    
    # Create test pod
    kubectl run "$test_pod" --image=curlimages/curl:latest --restart=Never --rm -i --tty=false -- sleep 300 &>/dev/null || true
    
    # Wait for pod to be ready
    local max_wait=60
    local elapsed=0
    while [[ $elapsed -lt $max_wait ]]; do
        if kubectl get pod "$test_pod" --no-headers | grep -q "Running"; then
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if kubectl get pod "$test_pod" --no-headers | grep -q "Running"; then
        # Test DNS resolution
        if kubectl exec "$test_pod" -- nslookup kubernetes.default.svc.cluster.local &>/dev/null; then
            add_result "DNS Resolution" "PASS" "Internal DNS working"
        else
            add_result "DNS Resolution" "FAIL" "DNS resolution failed"
        fi
        
        # Test API server connectivity
        if kubectl exec "$test_pod" -- curl -s -k https://kubernetes.default.svc.cluster.local/version &>/dev/null; then
            add_result "API Server Connectivity" "PASS" "Can reach Kubernetes API"
        else
            add_result "API Server Connectivity" "FAIL" "Cannot reach Kubernetes API"
        fi
    else
        add_result "Connectivity Tests" "FAIL" "Could not create test pod"
    fi
    
    # Cleanup
    kubectl delete pod "$test_pod" --ignore-not-found --grace-period=0 --force &>/dev/null || true
}

# Generate deployment report
generate_report() {
    log_header "📊 Generating Deployment Report"
    
    local report_file="$LOG_DIR/deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat >"$report_file" <<EOF
# Homelab Infrastructure Deployment Report

**Date**: $(date)
**Environment**: $ENVIRONMENT
**Dry Run**: $DRY_RUN
**Duration**: $((SECONDS / 60))m $((SECONDS % 60))s

## Summary

- **Total Checks**: $TOTAL_CHECKS
- **Passed**: $PASSED_CHECKS
- **Failed**: $((TOTAL_CHECKS - PASSED_CHECKS))
- **Success Rate**: $(((PASSED_CHECKS * 100) / TOTAL_CHECKS))%

## Validation Results

EOF
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        echo "$result" >>"$report_file"
    done
    
    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        cat >>"$report_file" <<EOF

## Failed Checks

EOF
        for failed_check in "${FAILED_CHECKS[@]}"; do
            echo "- $failed_check" >>"$report_file"
        done
    fi
    
    cat >>"$report_file" <<EOF

## Cluster Status

### Nodes
\`\`\`
$(kubectl get nodes -o wide 2>/dev/null || echo "kubectl not accessible")
\`\`\`

### Services
\`\`\`
$(kubectl get svc -A 2>/dev/null || echo "kubectl not accessible")
\`\`\`

### Ingress Resources
\`\`\`
$(kubectl get ingress -A 2>/dev/null || echo "kubectl not accessible")
\`\`\`

EOF
    
    log "INFO" "Deployment report: $report_file"
}

# Show final summary
show_summary() {
    log_header "🎯 Deployment Summary"
    
    echo
    echo "=============================================="
    echo "  HOMELAB DEPLOYMENT COMPLETE"  
    echo "=============================================="
    echo
    echo "Environment: $ENVIRONMENT"
    echo "Duration: $((SECONDS / 60))m $((SECONDS % 60))s"
    echo "Success Rate: $(((PASSED_CHECKS * 100) / TOTAL_CHECKS))%"
    echo
    echo "Results:"
    echo "  ✅ Passed: $PASSED_CHECKS"
    echo "  ❌ Failed: $((TOTAL_CHECKS - PASSED_CHECKS))"
    echo "  📊 Total:  $TOTAL_CHECKS"
    echo
    
    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        echo "⚠️  FAILED CHECKS:"
        for failed_check in "${FAILED_CHECKS[@]}"; do
            echo "   - $failed_check"
        done
        echo
        return 1
    else
        echo "🎉 ALL CHECKS PASSED!"
        echo
        echo "🚀 Your homelab infrastructure is ready!"
        echo
        return 0
    fi
}

# Main execution
main() {
    local start_time=$SECONDS
    
    # Run deployment phases
    validate_prerequisites || exit 1
    validate_charts || exit 1
    validate_templates || exit 1
    
    deploy_infrastructure || exit 1
    
    if [[ $DRY_RUN == false ]]; then
        wait_for_stabilization || exit 1
        run_health_checks
        run_connectivity_tests
    fi
    
    generate_report
    
    if show_summary; then
        log "INFO" "✅ Deployment completed successfully"
        exit 0
    else
        log "ERROR" "❌ Deployment completed with issues"
        exit 1
    fi
}

# Execute main function
main "$@"