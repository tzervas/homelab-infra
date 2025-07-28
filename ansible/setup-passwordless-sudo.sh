#!/bin/bash

set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly USERNAME="${1:-kang}"
readonly SUDOERS_FILE="/etc/sudoers.d/${USERNAME}-ansible"
readonly SUDOERS_BACKUP="/etc/sudoers.d/.${USERNAME}-ansible.bak"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    log "ERROR: $*"
    exit 1
}

validate_environment() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi

    if ! command -v visudo >/dev/null 2>&1; then
        error "visudo command not found. Please install sudo package."
    fi

    if ! id "$USERNAME" >/dev/null 2>&1; then
        error "User '$USERNAME' does not exist"
    fi
}

backup_existing_config() {
    if [[ -f "$SUDOERS_FILE" ]]; then
        log "Backing up existing sudoers file to $SUDOERS_BACKUP"
        cp "$SUDOERS_FILE" "$SUDOERS_BACKUP" || error "Failed to backup existing sudoers file"
    fi
}

create_sudoers_config() {
    log "Creating sudoers configuration for user '$USERNAME'"
    
    cat > "$SUDOERS_FILE" << EOF
# Sudoers configuration for $USERNAME - Ansible automation
# Created by $SCRIPT_NAME on $(date)
# This file allows passwordless sudo for ALL commands needed by Ansible
# Appropriate for homelab automation environment

$USERNAME ALL=(ALL) NOPASSWD: ALL
EOF
}

validate_sudoers_syntax() {
    log "Validating sudoers syntax"
    if ! visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
        error "Sudoers syntax validation failed. Restoring backup if available."
        if [[ -f "$SUDOERS_BACKUP" ]]; then
            mv "$SUDOERS_BACKUP" "$SUDOERS_FILE"
            log "Restored backup configuration"
        else
            rm -f "$SUDOERS_FILE"
            log "Removed invalid configuration file"
        fi
        exit 1
    fi
    log "Sudoers syntax validation passed"
}

set_file_permissions() {
    log "Setting appropriate file permissions"
    chmod 440 "$SUDOERS_FILE" || error "Failed to set permissions on sudoers file"
    chown root:root "$SUDOERS_FILE" || error "Failed to set ownership on sudoers file"
}

test_sudo_access() {
    log "Testing sudo access for user '$USERNAME'"
    if sudo -u "$USERNAME" sudo -n -l >/dev/null 2>&1; then
        log "Sudo access test successful"
    else
        log "WARNING: Sudo access test failed. Configuration may not be working correctly."
    fi
}

cleanup() {
    if [[ -f "$SUDOERS_BACKUP" ]]; then
        log "Cleaning up backup file"
        rm -f "$SUDOERS_BACKUP"
    fi
}

check_existing_config() {
    if [[ -f "$SUDOERS_FILE" ]]; then
        local existing_checksum backup_checksum
        existing_checksum=$(sha256sum "$SUDOERS_FILE" | cut -d' ' -f1)
        
        create_sudoers_config
        local new_checksum
        new_checksum=$(sha256sum "$SUDOERS_FILE" | cut -d' ' -f1)
        
        if [[ "$existing_checksum" == "$new_checksum" ]]; then
            log "Configuration is already up to date. No changes needed."
            return 0
        else
            log "Configuration has changed. Updating..."
            return 1
        fi
    fi
    return 1
}

main() {
    log "Starting passwordless sudo setup for user '$USERNAME'"
    
    validate_environment
    
    if check_existing_config; then
        log "Setup completed successfully (no changes needed)"
        exit 0
    fi
    
    backup_existing_config
    create_sudoers_config
    validate_sudoers_syntax
    set_file_permissions
    test_sudo_access
    cleanup
    
    log "Passwordless sudo setup completed successfully for user '$USERNAME'"
    log "Sudoers file created: $SUDOERS_FILE"
    log "User '$USERNAME' can now run ALL commands without password"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi