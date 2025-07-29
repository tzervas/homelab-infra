#!/bin/bash
# Enhanced Deployment Script with Automated Validation Hooks
# Integrates comprehensive validation hooks throughout the deployment process

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DEPLOYMENT_PHASE="${1:-vm-test}"
ENVIRONMENT="${ENVIRONMENT:-development}"
HOOKS_CONFIG="${HOOKS_CONFIG:-$PROJECT_ROOT/config/hooks/deployment-validation-hooks.yaml}"
VALIDATION_HOOKS_SCRIPT="$PROJECT_ROOT/scripts/testing/deployment_validation_hooks.py"

# Logging functions
log_info() {
    echo -e "\033[0;34m[INFO]\033[0m $*" >&2
}

log_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $*" >&2
}

log_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $*" >&2
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $*" >&2
}

log_header() {
    echo -e "\033[0;35m$*\033[0m" >&2
}

show_usage() {
    cat <<EOF
Enhanced Deployment with Automated Validation Hooks

USAGE:
    $0 <deployment-phase> [options]

DEPLOYMENT PHASES:
    vm-test           Deploy to test VM with full validation
    bare-metal        Deploy to bare metal with full validation
    staging           Deploy to staging environment
    production        Deploy to production environment
    validation-only   Skip deployment, only run validation hooks

ENVIRONMENT VARIABLES:
    ENVIRONMENT         Target environment (development, staging, production)
    HOOKS_CONFIG        Path to hooks configuration file
    SKIP_PRE_HOOKS      Skip pre-deployment hooks (default: false)
    SKIP_POST_HOOKS     Skip post-deployment hooks (default: false)
    ENABLE_CONTINUOUS   Enable continuous monitoring hooks (default: true)
    VERBOSE             Enable verbose logging (default: false)

EXAMPLES:
    # Full deployment with validation
    $0 vm-test

    # Production deployment with all validation
    ENVIRONMENT=production $0 production

    # Skip post-deployment hooks
    SKIP_POST_HOOKS=true $0 staging

    # Validation only mode
    $0 validation-only

EOF
}

validate_prerequisites() {
    log_header "🔍 Validating Prerequisites"

    local missing_tools=()

    # Check required tools
    for tool in python3 kubectl ansible-playbook; do
        if ! command -v "$tool" &>/dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install missing tools and try again."
        exit 1
    fi

    # Check validation hooks script
    if [[ ! -f "$VALIDATION_HOOKS_SCRIPT" ]]; then
        log_error "Validation hooks script not found: $VALIDATION_HOOKS_SCRIPT"
        exit 1
    fi

    # Check hooks configuration
    if [[ ! -f "$HOOKS_CONFIG" ]]; then
        log_warning "Hooks configuration not found: $HOOKS_CONFIG"
        log_info "Using default hook configuration"
        HOOKS_CONFIG=""
    fi

    # Check Python dependencies
    if ! python3 -c "import kubernetes, yaml" &>/dev/null; then
        log_error "Required Python dependencies not installed"
        log_info "Run: uv add kubernetes pyyaml"
        exit 1
    fi

    log_success "Prerequisites validation completed"
}

run_validation_hooks() {
    local phase="$1"
    local context="$2"

    log_header "🎯 Running $phase Validation Hooks"

    local hook_cmd=(
        python3 "$VALIDATION_HOOKS_SCRIPT"
        --phase "$phase"
        --log-level "${LOG_LEVEL:-INFO}"
    )

    if [[ -n "$HOOKS_CONFIG" ]]; then
        hook_cmd+=(--config-file "$HOOKS_CONFIG")
    fi

    if [[ -n "${KUBECONFIG:-}" ]]; then
        hook_cmd+=(--kubeconfig "$KUBECONFIG")
    fi

    if [[ -n "$context" ]]; then
        hook_cmd+=(--context "$context")
    fi

    log_info "Executing: ${hook_cmd[*]}"

    if "${hook_cmd[@]}"; then
        log_success "$phase validation hooks completed successfully"
        return 0
    else
        log_error "$phase validation hooks failed"
        return 1
    fi
}

build_deployment_context() {
    local phase="$1"

    # Build context for hook execution
    local context="{
        \"deployment_phase\": \"$phase\",
        \"environment\": \"$ENVIRONMENT\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"project_root\": \"$PROJECT_ROOT\",
        \"min_cpu_cores\": 2,
        \"min_memory_gb\": 4,
        \"config_paths\": [
            \"$PROJECT_ROOT/helm/environments\",
            \"$PROJECT_ROOT/kubernetes/base\",
            \"$PROJECT_ROOT/ansible/inventory\"
        ],
        \"prerequisites\": [
            {\"type\": \"namespace\", \"name\": \"kube-system\"},
            {\"type\": \"storageclass\", \"name\": \"longhorn\"}
        ],
        \"security_requirements\": {
            \"require_network_policies\": true,
            \"require_pod_security_standards\": true
        },
        \"include_workstation_tests\": false
    }"

    # Environment-specific context modifications
    case "$ENVIRONMENT" in
        "production")
            context=$(echo "$context" | jq '.security_requirements.require_network_policies = true |
                                             .min_cpu_cores = 4 |
                                             .min_memory_gb = 8')
            ;;
        "staging")
            context=$(echo "$context" | jq '.include_workstation_tests = true')
            ;;
        "development")
            context=$(echo "$context" | jq '.min_cpu_cores = 1 |
                                         .min_memory_gb = 2 |
                                         .security_requirements.require_network_policies = false')
            ;;
    esac

    echo "$context"
}

perform_deployment() {
    local phase="$1"

    log_header "🚀 Starting Deployment Phase: $phase"

    local deployment_script="$SCRIPT_DIR/deploy-homelab.sh"

    if [[ ! -f "$deployment_script" ]]; then
        log_error "Deployment script not found: $deployment_script"
        return 1
    fi

    case "$phase" in
        "vm-test"|"bare-metal"|"staging"|"production")
            log_info "Executing deployment for $phase environment..."
            if "$deployment_script" "$phase"; then
                log_success "Deployment completed successfully"
                return 0
            else
                log_error "Deployment failed"
                return 1
            fi
            ;;
        "validation-only")
            log_info "Skipping deployment (validation-only mode)"
            return 0
            ;;
        *)
            log_error "Unknown deployment phase: $phase"
            return 1
            ;;
    esac
}

wait_for_deployment_stabilization() {
    log_header "⏳ Waiting for Deployment Stabilization"

    local max_wait=600  # 10 minutes
    local check_interval=15
    local elapsed=0

    log_info "Waiting for pods to stabilize (timeout: ${max_wait}s)..."

    while [[ $elapsed -lt $max_wait ]]; do
        if kubectl cluster-info &>/dev/null; then
            # Check for problem pods
            local problem_pods
            problem_pods=$(kubectl get pods -A --no-headers 2>/dev/null | \
                          grep -cE "(Error|CrashLoopBackOff|ImagePullBackOff|Pending)" || echo 0)

            if [[ $problem_pods -eq 0 ]]; then
                local total_pods running_pods
                total_pods=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
                running_pods=$(kubectl get pods -A --no-headers 2>/dev/null | grep -c "Running" || echo 0)

                if [[ $total_pods -gt 0 && $running_pods -gt $((total_pods * 80 / 100)) ]]; then
                    log_success "Deployment stabilized (${running_pods}/${total_pods} pods running)"
                    return 0
                fi
            fi
        fi

        sleep $check_interval
        elapsed=$((elapsed + check_interval))
        echo -n "."
    done

    echo
    log_warning "Deployment did not fully stabilize within timeout"
    log_info "Proceeding with post-deployment validation"
    return 0
}

setup_continuous_monitoring() {
    log_header "📊 Setting Up Continuous Monitoring"

    if [[ "${ENABLE_CONTINUOUS:-true}" != "true" ]]; then
        log_info "Continuous monitoring disabled"
        return 0
    fi

    local context
    context=$(build_deployment_context "continuous")

    # Create systemd service for continuous monitoring (if running on systemd)
    if command -v systemctl &>/dev/null; then
        local service_file="/tmp/homelab-continuous-validation.service"

        cat > "$service_file" <<EOF
[Unit]
Description=Homelab Continuous Validation Monitoring
After=network.target

[Service]
Type=oneshot
ExecStart=python3 $VALIDATION_HOOKS_SCRIPT --phase continuous --context '$context'
User=$(whoami)
WorkingDirectory=$PROJECT_ROOT

[Install]
WantedBy=multi-user.target
EOF

        local timer_file="/tmp/homelab-continuous-validation.timer"

        cat > "$timer_file" <<EOF
[Unit]
Description=Run Homelab Continuous Validation every 15 minutes
Requires=homelab-continuous-validation.service

[Timer]
OnCalendar=*:0/15
Persistent=true

[Install]
WantedBy=timers.target
EOF

        log_info "Continuous monitoring service files created:"
        log_info "  Service: $service_file"
        log_info "  Timer: $timer_file"
        log_info "To install: sudo cp $service_file $timer_file /etc/systemd/system/ && sudo systemctl enable --now homelab-continuous-validation.timer"
    else
        # Create a simple cron job entry
        local cron_entry="*/15 * * * * cd $PROJECT_ROOT && python3 $VALIDATION_HOOKS_SCRIPT --phase continuous --context '$context' >> /var/log/homelab-validation.log 2>&1"
        log_info "Continuous monitoring cron entry:"
        log_info "  $cron_entry"
        log_info "Add this to your crontab with: crontab -e"
    fi

    # Also run initial continuous validation
    log_info "Running initial continuous validation..."
    if run_validation_hooks "continuous" "$context"; then
        log_success "Initial continuous validation completed"
    else
        log_warning "Initial continuous validation had issues"
    fi
}

generate_deployment_report() {
    local phase="$1"
    local pre_hooks_result="$2"
    local deployment_result="$3"
    local post_hooks_result="$4"

    log_header "📋 Generating Deployment Report"

    local report_file="$PROJECT_ROOT/deployment-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" <<EOF
# Homelab Infrastructure Deployment Report

**Date**: $(date)
**Deployment Phase**: $phase
**Environment**: $ENVIRONMENT
**Total Duration**: $((SECONDS / 60))m $((SECONDS % 60))s

## Deployment Summary

- **Pre-deployment Validation**: $([ "$pre_hooks_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")
- **Deployment Process**: $([ "$deployment_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")
- **Post-deployment Validation**: $([ "$post_hooks_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")

## Configuration

- **Environment**: $ENVIRONMENT
- **Hooks Configuration**: ${HOOKS_CONFIG:-"Default configuration"}
- **Project Root**: $PROJECT_ROOT
- **Kubernetes Config**: ${KUBECONFIG:-"Default kubeconfig"}

## Validation Hook Results

### Pre-deployment Hooks
$([ "$pre_hooks_result" -eq 0 ] && echo "All pre-deployment validation hooks passed successfully." || echo "Pre-deployment validation hooks failed. Check logs for details.")

### Post-deployment Hooks
$([ "$post_hooks_result" -eq 0 ] && echo "All post-deployment validation hooks passed successfully." || echo "Post-deployment validation hooks failed. Check logs for details.")

## Cluster Status

### Nodes
\`\`\`
$(kubectl get nodes -o wide 2>/dev/null || echo "kubectl not accessible")
\`\`\`

### Running Pods by Namespace
\`\`\`
$(kubectl get pods -A --field-selector=status.phase=Running 2>/dev/null | head -20 || echo "kubectl not accessible")
\`\`\`

### Service URLs
$(if kubectl get ingress -A --no-headers 2>/dev/null; then
    echo "#### Available Services"
    kubectl get ingress -A --no-headers 2>/dev/null | while read -r ns name _ hosts _ _ _; do
        echo "- **$name** ($ns): https://$hosts"
    done
else
    echo "No ingress resources found or kubectl not accessible"
fi)

## Hook Results Details

Hook execution results are stored in: \`test_results/hooks/\`

## Next Steps

$(if [[ $pre_hooks_result -eq 0 && $deployment_result -eq 0 && $post_hooks_result -eq 0 ]]; then
    cat <<NEXT_STEPS
### ✅ Deployment Successful

Your homelab infrastructure deployment completed successfully with all validation hooks passing!

**Immediate Actions:**
1. **Access Services**: Use the URLs listed above to access deployed services
2. **Verify SSO**: Test Keycloak integration with GitLab and other services
3. **Check Monitoring**: Ensure Prometheus and Grafana are collecting metrics
4. **Review Continuous Monitoring**: Continuous validation hooks are now active

**Ongoing Operations:**
- Monitor hook results in \`test_results/hooks/\`
- Review continuous monitoring alerts
- Update configurations as needed
- Schedule regular validation reviews

NEXT_STEPS
else
    cat <<TROUBLESHOOT
### ❌ Deployment Issues Detected

Some components failed validation. Please review the following:

**Immediate Actions:**
1. **Check Hook Results**: Review detailed results in \`test_results/hooks/\`
2. **Review Pod Status**: \`kubectl get pods -A | grep -v Running\`
3. **Check Logs**: \`kubectl logs -n <namespace> <pod-name>\`
4. **Verify Configuration**: Review configuration files and environment variables

**Troubleshooting Commands:**
\`\`\`bash
# Check failing pods
kubectl get pods -A | grep -v Running

# Get recent events
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

# Re-run validation hooks
python3 $VALIDATION_HOOKS_SCRIPT --phase post-deployment

# Check hook results
ls -la test_results/hooks/
\`\`\`

TROUBLESHOOT
fi)

---

**Generated by**: Enhanced Deployment with Validation Hooks
**Report Location**: $report_file
EOF

    log_success "Deployment report generated: $report_file"

    # Print summary
    echo
    echo "======================================"
    echo "  DEPLOYMENT WITH VALIDATION COMPLETE"
    echo "======================================"
    echo
    echo "Phase: $phase"
    echo "Environment: $ENVIRONMENT"
    echo "Duration: $((SECONDS / 60))m $((SECONDS % 60))s"
    echo "Pre-hooks: $([ "$pre_hooks_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo "Deployment: $([ "$deployment_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo "Post-hooks: $([ "$post_hooks_result" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
    echo "Report: $report_file"
    echo
}

main() {
    # Handle help
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        show_usage
        exit 0
    fi

    log_header "🏗️ Enhanced Homelab Deployment with Validation Hooks"
    echo "Deployment Phase: $DEPLOYMENT_PHASE"
    echo "Environment: $ENVIRONMENT"
    echo "Hooks Config: ${HOOKS_CONFIG:-"Default"}"
    echo "Project Root: $PROJECT_ROOT"
    echo

    # Validate prerequisites
    validate_prerequisites

    # Build deployment context
    local context
    context=$(build_deployment_context "$DEPLOYMENT_PHASE")

    # Track results
    local pre_hooks_result=0
    local deployment_result=0
    local post_hooks_result=0

    # Phase 1: Pre-deployment validation hooks
    if [[ "${SKIP_PRE_HOOKS:-false}" != "true" ]]; then
        if ! run_validation_hooks "pre-deployment" "$context"; then
            pre_hooks_result=1
            log_error "Pre-deployment validation failed - blocking deployment"
            generate_deployment_report "$DEPLOYMENT_PHASE" $pre_hooks_result 1 1
            exit 1
        fi
    else
        log_info "Skipping pre-deployment hooks"
    fi

    # Phase 2: Perform deployment
    if [[ "$DEPLOYMENT_PHASE" != "validation-only" ]]; then
        if ! perform_deployment "$DEPLOYMENT_PHASE"; then
            deployment_result=1
            log_error "Deployment failed"
            generate_deployment_report "$DEPLOYMENT_PHASE" $pre_hooks_result $deployment_result 1
            exit 1
        fi

        # Wait for deployment to stabilize
        wait_for_deployment_stabilization
    fi

    # Phase 3: Post-deployment validation hooks
    if [[ "${SKIP_POST_HOOKS:-false}" != "true" ]]; then
        if ! run_validation_hooks "post-deployment" "$context"; then
            post_hooks_result=1
            log_warning "Post-deployment validation failed"
        fi
    else
        log_info "Skipping post-deployment hooks"
    fi

    # Phase 4: Setup continuous monitoring
    setup_continuous_monitoring

    # Generate final report
    generate_deployment_report "$DEPLOYMENT_PHASE" $pre_hooks_result $deployment_result $post_hooks_result

    # Return appropriate exit code
    if [[ $pre_hooks_result -eq 0 && $deployment_result -eq 0 && $post_hooks_result -eq 0 ]]; then
        log_success "🎉 Deployment with validation completed successfully!"
        exit 0
    else
        log_error "❌ Deployment completed with validation issues"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
