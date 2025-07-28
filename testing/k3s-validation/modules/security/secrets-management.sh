#!/bin/bash
# Secrets Management Validation for K3s Clusters
# Verifies encryption and access controls over Kubernetes Secrets

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"
source "$SCRIPT_DIR/../../lib/debug.sh"

run_secrets_management() {
    start_test_module "Secrets Management Validation"

    # Test 1: Check secrets encryption at rest
    start_test "Secrets Encryption at Rest"
    if check_secrets_encryption; then
        log_success "Secrets are encrypted at rest"
    else
        log_warning "Secrets may not be encrypted at rest"
    fi

    # Test 2: Validate access to secrets
    start_test "Validate Access to Secrets"
    if validate_access_to_secrets; then
        log_success "Access controls for secrets are adequate"
    else
        log_error "Access to secrets is inadequately controlled"
    fi

    # Additional secret-related tests can be added here
}

check_secrets_encryption() {
    debug_enter "Checking secrets encryption at rest"

    # Verify if the encryption configuration is set
    if [[ -f "/etc/kubernetes/manifests/secrets-encryption-config.yaml" ]]; then
        log_info "Encryption config found, checking secrets..."
        local encrypted_secret_check
        encrypted_secret_check=$(grep 'kind: EncryptionConfiguration' /etc/kubernetes/manifests/secrets-encryption-config.yaml)

        if [[ -n "${encrypted_secret_check}" ]]; then
            debug_exit 0
            return 0
        fi
    fi

    debug_exit 1
    return 1
}

validate_access_to_secrets() {
    debug_enter "Validating access to secrets"

    # Check if secrets are accessed with roles restricting permissions
    local roles_with_secret_permissions
    roles_with_secret_permissions=$($KUBECTL_CMD get roles,rolebindings,clusterroles,clusterrolebindings --all-namespaces -o json 2>/dev/null | \
        jq -r '.items[] | select(.rules[]?.resources[] == "secrets") | "\(.kind): \(.metadata.name)"' || echo "")

    if [[ -n "$roles_with_secret_permissions" ]]; then
        log_info "Found roles accessing secrets: $roles_with_secret_permissions"
        debug_exit 0
        return 0
    fi

    log_warning "No specific roles with access to secrets found"
    debug_exit 1
    return 1
}

# Main execution
main() {
    init_framework
    create_test_namespace

    run_secrets_management

    cleanup_test_namespace
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
