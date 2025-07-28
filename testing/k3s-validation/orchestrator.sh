#!/bin/bash
# K3s Testing Framework Orchestrator
# Comprehensive testing suite for K3s clusters

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/debug.sh"

# Configuration
CONFIG_FILE=""
SELECTED_CATEGORIES=()
REPORT_FORMAT="text"
PARALLEL_EXECUTION=false
DRY_RUN=false
VERBOSE=false

usage() {
    cat <<EOF
K3s Testing Framework Orchestrator

Usage: $0 [OPTIONS] [CATEGORIES...]

OPTIONS:
    --all                   Run all test categories
    --config FILE          Use specific configuration file
    --report-format FORMAT Report format: text, json, html (default: text)
    --parallel             Run test modules in parallel where possible
    --dry-run              Show what would be executed without running tests
    --verbose              Enable verbose output and basic debugging
    --debug                Enable enhanced debugging (functions, commands, vars)
    --debug-all            Enable all debugging features including trace
    --help                 Show this help message

CATEGORIES:
    core                   Core Kubernetes functionality
    k3s-specific          K3s-specific components (traefik, servicelb, etc.)
    performance           Performance and benchmarking tests
    security              Security validation tests
    failure               Failure scenario and chaos tests
    production            Production readiness tests

EXAMPLES:
    $0 --all                              # Run all tests
    $0 core k3s-specific                  # Run specific categories
    $0 --config prod.yaml performance     # Use config and run performance tests
    $0 --all --report-format html         # Generate HTML report
    $0 --parallel --all                   # Run tests in parallel

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                SELECTED_CATEGORIES=("core" "k3s-specific" "performance" "security" "failure" "production")
                shift
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --report-format)
                REPORT_FORMAT="$2"
                shift 2
                ;;
            --parallel)
                PARALLEL_EXECUTION=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                export DEBUG=1
                debug_level_1
                shift
                ;;
            --debug)
                VERBOSE=true
                export DEBUG=1
                debug_level_2
                shift
                ;;
            --debug-all)
                VERBOSE=true
                export DEBUG=1
                debug_level_3
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            -*)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                SELECTED_CATEGORIES+=("$1")
                shift
                ;;
        esac
    done
}

load_configuration() {
    if [[ -n "$CONFIG_FILE" ]]; then
        if [[ -f "$CONFIG_FILE" ]]; then
            log_info "Loading configuration from $CONFIG_FILE"
            # Source configuration file (should be bash format)
            source "$CONFIG_FILE"
        else
            log_error "Configuration file not found: $CONFIG_FILE"
            exit 1
        fi
    fi
}

validate_categories() {
    local valid_categories=("core" "k3s-specific" "performance" "security" "failure" "production")

    for category in "${SELECTED_CATEGORIES[@]}"; do
        local valid=false
        for valid_cat in "${valid_categories[@]}"; do
            if [[ "$category" == "$valid_cat" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == false ]]; then
            log_error "Invalid category: $category"
            log_info "Valid categories: ${valid_categories[*]}"
            exit 1
        fi
    done
}

run_core_tests() {
    log_header "Core Kubernetes Tests"

    # Enhanced version of existing basic tests
    local modules=(
        "modules/core/api-server-health.sh:run_api_server_health"
        "modules/core/node-validation.sh:run_node_validation"
        "modules/core/system-pods.sh:run_system_pods"
        "modules/core/basic-networking.sh:run_basic_networking"
        "modules/core/dns-resolution.sh:run_dns_resolution"
        "modules/core/basic-storage.sh:run_basic_storage"
    )

    local modules_found=0
    local modules_run=0

    for module_spec in "${modules[@]}"; do
        local module_path="${module_spec%:*}"
        local module_function="${module_spec#*:}"

        if [[ -f "$SCRIPT_DIR/$module_path" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module_path ($module_function)"
                modules_run=$((modules_run + 1))
            else
                log_info "Running: $module_path"
                # Use safe execution with error recovery
                set_safe_mode
                if safe_exec "source module $module_path" source "$SCRIPT_DIR/$module_path" && \
                   with_error_recovery "execute $module_function" "$module_function"; then
                    modules_run=$((modules_run + 1))
                    log_success "Module completed: $module_path"
                else
                    log_error "Module failed: $module_path (continuing with other modules)"
                fi
                restore_strict_mode
            fi
        else
            log_warning "Module not found: $module_path (will be skipped)"
        fi
    done

    log_info "Core tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No core test modules found - framework may need module installation"
    fi
}

run_k3s_specific_tests() {
    log_header "K3s-Specific Component Tests"

    local modules=(
        "modules/k3s-specific/traefik-validation.sh"
        "modules/k3s-specific/servicelb-validation.sh"
        "modules/k3s-specific/local-path-provisioner.sh"
        "modules/k3s-specific/embedded-db-health.sh"
        "modules/k3s-specific/agent-server-comm.sh"
    )

    local modules_found=0
    local modules_run=0

    for module in "${modules[@]}"; do
        if [[ -f "$SCRIPT_DIR/$module" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module"
                modules_run=$((modules_run + 1))
            else
                log_info "Running: $module"
source "$SCRIPT_DIR/$module"
                if main; then
                    modules_run=$((modules_run + 1))
                else
                    log_error "Module failed: $module"
                fi
            fi
        else
            log_warning "Module not found: $module (will be skipped)"
        fi
    done

    log_info "K3s-specific tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No K3s-specific test modules found - framework may need module installation"
    fi
}

run_performance_tests() {
    log_header "Performance and Benchmarking Tests"

    local modules=(
        "modules/performance/startup-benchmarks.sh"
        "modules/performance/network-throughput.sh"
        "modules/performance/storage-io.sh"
        "modules/performance/load-testing.sh"
    )

    local modules_found=0
    local modules_run=0

    for module in "${modules[@]}"; do
        if [[ -f "$SCRIPT_DIR/$module" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module"
                modules_run=$((modules_run + 1))
            else
                log_info "Running: $module"
source "$SCRIPT_DIR/$module"
                if main; then
                    modules_run=$((modules_run + 1))
                else
                    log_error "Module failed: $module"
                fi
            fi
        else
            log_warning "Module not found: $module (will be skipped)"
        fi
    done

    log_info "Performance tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No performance test modules found - framework may need module installation"
    fi
}

run_security_tests() {
    log_header "Security Validation Tests"

    local modules=(
        "modules/security/tls-validation.sh"
        "modules/security/rbac-testing.sh"
        "modules/security/pod-security.sh"
        "modules/security/network-policies.sh"
        "modules/security/secrets-management.sh"
    )

    local modules_found=0
    local modules_run=0

    for module in "${modules[@]}"; do
        if [[ -f "$SCRIPT_DIR/$module" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module"
                modules_run=$((modules_run + 1))
            else
                log_info "Running: $module"
source "$SCRIPT_DIR/$module"
                if main; then
                    modules_run=$((modules_run + 1))
                else
                    log_error "Module failed: $module"
                fi
            fi
        else
            log_warning "Module not found: $module (will be skipped)"
        fi
    done

    log_info "Security tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No security test modules found - framework may need module installation"
    fi
}

run_failure_tests() {
    log_header "Failure Scenario and Chaos Tests"

    local modules=(
        "modules/failure/node-failure.sh"
        "modules/failure/pod-eviction.sh"
        "modules/failure/network-partition.sh"
        "modules/failure/storage-failure.sh"
        "modules/failure/resource-exhaustion.sh"
    )

    local modules_found=0
    local modules_run=0

    for module in "${modules[@]}"; do
        if [[ -f "$SCRIPT_DIR/$module" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module"
                modules_run=$((modules_run + 1))
            else
                log_warning "Running chaos test: $module"
source "$SCRIPT_DIR/$module"
                if main; then
                    modules_run=$((modules_run + 1))
                else
                    log_error "Module failed: $module"
                fi
            fi
        else
            log_warning "Module not found: $module (will be skipped)"
        fi
    done

    log_info "Failure tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No failure test modules found - framework may need module installation"
    fi
}

run_production_tests() {
    log_header "Production Readiness Tests"

    local modules=(
        "modules/production/backup-restore.sh"
        "modules/production/monitoring-endpoints.sh"
        "modules/production/log-collection.sh"
        "modules/production/high-availability.sh"
        "modules/production/upgrade-testing.sh"
    )

    local modules_found=0
    local modules_run=0

    for module in "${modules[@]}"; do
        if [[ -f "$SCRIPT_DIR/$module" ]]; then
            modules_found=$((modules_found + 1))
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run: $module"
                modules_run=$((modules_run + 1))
            else
                log_info "Running: $module"
source "$SCRIPT_DIR/$module"
                if main; then
                    modules_run=$((modules_run + 1))
                else
                    log_error "Module failed: $module"
                fi
            fi
        else
            log_warning "Module not found: $module (will be skipped)"
        fi
    done

    log_info "Production tests completed: $modules_run/$modules_found modules executed successfully"

    if [[ $modules_found -eq 0 ]]; then
        log_warning "No production test modules found - framework may need module installation"
    fi
}

run_test_category() {
    local category="$1"

    case "$category" in
        "core")
            run_core_tests
            ;;
        "k3s-specific")
            run_k3s_specific_tests
            ;;
        "performance")
            run_performance_tests
            ;;
        "security")
            run_security_tests
            ;;
        "failure")
            run_failure_tests
            ;;
        "production")
            run_production_tests
            ;;
        *)
            log_error "Unknown test category: $category"
            ;;
    esac
}

generate_final_report() {
    case "$REPORT_FORMAT" in
        "text")
            end_test_suite
            ;;
        "json")
            generate_test_report
            ;;
        "html")
            generate_html_report
            ;;
        *)
            log_error "Unknown report format: $REPORT_FORMAT"
            end_test_suite
            ;;
    esac
}

generate_html_report() {
    local html_file="$REPORTS_DIR/test-report-${TIMESTAMP}.html"

    cat > "$html_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>K3s Testing Report - $TIMESTAMP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .pass { color: green; }
        .fail { color: red; }
        .warn { color: orange; }
        .skip { color: blue; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>K3s Testing Framework Report</h1>
        <p>Generated: $(date)</p>
        <p>Test Suite: $TEST_SUITE</p>
        <p>Namespace: $TEST_NAMESPACE</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr><th>Metric</th><th>Count</th></tr>
            <tr><td>Total Tests</td><td>$TESTS_TOTAL</td></tr>
            <tr><td class="pass">Passed</td><td>$TESTS_PASSED</td></tr>
            <tr><td class="fail">Failed</td><td>$TESTS_FAILED</td></tr>
            <tr><td class="warn">Warnings</td><td>$TESTS_WARNING</td></tr>
            <tr><td class="skip">Skipped</td><td>$TESTS_SKIPPED</td></tr>
            <tr><td>Success Rate</td><td>$(( TESTS_TOTAL > 0 ? TESTS_PASSED * 100 / TESTS_TOTAL : 0 ))%</td></tr>
        </table>
    </div>

    <div class="details">
        <h2>Test Details</h2>
        <p>Full log available at: $REPORTS_DIR/test-${TIMESTAMP}.log</p>
    </div>
</body>
</html>
EOF

    log_info "HTML report generated: $html_file"
}

main() {
    # Parse command line arguments
    if [[ $# -eq 0 ]]; then
        usage
        exit 1
    fi

    parse_arguments "$@"

    # Validate input
    if [[ ${#SELECTED_CATEGORIES[@]} -eq 0 ]]; then
        log_error "No test categories specified"
        usage
        exit 1
    fi

    validate_categories

    # Load configuration
    load_configuration

    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN - No tests will be executed"
        log_info "Selected categories: ${SELECTED_CATEGORIES[*]}"
        log_info "Report format: $REPORT_FORMAT"
        log_info "Parallel execution: $PARALLEL_EXECUTION"
    fi

    # Initialize framework
    if [[ "$DRY_RUN" == false ]]; then
        init_framework
        create_test_namespace
        start_test_suite "K3s Comprehensive Validation"
    fi

    # Run selected test categories
    for category in "${SELECTED_CATEGORIES[@]}"; do
        if [[ "$PARALLEL_EXECUTION" == true ]] && [[ "$DRY_RUN" == false ]]; then
            # Run in background for parallel execution
            run_test_category "$category" &
        else
            run_test_category "$category"
        fi
    done

    # Wait for parallel executions to complete
    if [[ "$PARALLEL_EXECUTION" == true ]] && [[ "$DRY_RUN" == false ]]; then
        wait
    fi

    # Generate final report
    if [[ "$DRY_RUN" == false ]]; then
        generate_final_report

        # Exit with appropriate code
        if [[ $TESTS_FAILED -gt 0 ]]; then
            exit 1
        else
            exit 0
        fi
    fi
}

# Execute main function
main "$@"
