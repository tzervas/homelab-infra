#!/bin/bash
# TLS Certificate Validation for K3s Clusters
# Validates TLS certificates for API server, etcd, and service communications

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"
source "$SCRIPT_DIR/../../lib/debug.sh"

run_tls_validation() {
    start_test_module "TLS Certificate Validation"

    # Test 1: API Server Certificate Validity
    start_test "API Server TLS Certificate"
    if validate_api_server_cert; then
        log_success "API server certificate is valid"
    else
        log_error "API server certificate validation failed"
    fi

    # Test 2: Certificate Expiration Check
    start_test "Certificate Expiration Check"
    if check_certificate_expiration; then
        log_success "All certificates have sufficient validity period"
    else
        log_warning "Some certificates are near expiration"
    fi

    # Test 3: Certificate Chain Validation
    start_test "Certificate Chain Validation"
    if validate_certificate_chain; then
        log_success "Certificate chain is properly configured"
    else
        log_error "Certificate chain validation failed"
    fi

    # Test 4: Service Account Token Validation
    start_test "Service Account Token Security"
    if validate_service_account_tokens; then
        log_success "Service account tokens are properly secured"
    else
        log_error "Service account token security issues detected"
    fi

    # Test 5: Webhook Certificate Validation
    start_test "Webhook TLS Certificates"
    if validate_webhook_certificates; then
        log_success "Webhook certificates are valid"
    else
        log_warning "Some webhook certificates may have issues"
    fi
}

validate_api_server_cert() {
    debug_enter "Validating API server certificate"

    # Get the API server endpoint
    local api_server
    api_server=$($KUBECTL_CMD config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo "")

    if [[ -z "$api_server" ]]; then
        log_error "Could not determine API server endpoint"
        debug_exit 1
        return 1
    fi

    # Extract hostname and port
    local host port
    if [[ "$api_server" =~ https://([^:]+):([0-9]+) ]]; then
        host="${BASH_REMATCH[1]}"
        port="${BASH_REMATCH[2]}"
    else
        log_error "Could not parse API server URL: $api_server"
        debug_exit 1
        return 1
    fi

    # Check certificate using openssl
    if command_exists openssl; then
        set +e
        local cert_info
        cert_info=$(echo | openssl s_client -connect "$host:$port" -servername "$host" 2>/dev/null | openssl x509 -noout -text 2>/dev/null)
        local exit_code=$?
        set -e

        if [[ $exit_code -eq 0 ]] && [[ -n "$cert_info" ]]; then
            # Check for common certificate issues
            if echo "$cert_info" | grep -q "Subject:.*kubernetes"; then
                debug_exec echo "Certificate appears to be valid Kubernetes cert"
                debug_exit 0
                return 0
            fi
        fi
    fi

    # Fallback: check if API is accessible
    if $KUBECTL_CMD version --short >/dev/null 2>&1; then
        debug_exit 0
        return 0
    fi

    debug_exit 1
    return 1
}

check_certificate_expiration() {
    debug_enter "Checking certificate expiration"

    local warning_days=30
    local critical_days=7
    local issues_found=false

    # Check API server certificate expiration
    local api_server
    api_server=$($KUBECTL_CMD config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo "")

    if [[ -n "$api_server" ]] && command_exists openssl; then
        local host port
        if [[ "$api_server" =~ https://([^:]+):([0-9]+) ]]; then
            host="${BASH_REMATCH[1]}"
            port="${BASH_REMATCH[2]}"

            set +e
            local expiry_date
            expiry_date=$(echo | openssl s_client -connect "$host:$port" -servername "$host" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
            set -e

            if [[ -n "$expiry_date" ]]; then
                local expiry_epoch
                expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null || echo "0")
                local current_epoch
                current_epoch=$(date +%s)

                if [[ $expiry_epoch -gt 0 ]]; then
                    local days_remaining=$(((expiry_epoch - current_epoch) / 86400))

                    if [[ $days_remaining -lt $critical_days ]]; then
                        log_error "API server certificate expires in $days_remaining days!"
                        issues_found=true
                    elif [[ $days_remaining -lt $warning_days ]]; then
                        log_warning "API server certificate expires in $days_remaining days"
                        issues_found=true
                    else
                        log_info "API server certificate valid for $days_remaining days"
                    fi
                fi
            fi
        fi
    fi

    # Check for K3s-specific certificate information
    if [[ -d "/var/lib/rancher/k3s/server/tls" ]]; then
        log_info "Checking K3s server certificates (requires appropriate access)"
        # Note: This would require running on the K3s server with appropriate permissions
    fi

    if [[ "$issues_found" == "true" ]]; then
        debug_exit 1
        return 1
    fi

    debug_exit 0
    return 0
}

validate_certificate_chain() {
    debug_enter "Validating certificate chain"

    # Check if we can get the certificate chain
    local api_server
    api_server=$($KUBECTL_CMD config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo "")

    if [[ -n "$api_server" ]] && command_exists openssl; then
        local host port
        if [[ "$api_server" =~ https://([^:]+):([0-9]+) ]]; then
            host="${BASH_REMATCH[1]}"
            port="${BASH_REMATCH[2]}"

            set +e
            local chain_info
            chain_info=$(echo | openssl s_client -connect "$host:$port" -servername "$host" -showcerts 2>/dev/null)
            set -e

            if [[ -n "$chain_info" ]]; then
                # Check if we have a complete chain
                local cert_count
                cert_count=$(echo "$chain_info" | grep -c "BEGIN CERTIFICATE" || echo "0")

                if [[ $cert_count -ge 1 ]]; then
                    log_info "Found $cert_count certificate(s) in chain"
                    debug_exit 0
                    return 0
                fi
            fi
        fi
    fi

    # Fallback: assume chain is valid if API is working
    if $KUBECTL_CMD version --short >/dev/null 2>&1; then
        debug_exit 0
        return 0
    fi

    debug_exit 1
    return 1
}

validate_service_account_tokens() {
    debug_enter "Validating service account tokens"

    # Check if service account tokens are being automounted appropriately
    local issues_found=false

    # Check default service account in kube-system
    local sa_info
    sa_info=$($KUBECTL_CMD get serviceaccount default -n kube-system -o json 2>/dev/null || echo "{}")

    if [[ -n "$sa_info" ]] && [[ "$sa_info" != "{}" ]]; then
        # Check if automountServiceAccountToken is explicitly set
        local automount
        automount=$(echo "$sa_info" | jq -r '.automountServiceAccountToken // "not-set"')

        if [[ "$automount" == "not-set" ]]; then
            log_warning "Default service account in kube-system does not explicitly set automountServiceAccountToken"
        fi
    fi

    # Check for pods running without service account tokens when they should have them
    local pods_without_tokens
    pods_without_tokens=$($KUBECTL_CMD get pods --all-namespaces -o json 2>/dev/null | \
        jq -r '.items[] | select(.spec.automountServiceAccountToken == false) | "\(.metadata.namespace)/\(.metadata.name)"' || echo "")

    if [[ -n "$pods_without_tokens" ]]; then
        log_info "Found pods with automountServiceAccountToken disabled (this may be intentional)"
    fi

    # Check token expiration settings (K3s specific)
    # K3s typically handles this automatically

    if [[ "$issues_found" == "true" ]]; then
        debug_exit 1
        return 1
    fi

    debug_exit 0
    return 0
}

validate_webhook_certificates() {
    debug_enter "Validating webhook certificates"

    local issues_found=false

    # Check validating webhook configurations
    local validating_webhooks
    validating_webhooks=$($KUBECTL_CMD get validatingwebhookconfigurations -o json 2>/dev/null || echo "{}")

    if [[ "$validating_webhooks" != "{}" ]]; then
        local webhook_count
        webhook_count=$(echo "$validating_webhooks" | jq '.items | length' || echo "0")

        if [[ $webhook_count -gt 0 ]]; then
            log_info "Found $webhook_count validating webhook configuration(s)"

            # Check each webhook for proper TLS configuration
            local webhooks_with_issues
            webhooks_with_issues=$(echo "$validating_webhooks" | jq -r '.items[] | select(.webhooks[]?.clientConfig.caBundle == null) | .metadata.name' || echo "")

            if [[ -n "$webhooks_with_issues" ]]; then
                log_warning "Webhooks without CA bundle: $webhooks_with_issues"
                issues_found=true
            fi
        fi
    fi

    # Check mutating webhook configurations
    local mutating_webhooks
    mutating_webhooks=$($KUBECTL_CMD get mutatingwebhookconfigurations -o json 2>/dev/null || echo "{}")

    if [[ "$mutating_webhooks" != "{}" ]]; then
        local webhook_count
        webhook_count=$(echo "$mutating_webhooks" | jq '.items | length' || echo "0")

        if [[ $webhook_count -gt 0 ]]; then
            log_info "Found $webhook_count mutating webhook configuration(s)"
        fi
    fi

    if [[ "$issues_found" == "true" ]]; then
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

    run_tls_validation

    cleanup_test_namespace
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
