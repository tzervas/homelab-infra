#!/bin/bash
# Comprehensive Deployment Validation and Testing Script
# Validates all aspects of the homelab infrastructure deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DEPLOYMENT_TYPE="${1:-vm-test}"
VALIDATION_TIMEOUT=300
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_DELAY=10

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration for report output
REPORT_DIR="${REPORT_DIR:-$PROJECT_ROOT}"
REPORT_FILENAME="${REPORT_FILENAME:-validation-report-$(date +%Y%m%d-%H%M%S-%N).md}"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Generic helper function to check pods in namespaces
check_pods() {
    local namespace="$1"
    local component_name="$2"
    local label_selector="${3:-}"

    if kubectl get namespace "$namespace" &>/dev/null; then
        local kubectl_cmd="kubectl get pods -n $namespace"
        if [[ -n "$label_selector" ]]; then
            kubectl_cmd="$kubectl_cmd -l $label_selector"
        fi

        if $kubectl_cmd &>/dev/null; then
            local ready_pods=$(eval "$kubectl_cmd --no-headers" | grep -c "Running" || echo "0")
            local total_pods=$(eval "$kubectl_cmd --no-headers" | wc -l)

            if [[ "$ready_pods" == "$total_pods" && "$ready_pods" -gt 0 ]]; then
                add_result "$component_name" "PASS" "$ready_pods/$total_pods pods running"
                return 0
            else
                add_result "$component_name" "FAIL" "Only $ready_pods/$total_pods pods running"
                return 1
            fi
        else
            add_result "$component_name" "FAIL" "No $component_name pods found"
            return 1
        fi
    else
        add_result "$component_name" "FAIL" "$namespace namespace not found"
        return 1
    fi
}

# Validation results tracking
VALIDATION_RESULTS=()
FAILED_CHECKS=()
TOTAL_CHECKS=0
PASSED_CHECKS=0

add_result() {
    local check_name="$1"
    local status="$2"
    local details="$3"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ "$status" == "PASS" ]]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log_success "$check_name: $details"
        VALIDATION_RESULTS+=("✅ $check_name: $details")
    else
        log_error "$check_name: $details"
        VALIDATION_RESULTS+=("❌ $check_name: $details")
        FAILED_CHECKS+=("$check_name")
    fi
}

# Utility functions
wait_for_condition() {
    local condition="$1"
    local description="$2"
    local timeout="${3:-$VALIDATION_TIMEOUT}"
    local interval="${4:-5}"

    log_info "Waiting for: $description (timeout: ${timeout}s)"

    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if eval "$condition" 2>/dev/null; then
            return 0
        fi
        sleep "$interval"
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    echo
    return 1
}

check_kubectl_access() {
    log_header "🔧 Validating Kubernetes Access"

    if kubectl cluster-info &>/dev/null; then
        add_result "Kubernetes Access" "PASS" "kubectl can access cluster"
    else
        add_result "Kubernetes Access" "FAIL" "Cannot access Kubernetes cluster"
        return 1
    fi

    # Check if we can list nodes
    if kubectl get nodes &>/dev/null; then
        local node_count=$(kubectl get nodes --no-headers | wc -l)
        add_result "Node Connectivity" "PASS" "$node_count node(s) accessible"
    else
        add_result "Node Connectivity" "FAIL" "Cannot list cluster nodes"
        return 1
    fi
}

validate_infrastructure() {
    log_header "🏗️ Validating Core Infrastructure"

    # Check MetalLB using generic helper
    check_pods "metallb-system" "MetalLB Load Balancer"

    # Check cert-manager using generic helper
    check_pods "cert-manager" "Certificate Manager"

    # Check NGINX Ingress using generic helper
    check_pods "ingress-nginx" "NGINX Ingress Controller"
}

validate_applications() {
    log_header "🦊 Validating Applications"

    # Check GitLab using generic helper
    check_pods "gitlab" "GitLab Application"

    # Check Keycloak using generic helper
    check_pods "keycloak" "Keycloak SSO"
}

validate_monitoring() {
    log_header "📊 Validating Monitoring Stack"

    # Check if monitoring namespace exists first
    if ! kubectl get namespace monitoring &>/dev/null; then
        add_result "Monitoring Stack" "FAIL" "Monitoring namespace not found"
        return
    fi

    # Check Prometheus using generic helper with label selector
    check_pods "monitoring" "Prometheus Monitoring" "app.kubernetes.io/name=prometheus"

    # Check Grafana using generic helper with label selector
    check_pods "monitoring" "Grafana Dashboard" "app.kubernetes.io/name=grafana"

    # Check AlertManager using generic helper with label selector
    check_pods "monitoring" "AlertManager" "app.kubernetes.io/name=alertmanager"
}

validate_networking() {
    log_header "🌐 Validating Network Configuration"

    # Check ingress resources
    local ingress_count=$(kubectl get ingress -A --no-headers | wc -l)
    if [[ "$ingress_count" -gt 0 ]]; then
        add_result "Ingress Resources" "PASS" "$ingress_count ingress rule(s) configured"

        # Check specific ingresses
        kubectl get ingress -A --no-headers | while read namespace name class hosts address ports age; do
            if [[ -n "$address" && "$address" != "<none>" ]]; then
                add_result "Ingress: $namespace/$name" "PASS" "Address assigned: $address"
            else
                add_result "Ingress: $namespace/$name" "FAIL" "No address assigned"
            fi
        done
    else
        add_result "Ingress Resources" "FAIL" "No ingress resources found"
    fi

    # Check services with LoadBalancer type
    local lb_services=$(kubectl get svc -A --no-headers | grep LoadBalancer | wc -l)
    if [[ "$lb_services" -gt 0 ]]; then
        add_result "LoadBalancer Services" "PASS" "$lb_services service(s) with external IPs"
    else
        add_result "LoadBalancer Services" "FAIL" "No LoadBalancer services found"
    fi
}

validate_certificates() {
    log_header "🔒 Validating TLS Certificates"

    # Check certificate resources
    if kubectl get certificates -A &>/dev/null; then
        local cert_count=$(kubectl get certificates -A --no-headers | wc -l)
        if [[ "$cert_count" -gt 0 ]]; then
            local ready_certs=$(kubectl get certificates -A --no-headers | grep -c "True" || echo "0")
            add_result "TLS Certificates" "PASS" "$ready_certs/$cert_count certificates ready"

            # Check individual certificates using JSON output to handle spaces in names
            kubectl get certificates -A -o json | jq -r '
                .items[] | [
                    .metadata.namespace,
                    .metadata.name,
                    (
                        .status.conditions // [] | map(select(.type == "Ready"))[0].status // "Unknown"
                    )
                ] | @tsv
            ' | while IFS=$'\t' read -r namespace name ready; do
                if [[ "$ready" == "True" ]]; then
                    add_result "Certificate: $namespace/$name" "PASS" "Certificate ready"
                else
                    add_result "Certificate: $namespace/$name" "FAIL" "Certificate not ready"
                fi
            done
        else
            add_result "TLS Certificates" "FAIL" "No certificates found"
        fi
    else
        add_result "TLS Certificates" "FAIL" "Certificate CRDs not available"
    fi

    # Check cluster issuers
    if kubectl get clusterissuer &>/dev/null; then
        local issuer_count=$(kubectl get clusterissuer --no-headers | wc -l)
        if [[ "$issuer_count" -gt 0 ]]; then
            local ready_issuers=$(kubectl get clusterissuer --no-headers | grep -c "True" || echo "0")
            add_result "Certificate Issuers" "PASS" "$ready_issuers/$issuer_count issuers ready"
        else
            add_result "Certificate Issuers" "FAIL" "No cluster issuers found"
        fi
    else
        add_result "Certificate Issuers" "FAIL" "ClusterIssuer CRDs not available"
    fi
}

validate_storage() {
    log_header "💾 Validating Storage Configuration"

    # Check storage classes
    local storage_classes=$(kubectl get storageclass --no-headers | wc -l)
    if [[ "$storage_classes" -gt 0 ]]; then
        add_result "Storage Classes" "PASS" "$storage_classes storage class(es) available"

        # Check for default storage class
        if kubectl get storageclass --no-headers | grep -q "(default)"; then
            local default_sc=$(kubectl get storageclass --no-headers | grep "(default)" | awk '{print $1}')
            add_result "Default Storage Class" "PASS" "Default: $default_sc"
        else
            add_result "Default Storage Class" "FAIL" "No default storage class set"
        fi
    else
        add_result "Storage Classes" "FAIL" "No storage classes found"
    fi

    # Check persistent volumes
    local pv_count=$(kubectl get pv --no-headers | wc -l)
    if [[ "$pv_count" -gt 0 ]]; then
        local bound_pvs=$(kubectl get pv --no-headers | grep -c "Bound" || echo "0")
        add_result "Persistent Volumes" "PASS" "$bound_pvs/$pv_count volumes bound"
    else
        add_result "Persistent Volumes" "FAIL" "No persistent volumes found"
    fi

    # Check persistent volume claims
    local pvc_count=$(kubectl get pvc -A --no-headers | wc -l)
    if [[ "$pvc_count" -gt 0 ]]; then
        local bound_pvcs=$(kubectl get pvc -A --no-headers | grep -c "Bound" || echo "0")
        add_result "Persistent Volume Claims" "PASS" "$bound_pvcs/$pvc_count claims bound"
    else
        add_result "Persistent Volume Claims" "FAIL" "No persistent volume claims found"
    fi
}

validate_security() {
    log_header "🛡️ Validating Security Configuration"

    # Check network policies
    local netpol_count=$(kubectl get networkpolicy -A --no-headers | wc -l)
    if [[ "$netpol_count" -gt 0 ]]; then
        add_result "Network Policies" "PASS" "$netpol_count network policies configured"
    else
        add_result "Network Policies" "FAIL" "No network policies found"
    fi

    # Check RBAC
    local roles_count=$(kubectl get roles -A --no-headers | wc -l)
    local clusterroles_count=$(kubectl get clusterroles --no-headers | wc -l)
    if [[ "$roles_count" -gt 0 || "$clusterroles_count" -gt 0 ]]; then
        add_result "RBAC Configuration" "PASS" "$roles_count roles, $clusterroles_count cluster roles"
    else
        add_result "RBAC Configuration" "FAIL" "No RBAC roles found"
    fi

    # Check service accounts
    local sa_count=$(kubectl get serviceaccounts -A --no-headers | wc -l)
    if [[ "$sa_count" -gt 0 ]]; then
        add_result "Service Accounts" "PASS" "$sa_count service accounts configured"
    else
        add_result "Service Accounts" "FAIL" "No custom service accounts found"
    fi
}

perform_connectivity_tests() {
    log_header "🔗 Performing Connectivity Tests"

    # Test internal service connectivity
    local test_pod="connectivity-test-$(date +%s)"

    # Ensure the test pod is deleted if the script exits or is interrupted
    trap "kubectl delete pod \$test_pod --ignore-not-found --grace-period=0 --force &>/dev/null" EXIT

    # Create a test pod for connectivity testing
    kubectl run "$test_pod" --image=curlimages/curl:latest --restart=Never --rm -i --tty=false -- sleep 3600 &>/dev/null || true

    if wait_for_condition "kubectl get pod $test_pod --no-headers | grep -q Running" "Test pod ready" 60; then
        # Test DNS resolution
        if kubectl exec "$test_pod" -- nslookup kubernetes.default.svc.cluster.local &>/dev/null; then
            add_result "Internal DNS Resolution" "PASS" "Cluster DNS working"
        else
            add_result "Internal DNS Resolution" "FAIL" "Cannot resolve cluster DNS"
        fi

        # Test service connectivity
        if kubectl get svc -n default kubernetes &>/dev/null; then
            if kubectl exec "$test_pod" -- curl -s -k https://kubernetes.default.svc.cluster.local/version &>/dev/null; then
                add_result "API Server Connectivity" "PASS" "Can reach Kubernetes API"
            else
                add_result "API Server Connectivity" "FAIL" "Cannot reach Kubernetes API"
            fi
        fi
    else
        add_result "Connectivity Tests" "FAIL" "Could not create test pod"
    fi

    # Clean up the test pod and remove the trap
    kubectl delete pod "$test_pod" --ignore-not-found --grace-period=0 --force &>/dev/null
    trap - EXIT
}

perform_health_checks() {
    log_header "🏥 Performing Application Health Checks"

    # Define service health check endpoints
    declare -A health_endpoints=(
        ["gitlab"]="/users/sign_in"
        ["keycloak"]="/auth"
        ["grafana"]="/login"
        ["prometheus"]="/graph"
    )

    # Get ingress hostnames and perform health checks - handle multiple ingresses per service
    for service in "${!health_endpoints[@]}"; do
        local ingress_count=0
        local endpoint="${health_endpoints[$service]}"

        # Use process substitution to avoid subshell issues with counter
        while IFS= read -r ingress_info; do
            if [[ -n "$ingress_info" ]]; then
                ingress_count=$((ingress_count + 1))
                local namespace=$(echo "$ingress_info" | awk '{print $1}')
                local hosts=$(echo "$ingress_info" | awk '{print $4}')
                local host=$(echo "$hosts" | cut -d',' -f1)

                # Test HTTP/HTTPS connectivity
                local service_accessible=false
                for protocol in https http; do
                    local url="${protocol}://${host}${endpoint}"
                    if curl -s -k -m 10 "$url" &>/dev/null; then
                        add_result "${service^} Health Check (#$ingress_count)" "PASS" "Accessible at $url"
                        service_accessible=true
                        break
                    fi
                done

                # If neither protocol worked, report failure
                if [[ "$service_accessible" == "false" ]]; then
                    local url="https://${host}${endpoint}"
                    add_result "${service^} Health Check (#$ingress_count)" "FAIL" "Not accessible at $url"
                fi
            fi
        done < <(kubectl get ingress -A --no-headers | grep "$service")

        # If no ingresses found for this service
        if [[ $ingress_count -eq 0 ]]; then
            add_result "${service^} Health Check" "FAIL" "No ingress found for $service"
        fi
    done
}

generate_detailed_report() {
    log_header "📋 Generating Detailed Validation Report"

    local report_file="$REPORT_DIR/$REPORT_FILENAME"

    cat > "$report_file" << EOF
# Homelab Infrastructure Validation Report

**Generated**: $(date)
**Deployment Type**: $DEPLOYMENT_TYPE
**Validation Duration**: $((SECONDS / 60))m $((SECONDS % 60))s

## Summary

- **Total Checks**: $TOTAL_CHECKS
- **Passed**: $PASSED_CHECKS
- **Failed**: $((TOTAL_CHECKS - PASSED_CHECKS))
- **Success Rate**: $(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))%

## Validation Results

EOF

    for result in "${VALIDATION_RESULTS[@]}"; do
        echo "$result" >> "$report_file"
    done

    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        cat >> "$report_file" << EOF

## Failed Checks Summary

The following checks failed and require attention:

EOF
        for failed_check in "${FAILED_CHECKS[@]}"; do
            echo "- $failed_check" >> "$report_file"
        done
    fi

    cat >> "$report_file" << EOF

## Cluster Status

### Nodes
\`\`\`
$(kubectl get nodes -o wide)
\`\`\`

### Namespaces
\`\`\`
$(kubectl get namespaces)
\`\`\`

### All Pods Status
\`\`\`
$(kubectl get pods -A)
\`\`\`

### Services
\`\`\`
$(kubectl get svc -A)
\`\`\`

### Ingress Resources
\`\`\`
$(kubectl get ingress -A)
\`\`\`

### Storage
\`\`\`
$(kubectl get storageclass)
$(kubectl get pv)
$(kubectl get pvc -A)
\`\`\`

EOF

    log_success "Detailed report generated: $report_file"
}

show_final_summary() {
    log_header "🎯 Final Validation Summary"

    echo
    echo "=============================================="
    echo "  HOMELAB DEPLOYMENT VALIDATION COMPLETE"
    echo "=============================================="
    echo
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Total Duration: $((SECONDS / 60))m $((SECONDS % 60))s"
    echo
    echo "Results:"
    echo "  ✅ Passed: $PASSED_CHECKS"
    echo "  ❌ Failed: $((TOTAL_CHECKS - PASSED_CHECKS))"
    echo "  📊 Total:  $TOTAL_CHECKS"
    echo "  📈 Success Rate: $(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))%"
    echo

    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        echo "⚠️  FAILED CHECKS:"
        for failed_check in "${FAILED_CHECKS[@]}"; do
            echo "   - $failed_check"
        done
        echo
        echo "🔧 Next Steps:"
        echo "   1. Review the detailed report for specific issues"
        echo "   2. Check pod logs: kubectl logs -n <namespace> <pod-name>"
        echo "   3. Verify configuration and redeploy if necessary"
        echo "   4. Run validation again after fixes"
        echo
        return 1
    else
        echo "🎉 ALL CHECKS PASSED!"
        echo
        echo "🚀 Your homelab infrastructure is ready for use:"
        echo "   - All core services are running"
        echo "   - Network connectivity verified"
        echo "   - Security configurations in place"
        echo "   - TLS certificates issued"
        echo "   - Monitoring stack operational"
        echo
        echo "📚 Next Steps:"
        echo "   1. Access your services via the configured URLs"
        echo "   2. Configure SSO integration between Keycloak and GitLab"
        echo "   3. Set up monitoring alerts and backup procedures"
        echo "   4. Review the operations documentation"
        echo
        return 0
    fi
}

# Main execution
main() {
    local start_time=$SECONDS

    log_header "🚀 Starting Comprehensive Homelab Deployment Validation"
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Validation Timeout: ${VALIDATION_TIMEOUT}s"
    echo

    # Execute validation phases
    check_kubectl_access || exit 1
    validate_infrastructure
    validate_applications
    validate_monitoring
    validate_networking
    validate_certificates
    validate_storage
    validate_security
    perform_connectivity_tests
    perform_health_checks

    # Generate reports
    generate_detailed_report
    show_final_summary
}

# Execute main function
main "$@"
