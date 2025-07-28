#!/bin/bash
# Homelab Infrastructure Test Suite Launcher
# Copyright (c) 2025 Tyler Zervas
# Licensed under the MIT License
#
# Convenience wrapper for running the integrated testing framework
# Usage: ./run-tests.sh [OPTIONS]

set -euo pipefail

# Colors for output
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Show usage information
usage() {
    cat <<EOF
Homelab Infrastructure Test Suite Launcher

Usage: $0 [OPTIONS]

OPTIONS:
    --help                     Show this help message
    --integrated               Run integrated test suite (default)
    --python-only              Run Python framework tests only
    --k3s-only                 Run K3s validation tests only
    --quick                    Run quick tests (core categories only)
    --full                     Run comprehensive tests (all categories)
    --include-workstation      Include workstation perspective tests
    --parallel                 Run K3s tests in parallel
    --output-format FORMAT    Output format: console, json, markdown, all (default: console)
    --output-file FILE         Custom output filename (without extension)
    --log-level LEVEL          Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    --kubeconfig PATH          Path to kubeconfig file
    --dry-run                  Show what would be executed without running tests

EXAMPLES:
    $0                                   # Run integrated test suite
    $0 --quick                          # Quick health check
    $0 --full --output-format all       # Comprehensive tests with all reports
    $0 --python-only --include-workstation # Python framework with workstation tests
    $0 --k3s-only --parallel            # K3s validation tests in parallel

EOF
}

# Default values
FRAMEWORK="integrated"
TEST_SCOPE="default"
INCLUDE_WORKSTATION=false
PARALLEL_K3S=false
OUTPUT_FORMAT="console"
OUTPUT_FILE=""
LOG_LEVEL="INFO"
KUBECONFIG=""
DRY_RUN=false

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                usage
                exit 0
                ;;
            --integrated)
                FRAMEWORK="integrated"
                shift
                ;;
            --python-only)
                FRAMEWORK="python"
                shift
                ;;
            --k3s-only)
                FRAMEWORK="k3s"
                shift
                ;;
            --quick)
                TEST_SCOPE="quick"
                shift
                ;;
            --full)
                TEST_SCOPE="full"
                shift
                ;;
            --include-workstation)
                INCLUDE_WORKSTATION=true
                shift
                ;;
            --parallel)
                PARALLEL_K3S=true
                shift
                ;;
            --output-format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --output-file)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --kubeconfig)
                KUBECONFIG="$2"
                shift 2
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
    
    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 is required but not installed"
        return 1
    fi
    
    # Check kubectl
    if ! command -v kubectl >/dev/null 2>&1 && ! command -v k3s >/dev/null 2>&1; then
        log_warning "Neither kubectl nor k3s command found"
        log_warning "Some tests may fail without cluster access"
    fi
    
    # Check if integrated orchestrator exists
    if [[ "$FRAMEWORK" == "integrated" ]] && [[ ! -f "$SCRIPT_DIR/scripts/testing/integrated_test_orchestrator.py" ]]; then
        log_error "Integrated orchestrator not found: $SCRIPT_DIR/scripts/testing/integrated_test_orchestrator.py"
        return 1
    fi
    
    # Check if K3s validation framework exists
    if [[ "$FRAMEWORK" == "k3s" || "$FRAMEWORK" == "integrated" ]] && [[ ! -f "$SCRIPT_DIR/testing/k3s-validation/orchestrator.sh" ]]; then
        log_warning "K3s validation framework not found: $SCRIPT_DIR/testing/k3s-validation/orchestrator.sh"
        if [[ "$FRAMEWORK" == "k3s" ]]; then
            log_error "Cannot run K3s-only tests without K3s validation framework"
            return 1
        fi
    fi
    
    log_success "Prerequisites check completed"
}

# Build command arguments
build_command() {
    local cmd=()
    
    case "$FRAMEWORK" in
        "integrated")
            cmd=("python3" "$SCRIPT_DIR/scripts/testing/integrated_test_orchestrator.py")
            
            # Add K3s categories based on test scope
            case "$TEST_SCOPE" in
                "quick")
                    cmd+=("--k3s-categories" "core")
                    ;;
                "full")
                    cmd+=("--k3s-categories" "core" "k3s-specific" "performance" "security" "production")
                    ;;
                # default: let integrated orchestrator decide
            esac
            
            if [[ "$INCLUDE_WORKSTATION" == true ]]; then
                cmd+=("--include-workstation")
            fi
            
            if [[ "$PARALLEL_K3S" == true ]]; then
                cmd+=("--parallel-k3s")
            fi
            ;;
            
        "python")
            cmd=("python3" "$SCRIPT_DIR/scripts/testing/test_reporter.py")
            
            if [[ "$INCLUDE_WORKSTATION" == true ]]; then
                cmd+=("--include-workstation")
            fi
            ;;
            
        "k3s")
            cmd=("$SCRIPT_DIR/testing/k3s-validation/orchestrator.sh")
            
            # Add categories based on test scope
            case "$TEST_SCOPE" in
                "quick")
                    cmd+=("core")
                    ;;
                "full")
                    cmd+=("--all")
                    ;;
                *)
                    cmd+=("--all")
                    ;;
            esac
            
            if [[ "$PARALLEL_K3S" == true ]]; then
                cmd+=("--parallel")
            fi
            
            cmd+=("--report-format" "json")
            ;;
    esac
    
    # Add common options
    cmd+=("--output-format" "$OUTPUT_FORMAT")
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        cmd+=("--output-file" "$OUTPUT_FILE")
    fi
    
    if [[ -n "$LOG_LEVEL" && "$FRAMEWORK" != "k3s" ]]; then
        cmd+=("--log-level" "$LOG_LEVEL")
    fi
    
    if [[ -n "$KUBECONFIG" ]]; then
        cmd+=("--kubeconfig" "$KUBECONFIG")
    fi
    
    echo "${cmd[@]}"
}

# Execute the tests
run_tests() {
    local cmd_array
    IFS=' ' read -ra cmd_array <<< "$(build_command)"
    
    log_info "Running $FRAMEWORK testing framework..."
    log_info "Test scope: $TEST_SCOPE"
    log_info "Output format: $OUTPUT_FORMAT"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN - Command that would be executed:"
        echo "  ${cmd_array[*]}"
        return 0
    fi
    
    log_info "Executing: ${cmd_array[*]}"
    
    # Change to script directory for relative path resolution
    cd "$SCRIPT_DIR"
    
    # Execute the command
    if "${cmd_array[@]}"; then
        log_success "Test execution completed successfully"
        return 0
    else
        local exit_code=$?
        log_error "Test execution failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Generate summary based on framework
show_summary() {
    log_info "Test execution summary:"
    
    case "$FRAMEWORK" in
        "integrated")
            echo "  Framework: Integrated (Python + K3s validation)"
            ;;
        "python")
            echo "  Framework: Python testing framework only"
            ;;
        "k3s")
            echo "  Framework: K3s validation framework only"
            ;;
    esac
    
    echo "  Test Scope: $TEST_SCOPE"
    echo "  Include Workstation: $INCLUDE_WORKSTATION"
    
    if [[ "$FRAMEWORK" != "python" ]]; then
        echo "  Parallel K3s: $PARALLEL_K3S"
    fi
    
    echo "  Output Format: $OUTPUT_FORMAT"
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "  Output File: $OUTPUT_FILE"
    fi
    
    # Show where results can be found
    if [[ "$OUTPUT_FORMAT" == "json" || "$OUTPUT_FORMAT" == "all" ]]; then
        echo "  JSON reports will be saved to: test_results/"
    fi
    
    if [[ "$OUTPUT_FORMAT" == "markdown" || "$OUTPUT_FORMAT" == "all" ]]; then
        echo "  Markdown reports will be saved to: test_results/"
    fi
    
    if [[ "$FRAMEWORK" == "k3s" || "$FRAMEWORK" == "integrated" ]]; then
        echo "  K3s validation reports will be saved to: testing/k3s-validation/reports/"
    fi
}

# Main function
main() {
    echo -e "${BLUE}🏠 Homelab Infrastructure Test Suite Launcher${NC}"
    echo -e "${BLUE}===========================================${NC}"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Show summary of what will be executed
    show_summary
    echo
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    echo
    
    # Run the tests
    if run_tests; then
        echo
        log_success "🎉 Test suite execution completed successfully!"
        
        # Show next steps
        echo
        log_info "Next steps:"
        echo "  - Review test results above"
        echo "  - Check generated report files (if any)"
        echo "  - Address any failed tests or warnings"
        echo "  - Set up automated testing schedule"
        
    else
        echo
        log_error "❌ Test suite execution failed!"
        echo
        log_info "Troubleshooting tips:"
        echo "  - Check cluster connectivity: kubectl cluster-info"
        echo "  - Verify prerequisites are installed"
        echo "  - Run with --log-level DEBUG for more details"
        echo "  - Try individual framework tests: --python-only or --k3s-only"
        
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
