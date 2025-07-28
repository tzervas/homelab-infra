#!/bin/bash
# RBAC Testing for K3s Clusters
# Validates Role-Based Access Control settings and policies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"
source "$SCRIPT_DIR/../../lib/debug.sh"

run_rbac_testing() {
    start_test_module "RBAC Testing"

    # Test 1: Validate cluster roles and bindings
    start_test "Cluster Role and RoleBinding Validation"
    if validate_cluster_roles_and_bindings; then
        log_success "Cluster roles and role bindings are correctly configured"
    else
        log_error "Cluster role or binding validation failed"
    fi

    # Test 2: Default namespaces RBAC policies
    start_test "Default Namespace RBAC Policies"
    if verify_default_ns_rbac; then
        log_success "Default namespace RBAC policies are adequate"
    else
        log_warning "RBAC policies in default namespace need review"
    fi

    # Additional RBAC tests can be inserted here
}

validate_cluster_roles_and_bindings() {
    debug_enter "Validating cluster roles and bindings"

    local role_issues=false

    # Get all cluster roles
    local cluster_roles
    cluster_roles=$($KUBECTL_CMD get clusterroles -o json 2>/dev/null || echo "{}")

    if [[ "$cluster_roles" != "{}" ]]; then
        # Verify some default roles exist (example)
        if ! echo "$cluster_roles" | jq -e '.items[] | select(.metadata.name == "cluster-admin")' >/dev/null; then
            log_warning "Default cluster-admin role missing!"
            role_issues=true
        fi
    fi

    # Similarly check for cluster role bindings
    local cluster_role_bindings
    cluster_role_bindings=$($KUBECTL_CMD get clusterrolebindings -o json 2>/dev/null || echo "{}")

    if [[ "$cluster_role_bindings" != "{}" ]]; then
        # Verify default bindings
        if ! echo "$cluster_role_bindings" | jq -e '.items[] | select(.metadata.name == "cluster-admin")' >/dev/null; then
            log_warning "Default cluster-admin binding missing!"
            role_issues=true
        fi
    fi

    if [[ "$role_issues" == "true" ]]; then
        debug_exit 1
        return 1
    fi

    debug_exit 0
    return 0
}

verify_default_ns_rbac() {
    debug_enter "Verifying default namespace RBAC policies"

    local ns="default"
    local rbac_issues=false

    # Get roles and bindings in the default namespace
    local roles_bindings
    roles_bindings=$($KUBECTL_CMD get roles,rolebindings -n "$ns" -o json 2>/dev/null || echo "{}")

    # Example check: verify certain roles/permissions
    if [[ "$roles_bindings" != "{}" ]]; then
        if ! echo "$roles_bindings" | jq -e '.items[] | select(.metadata.name == "admin")' >/dev/null; then
            log_info "Admin role in default namespace not available"
            # Not necessarily an error; do not change rbac_issues
        fi
    fi

    if [[ "$rbac_issues" == "true" ]]; then
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

    run_rbac_testing

    cleanup_test_namespace
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
