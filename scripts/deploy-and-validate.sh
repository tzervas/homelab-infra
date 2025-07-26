#!/bin/bash
# Enhanced Deployment Script with Comprehensive Validation
# Deploys homelab infrastructure and performs thorough validation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
DEPLOYMENT_PHASE="${1:-vm-test}"
SKIP_DEPLOYMENT="${SKIP_DEPLOYMENT:-false}"
VALIDATION_ONLY="${VALIDATION_ONLY:-false}"
VERBOSE="${VERBOSE:-false}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

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

show_usage() {
    cat << EOF
Enhanced Homelab Deployment with Comprehensive Validation

USAGE:
    $0 <deployment-phase> [options]

DEPLOYMENT PHASES:
    vm-test           Deploy to test VM and validate
    bare-metal        Deploy to bare metal and validate
    validation-only   Skip deployment, only run validation

OPTIONS:
    SKIP_DEPLOYMENT=true    Skip deployment, only validate existing
    VALIDATION_ONLY=true    Only run validation (alias for validation-only)
    VERBOSE=true           Enable verbose output

EXAMPLES:
    # Full VM test deployment with validation
    $0 vm-test

    # Deploy to bare metal with validation
    $0 bare-metal

    # Only validate existing deployment
    $0 validation-only
    VALIDATION_ONLY=true $0 vm-test

    # Skip deployment, validate existing
    SKIP_DEPLOYMENT=true $0 vm-test

ENVIRONMENT VARIABLES:
    VERBOSE           Enable verbose logging
    SKIP_DEPLOYMENT   Skip deployment phase
    VALIDATION_ONLY   Only perform validation

EOF
}

validate_prerequisites() {
    log_header "🔍 Validating Prerequisites"

    local missing_tools=()

    # Check required tools
    for tool in ansible ansible-playbook kubectl curl; do
        if ! command -v "$tool" &>/dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install missing tools and try again."
        exit 1
    fi

    log_success "All required tools available"

    # Validate configuration files (flexible approach)
    local env_required="${ENV_REQUIRED:-true}"

    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        if [[ "$env_required" == "true" && "$DEPLOYMENT_PHASE" != "validation-only" && "$VALIDATION_ONLY" != "true" ]]; then
            log_error "Configuration file .env not found and required for deployment"
            log_info "Either create .env file or set ENV_REQUIRED=false to skip this check"
            log_info "For validation-only mode, .env file is not strictly required"
            exit 1
        else
            log_warning "Configuration file .env not found, proceeding without it"
            log_info "Set ENV_REQUIRED=true if .env is mandatory for your deployment"
        fi
    else
        log_success "Configuration file .env found"
        # Load environment variables from .env
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
    fi

    # Check for private configuration
    if [[ -f "$PROJECT_ROOT/.env.private.local" ]]; then
        log_success "Private configuration found"
        # Load private environment variables
        set -a
        source "$PROJECT_ROOT/.env.private.local"
        set +a
    else
        log_warning "No private configuration (.env.private.local) found"
        log_info "Using default/environment variable configuration values"
    fi

    log_success "Configuration validation completed"
}

perform_deployment() {
    local phase="$1"

    log_header "🚀 Starting Deployment Phase: $phase"

    case "$phase" in
        "vm-test"|"full-vm-test")
            log_info "Creating test VM and deploying infrastructure..."
            "$SCRIPT_DIR/deploy-homelab.sh" "$phase"
            ;;
        "bare-metal")
            log_info "Deploying to bare metal infrastructure..."
            "$SCRIPT_DIR/deploy-homelab.sh" "$phase"
            ;;
        *)
            log_error "Unknown deployment phase: $phase"
            show_usage
            exit 1
            ;;
    esac

    local deploy_result=$?
    if [[ $deploy_result -eq 0 ]]; then
        log_success "Deployment completed successfully"
    else
        log_error "Deployment failed with exit code $deploy_result"
        exit $deploy_result
    fi
}

wait_for_deployment_ready() {
    log_header "⏳ Waiting for Deployment to Stabilize"

    local max_wait=300  # 5 minutes
    local check_interval=10
    local elapsed=0

    log_info "Waiting for pods to be ready (timeout: ${max_wait}s)..."

    while [[ $elapsed -lt $max_wait ]]; do
        # Check if kubectl is accessible
        if kubectl cluster-info &>/dev/null; then
            # Check for any pods in crash/error state
            local problem_pods=$(kubectl get pods -A --no-headers | grep -E "(Error|CrashLoopBackOff|ImagePullBackOff)" | wc -l)

            if [[ $problem_pods -eq 0 ]]; then
                # Check if most pods are running
                local total_pods=$(kubectl get pods -A --no-headers | wc -l)
                local running_pods=$(kubectl get pods -A --no-headers | grep "Running" | wc -l)

                if [[ $total_pods -gt 0 && $running_pods -gt $((total_pods * 70 / 100)) ]]; then
                    log_success "Deployment appears stable (${running_pods}/${total_pods} pods running)"
                    return 0
                fi
            fi
        fi

        sleep $check_interval
        elapsed=$((elapsed + check_interval))
        echo -n "."
    done

    echo
    log_warning "Deployment did not stabilize within timeout, proceeding with validation"
    return 0
}

run_comprehensive_validation() {
    local deployment_type="$1"

    log_header "🔬 Running Comprehensive Validation"

    # Run the comprehensive validation script
    if "$SCRIPT_DIR/validate-deployment-comprehensive.sh" "$deployment_type"; then
        log_success "Comprehensive validation completed successfully"
        return 0
    else
        log_error "Validation failed - see details above"
        return 1
    fi
}

perform_smoke_tests() {
    log_header "💨 Performing Smoke Tests"

    # Quick smoke tests for critical services
    local smoke_test_results=0

    # Test 1: Kubernetes API accessibility
    if kubectl version --client &>/dev/null && kubectl cluster-info &>/dev/null; then
        log_success "Kubernetes API accessible"
    else
        log_error "Kubernetes API not accessible"
        smoke_test_results=1
    fi

    # Test 2: Core namespaces exist
    local required_namespaces=("kube-system")
    for ns in "${required_namespaces[@]}"; do
        if kubectl get namespace "$ns" &>/dev/null; then
            log_success "Namespace $ns exists"
        else
            log_error "Required namespace $ns missing"
            smoke_test_results=1
        fi
    done

    # Test 3: DNS resolution working
    if kubectl run smoke-test-dns --image=busybox:1.28 --restart=Never --rm -i --tty=false -- nslookup kubernetes.default &>/dev/null; then
        log_success "DNS resolution working"
    else
        log_warning "DNS resolution test failed or timed out"
    fi

    return $smoke_test_results
}

generate_deployment_summary() {
    local deployment_type="$1"
    local validation_result="$2"

    log_header "📊 Deployment Summary"

    local summary_file="$PROJECT_ROOT/deployment-summary-$(date +%Y%m%d-%H%M%S).md"

    cat > "$summary_file" << EOF
# Homelab Infrastructure Deployment Summary

**Date**: $(date)
**Deployment Type**: $deployment_type
**Validation Result**: $(if [[ $validation_result -eq 0 ]]; then echo "✅ PASSED"; else echo "❌ FAILED"; fi)
**Total Duration**: $((SECONDS / 60))m $((SECONDS % 60))s

## Deployment Configuration

- **Environment**: $deployment_type
- **Project Root**: $PROJECT_ROOT
- **Verbose Mode**: $VERBOSE

## Quick Status Check

### Cluster Nodes
\`\`\`
$(kubectl get nodes 2>/dev/null || echo "kubectl not accessible")
\`\`\`

### Running Pods by Namespace
\`\`\`
$(kubectl get pods -A --field-selector=status.phase=Running 2>/dev/null | head -20 || echo "kubectl not accessible")
\`\`\`

### Service URLs

$(if kubectl get ingress -A --no-headers 2>/dev/null | head -10; then
    echo "#### Available Services"
    kubectl get ingress -A --no-headers 2>/dev/null | while read ns name class hosts addr ports age; do
        echo "- **$name** ($ns): https://$hosts"
    done
else
    echo "No ingress resources found or kubectl not accessible"
fi)

## Next Steps

$(if [[ $validation_result -eq 0 ]]; then
cat << NEXT_STEPS
### ✅ Deployment Successful

Your homelab infrastructure is ready!

1. **Access Services**: Use the URLs listed above
2. **Configure SSO**: Set up Keycloak integration with GitLab
3. **Setup Monitoring**: Configure alerting and dashboards
4. **Review Documentation**: Check docs/ for operational procedures

### Useful Commands

\`\`\`bash
# Check all services
kubectl get all -A

# View service logs
kubectl logs -n <namespace> <pod-name>

# Access Grafana dashboards
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access GitLab
kubectl port-forward -n gitlab svc/gitlab-webservice 8080:8080
\`\`\`
NEXT_STEPS
else
cat << TROUBLESHOOT
### ❌ Deployment Issues Detected

Some components failed validation. Please review:

1. **Check Validation Report**: Look for detailed validation report
2. **Review Pod Status**: \`kubectl get pods -A\`
3. **Check Logs**: \`kubectl logs -n <namespace> <pod-name>\`
4. **Verify Configuration**: Review .env and configuration files
5. **Retry Deployment**: Fix issues and run deployment again

### Troubleshooting Commands

\`\`\`bash
# Check failing pods
kubectl get pods -A | grep -v Running

# Get pod logs
kubectl logs -n <namespace> <pod-name> --previous

# Describe problem resources
kubectl describe pod -n <namespace> <pod-name>

# Check events
kubectl get events -A --sort-by='.lastTimestamp'
\`\`\`
TROUBLESHOOT
fi)

---

**Generated by**: Enhanced Homelab Deployment Script
**Report Location**: $summary_file
EOF

    log_success "Deployment summary generated: $summary_file"

    # Show key information
    echo
    echo "=========================="
    echo "  DEPLOYMENT COMPLETE"
    echo "=========================="
    echo
    echo "Type: $deployment_type"
    echo "Duration: $((SECONDS / 60))m $((SECONDS % 60))s"
    echo "Status: $(if [[ $validation_result -eq 0 ]]; then echo "✅ SUCCESS"; else echo "❌ FAILED"; fi)"
    echo "Summary: $summary_file"
    echo
}

# Main execution function
main() {
    local start_time=$SECONDS

    # Handle help and validation-only modes
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi

    if [[ "$1" == "validation-only" || "$VALIDATION_ONLY" == "true" ]]; then
        SKIP_DEPLOYMENT=true
        DEPLOYMENT_PHASE="validation-only"
    fi

    log_header "🏗️ Enhanced Homelab Deployment with Validation"
    echo "Deployment Phase: $DEPLOYMENT_PHASE"
    echo "Skip Deployment: $SKIP_DEPLOYMENT"
    echo "Verbose Mode: $VERBOSE"
    echo "Project Root: $PROJECT_ROOT"
    echo

    # Step 1: Validate prerequisites
    validate_prerequisites

    # Step 2: Perform deployment (unless skipped)
    if [[ "$SKIP_DEPLOYMENT" != "true" ]]; then
        perform_deployment "$DEPLOYMENT_PHASE"

        # Step 3: Wait for deployment to stabilize
        wait_for_deployment_ready
    else
        log_info "Skipping deployment phase"
    fi

    # Step 4: Perform smoke tests
    if ! perform_smoke_tests; then
        log_warning "Some smoke tests failed, but continuing with comprehensive validation"
    fi

    # Step 5: Run comprehensive validation
    local validation_result=0
    if ! run_comprehensive_validation "$DEPLOYMENT_PHASE"; then
        validation_result=1
    fi

    # Step 6: Generate summary
    generate_deployment_summary "$DEPLOYMENT_PHASE" $validation_result

    # Return appropriate exit code
    exit $validation_result
}

# Execute main function with all arguments
main "$@"
