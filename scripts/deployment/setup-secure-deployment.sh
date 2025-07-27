#!/bin/bash
# Secure deployment setup script
# This script prepares the system for rootless deployment with proper credential management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_USER="${DEPLOYMENT_USER:-homelab-deploy}"
ADMIN_USER="${SUDO_USER:-${USER}}"
LOG_FILE="/var/log/homelab-secure-setup.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  echo "[$timestamp] [$level] $message" | sudo tee -a "$LOG_FILE" >/dev/null

  case "$level" in
    ERROR) echo -e "${RED}[$level]${NC} $message" >&2 ;;
    WARN) echo -e "${YELLOW}[$level]${NC} $message" ;;
    INFO) echo -e "${GREEN}[$level]${NC} $message" ;;
    DEBUG) [[ ${DEBUG:-false} == "true" ]] && echo -e "${BLUE}[$level]${NC} $message" ;;
  esac
}

# Function to check if running with appropriate privileges
check_initial_privileges() {
  log "INFO" "Checking initial setup privileges..."

  if [[ $EUID -eq 0 ]]; then
    log "INFO" "Running as root - this is required for initial setup"
    return 0
  fi

  if sudo -n true 2>/dev/null; then
    log "INFO" "Have sudo access - proceeding with setup"
    return 0
  fi

  log "ERROR" "This script requires sudo access for initial system setup"
  log "INFO" "Please run: sudo $0"
  exit 1
}

# Function to validate system requirements
validate_system_requirements() {
  log "INFO" "Validating system requirements..."

  # Check OS compatibility
  if [[ ! -f /etc/os-release ]]; then
    log "ERROR" "Cannot determine OS version"
    return 1
  fi

  source /etc/os-release
  case "$ID" in
    ubuntu | debian)
      log "INFO" "Detected compatible OS: $PRETTY_NAME"
      ;;
    *)
      log "WARN" "Untested OS: $PRETTY_NAME - proceeding with caution"
      ;;
  esac

  # Check required packages
  local required_packages=("sudo" "openssh-server" "curl" "wget" "git" "acl")
  local missing_packages=()

  for package in "${required_packages[@]}"; do
    if ! dpkg -l "$package" >/dev/null 2>&1; then
      missing_packages+=("$package")
    fi
  done

  if [[ ${#missing_packages[@]} -gt 0 ]]; then
    log "INFO" "Installing missing packages: ${missing_packages[*]}"
    apt update && apt install -y "${missing_packages[@]}"
  fi

  log "INFO" "System requirements validation completed"
}

# Function to create deployment user with secure configuration
create_deployment_user() {
  log "INFO" "Creating deployment user: $DEPLOYMENT_USER"

  # Check if user already exists
  if id "$DEPLOYMENT_USER" >/dev/null 2>&1; then
    log "WARN" "User $DEPLOYMENT_USER already exists - updating configuration"
  else
    # Create user with secure defaults
    useradd \
      --create-home \
      --shell /bin/bash \
      --uid 1001 \
      --comment "Homelab Deployment User" \
      "$DEPLOYMENT_USER"

    log "INFO" "Created user: $DEPLOYMENT_USER"
  fi

  # Set up groups
  usermod -aG docker "$DEPLOYMENT_USER" 2>/dev/null || log "WARN" "Docker group not found - will create later"

  # Create required directories
  local user_home="/home/$DEPLOYMENT_USER"
  local required_dirs=(
    "$user_home/.ssh"
    "$user_home/.kube"
    "$user_home/.local/bin"
    "$user_home/.local/log"
    "$user_home/.cache/helm"
    "$user_home/.config/helm"
    "$user_home/.local/share/helm"
  )

  for dir in "${required_dirs[@]}"; do
    mkdir -p "$dir"
    chown "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$dir"
    chmod 755 "$dir"
  done

  # Set restrictive permissions on .ssh
  chmod 700 "$user_home/.ssh"

  log "INFO" "Deployment user configuration completed"
}

# Function to configure SSH access
configure_ssh_access() {
  log "INFO" "Configuring SSH access for deployment user..."

  local user_home="/home/$DEPLOYMENT_USER"
  local ssh_dir="$user_home/.ssh"
  local authorized_keys="$ssh_dir/authorized_keys"

  # Generate SSH key for deployment user if it doesn't exist
  if [[ ! -f "$ssh_dir/id_ed25519" ]]; then
    sudo -u "$DEPLOYMENT_USER" ssh-keygen \
      -t ed25519 \
      -f "$ssh_dir/id_ed25519" \
      -N "" \
      -C "${DEPLOYMENT_USER}@$(hostname)"

    log "INFO" "Generated SSH key for $DEPLOYMENT_USER"
  fi

  # Copy authorized keys from admin user if they exist
  local admin_home
  admin_home=$(getent passwd "$ADMIN_USER" | cut -d: -f6)

  if [[ -f "$admin_home/.ssh/authorized_keys" ]]; then
    cp "$admin_home/.ssh/authorized_keys" "$authorized_keys"
    chown "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$authorized_keys"
    chmod 600 "$authorized_keys"
    log "INFO" "Copied SSH keys from $ADMIN_USER to $DEPLOYMENT_USER"
  else
    log "WARN" "No SSH keys found for $ADMIN_USER - manual SSH key setup required"
  fi

  # Configure SSH daemon for security
  local sshd_config="/etc/ssh/sshd_config"
  local sshd_backup="/etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"

  # Backup original config
  cp "$sshd_config" "$sshd_backup"

  # Apply security hardening
  cat >>"$sshd_config" <<EOF

# Homelab deployment security settings
# Generated by homelab setup script
Match User $DEPLOYMENT_USER
    PubkeyAuthentication yes
    PasswordAuthentication no
    PermitRootLogin no
    X11Forwarding no
    AllowTcpForwarding yes
    AllowAgentForwarding no
    ForceCommand none
EOF

  # Validate SSH configuration
  if sshd -t; then
    log "INFO" "SSH configuration validated successfully"
    systemctl reload sshd
  else
    log "ERROR" "SSH configuration validation failed - restoring backup"
    cp "$sshd_backup" "$sshd_config"
    return 1
  fi

  log "INFO" "SSH access configuration completed"
}

# Function to configure secure sudo access
configure_sudo_access() {
  log "INFO" "Configuring secure sudo access for deployment user..."

  local sudoers_file="/etc/sudoers.d/$DEPLOYMENT_USER"
  local sudoers_temp="/tmp/sudoers.$DEPLOYMENT_USER.$$"

  # Create sudoers configuration
  cat >"$sudoers_temp" <<EOF
# Sudoers configuration for $DEPLOYMENT_USER
# This file grants specific passwordless sudo permissions for homelab deployment
# Generated by homelab setup script - DO NOT EDIT MANUALLY

# User specification for $DEPLOYMENT_USER
# Allow passwordless sudo only for specific required commands

# Systemd service management for K3s
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl start k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl enable k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl disable k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl status k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload

# Package management (limited to specific packages)
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/apt update
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/apt install curl wget git
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/snap install kubectl helm
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/snap refresh kubectl helm

# File operations in system directories
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/mkdir -p /etc/rancher/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/mkdir -p /var/lib/rancher/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/chown $DEPLOYMENT_USER\\:$DEPLOYMENT_USER /etc/rancher/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/chown $DEPLOYMENT_USER\\:$DEPLOYMENT_USER /var/lib/rancher/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/chmod 755 /etc/rancher/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /bin/chmod 755 /var/lib/rancher/k3s*

# K3s specific commands
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/local/bin/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /opt/bin/k3s*
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/k3s*

# Docker operations
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/docker system prune -f
$DEPLOYMENT_USER ALL=(ALL) NOPASSWD: /usr/bin/docker volume prune -f

# Environment preservation and security settings
Defaults:$DEPLOYMENT_USER env_keep += "PATH HOME KUBECONFIG HOMELAB_USER HOMELAB_HOME"
Defaults:$DEPLOYMENT_USER !requiretty
Defaults:$DEPLOYMENT_USER timestamp_timeout=5
Defaults:$DEPLOYMENT_USER passwd_tries=3

# Audit logging
Defaults:$DEPLOYMENT_USER log_input, log_output
Defaults:$DEPLOYMENT_USER iolog_dir=/var/log/sudo-io/$DEPLOYMENT_USER
EOF

  # Validate sudoers syntax
  if visudo -cf "$sudoers_temp"; then
    mv "$sudoers_temp" "$sudoers_file"
    chmod 440 "$sudoers_file"
    log "INFO" "Sudoers configuration created and validated"
  else
    log "ERROR" "Sudoers syntax validation failed"
    rm -f "$sudoers_temp"
    return 1
  fi

  # Create sudo log directory
  mkdir -p "/var/log/sudo-io/$DEPLOYMENT_USER"
  chown root:root "/var/log/sudo-io/$DEPLOYMENT_USER"
  chmod 750 "/var/log/sudo-io/$DEPLOYMENT_USER"

  # Test sudo configuration
  if sudo -u "$DEPLOYMENT_USER" sudo -n -l >/dev/null 2>&1; then
    log "INFO" "Sudo configuration test passed"
  else
    log "WARN" "Sudo configuration test failed - manual verification required"
  fi

  log "INFO" "Secure sudo access configuration completed"
}

# Function to configure Docker for rootless operation
configure_docker_rootless() {
  log "INFO" "Configuring Docker for rootless operation..."

  # Install Docker if not present
  if ! command -v docker >/dev/null 2>&1; then
    log "INFO" "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
  fi

  # Create docker group if it doesn't exist
  groupadd -f docker

  # Add deployment user to docker group
  usermod -aG docker "$DEPLOYMENT_USER"

  # Enable Docker service
  systemctl enable docker
  systemctl start docker

  # Test Docker access for deployment user
  if sudo -u "$DEPLOYMENT_USER" docker ps >/dev/null 2>&1; then
    log "INFO" "Docker access verified for $DEPLOYMENT_USER"
  else
    log "WARN" "Docker access test failed - user may need to log out and back in"
  fi

  log "INFO" "Docker rootless configuration completed"
}

# Function to set up credential management
setup_credential_management() {
  log "INFO" "Setting up credential management..."

  local user_home="/home/$DEPLOYMENT_USER"
  local credentials_dir="$user_home/.credentials"

  # Create secure credentials directory
  mkdir -p "$credentials_dir"
  chown "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$credentials_dir"
  chmod 700 "$credentials_dir"

  # Create environment file template
  cat >"$user_home/.environment" <<EOF
# Environment configuration for $DEPLOYMENT_USER
# Generated by homelab setup script

# User and deployment configuration
export HOMELAB_USER="$DEPLOYMENT_USER"
export HOMELAB_HOME="$user_home"
export HOMELAB_DEPLOYMENT_MODE="rootless"

# Kubernetes configuration
export KUBECONFIG="\$HOME/.kube/config"
export KUBECTL_EXTERNAL_DIFF="diff -u"

# Helm configuration
export HELM_CACHE_HOME="\$HOME/.cache/helm"
export HELM_CONFIG_HOME="\$HOME/.config/helm"
export HELM_DATA_HOME="\$HOME/.local/share/helm"

# Docker configuration
export DOCKER_HOST="unix://\$HOME/.docker/desktop/docker.sock"

# Ansible configuration
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_STDOUT_CALLBACK=yaml
export ANSIBLE_STDERR_CALLBACK=yaml

# Path configuration
export PATH="\$HOME/.local/bin:/usr/local/bin:\$PATH"
EOF

  chown "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$user_home/.environment"
  chmod 600 "$user_home/.environment"

  # Update .bashrc to source environment
  if ! grep -q "source.*\.environment" "$user_home/.bashrc"; then
    echo 'source $HOME/.environment' >>"$user_home/.bashrc"
    chown "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$user_home/.bashrc"
  fi

  # Create credential template files
  cat >"$credentials_dir/README.md" <<EOF
# Credentials Directory

This directory contains credential templates and configuration files for the homelab deployment.

## Security Notes

- All files in this directory should have restrictive permissions (600 or 700)
- Never commit actual credentials to version control
- Use environment variables or encrypted secrets management where possible
- Rotate credentials regularly

## Files

- \`.env.template\` - Environment variable template
- \`ssh-config.template\` - SSH configuration template
- \`kubeconfig.template\` - Kubernetes configuration template

## Usage

1. Copy template files and remove the \`.template\` extension
2. Fill in actual values
3. Ensure proper file permissions: \`chmod 600 <file>\`
EOF

  # Create environment template
  cat >"$credentials_dir/.env.template" <<EOF
# Environment variables for homelab deployment
# Copy to .env and fill in actual values

# Homelab configuration
HOMELAB_DOMAIN=homelab.local
HOMELAB_DEV_DOMAIN=dev.homelab.local

# Network configuration
METALLB_IP_RANGE=192.168.16.200-192.168.16.220
GITLAB_IP=192.168.16.201
KEYCLOAK_IP=192.168.16.202
PROMETHEUS_IP=192.168.16.204
GRAFANA_IP=192.168.16.205

# Database passwords (generate strong passwords)
GITLAB_DB_PASSWORD=
KEYCLOAK_DB_PASSWORD=
PROMETHEUS_DB_PASSWORD=

# Admin passwords (generate strong passwords)
GITLAB_ROOT_PASSWORD=
GRAFANA_ADMIN_PASSWORD=
KEYCLOAK_ADMIN_PASSWORD=

# TLS configuration
TLS_EMAIL=tz-dev@vectorweight.com
EOF

  chown -R "$DEPLOYMENT_USER:$DEPLOYMENT_USER" "$credentials_dir"
  chmod -R 600 "$credentials_dir"/*

  log "INFO" "Credential management setup completed"
}

# Function to verify security configuration
verify_security_configuration() {
  log "INFO" "Verifying security configuration..."

  local errors=0

  # Check user configuration
  if id "$DEPLOYMENT_USER" >/dev/null 2>&1; then
    log "INFO" "✓ Deployment user exists"
  else
    log "ERROR" "✗ Deployment user does not exist"
    ((errors++))
  fi

  # Check sudo configuration
  if [[ -f "/etc/sudoers.d/$DEPLOYMENT_USER" ]]; then
    log "INFO" "✓ Sudoers configuration exists"
    if visudo -cf "/etc/sudoers.d/$DEPLOYMENT_USER"; then
      log "INFO" "✓ Sudoers syntax is valid"
    else
      log "ERROR" "✗ Sudoers syntax is invalid"
      ((errors++))
    fi
  else
    log "ERROR" "✗ Sudoers configuration missing"
    ((errors++))
  fi

  # Check SSH configuration
  local user_home="/home/$DEPLOYMENT_USER"
  if [[ -f "$user_home/.ssh/authorized_keys" ]]; then
    log "INFO" "✓ SSH authorized_keys configured"
  else
    log "WARN" "⚠ SSH authorized_keys not configured"
  fi

  # Check file permissions
  local permission_checks=(
    "$user_home/.ssh:700"
    "$user_home/.credentials:700"
    "$user_home/.environment:600"
  )

  for check in "${permission_checks[@]}"; do
    local path="${check%:*}"
    local expected_perm="${check#*:}"

    if [[ -e $path ]]; then
      local actual_perm=$(stat -c "%a" "$path")
      if [[ $actual_perm == "$expected_perm" ]]; then
        log "INFO" "✓ Correct permissions on $path ($actual_perm)"
      else
        log "WARN" "⚠ Incorrect permissions on $path (expected $expected_perm, got $actual_perm)"
      fi
    fi
  done

  # Check Docker access
  if sudo -u "$DEPLOYMENT_USER" docker ps >/dev/null 2>&1; then
    log "INFO" "✓ Docker access verified"
  else
    log "WARN" "⚠ Docker access not verified"
  fi

  if [[ $errors -eq 0 ]]; then
    log "INFO" "Security configuration verification completed successfully"
    return 0
  else
    log "ERROR" "Security configuration verification failed with $errors errors"
    return 1
  fi
}

# Function to show usage
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Set up secure deployment environment for homelab infrastructure.

OPTIONS:
    -h, --help          Show this help message
    -u, --user USER     Specify deployment user (default: $DEPLOYMENT_USER)
    -d, --debug         Enable debug output
    --skip-docker       Skip Docker configuration
    --skip-ssh          Skip SSH configuration
    --verify-only       Only run verification checks

This script must be run with sudo privileges for initial system setup.

EXAMPLES:
    sudo $0                    # Full setup with default user
    sudo $0 -u deploy-user     # Setup with custom user
    sudo $0 --verify-only      # Only run verification checks

EOF
}

# Main function
main() {
  local skip_docker=false
  local skip_ssh=false
  local verify_only=false

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      -h | --help)
        usage
        exit 0
        ;;
      -u | --user)
        DEPLOYMENT_USER="$2"
        shift 2
        ;;
      -d | --debug)
        export DEBUG=true
        shift
        ;;
      --skip-docker)
        skip_docker=true
        shift
        ;;
      --skip-ssh)
        skip_ssh=true
        shift
        ;;
      --verify-only)
        verify_only=true
        shift
        ;;
      *)
        log "ERROR" "Unknown argument: $1"
        usage
        exit 1
        ;;
    esac
  done

  log "INFO" "Starting secure deployment setup for user: $DEPLOYMENT_USER"

  # Check initial privileges
  check_initial_privileges

  if [[ $verify_only == "true" ]]; then
    verify_security_configuration
    exit $?
  fi

  # Run setup steps
  validate_system_requirements
  create_deployment_user

  if [[ $skip_ssh != "true" ]]; then
    configure_ssh_access
  fi

  configure_sudo_access

  if [[ $skip_docker != "true" ]]; then
    configure_docker_rootless
  fi

  setup_credential_management

  # Final verification
  verify_security_configuration

  log "INFO" "Secure deployment setup completed successfully"
  log "INFO" "Next steps:"
  log "INFO" "1. Log out and log back in as $DEPLOYMENT_USER"
  log "INFO" "2. Configure credentials in /home/$DEPLOYMENT_USER/.credentials/"
  log "INFO" "3. Run deployment scripts as $DEPLOYMENT_USER"
  log "INFO" "4. Use './scripts/deployment/deploy-with-privileges.sh check' to verify setup"
}

# Execute main function
main "$@"
