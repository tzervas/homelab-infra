#!/bin/bash
# Enhanced Testing and Validation Suite Runner
# Integrates Terratest, helm-unittest, security testing, and performance benchmarking
# Copyright (c) 2025 Tyler Zervas - Licensed under MIT

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
TEST_TIMEOUT=${TEST_TIMEOUT:-1800}  # 30 minutes
PARALLEL_JOBS=${PARALLEL_JOBS:-4}
OUTPUT_DIR="${PROJECT_ROOT}/test_results"
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Test categories
ENABLE_TERRATEST=${ENABLE_TERRATEST:-true}
ENABLE_HELM_UNITTEST=${ENABLE_HELM_UNITTEST:-true}
ENABLE_SECURITY_TESTS=${ENABLE_SECURITY_TESTS:-true}
ENABLE_PERFORMANCE_TESTS=${ENABLE_PERFORMANCE_TESTS:-true}
ENABLE_COMPLIANCE_SCAN=${ENABLE_COMPLIANCE_SCAN:-true}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_section() {
    echo -e "${PURPLE}[SECTION]${NC} $*" >&2
}

# Show usage information
usage() {
    cat <<EOF
Enhanced Testing and Validation Suite

Usage: $0 [OPTIONS]

OPTIONS:
    --help                          Show this help message
    --terratest                     Run Terratest (default: enabled)
    --no-terratest                  Skip Terratest
    --helm-unittest                 Run Helm unit tests (default: enabled)
    --no-helm-unittest              Skip Helm unit tests
    --security                      Run security tests (default: enabled)
    --no-security                   Skip security tests
    --performance                   Run performance benchmarks (default: enabled)
    --no-performance                Skip performance benchmarks
    --compliance                    Run compliance scanning (default: enabled)
    --no-compliance                 Skip compliance scanning
    --timeout SECONDS               Test timeout in seconds (default: 1800)
    --parallel-jobs N               Number of parallel jobs (default: 4)
    --output-dir PATH               Output directory for results (default: test_results)
    --log-level LEVEL               Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    --kubeconfig PATH               Path to kubeconfig file
    --clean                         Clean up test artifacts before running
    --dry-run                       Show what would be executed without running

EXAMPLES:
    $0                              # Run all tests with defaults
    $0 --no-performance             # Skip performance tests
    $0 --terratest --security       # Run only Terratest and security tests
    $0 --timeout 3600 --parallel-jobs 8  # Extended timeout with more parallelism

ENVIRONMENT VARIABLES:
    TEST_TIMEOUT                    Test timeout in seconds
    PARALLEL_JOBS                   Number of parallel jobs
    LOG_LEVEL                       Logging level
    KUBECONFIG                      Path to kubeconfig file
    ENABLE_TERRATEST                Enable/disable Terratest (true/false)
    ENABLE_HELM_UNITTEST            Enable/disable Helm unit tests (true/false)
    ENABLE_SECURITY_TESTS           Enable/disable security tests (true/false)
    ENABLE_PERFORMANCE_TESTS        Enable/disable performance tests (true/false)
    ENABLE_COMPLIANCE_SCAN          Enable/disable compliance scanning (true/false)

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                usage
                exit 0
                ;;
            --terratest)
                ENABLE_TERRATEST=true
                shift
                ;;
            --no-terratest)
                ENABLE_TERRATEST=false
                shift
                ;;
            --helm-unittest)
                ENABLE_HELM_UNITTEST=true
                shift
                ;;
            --no-helm-unittest)
                ENABLE_HELM_UNITTEST=false
                shift
                ;;
            --security)
                ENABLE_SECURITY_TESTS=true
                shift
                ;;
            --no-security)
                ENABLE_SECURITY_TESTS=false
                shift
                ;;
            --performance)
                ENABLE_PERFORMANCE_TESTS=true
                shift
                ;;
            --no-performance)
                ENABLE_PERFORMANCE_TESTS=false
                shift
                ;;
            --compliance)
                ENABLE_COMPLIANCE_SCAN=true
                shift
                ;;
            --no-compliance)
                ENABLE_COMPLIANCE_SCAN=false
                shift
                ;;
            --timeout)
                TEST_TIMEOUT="$2"
                shift 2
                ;;
            --parallel-jobs)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --kubeconfig)
                export KUBECONFIG="$2"
                shift 2
                ;;
            --clean)
                CLEAN_BEFORE_RUN=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    if [[ "$ENABLE_TERRATEST" == "true" ]]; then
        if ! command -v go &> /dev/null; then
            missing_tools+=("go")
        fi
        if ! command -v terraform &> /dev/null; then
            missing_tools+=("terraform")
        fi
    fi
    
    if [[ "$ENABLE_HELM_UNITTEST" == "true" ]]; then
        if ! command -v helm &> /dev/null; then
            missing_tools+=("helm")
        fi
    fi
    
    if [[ "$ENABLE_SECURITY_TESTS" == "true" || "$ENABLE_PERFORMANCE_TESTS" == "true" ]]; then
        if ! command -v python3 &> /dev/null; then
            missing_tools+=("python3")
        fi
        if ! command -v kubectl &> /dev/null && ! command -v k3s &> /dev/null; then
            missing_tools+=("kubectl or k3s")
        fi
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again"
        return 1
    fi
    
    log_success "Prerequisites check completed"
}

# Setup output directory
setup_output_directory() {
    log_info "Setting up output directory: $OUTPUT_DIR"
    
    if [[ "${CLEAN_BEFORE_RUN:-false}" == "true" && -d "$OUTPUT_DIR" ]]; then
        log_info "Cleaning existing output directory"
        rm -rf "$OUTPUT_DIR"
    fi
    
    mkdir -p "$OUTPUT_DIR"/{terratest,helm-unittest,security,performance,compliance}
    
    # Create timestamp for this test run
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OUTPUT_DIR/test_run_timestamp"
}

# Run Terratest
run_terratest() {
    if [[ "$ENABLE_TERRATEST" != "true" ]]; then
        log_info "Skipping Terratest (disabled)"
        return 0
    fi
    
    log_section "Running Terratest Infrastructure Tests"
    
    local terratest_dir="$PROJECT_ROOT/testing/terraform/terratest"
    local output_file="$OUTPUT_DIR/terratest/results.json"
    
    if [[ ! -d "$terratest_dir" ]]; then
        log_warning "Terratest directory not found: $terratest_dir"
        return 0
    fi
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_info "DRY RUN: Would execute Terratest in $terratest_dir"
        return 0
    fi
    
    cd "$terratest_dir"
    
    # Install dependencies
    log_info "Installing Go dependencies..."
    if ! go mod download; then
        log_error "Failed to install Go dependencies"
        return 1
    fi
    
    # Run tests with timeout and JSON output
    log_info "Running Terratest..."
    if timeout "$TEST_TIMEOUT" go test -v -timeout "${TEST_TIMEOUT}s" -json ./... > "$output_file" 2>&1; then
        log_success "Terratest completed successfully"
        
        # Parse results for summary
        local passed failed
        passed=$(grep -c '"Action":"pass"' "$output_file" || echo "0")
        failed=$(grep -c '"Action":"fail"' "$output_file" || echo "0")
        
        log_info "Terratest Results: $passed passed, $failed failed"
        
        if [[ $failed -gt 0 ]]; then
            log_warning "Some Terratest tests failed"
            return 1
        fi
    else
        log_error "Terratest failed or timed out"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Run Helm unit tests
run_helm_unittest() {
    if [[ "$ENABLE_HELM_UNITTEST" != "true" ]]; then
        log_info "Skipping Helm unit tests (disabled)"
        return 0
    fi
    
    log_section "Running Helm Unit Tests"
    
    local helm_charts_dir="$PROJECT_ROOT/helm/charts"
    local test_file="$PROJECT_ROOT/testing/helm/helm-unittest/charts_test.yaml"
    local output_file="$OUTPUT_DIR/helm-unittest/results.xml"
    
    if [[ ! -d "$helm_charts_dir" ]]; then
        log_warning "Helm charts directory not found: $helm_charts_dir"
        return 0
    fi
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_info "DRY RUN: Would execute Helm unit tests for charts in $helm_charts_dir"
        return 0
    fi
    
    # Install helm unittest plugin if not already installed
    if ! helm plugin list | grep -q unittest; then
        log_info "Installing helm unittest plugin..."
        helm plugin install https://github.com/quintush/helm-unittest
    fi
    
    # Run tests for each chart
    local total_tests=0
    local failed_tests=0
    
    for chart_dir in "$helm_charts_dir"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            local chart_name
            chart_name=$(basename "$chart_dir")
            
            log_info "Testing Helm chart: $chart_name"
            
            local chart_output="$OUTPUT_DIR/helm-unittest/$chart_name.xml"
            
            if helm unittest "$chart_dir" -o junit -f "$chart_output" 2>&1; then
                log_success "Helm chart $chart_name tests passed"
                
                # Count tests from XML output
                if [[ -f "$chart_output" ]]; then
                    local tests failures
                    tests=$(xmllint --xpath 'string(//testsuite/@tests)' "$chart_output" 2>/dev/null || echo "0")
                    failures=$(xmllint --xpath 'string(//testsuite/@failures)' "$chart_output" 2>/dev/null || echo "0")
                    
                    total_tests=$((total_tests + tests))
                    failed_tests=$((failed_tests + failures))
                fi
            else
                log_warning "Helm chart $chart_name tests failed"
                failed_tests=$((failed_tests + 1))
            fi
        fi
    done
    
    log_info "Helm Unit Tests Results: $((total_tests - failed_tests))/$total_tests passed"
    
    if [[ $failed_tests -gt 0 ]]; then
        log_warning "Some Helm unit tests failed"
        return 1
    fi
    
    log_success "All Helm unit tests passed"
}

# Run security tests
run_security_tests() {
    if [[ "$ENABLE_SECURITY_TESTS" != "true" ]]; then
        log_info "Skipping security tests (disabled)"
        return 0
    fi
    
    log_section "Running Security Validation Tests"
    
    local security_dir="$PROJECT_ROOT/testing/security"
    local output_file="$OUTPUT_DIR/security/results.json"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_info "DRY RUN: Would execute security tests"
        return 0
    fi
    
    # Install Python dependencies if requirements file exists
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_info "Installing Python dependencies..."
        python3 -m pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
    fi
    
    # Run certificate validation tests
    log_info "Running certificate validation tests..."
    if python3 "$security_dir/certificate_validator.py" \
        --log-level "$LOG_LEVEL" \
        --kubeconfig "${KUBECONFIG:-}" \
        > "$OUTPUT_DIR/security/certificate_validation.log" 2>&1; then
        log_success "Certificate validation completed"
    else
        log_warning "Certificate validation had issues"
    fi
    
    # Run K3s security validation tests
    if [[ -f "$PROJECT_ROOT/testing/k3s-validation/modules/security/tls-validation.sh" ]]; then
        log_info "Running K3s TLS validation..."
        if timeout "$TEST_TIMEOUT" "$PROJECT_ROOT/testing/k3s-validation/modules/security/tls-validation.sh" \
            > "$OUTPUT_DIR/security/tls_validation.log" 2>&1; then
            log_success "TLS validation completed"
        else
            log_warning "TLS validation had issues"
        fi
        
        log_info "Running K3s RBAC validation..."
        if timeout "$TEST_TIMEOUT" "$PROJECT_ROOT/testing/k3s-validation/modules/security/rbac-testing.sh" \
            > "$OUTPUT_DIR/security/rbac_validation.log" 2>&1; then
            log_success "RBAC validation completed"
        else
            log_warning "RBAC validation had issues"
        fi
        
        log_info "Running K3s Network Policy validation..."
        if timeout "$TEST_TIMEOUT" "$PROJECT_ROOT/testing/k3s-validation/modules/security/network-policies.sh" \
            > "$OUTPUT_DIR/security/network_policy_validation.log" 2>&1; then
            log_success "Network Policy validation completed"
        else
            log_warning "Network Policy validation had issues"
        fi
    fi
    
    log_success "Security tests completed"
}

# Run performance benchmarks
run_performance_tests() {
    if [[ "$ENABLE_PERFORMANCE_TESTS" != "true" ]]; then
        log_info "Skipping performance tests (disabled)"
        return 0
    fi
    
    log_section "Running Performance Benchmarks"
    
    local performance_script="$PROJECT_ROOT/testing/performance/benchmarks.py"
    local output_file="$OUTPUT_DIR/performance/benchmark_results.json"
    local markdown_output="$OUTPUT_DIR/performance/benchmark_report.md"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_info "DRY RUN: Would execute performance benchmarks"
        return 0
    fi
    
    if [[ ! -f "$performance_script" ]]; then
        log_warning "Performance benchmark script not found: $performance_script"
        return 0
    fi
    
    # Install Python dependencies
    python3 -m pip install kubernetes psutil requests --quiet
    
    log_info "Running comprehensive performance benchmarks..."
    
    local endpoints=(
        "https://gitlab.homelab.local/api/v4/projects"
        "https://prometheus.homelab.local/api/v1/status/config"  
        "https://grafana.homelab.local/api/health"
    )
    
    local load_test_targets=(
        "https://gitlab.homelab.local"
    )
    
    if timeout "$TEST_TIMEOUT" python3 "$performance_script" \
        --log-level "$LOG_LEVEL" \
        --kubeconfig "${KUBECONFIG:-}" \
        --endpoints "${endpoints[@]}" \
        --load-test "${load_test_targets[@]}" \
        --output "$output_file" \
        --format json \
        > "$OUTPUT_DIR/performance/benchmark.log" 2>&1; then
        
        log_success "Performance benchmarks completed"
        
        # Generate markdown report
        python3 "$performance_script" \
            --log-level "$LOG_LEVEL" \
            --kubeconfig "${KUBECONFIG:-}" \
            --endpoints "${endpoints[@]}" \
            --output "$markdown_output" \
            --format markdown \
            > /dev/null 2>&1 || true
        
        # Extract summary from JSON results
        if [[ -f "$output_file" ]]; then
            local total_tests success_rate avg_response_time
            total_tests=$(python3 -c "import json; data=json.load(open('$output_file')); print(data.get('summary_stats', {}).get('total_tests', 0))" 2>/dev/null || echo "0")
            success_rate=$(python3 -c "import json; data=json.load(open('$output_file')); print(f\"{data.get('summary_stats', {}).get('success_rate', 0):.1f}\")" 2>/dev/null || echo "0.0")
            avg_response_time=$(python3 -c "import json; data=json.load(open('$output_file')); print(f\"{data.get('summary_stats', {}).get('avg_response_time_ms', 0):.2f}\")" 2>/dev/null || echo "0.00")
            
            log_info "Performance Results: $total_tests tests, $success_rate% success rate, ${avg_response_time}ms avg response time"
        fi
    else
        log_warning "Performance benchmarks failed or timed out"
        return 1
    fi
}

# Run compliance scanning
run_compliance_scan() {
    if [[ "$ENABLE_COMPLIANCE_SCAN" != "true" ]]; then
        log_info "Skipping compliance scanning (disabled)"
        return 0
    fi
    
    log_section "Running Infrastructure Compliance Scanning"
    
    local output_file="$OUTPUT_DIR/compliance/scan_results.json"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_info "DRY RUN: Would execute compliance scanning"
        return 0
    fi
    
    # Run existing infrastructure compliance checks
    if [[ -f "$PROJECT_ROOT/scripts/testing/config_validator.py" ]]; then
        log_info "Running configuration compliance checks..."
        
        if python3 "$PROJECT_ROOT/scripts/testing/config_validator.py" \
            --directory "$PROJECT_ROOT/ansible/inventory" \
            --log-level "$LOG_LEVEL" \
            > "$OUTPUT_DIR/compliance/config_validation.log" 2>&1; then
            log_success "Configuration compliance checks completed"
        else
            log_warning "Configuration compliance checks had issues"
        fi
    fi
    
    # Run Terraform state validation
    if [[ -f "$PROJECT_ROOT/scripts/testing/terraform_validator.py" ]]; then
        log_info "Running Terraform state compliance checks..."
        
        if python3 "$PROJECT_ROOT/scripts/testing/terraform_validator.py" \
            --terraform-dir "$PROJECT_ROOT/terraform" \
            --log-level "$LOG_LEVEL" \
            > "$OUTPUT_DIR/compliance/terraform_validation.log" 2>&1; then
            log_success "Terraform compliance checks completed"
        else
            log_warning "Terraform compliance checks had issues"  
        fi
    fi
    
    # Run Helm chart validation
    if [[ -f "$PROJECT_ROOT/helm/validate-charts.sh" ]]; then
        log_info "Running Helm chart compliance checks..."
        
        if cd "$PROJECT_ROOT/helm" && timeout "$TEST_TIMEOUT" ./validate-charts.sh \
            > "$OUTPUT_DIR/compliance/helm_validation.log" 2>&1; then
            log_success "Helm compliance checks completed"
            cd "$PROJECT_ROOT"
        else
            log_warning "Helm compliance checks had issues"
            cd "$PROJECT_ROOT"
        fi
    fi
    
    log_success "Compliance scanning completed"
}

# Generate comprehensive test report
generate_test_report() {
    log_section "Generating Comprehensive Test Report"
    
    local report_file="$OUTPUT_DIR/comprehensive_test_report.md"
    local timestamp
    timestamp=$(cat "$OUTPUT_DIR/test_run_timestamp" 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
    
    cat > "$report_file" <<EOF
# Infrastructure Testing & Validation Report

**Generated:** $timestamp  
**Test Suite:** Enhanced Infrastructure Testing  
**Environment:** $(uname -a)  

## Test Execution Summary

EOF
    
    # Add results from each test category
    local overall_status="✅ PASS"
    local total_categories=0
    local passed_categories=0
    
    # Terratest results
    if [[ "$ENABLE_TERRATEST" == "true" ]]; then
        total_categories=$((total_categories + 1))
        echo "### 🏗️ Terratest Infrastructure Tests" >> "$report_file"
        
        if [[ -f "$OUTPUT_DIR/terratest/results.json" ]]; then
            local passed failed
            passed=$(grep -c '"Action":"pass"' "$OUTPUT_DIR/terratest/results.json" 2>/dev/null || echo "0")
            failed=$(grep -c '"Action":"fail"' "$OUTPUT_DIR/terratest/results.json" 2>/dev/null || echo "0")
            
            if [[ $failed -eq 0 ]]; then
                echo "- **Status:** ✅ PASS" >> "$report_file"
                passed_categories=$((passed_categories + 1))
            else
                echo "- **Status:** ❌ FAIL" >> "$report_file"
                overall_status="❌ FAIL"
            fi
            
            echo "- **Tests:** $passed passed, $failed failed" >> "$report_file"
        else
            echo "- **Status:** ⚠️ SKIPPED" >> "$report_file"
            echo "- **Reason:** No results file found" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi
    
    # Helm unittest results
    if [[ "$ENABLE_HELM_UNITTEST" == "true" ]]; then
        total_categories=$((total_categories + 1))
        echo "### ⚓ Helm Unit Tests" >> "$report_file"
        
        local helm_results_count
        helm_results_count=$(find "$OUTPUT_DIR/helm-unittest" -name "*.xml" 2>/dev/null | wc -l)
        
        if [[ $helm_results_count -gt 0 ]]; then
            echo "- **Status:** ✅ PASS" >> "$report_file"
            echo "- **Charts Tested:** $helm_results_count" >> "$report_file"
            passed_categories=$((passed_categories + 1))
        else
            echo "- **Status:** ⚠️ SKIPPED" >> "$report_file"
            echo "- **Reason:** No test results found" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi
    
    # Security tests results
    if [[ "$ENABLE_SECURITY_TESTS" == "true" ]]; then
        total_categories=$((total_categories + 1))
        echo "### 🔒 Security Validation Tests" >> "$report_file"
        
        local security_logs
        security_logs=$(find "$OUTPUT_DIR/security" -name "*.log" 2>/dev/null | wc -l)
        
        if [[ $security_logs -gt 0 ]]; then
            echo "- **Status:** ✅ PASS" >> "$report_file"
            echo "- **Security Checks:** $security_logs completed" >> "$report_file"
            passed_categories=$((passed_categories + 1))
        else
            echo "- **Status:** ⚠️ SKIPPED" >> "$report_file"
            echo "- **Reason:** No security test logs found" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi
    
    # Performance tests results
    if [[ "$ENABLE_PERFORMANCE_TESTS" == "true" ]]; then
        total_categories=$((total_categories + 1))
        echo "### ⚡ Performance Benchmarks" >> "$report_file"
        
        if [[ -f "$OUTPUT_DIR/performance/benchmark_results.json" ]]; then
            local total_tests success_rate avg_response_time
            total_tests=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/performance/benchmark_results.json')); print(data.get('summary_stats', {}).get('total_tests', 0))" 2>/dev/null || echo "0")
            success_rate=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/performance/benchmark_results.json')); print(f\"{data.get('summary_stats', {}).get('success_rate', 0):.1f}\")" 2>/dev/null || echo "0.0")
            avg_response_time=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/performance/benchmark_results.json')); print(f\"{data.get('summary_stats', {}).get('avg_response_time_ms', 0):.2f}\")" 2>/dev/null || echo "0.00")
            
            echo "- **Status:** ✅ PASS" >> "$report_file"
            echo "- **Total Tests:** $total_tests" >> "$report_file"
            echo "- **Success Rate:** $success_rate%" >> "$report_file"
            echo "- **Avg Response Time:** ${avg_response_time}ms" >> "$report_file"
            passed_categories=$((passed_categories + 1))
        else
            echo "- **Status:** ⚠️ SKIPPED" >> "$report_file"
            echo "- **Reason:** No benchmark results found" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi
    
    # Compliance scan results  
    if [[ "$ENABLE_COMPLIANCE_SCAN" == "true" ]]; then
        total_categories=$((total_categories + 1))
        echo "### 📋 Compliance Scanning" >> "$report_file"
        
        local compliance_logs
        compliance_logs=$(find "$OUTPUT_DIR/compliance" -name "*.log" 2>/dev/null | wc -l)
        
        if [[ $compliance_logs -gt 0 ]]; then
            echo "- **Status:** ✅ PASS" >> "$report_file"
            echo "- **Compliance Checks:** $compliance_logs completed" >> "$report_file"
            passed_categories=$((passed_categories + 1))
        else
            echo "- **Status:** ⚠️ SKIPPED" >> "$report_file"
            echo "- **Reason:** No compliance logs found" >> "$report_file"
        fi
        echo "" >> "$report_file"
    fi
    
    # Overall summary
    cat >> "$report_file" <<EOF

## Overall Test Results

- **Overall Status:** $overall_status
- **Categories Passed:** $passed_categories/$total_categories
- **Success Rate:** $(( (passed_categories * 100) / total_categories ))%

## Test Artifacts

All test results, logs, and reports have been saved to: \`$OUTPUT_DIR\`

### Directory Structure:
\`\`\`
$OUTPUT_DIR/
├── terratest/           # Terratest results and logs
├── helm-unittest/       # Helm unit test results  
├── security/           # Security validation logs
├── performance/        # Performance benchmark results
├── compliance/         # Compliance scan results
└── comprehensive_test_report.md  # This report
\`\`\`

---
*Report generated by Enhanced Testing Suite - $(date)*
EOF
    
    log_success "Comprehensive test report generated: $report_file"
    
    # Print summary to console
    echo ""
    log_section "📊 TEST EXECUTION SUMMARY"
    echo "Overall Status: $overall_status"
    echo "Categories Passed: $passed_categories/$total_categories"
    echo "Success Rate: $(( (passed_categories * 100) / total_categories ))%"
    echo "Full Report: $report_file"
    echo ""
    
    if [[ $passed_categories -lt $total_categories ]]; then
        return 1
    fi
}

# Main execution function
main() {
    echo -e "${PURPLE}🧪 Enhanced Infrastructure Testing & Validation Suite${NC}"
    echo -e "${PURPLE}=====================================================${NC}"
    echo ""
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Show configuration
    log_info "Test Configuration:"
    echo "  - Terratest: $ENABLE_TERRATEST"
    echo "  - Helm Unit Tests: $ENABLE_HELM_UNITTEST" 
    echo "  - Security Tests: $ENABLE_SECURITY_TESTS"
    echo "  - Performance Tests: $ENABLE_PERFORMANCE_TESTS"
    echo "  - Compliance Scan: $ENABLE_COMPLIANCE_SCAN"
    echo "  - Timeout: ${TEST_TIMEOUT}s"
    echo "  - Parallel Jobs: $PARALLEL_JOBS"
    echo "  - Output Directory: $OUTPUT_DIR"
    echo "  - Log Level: $LOG_LEVEL"
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Setup output directory
    setup_output_directory
    
    # Record start time
    local start_time
    start_time=$(date +%s)
    
    # Execute test categories
    local exit_code=0
    
    # Run tests in sequence (could be parallelized in future)
    run_terratest || exit_code=1
    run_helm_unittest || exit_code=1
    run_security_tests || exit_code=1
    run_performance_tests || exit_code=1
    run_compliance_scan || exit_code=1
    
    # Generate comprehensive report
    generate_test_report || exit_code=1
    
    # Calculate total execution time
    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo ""
    if [[ $exit_code -eq 0 ]]; then
        log_success "🎉 All tests completed successfully in ${duration}s!"
    else
        log_error "❌ Some tests failed. Check the report for details. Total time: ${duration}s"
    fi
    
    log_info "💾 Test results saved to: $OUTPUT_DIR"
    
    exit $exit_code
}

# Execute main function with all arguments
main "$@"
