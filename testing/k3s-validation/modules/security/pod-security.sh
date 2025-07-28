#!/bin/bash
# Pod Security Validation for K3s Clusters
# Verifies pod security policies and settings

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"
source "$SCRIPT_DIR/../../lib/debug.sh"

run_pod_security() {
    start_test_module "Pod Security Validation"

    # Test 1: Check Pod Security Policies
    start_test "Pod Security Policies"
    if check_pod_security_policies; then
        log_success "Pod security policies are in place"
    else
        log_warning "Some pod security policies are missing or inadequate"
    fi

    # Test 2: Verify RunAsNonRoot Policy
    start_test "RunAsNonRoot Policy"
    if check_run_as_non_root; then
        log_success "RunAsNonRoot policy is enforced"
    else
        log_error "RunAsNonRoot policy is not enforced on some pods"
    fi

    # Add more pod security checks as necessary
}

check_pod_security_policies() {
    debug_enter "Checking Pod Security Policies"

    # Check if any Pod Security Policies are defined (example check)
    local psp
    psp=$($KUBECTL_CMD get psp -o json 2>/dev/null || echo "{}")

    if [[ "$psp" != "{}" ]]; then
        log_info "Pod Security Policies found"
        debug_exit 0
        return 0
    fi

    debug_exit 1
    return 1
}

check_run_as_non_root() {
    debug_enter "Check RunAsNonRoot Policy"

    # Example check for pods with RunAsNonRoot policy
    local pods_without_security
    pods_without_security=$($KUBECTL_CMD get pods --all-namespaces -o json 2>/dev/null | \
        jq -r '.items[] | select(.spec.securityContext.runAsNonRoot != true) | "\(.metadata.namespace)/\(.metadata.name)"' || echo "")

    if [[ -n "$pods_without_security" ]]; then
        log_warning "The following pods do not enforce RunAsNonRoot policy: $pods_without_security"
        debug_exit 1
        return 1
    fi

    debug_exit 0
    return 0
}

# Main execution
main() {
    init_framework
    create_test_namespace

    run_pod_security

    cleanup_test_namespace
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
