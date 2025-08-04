#!/bin/bash
# Security Secret Generation Script
# Generates secure random secrets for OAuth2 and other authentication components

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
readonly ENV_FILE="$PROJECT_ROOT/.env"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    log "ERROR: $*"
    exit 1
}

generate_random_string() {
    local length="${1:-32}"
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

generate_base64_secret() {
    local length="${1:-32}"
    openssl rand -base64 "$length"
}

generate_oauth2_secrets() {
    log "Generating OAuth2 authentication secrets..."

    # Generate OAuth2 client secrets (base64 encoded random strings)
    local oauth2_client_secret
    oauth2_client_secret=$(generate_base64_secret 24)

    local oauth2_cookie_secret
    oauth2_cookie_secret=$(generate_base64_secret 32)

    local prometheus_client_secret
    prometheus_client_secret=$(generate_base64_secret 24)

    local prometheus_cookie_secret
    prometheus_cookie_secret=$(generate_base64_secret 32)

    # Generate Grafana admin password
    local grafana_password
    grafana_password=$(generate_random_string 16)

    # Generate Longhorn backup secret
    local longhorn_secret
    longhorn_secret=$(generate_random_string 32)

    cat > "$ENV_FILE" <<EOF
# Homelab Infrastructure Environment Configuration
# Generated on $(date)
# IMPORTANT: Keep this file secure and never commit to version control

# SECURITY CONFIGURATION - REQUIRED FOR PRODUCTION
# OAuth2 Authentication Secrets (base64 encoded values)
OAUTH2_CLIENT_SECRET=$oauth2_client_secret
OAUTH2_COOKIE_SECRET=$oauth2_cookie_secret
PROMETHEUS_OAUTH2_CLIENT_SECRET=$prometheus_client_secret
PROMETHEUS_OAUTH2_COOKIE_SECRET=$prometheus_cookie_secret

# Grafana Admin Password
GRAFANA_ADMIN_PASSWORD=$grafana_password

# Prometheus Retention (optional)
PROMETHEUS_RETENTION_DAYS=30

# Storage Sizes (optional)
PROMETHEUS_STORAGE_SIZE=50Gi
LOKI_STORAGE_SIZE=20Gi
GRAFANA_STORAGE_SIZE=10Gi

# Longhorn Settings (optional)
LONGHORN_REPLICA_COUNT=3
LONGHORN_BACKUP_TARGET=
LONGHORN_BACKUP_SECRET=$longhorn_secret

# Additional Settings
ENVIRONMENT=development  # development, staging, or production
DEBUG=false

# Domain Configuration
HOMELAB_DOMAIN=homelab.local

# TLS/SSL Certificate Configuration
TLS_CERT_EMAIL=admin@homelab.local
ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory
CERT_EXPIRY_WEBHOOK_URL=

# Custom CA Configuration (optional - leave empty for Let's Encrypt/self-signed)
CUSTOM_CA_CERT=
CUSTOM_CA_KEY=
EOF

    # Secure the file
    chmod 600 "$ENV_FILE"

    log "✅ Secrets generated successfully!"
    log "📄 Configuration saved to: $ENV_FILE"
    log "🔒 File permissions set to 600 (owner read/write only)"
    log ""
    log "IMPORTANT SECURITY NOTES:"
    log "1. Never commit the .env file to version control"
    log "2. Back up these secrets securely"
    log "3. Rotate secrets regularly in production"
    log "4. Use a proper secret management system for production deployments"
}

main() {
    log "Starting secure secret generation for homelab infrastructure..."

    # Check if .env already exists
    if [[ -f "$ENV_FILE" ]]; then
        log "⚠️  .env file already exists: $ENV_FILE"
        read -p "Do you want to overwrite it? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Aborted. Existing .env file preserved."
            exit 0
        fi
    fi

    # Check for required tools
    if ! command -v openssl >/dev/null 2>&1; then
        error "openssl is required but not installed"
    fi

    generate_oauth2_secrets

    log "🎉 Secret generation completed successfully!"
    log "Next steps:"
    log "1. Review the generated .env file"
    log "2. Deploy infrastructure: python -m homelab_orchestrator deploy infrastructure"
    log "3. Verify authentication is working properly"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
