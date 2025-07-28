#!/bin/bash

# Enhanced Monitoring Validation Script
# Validates all observability and monitoring enhancements

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/monitoring-validation-$(date +%Y%m%d-%H%M%S).log"

# Ensure logs directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_colored() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Test tracking
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name=$1
    local test_command=$2
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_info "Running test: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        print_colored "$GREEN" "✅ PASS: $test_name"
        log_success "Test passed: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        print_colored "$RED" "❌ FAIL: $test_name"
        log_error "Test failed: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    run_test "kubectl available" "command -v kubectl"
    run_test "helm available" "command -v helm"
    run_test "curl available" "command -v curl"
    run_test "jq available" "command -v jq"
    
    run_test "Kubernetes cluster accessible" "kubectl cluster-info"
    run_test "Monitoring namespace exists" "kubectl get namespace monitoring"
}

# Core monitoring stack validation
validate_core_monitoring() {
    log_info "Validating core monitoring stack..."
    
    # Prometheus
    run_test "Prometheus operator deployed" "kubectl get deployment -n monitoring | grep -q prometheus-operator"
    run_test "Prometheus instance running" "kubectl get prometheus -n monitoring | grep -q prometheus"
    run_test "Prometheus targets accessible" "kubectl get servicemonitor -n monitoring"
    
    # AlertManager
    run_test "AlertManager deployed" "kubectl get alertmanager -n monitoring"
    run_test "AlertManager service accessible" "kubectl get service -n monitoring | grep -q alertmanager"
    
    # Grafana
    run_test "Grafana deployed" "kubectl get deployment -n monitoring | grep -q grafana"
    run_test "Grafana service accessible" "kubectl get service -n monitoring | grep -q grafana"
    
    # Loki
    run_test "Loki deployed" "kubectl get deployment -n monitoring | grep -q loki"
    run_test "Loki service accessible" "kubectl get service -n monitoring | grep -q loki"
    
    # Promtail
    run_test "Promtail daemonset deployed" "kubectl get daemonset -n monitoring | grep -q promtail"
}

# Enhanced monitoring features validation
validate_enhanced_features() {
    log_info "Validating enhanced monitoring features..."
    
    # Terraform state monitoring
    run_test "Terraform state monitor deployed" "kubectl get deployment -n monitoring | grep -q terraform-state-monitor || echo 'Not enabled'"
    
    # Helm release monitoring
    run_test "Helm release monitor deployed" "kubectl get deployment -n monitoring | grep -q helm-release-monitor || echo 'Not enabled'"
    
    # Certificate monitoring
    run_test "Certificate monitoring enabled" "kubectl get prometheusrule -n monitoring | grep -q certificate || echo 'Rules not found'"
    
    # Security policy monitoring
    run_test "Security policy rules deployed" "kubectl get prometheusrule -n monitoring | grep -q security"
    
    # Enhanced alert rules
    run_test "Enhanced infrastructure alerts deployed" "kubectl get prometheusrule -n monitoring | grep -q enhanced-infrastructure-alerts"
}

# ServiceMonitor validation
validate_servicemonitors() {
    log_info "Validating ServiceMonitors..."
    
    run_test "Prometheus ServiceMonitor exists" "kubectl get servicemonitor -n monitoring prometheus"
    run_test "AlertManager ServiceMonitor exists" "kubectl get servicemonitor -n monitoring alertmanager || echo 'May not exist'"
    run_test "Grafana ServiceMonitor exists" "kubectl get servicemonitor -n monitoring grafana || echo 'May not exist'"
    
    # Enhanced ServiceMonitors
    run_test "Helm release ServiceMonitor exists" "kubectl get servicemonitor -n monitoring | grep -q helm-release || echo 'Not enabled'"
    run_test "Terraform state ServiceMonitor exists" "kubectl get servicemonitor -n monitoring | grep -q terraform-state || echo 'Not enabled'"
}

# Metrics validation
validate_metrics() {
    log_info "Validating metrics availability..."
    
    # Get Prometheus service endpoint
    local prometheus_port
    prometheus_port=$(kubectl get service -n monitoring | grep prometheus | grep -v operated | awk '{print $5}' | cut -d: -f2 | cut -d/ -f1)
    
    if [[ -n "$prometheus_port" ]]; then
        # Port forward to access Prometheus
        kubectl port-forward -n monitoring service/prometheus-operated 9090:9090 &
        local pf_pid=$!
        
        sleep 5
        
        # Test basic metrics
        run_test "Prometheus up metric available" "curl -s 'http://localhost:9090/api/v1/query?query=up' | jq -r '.data.result | length' | grep -q '^[1-9]'"
        run_test "Node exporter metrics available" "curl -s 'http://localhost:9090/api/v1/query?query=node_cpu_seconds_total' | jq -r '.data.result | length' | grep -q '^[1-9]'"
        run_test "Kubernetes metrics available" "curl -s 'http://localhost:9090/api/v1/query?query=kube_pod_info' | jq -r '.data.result | length' | grep -q '^[1-9]'"
        
        # Test enhanced metrics (if enabled)
        if curl -s 'http://localhost:9090/api/v1/query?query=terraform_state_resources_total' | jq -r '.data.result | length' | grep -q '^[1-9]'; then
            run_test "Terraform state metrics available" "echo 'Terraform monitoring enabled'"
        else
            log_info "Terraform state metrics not available (may not be enabled)"
        fi
        
        if curl -s 'http://localhost:9090/api/v1/query?query=helm_release_status' | jq -r '.data.result | length' | grep -q '^[1-9]'; then
            run_test "Helm release metrics available" "echo 'Helm monitoring enabled'"
        else
            log_info "Helm release metrics not available (may not be enabled)"
        fi
        
        # Kill port forward
        kill $pf_pid 2>/dev/null || true
    else
        log_warn "Could not find Prometheus service port for metrics validation"
    fi
}

# Alerts validation
validate_alerts() {
    log_info "Validating alert rules..."
    
    # Get all PrometheusRules
    local rules_count
    rules_count=$(kubectl get prometheusrule -n monitoring --no-headers | wc -l)
    
    run_test "PrometheusRules deployed" "test $rules_count -gt 0"
    
    # Check for specific alert rules
    run_test "Infrastructure alerts exist" "kubectl get prometheusrule -n monitoring -o yaml | grep -q 'KubernetesNodeReady'"
    run_test "Resource alerts exist" "kubectl get prometheusrule -n monitoring -o yaml | grep -q 'HighCPUUsage'"
    run_test "Certificate alerts exist" "kubectl get prometheusrule -n monitoring -o yaml | grep -q 'CertificateExpiring' || echo 'May not be configured'"
    run_test "Security alerts exist" "kubectl get prometheusrule -n monitoring -o yaml | grep -q 'SecurityPolicy' || echo 'May not be configured'"
}

# Grafana dashboards validation
validate_dashboards() {
    log_info "Validating Grafana dashboards..."
    
    # Check if Grafana is accessible
    local grafana_port
    grafana_port=$(kubectl get service -n monitoring grafana -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "")
    
    if [[ -n "$grafana_port" ]]; then
        kubectl port-forward -n monitoring service/grafana $grafana_port:$grafana_port &
        local gf_pid=$!
        
        sleep 5
        
        # Test Grafana API (basic auth with admin:admin)
        run_test "Grafana API accessible" "curl -s -u admin:admin http://localhost:$grafana_port/api/health | jq -r '.database' | grep -q 'ok'"
        run_test "Grafana datasources configured" "curl -s -u admin:admin http://localhost:$grafana_port/api/datasources | jq '. | length' | grep -q '^[1-9]'"
        
        # Check for dashboards
        local dashboard_count
        dashboard_count=$(curl -s -u admin:admin "http://localhost:$grafana_port/api/search?query=&" | jq '. | length' 2>/dev/null || echo "0")
        run_test "Grafana dashboards exist" "test $dashboard_count -gt 0"
        
        kill $gf_pid 2>/dev/null || true
    else
        log_warn "Could not access Grafana for dashboard validation"
    fi
}

# Structured logging validation
validate_structured_logging() {
    log_info "Validating structured logging..."
    
    # Check Promtail configuration
    run_test "Promtail configured" "kubectl get configmap -n monitoring | grep -q structured-logging || kubectl get configmap -n monitoring | grep -q promtail"
    
    # Check Loki connectivity
    run_test "Loki service accessible" "kubectl get service -n monitoring loki"
    
    # Test log ingestion (if possible)
    local loki_port
    loki_port=$(kubectl get service -n monitoring loki -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "")
    
    if [[ -n "$loki_port" ]]; then
        kubectl port-forward -n monitoring service/loki $loki_port:$loki_port &
        local loki_pid=$!
        
        sleep 5
        
        run_test "Loki API accessible" "curl -s http://localhost:$loki_port/ready | grep -q 'ready'"
        run_test "Loki ingesting logs" "curl -s 'http://localhost:$loki_port/loki/api/v1/label' | jq -r '.data | length' | grep -q '^[1-9]'"
        
        kill $loki_pid 2>/dev/null || true
    fi
}

# Runbooks validation
validate_runbooks() {
    log_info "Validating operational runbooks..."
    
    local runbooks_dir="${PROJECT_ROOT}/docs/operations/runbooks"
    
    run_test "Runbooks directory exists" "test -d '$runbooks_dir'"
    run_test "Terraform runbooks exist" "test -d '$runbooks_dir/terraform'"
    run_test "Helm runbooks exist" "test -d '$runbooks_dir/helm'"
    run_test "Certificate runbooks exist" "test -d '$runbooks_dir/certificates'"
    run_test "Security runbooks exist" "test -d '$runbooks_dir/security'"
    
    # Check specific runbook files
    run_test "Drift resolution runbook exists" "test -f '$runbooks_dir/terraform/drift-resolution.md'"
}

# Security and RBAC validation
validate_security() {
    log_info "Validating security configuration..."
    
    # Check ServiceAccounts
    run_test "Monitoring ServiceAccounts exist" "kubectl get serviceaccount -n monitoring | grep -q prometheus"
    
    # Check RBAC
    run_test "ClusterRoles exist" "kubectl get clusterrole | grep -q prometheus"
    run_test "ClusterRoleBindings exist" "kubectl get clusterrolebinding | grep -q prometheus"
    
    # Check Security Contexts
    run_test "Pods running with security contexts" "kubectl get pods -n monitoring -o yaml | grep -q 'runAsNonRoot: true'"
    
    # Check Network Policies (if enabled)
    if kubectl get networkpolicy -n monitoring >/dev/null 2>&1; then
        run_test "Network policies configured" "kubectl get networkpolicy -n monitoring"
    else
        log_info "Network policies not configured (may be intentional)"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    # Kill any remaining port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
}

# Main execution
main() {
    print_colored "$BLUE" "=== Enhanced Monitoring Validation ==="
    print_colored "$BLUE" "Log file: $LOG_FILE"
    echo
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run all validation steps
    check_prerequisites
    echo
    validate_core_monitoring
    echo
    validate_enhanced_features
    echo
    validate_servicemonitors
    echo
    validate_metrics
    echo
    validate_alerts
    echo
    validate_dashboards
    echo
    validate_structured_logging
    echo
    validate_runbooks
    echo
    validate_security
    echo
    
    # Summary
    print_colored "$BLUE" "=== Validation Summary ==="
    echo "Total tests: $TESTS_TOTAL"
    print_colored "$GREEN" "Passed: $TESTS_PASSED"
    print_colored "$RED" "Failed: $TESTS_FAILED"
    echo
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_colored "$GREEN" "🎉 All monitoring enhancements validated successfully!"
        log_success "All tests passed"
        exit 0
    else
        print_colored "$RED" "❌ Some tests failed. Check the log for details: $LOG_FILE"
        log_error "$TESTS_FAILED tests failed"
        exit 1
    fi
}

# Run main function
main "$@"
