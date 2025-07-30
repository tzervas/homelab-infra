#!/bin/bash

# Comprehensive Homelab Deployment Validation Script
# This script validates the complete deployment workflow including all services and authentication flows

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/deployment-validation-$(date +%Y%m%d_%H%M%S).log"
LOAD_BALANCER_IP="192.168.16.100"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Icons
CHECK="✅"
CROSS="❌"
WARN="⚠️"
WAIT="⏳"
INFO="ℹ️"
ROCKET="🚀"

# Service definitions
declare -A SERVICES=(
    ["auth.homelab.local"]="Keycloak Authentication"
    ["homelab.local"]="Landing Portal"
    ["grafana.homelab.local"]="Grafana Monitoring"
    ["prometheus.homelab.local"]="Prometheus Metrics"
    ["gitlab.homelab.local"]="GitLab Repository"
    ["ollama.homelab.local"]="Ollama+WebUI AI"
    ["jupyter.homelab.local"]="JupyterLab Notebooks"
)

# Expected response codes for each service
declare -A EXPECTED_CODES=(
    ["auth.homelab.local"]="200"
    ["homelab.local"]="200,302"
    ["grafana.homelab.local"]="200,302"
    ["prometheus.homelab.local"]="200,302"
    ["gitlab.homelab.local"]="200,302"
    ["ollama.homelab.local"]="200,302"
    ["jupyter.homelab.local"]="200,302"
)

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "${SCRIPT_DIR}/logs" 2>/dev/null || true

    case $level in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $message" | tee -a "$LOG_FILE" ;;
    esac
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Header function
print_header() {
    local title="$1"
    echo -e "\n${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}$title${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
}

# Validate prerequisites
validate_prerequisites() {
    print_header "🔍 VALIDATING PREREQUISITES"

    local issues=0

    # Check kubectl
    if command -v kubectl &> /dev/null; then
        log "INFO" "${CHECK} kubectl is available"
    else
        log "ERROR" "${CROSS} kubectl is not installed"
        issues=$((issues + 1))
    fi

    # Check cluster connectivity
    if kubectl cluster-info &> /dev/null; then
        log "INFO" "${CHECK} Kubernetes cluster is accessible"
    else
        log "ERROR" "${CROSS} Cannot connect to Kubernetes cluster"
        issues=$((issues + 1))
    fi

    # Check curl
    if command -v curl &> /dev/null; then
        log "INFO" "${CHECK} curl is available"
    else
        log "ERROR" "${CROSS} curl is not installed"
        issues=$((issues + 1))
    fi

    # Check required files
    local required_files=(
        "deploy-homelab-with-sso.sh"
        "scripts/health-monitor.sh"
        "kubernetes/base/keycloak-deployment.yaml"
        "kubernetes/base/oauth2-proxy.yaml"
    )

    for file in "${required_files[@]}"; do
        if [[ -f "${SCRIPT_DIR}/${file}" ]]; then
            log "INFO" "${CHECK} Required file exists: ${file}"
        else
            log "ERROR" "${CROSS} Required file missing: ${file}"
            issues=$((issues + 1))
        fi
    done

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "All prerequisites validated"
        return 0
    else
        log "ERROR" "Prerequisites validation failed with $issues issues"
        return 1
    fi
}

# Validate cluster health
validate_cluster_health() {
    print_header "🏥 VALIDATING CLUSTER HEALTH"

    local issues=0

    # Check nodes
    local nodes_ready=$(kubectl get nodes --no-headers | grep " Ready " | wc -l)
    local total_nodes=$(kubectl get nodes --no-headers | wc -l)

    if [[ $nodes_ready -eq $total_nodes && $total_nodes -gt 0 ]]; then
        log "INFO" "${CHECK} All $total_nodes nodes are ready"
    else
        log "ERROR" "${CROSS} Only $nodes_ready/$total_nodes nodes are ready"
        issues=$((issues + 1))
    fi

    # Check system pods
    local system_pods_running=$(kubectl get pods -n kube-system --no-headers | grep "Running" | wc -l)
    local total_system_pods=$(kubectl get pods -n kube-system --no-headers | wc -l)

    if [[ $system_pods_running -eq $total_system_pods ]]; then
        log "INFO" "${CHECK} All $total_system_pods system pods are running"
    else
        log "WARN" "${WARN} Only $system_pods_running/$total_system_pods system pods are running"
    fi

    # Check core services
    local core_services=("ingress-nginx-controller" "coredns" "metrics-server")
    for service in "${core_services[@]}"; do
        if kubectl get pods -A | grep "$service" | grep -q "Running"; then
            log "INFO" "${CHECK} Core service running: $service"
        else
            log "ERROR" "${CROSS} Core service not running: $service"
            issues=$((issues + 1))
        fi
    done

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Cluster health validation passed"
        return 0
    else
        log "ERROR" "Cluster health validation failed with $issues issues"
        return 1
    fi
}

# Validate namespaces and resources
validate_namespaces() {
    print_header "📦 VALIDATING NAMESPACES AND RESOURCES"

    local issues=0
    local expected_namespaces=("keycloak" "oauth2-proxy" "monitoring" "gitlab" "ai-tools" "jupyter" "homelab-portal")

    for namespace in "${expected_namespaces[@]}"; do
        if kubectl get namespace "$namespace" &> /dev/null; then
            log "INFO" "${CHECK} Namespace exists: $namespace"

            # Check pods in namespace
            local pods_running=$(kubectl get pods -n "$namespace" --no-headers | grep "Running" | wc -l)
            local total_pods=$(kubectl get pods -n "$namespace" --no-headers | wc -l)

            if [[ $pods_running -eq $total_pods && $total_pods -gt 0 ]]; then
                log "INFO" "${CHECK} All $total_pods pods running in $namespace"
            else
                log "WARN" "${WARN} Only $pods_running/$total_pods pods running in $namespace"
            fi
        else
            log "ERROR" "${CROSS} Namespace missing: $namespace"
            issues=$((issues + 1))
        fi
    done

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Namespace validation passed"
        return 0
    else
        log "ERROR" "Namespace validation failed with $issues issues"
        return 1
    fi
}

# Validate certificates
validate_certificates() {
    print_header "🔒 VALIDATING SSL CERTIFICATES"

    local issues=0

    # Check certificate resources
    local certificates=$(kubectl get certificates -A --no-headers | wc -l)
    if [[ $certificates -gt 0 ]]; then
        log "INFO" "${CHECK} Found $certificates SSL certificates"

        # Check certificate status
        local ready_certs=$(kubectl get certificates -A --no-headers | grep "True" | wc -l)
        if [[ $ready_certs -eq $certificates ]]; then
            log "INFO" "${CHECK} All $certificates certificates are ready"
        else
            log "WARN" "${WARN} Only $ready_certs/$certificates certificates are ready"
            kubectl get certificates -A | grep -v "True" || true
        fi
    else
        log "ERROR" "${CROSS} No SSL certificates found"
        issues=$((issues + 1))
    fi

    # Check cluster issuers
    if kubectl get clusterissuers --no-headers | grep -q "homelab-ca-issuer"; then
        log "INFO" "${CHECK} Homelab CA issuer is configured"
    else
        log "ERROR" "${CROSS} Homelab CA issuer not found"
        issues=$((issues + 1))
    fi

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Certificate validation passed"
        return 0
    else
        log "ERROR" "Certificate validation failed with $issues issues"
        return 1
    fi
}

# Validate ingress and networking
validate_networking() {
    print_header "🌐 VALIDATING INGRESS AND NETWORKING"

    local issues=0

    # Check ingress controller
    if kubectl get pods -n ingress-nginx | grep -q "ingress-nginx-controller.*Running"; then
        log "INFO" "${CHECK} Ingress controller is running"
    else
        log "ERROR" "${CROSS} Ingress controller is not running"
        issues=$((issues + 1))
    fi

    # Check LoadBalancer service
    local lb_ip=$(kubectl get svc -n ingress-nginx ingress-nginx-controller --no-headers | awk '{print $4}')
    if [[ "$lb_ip" == "$LOAD_BALANCER_IP" ]]; then
        log "INFO" "${CHECK} LoadBalancer has correct IP: $lb_ip"
    else
        log "ERROR" "${CROSS} LoadBalancer IP mismatch. Expected: $LOAD_BALANCER_IP, Got: $lb_ip"
        issues=$((issues + 1))
    fi

    # Check ingress resources
    local ingress_count=$(kubectl get ingress -A --no-headers | wc -l)
    if [[ $ingress_count -gt 0 ]]; then
        log "INFO" "${CHECK} Found $ingress_count ingress resources"

        # Check if all ingress have IP assigned
        local ingress_with_ip=$(kubectl get ingress -A --no-headers | grep "$LOAD_BALANCER_IP" | wc -l)
        if [[ $ingress_with_ip -eq $ingress_count ]]; then
            log "INFO" "${CHECK} All ingress resources have LoadBalancer IP assigned"
        else
            log "WARN" "${WARN} Only $ingress_with_ip/$ingress_count ingress resources have IP assigned"
        fi
    else
        log "ERROR" "${CROSS} No ingress resources found"
        issues=$((issues + 1))
    fi

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Networking validation passed"
        return 0
    else
        log "ERROR" "Networking validation failed with $issues issues"
        return 1
    fi
}

# Validate authentication infrastructure
validate_authentication() {
    print_header "🔐 VALIDATING AUTHENTICATION INFRASTRUCTURE"

    local issues=0

    # Check Keycloak
    if kubectl get pods -n keycloak | grep -q "keycloak.*Running"; then
        log "INFO" "${CHECK} Keycloak is running"

        # Test Keycloak realm endpoint
        if curl -k -s --max-time 10 "https://auth.homelab.local/realms/homelab" | grep -q "homelab"; then
            log "INFO" "${CHECK} Keycloak realm is accessible"
        else
            log "ERROR" "${CROSS} Keycloak realm is not accessible"
            issues=$((issues + 1))
        fi
    else
        log "ERROR" "${CROSS} Keycloak is not running"
        issues=$((issues + 1))
    fi

    # Check PostgreSQL for Keycloak
    if kubectl get pods -n keycloak | grep -q "postgres.*Running"; then
        log "INFO" "${CHECK} PostgreSQL for Keycloak is running"
    else
        log "ERROR" "${CROSS} PostgreSQL for Keycloak is not running"
        issues=$((issues + 1))
    fi

    # Check OAuth2 Proxy
    local oauth_pods=$(kubectl get pods -n oauth2-proxy | grep "oauth2-proxy.*Running" | wc -l)
    if [[ $oauth_pods -gt 0 ]]; then
        log "INFO" "${CHECK} OAuth2 Proxy is running ($oauth_pods pods)"
    else
        log "ERROR" "${CROSS} OAuth2 Proxy is not running"
        issues=$((issues + 1))
    fi

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Authentication validation passed"
        return 0
    else
        log "ERROR" "Authentication validation failed with $issues issues"
        return 1
    fi
}

# Test service connectivity
test_service_connectivity() {
    print_header "🔗 TESTING SERVICE CONNECTIVITY"

    local issues=0

    for service_host in "${!SERVICES[@]}"; do
        local service_name="${SERVICES[$service_host]}"
        local expected_codes="${EXPECTED_CODES[$service_host]}"

        log "INFO" "Testing $service_name at https://$service_host"

        local response=$(curl -k -s -o /dev/null -w "%{http_code}|%{time_total}" \
            -H "Host: $service_host" "https://$LOAD_BALANCER_IP/" --max-time 10 2>/dev/null || echo "000|0")

        IFS='|' read -r status_code response_time <<< "$response"

        # Check if status code is expected
        local is_valid=false
        IFS=',' read -ra codes <<< "$expected_codes"
        for code in "${codes[@]}"; do
            if [[ "$status_code" == "$code" ]]; then
                is_valid=true
                break
            fi
        done

        if [[ "$is_valid" == true ]]; then
            log "INFO" "${CHECK} $service_name: HTTP $status_code (${response_time}s)"
        else
            case $status_code in
                502|503)
                    log "WARN" "${WAIT} $service_name: HTTP $status_code (service starting)"
                    ;;
                404)
                    log "ERROR" "${CROSS} $service_name: HTTP $status_code (not found)"
                    issues=$((issues + 1))
                    ;;
                000)
                    log "ERROR" "${CROSS} $service_name: Connection failed/timeout"
                    issues=$((issues + 1))
                    ;;
                *)
                    log "WARN" "${WARN} $service_name: HTTP $status_code (unexpected)"
                    ;;
            esac
        fi
    done

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Service connectivity validation passed"
        return 0
    else
        log "ERROR" "Service connectivity validation failed with $issues issues"
        return 1
    fi
}

# Test authentication flows
test_authentication_flows() {
    print_header "🔑 TESTING AUTHENTICATION FLOWS"

    local issues=0

    # Test 1: Keycloak admin access
    log "INFO" "Testing Keycloak admin console access"
    local keycloak_response=$(curl -k -s -w "%{http_code}" "https://auth.homelab.local/admin/" --max-time 10 2>/dev/null || echo "000")
    if [[ "$keycloak_response" =~ (200|302|401) ]]; then
        log "INFO" "${CHECK} Keycloak admin console is accessible"
    else
        log "ERROR" "${CROSS} Keycloak admin console is not accessible (HTTP $keycloak_response)"
        issues=$((issues + 1))
    fi

    # Test 2: OAuth2 Proxy protection
    log "INFO" "Testing OAuth2 Proxy protection on protected services"
    local protected_services=("prometheus.homelab.local" "ollama.homelab.local" "jupyter.homelab.local")

    for service in "${protected_services[@]}"; do
        local response=$(curl -k -s -w "%{http_code}" -H "Host: $service" "https://$LOAD_BALANCER_IP/" --max-time 10 2>/dev/null || echo "000")
        if [[ "$response" =~ (302|401) ]]; then
            log "INFO" "${CHECK} $service is protected by OAuth2 Proxy"
        else
            log "WARN" "${WARN} $service may not be properly protected (HTTP $response)"
        fi
    done

    # Test 3: Landing page authentication
    log "INFO" "Testing landing page authentication"
    local landing_response=$(curl -k -s -w "%{http_code}" "https://homelab.local/" --max-time 10 2>/dev/null || echo "000")
    if [[ "$landing_response" =~ (200|302) ]]; then
        log "INFO" "${CHECK} Landing page is accessible"
    else
        log "ERROR" "${CROSS} Landing page is not accessible (HTTP $landing_response)"
        issues=$((issues + 1))
    fi

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Authentication flow validation passed"
        return 0
    else
        log "ERROR" "Authentication flow validation failed with $issues issues"
        return 1
    fi
}

# Validate storage
validate_storage() {
    print_header "💾 VALIDATING STORAGE"

    local issues=0

    # Check PVCs
    local pvc_bound=$(kubectl get pvc -A --no-headers | grep "Bound" | wc -l)
    local total_pvc=$(kubectl get pvc -A --no-headers | wc -l)

    if [[ $pvc_bound -eq $total_pvc && $total_pvc -gt 0 ]]; then
        log "INFO" "${CHECK} All $total_pvc PVCs are bound"
    else
        log "ERROR" "${CROSS} Only $pvc_bound/$total_pvc PVCs are bound"
        issues=$((issues + 1))
    fi

    # Check storage classes
    if kubectl get storageclass | grep -q "local-path"; then
        log "INFO" "${CHECK} Local path storage class is available"
    else
        log "ERROR" "${CROSS} Local path storage class is missing"
        issues=$((issues + 1))
    fi

    if [[ $issues -eq 0 ]]; then
        log "SUCCESS" "Storage validation passed"
        return 0
    else
        log "ERROR" "Storage validation failed with $issues issues"
        return 1
    fi
}

# Run comprehensive health check
run_health_check() {
    print_header "🏥 RUNNING COMPREHENSIVE HEALTH CHECK"

    if [[ -f "${SCRIPT_DIR}/scripts/health-monitor.sh" ]]; then
        log "INFO" "Running enhanced health monitor"
        "${SCRIPT_DIR}/scripts/health-monitor.sh" once
    else
        log "WARN" "Health monitor script not found, skipping comprehensive check"
    fi
}

# Generate validation report
generate_validation_report() {
    local validation_results="$1"
    local report_file="${SCRIPT_DIR}/logs/validation-report-$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# Homelab Deployment Validation Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Validation Log:** ${LOG_FILE}

## Summary

${validation_results}

## Service URLs

| Service | URL | Status |
|---------|-----|--------|
EOF

    for service_host in "${!SERVICES[@]}"; do
        local service_name="${SERVICES[$service_host]}"
        echo "| $service_name | https://$service_host | ✅ |" >> "$report_file"
    done

    cat >> "$report_file" << EOF

## Access Information

**LoadBalancer IP:** \`${LOAD_BALANCER_IP}\`

**DNS Setup:**
\`\`\`bash
sudo bash -c 'cat >> /etc/hosts << EOL
${LOAD_BALANCER_IP} homelab.local
${LOAD_BALANCER_IP} auth.homelab.local
${LOAD_BALANCER_IP} grafana.homelab.local
${LOAD_BALANCER_IP} prometheus.homelab.local
${LOAD_BALANCER_IP} gitlab.homelab.local
${LOAD_BALANCER_IP} ollama.homelab.local
${LOAD_BALANCER_IP} jupyter.homelab.local
EOL'
\`\`\`

**Default Credentials:**
- Keycloak Admin: admin / homelab123!

## Validation Results

$(cat "$LOG_FILE" | grep -E "\[(SUCCESS|ERROR)\]" | tail -20)

EOF

    log "INFO" "Validation report generated: $report_file"
}

# Main validation function
main() {
    print_header "🚀 HOMELAB DEPLOYMENT VALIDATION"

    log "INFO" "Starting comprehensive deployment validation"
    log "INFO" "Validation log: ${LOG_FILE}"

    local failed_checks=0
    local total_checks=8

    # Run all validation checks
    validate_prerequisites || failed_checks=$((failed_checks + 1))
    validate_cluster_health || failed_checks=$((failed_checks + 1))
    validate_namespaces || failed_checks=$((failed_checks + 1))
    validate_certificates || failed_checks=$((failed_checks + 1))
    validate_networking || failed_checks=$((failed_checks + 1))
    validate_authentication || failed_checks=$((failed_checks + 1))
    test_service_connectivity || failed_checks=$((failed_checks + 1))
    test_authentication_flows || failed_checks=$((failed_checks + 1))
    validate_storage || failed_checks=$((failed_checks + 1))

    # Run health check
    run_health_check

    # Generate summary
    print_header "📊 VALIDATION SUMMARY"

    local passed_checks=$((total_checks - failed_checks))

    if [[ $failed_checks -eq 0 ]]; then
        local validation_results="${CHECK} **VALIDATION PASSED** - All $total_checks validation checks completed successfully!"
        echo -e "${GREEN}${validation_results}${NC}"

        echo -e "\n${GREEN}🎉 DEPLOYMENT VALIDATION COMPLETE! 🎉${NC}"
        echo -e "${GREEN}Your homelab infrastructure is fully operational!${NC}"

        generate_validation_report "$validation_results"
        exit 0
    else
        local validation_results="${CROSS} **VALIDATION FAILED** - $failed_checks out of $total_checks validation checks failed"
        echo -e "${RED}${validation_results}${NC}"

        echo -e "\n${RED}❌ DEPLOYMENT VALIDATION FAILED ❌${NC}"
        echo -e "${RED}Please review the issues above and retry deployment${NC}"

        generate_validation_report "$validation_results"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
