#!/bin/bash

# Homelab Infrastructure Health Monitor
# This script continuously monitors all services and only marks deployment complete
# when all services are healthy and accessible

set -e

# Configuration
LOAD_BALANCER_IP="192.168.16.100"
SERVICES=(
    "auth.homelab.local:Keycloak:keycloak"
    "homelab.local:Landing Portal:portal"
    "grafana.homelab.local:Grafana:monitoring"
    "prometheus.homelab.local:Prometheus:monitoring"
    "ollama.homelab.local:Ollama+WebUI:ai-tools"
    "jupyter.homelab.local:JupyterLab:jupyter"
    "gitlab.homelab.local:GitLab:gitlab"
)

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
WAIT="⏳"
INFO="ℹ️"

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_kubernetes_health() {
    log "${BLUE}🔍 Checking Kubernetes cluster health...${NC}"

    # Check node status
    local node_status=$(kubectl get nodes --no-headers | awk '{print $2}')
    if [[ "$node_status" != "Ready" ]]; then
        log "${RED}${CROSS} Kubernetes node is not ready${NC}"
        return 1
    fi

    # Check system pods
    local failed_pods=$(kubectl get pods -n kube-system --no-headers | grep -v "Running\|Completed" | wc -l)
    if [[ "$failed_pods" -gt 0 ]]; then
        log "${RED}${CROSS} $failed_pods system pods are not running${NC}"
        return 1
    fi

    # Check ingress controller
    local ingress_ready=$(kubectl get pods -n ingress-nginx --no-headers | grep "ingress-nginx-controller" | awk '{print $2}')
    if [[ "$ingress_ready" != "1/1" ]]; then
        log "${RED}${CROSS} Ingress controller is not ready${NC}"
        return 1
    fi

    # Check cert-manager
    local cert_manager_pods=$(kubectl get pods -n cert-manager --no-headers | grep -v "Running" | wc -l)
    if [[ "$cert_manager_pods" -gt 0 ]]; then
        log "${RED}${CROSS} Cert-manager pods are not running${NC}"
        return 1
    fi

    log "${GREEN}${CHECK} Kubernetes cluster is healthy${NC}"
    return 0
}

check_service_pods() {
    log "${BLUE}🔍 Checking service pod health...${NC}"

    local failed_services=0
    local namespaces=("homelab-portal" "monitoring" "ai-tools" "jupyter" "gitlab")

    for namespace in "${namespaces[@]}"; do
        if kubectl get namespace "$namespace" &>/dev/null; then
            local pod_status=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null)
            if [[ -n "$pod_status" ]]; then
                local not_running=$(echo "$pod_status" | grep -v "Running" | wc -l)
                local total_pods=$(echo "$pod_status" | wc -l)
                local running_pods=$((total_pods - not_running))

                if [[ "$not_running" -gt 0 ]]; then
                    log "${YELLOW}${WARN} Namespace $namespace: $running_pods/$total_pods pods running${NC}"
                    failed_services=$((failed_services + not_running))
                else
                    log "${GREEN}${CHECK} Namespace $namespace: All $total_pods pods running${NC}"
                fi
            fi
        fi
    done

    if [[ "$failed_services" -gt 0 ]]; then
        log "${RED}${CROSS} $failed_services service pods are not running${NC}"
        return 1
    fi

    log "${GREEN}${CHECK} All service pods are healthy${NC}"
    return 0
}

check_certificates() {
    log "${BLUE}🔍 Checking SSL certificates...${NC}"

    local cert_status=$(kubectl get certificates -A --no-headers | grep -v "True" | wc -l)
    if [[ "$cert_status" -gt 0 ]]; then
        log "${RED}${CROSS} $cert_status certificates are not ready${NC}"
        kubectl get certificates -A | grep -v "True"
        return 1
    fi

    log "${GREEN}${CHECK} All SSL certificates are valid${NC}"
    return 0
}

check_storage() {
    log "${BLUE}🔍 Checking persistent storage...${NC}"

    local pvc_status=$(kubectl get pvc -A --no-headers | grep -v "Bound" | wc -l)
    if [[ "$pvc_status" -gt 0 ]]; then
        log "${RED}${CROSS} $pvc_status PVCs are not bound${NC}"
        return 1
    fi

    log "${GREEN}${CHECK} All persistent volumes are bound${NC}"
    return 0
}

check_service_connectivity() {
    local url=$1
    local name=$2
    local expected_codes=("200" "302" "401")  # Accept these as healthy

    local response=$(curl -k -s -o /dev/null -w "%{http_code}|%{time_total}" \
        -H "Host: $url" "https://$LOAD_BALANCER_IP/" --max-time 10 2>/dev/null || echo "000|0")

    IFS='|' read -r status_code response_time <<< "$response"

    # Check if status code is in expected healthy codes
    local is_healthy=false
    for code in "${expected_codes[@]}"; do
        if [[ "$status_code" == "$code" ]]; then
            is_healthy=true
            break
        fi
    done

    if [[ "$is_healthy" == true ]]; then
        printf "${GREEN}${CHECK} %-15s | HTTP %s | %ss${NC}\n" "$name" "$status_code" "$response_time"
        return 0
    else
        case $status_code in
            502|503) printf "${YELLOW}${WAIT} %-15s | HTTP %s | Still starting${NC}\n" "$name" "$status_code" ;;
            404) printf "${RED}${CROSS} %-15s | HTTP %s | Not found${NC}\n" "$name" "$status_code" ;;
            000) printf "${RED}${CROSS} %-15s | Timeout/Connection failed${NC}\n" "$name" ;;
            *) printf "${YELLOW}${WARN} %-15s | HTTP %s | Unexpected${NC}\n" "$name" "$status_code" ;;
        esac
        return 1
    fi
}

check_all_services() {
    log "${BLUE}🔍 Checking service connectivity...${NC}"

    local failed_services=0

    for service_entry in "${SERVICES[@]}"; do
        IFS=':' read -r url name namespace <<< "$service_entry"
        if ! check_service_connectivity "$url" "$name"; then
            failed_services=$((failed_services + 1))
        fi
    done

    if [[ "$failed_services" -gt 0 ]]; then
        log "${RED}${CROSS} $failed_services services are not accessible${NC}"
        return 1
    fi

    log "${GREEN}${CHECK} All services are accessible${NC}"
    return 0
}

perform_health_check() {
    local checks_passed=0
    local total_checks=5

    echo "═══════════════════════════════════════════"
    log "${BLUE}🏠 HOMELAB INFRASTRUCTURE HEALTH CHECK${NC}"
    echo "═══════════════════════════════════════════"

    # Run all health checks
    if check_kubernetes_health; then checks_passed=$((checks_passed + 1)); fi
    echo
    if check_service_pods; then checks_passed=$((checks_passed + 1)); fi
    echo
    if check_certificates; then checks_passed=$((checks_passed + 1)); fi
    echo
    if check_storage; then checks_passed=$((checks_passed + 1)); fi
    echo
    if check_all_services; then checks_passed=$((checks_passed + 1)); fi
    echo

    # Summary
    echo "═══════════════════════════════════════════"
    log "${BLUE}📊 HEALTH CHECK SUMMARY${NC}"
    echo "═══════════════════════════════════════════"

    if [[ "$checks_passed" -eq "$total_checks" ]]; then
        log "${GREEN}🎉 DEPLOYMENT COMPLETE! All systems are healthy and operational${NC}"
        log "${GREEN}${CHECK} Kubernetes cluster: Healthy${NC}"
        log "${GREEN}${CHECK} Service pods: All running${NC}"
        log "${GREEN}${CHECK} SSL certificates: All valid${NC}"
        log "${GREEN}${CHECK} Storage: All volumes bound${NC}"
        log "${GREEN}${CHECK} Service connectivity: All accessible${NC}"
        echo
        log "${GREEN}✨ Your homelab infrastructure is ready for production use!${NC}"
        return 0
    else
        local failed_checks=$((total_checks - checks_passed))
        log "${YELLOW}${WARN} DEPLOYMENT INCOMPLETE: $checks_passed/$total_checks checks passed${NC}"
        log "${YELLOW}${INFO} $failed_checks systems need attention${NC}"
        return 1
    fi
}

continuous_monitoring() {
    local iteration=1
    local max_iterations=${1:-60}  # Default 60 iterations (10 minutes with 10s intervals)

    while [[ $iteration -le $max_iterations ]]; do
        log "${BLUE}🔄 Health Check Iteration $iteration/$max_iterations${NC}"

        if perform_health_check; then
            log "${GREEN}🏁 Continuous monitoring complete - all systems healthy!${NC}"
            return 0
        fi

        if [[ $iteration -lt $max_iterations ]]; then
            log "${BLUE}⏱️  Waiting 10 seconds before next check...${NC}"
            sleep 10
        fi

        iteration=$((iteration + 1))
        echo
    done

    log "${RED}${CROSS} Maximum monitoring iterations reached. Some systems may still be initializing.${NC}"
    return 1
}

# Main execution
case "${1:-continuous}" in
    "once")
        perform_health_check
        ;;
    "continuous")
        continuous_monitoring "${2:-60}"
        ;;
    "quick")
        continuous_monitoring 10
        ;;
    *)
        echo "Usage: $0 [once|continuous|quick] [max_iterations]"
        echo "  once        - Run health check once"
        echo "  continuous  - Run continuous monitoring (default, 60 iterations)"
        echo "  quick       - Run quick monitoring (10 iterations)"
        exit 1
        ;;
esac
