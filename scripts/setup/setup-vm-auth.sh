#!/bin/bash
# Script to set up SSH authentication for homelab test VMs
# This ensures consistent authentication setup across VM deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  source "$PROJECT_ROOT/.env"
fi

# Configuration
VM_USER="${HOMELAB_TEST_VM_USER:-kang}"
VM_SSH_KEY_PATH="${HOMELAB_TEST_VM_SSH_KEY_PATH:-~/.ssh/homelab-test-vm-key}"
VM_SSH_KEY_PATH=$(eval echo "$VM_SSH_KEY_PATH")  # Expand tilde
HOMELAB_SERVER="${HOMELAB_SERVER_IP:-192.168.16.26}"
HOMELAB_USER="${HOMELAB_SSH_USER:-kang}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate SSH key if it doesn't exist
generate_ssh_key() {
  if [[ ! -f "$VM_SSH_KEY_PATH" ]]; then
    log_info "Generating new SSH key for VM authentication..."
    ssh-keygen -t ed25519 -f "$VM_SSH_KEY_PATH" -N "" -C "homelab-test-vm@homelab"
    log_success "SSH key generated at: $VM_SSH_KEY_PATH"
  else
    log_info "SSH key already exists at: $VM_SSH_KEY_PATH"
  fi
}

# Function to add SSH key to VM
add_key_to_vm() {
  local vm_ip="$1"

  log_info "Adding SSH key to VM at $vm_ip..."

  # Check if we can already authenticate with the key
  if ssh -i "$VM_SSH_KEY_PATH" -o ConnectTimeout=5 -o BatchMode=yes \
       -o ProxyJump="${HOMELAB_USER}@${HOMELAB_SERVER}" \
       -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
       "${VM_USER}@${vm_ip}" "echo 'Key already authorized'" 2>/dev/null; then
    log_success "SSH key is already authorized on VM"
    return 0
  fi

  # Try to add the key
  if ssh-copy-id -i "${VM_SSH_KEY_PATH}.pub" \
       -o ProxyJump="${HOMELAB_USER}@${HOMELAB_SERVER}" \
       "${VM_USER}@${vm_ip}"; then
    log_success "SSH key added to VM successfully"
  else
    log_error "Failed to add SSH key to VM"
    return 1
  fi
}

# Function to update SSH config
update_ssh_config() {
  local vm_ip="$1"
  local vm_name="${2:-homelab-test-vm}"

  log_info "Updating SSH config for $vm_name..."

  # Check if entry already exists
  if grep -q "Host $vm_name" ~/.ssh/config 2>/dev/null; then
    log_info "SSH config entry for $vm_name already exists, updating..."
    # Remove old entry
    sed -i "/# Homelab Test VM Configuration - $vm_name/,/^$/d" ~/.ssh/config 2>/dev/null || true
    sed -i "/Host $vm_name/,/^$/d" ~/.ssh/config 2>/dev/null || true
  fi

  # Add new entry
  cat >> ~/.ssh/config << EOF

# Homelab Test VM Configuration - $vm_name
Host $vm_name
  HostName $vm_ip
  User $VM_USER
  IdentityFile $VM_SSH_KEY_PATH
  ProxyJump ${HOMELAB_USER}@${HOMELAB_SERVER}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ServerAliveInterval 60
  ServerAliveCountMax 3
EOF

  log_success "SSH config updated for $vm_name"
}

# Function to test SSH connectivity
test_ssh_connection() {
  local vm_ip="$1"
  local vm_name="${2:-homelab-test-vm}"

  log_info "Testing SSH connection to $vm_name..."

  if ssh -i "$VM_SSH_KEY_PATH" "$vm_name" "echo 'SSH test successful' && hostname" 2>/dev/null; then
    log_success "SSH connection to $vm_name successful!"
    return 0
  else
    log_error "SSH connection to $vm_name failed"
    return 1
  fi
}

# Main function
main() {
  local vm_ip="${1}"
  local vm_name="${2:-homelab-test-vm}"

  if [[ -z "$vm_ip" ]]; then
    # Try to get VM IP from virsh
    log_info "No VM IP provided, attempting to get from virsh..."
    vm_ip=$(ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" \
            "virsh -c qemu:///system domifaddr ${vm_name} 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1")

    if [[ -z "$vm_ip" ]]; then
      log_error "Could not determine VM IP address"
      echo "Usage: $0 [VM_IP] [VM_NAME]"
      exit 1
    fi

    log_success "Found VM IP: $vm_ip"
  fi

  log_info "Setting up SSH authentication for VM: $vm_name ($vm_ip)"

  # Generate SSH key if needed
  generate_ssh_key

  # Add key to VM
  add_key_to_vm "$vm_ip"

  # Update SSH config
  update_ssh_config "$vm_ip" "$vm_name"

  # Test connection
  if test_ssh_connection "$vm_ip" "$vm_name"; then
    log_success "VM authentication setup complete!"
    echo
    echo "You can now connect to the VM using:"
    echo "  ssh $vm_name"
    echo "  ssh -i $VM_SSH_KEY_PATH $vm_name"
  else
    log_error "Setup completed but connection test failed"
    exit 1
  fi
}

# Run main function
main "$@"
