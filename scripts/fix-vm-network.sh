#!/bin/bash
# Script to fix VM network connectivity and SSH access
# This ensures proper routing and SSH proxying through the homelab server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  source "$PROJECT_ROOT/.env"
fi

# Configuration
HOMELAB_SERVER="${HOMELAB_SERVER:-192.168.16.26}"
HOMELAB_USER="${HOMELAB_USER:-kang}"
VM_NAME="${VM_NAME:-homelab-test-vm}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if VM exists and is running
check_vm_status() {
  log_info "Checking VM status on homelab server..."

  local vm_status=$(ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" "virsh -c qemu:///system domstate ${VM_NAME} 2>/dev/null || echo 'not-found'")

  if [[ "$vm_status" == "not-found" ]]; then
    log_error "VM ${VM_NAME} not found on homelab server"
    return 1
  elif [[ "$vm_status" != "running" ]]; then
    log_warning "VM ${VM_NAME} is in state: $vm_status"
    log_info "Starting VM..."
    ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" "virsh -c qemu:///system start ${VM_NAME}"
    sleep 10
  else
    log_success "VM ${VM_NAME} is running"
  fi

  return 0
}

# Function to get VM IP address
get_vm_ip() {
  log_info "Getting VM IP address..."

  local max_attempts=30
  local attempt=0
  local vm_ip=""

  while [[ $attempt -lt $max_attempts ]]; do
    vm_ip=$(ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" "virsh -c qemu:///system domifaddr ${VM_NAME} 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1")

    if [[ -n "$vm_ip" ]]; then
      log_success "VM IP address: $vm_ip"
      echo "$vm_ip"
      return 0
    fi

    attempt=$((attempt + 1))
    log_info "Waiting for VM to get IP address (attempt $attempt/$max_attempts)..."
    sleep 5
  done

  log_error "Failed to get VM IP address after $max_attempts attempts"
  return 1
}

# Function to setup SSH config for VM access
setup_ssh_config() {
  local vm_ip="$1"

  log_info "Setting up SSH configuration for VM access..."

  # Create SSH config entry for VM
  local ssh_config_entry="
# Homelab Test VM Configuration
Host homelab-test-vm
  HostName $vm_ip
  User kang
  ProxyJump ${HOMELAB_USER}@${HOMELAB_SERVER}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ServerAliveInterval 60
  ServerAliveCountMax 3
"

  # Check if entry already exists
  if grep -q "Host homelab-test-vm" ~/.ssh/config 2>/dev/null; then
    log_info "Updating existing SSH config entry..."
    # Remove old entry
    sed -i '/# Homelab Test VM Configuration/,/^$/d' ~/.ssh/config 2>/dev/null || true
  fi

  # Add new entry
  echo "$ssh_config_entry" >> ~/.ssh/config

  log_success "SSH config updated. You can now access VM with: ssh homelab-test-vm"
}

# Function to test SSH connectivity through proxy
test_ssh_connectivity() {
  local vm_ip="$1"

  log_info "Testing SSH connectivity to VM through homelab server..."

  # First test if we can reach the homelab server
  if ! ssh -o ConnectTimeout=5 "${HOMELAB_USER}@${HOMELAB_SERVER}" "echo 'Homelab server reachable'" >/dev/null 2>&1; then
    log_error "Cannot connect to homelab server at ${HOMELAB_SERVER}"
    return 1
  fi

  log_success "Homelab server is reachable"

  # Test if homelab server can reach the VM
  log_info "Testing VM connectivity from homelab server..."
  if ! ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" "ping -c 1 -W 2 $vm_ip" >/dev/null 2>&1; then
    log_error "Homelab server cannot reach VM at $vm_ip"
    log_info "Checking libvirt network status..."
    ssh "${HOMELAB_USER}@${HOMELAB_SERVER}" "virsh -c qemu:///system net-list --all"
    return 1
  fi

  log_success "VM is reachable from homelab server"

  # Test SSH through proxy
  log_info "Testing SSH to VM through proxy jump..."
  local max_attempts=20
  local attempt=0

  while [[ $attempt -lt $max_attempts ]]; do
    if ssh -o ConnectTimeout=5 -o ProxyJump="${HOMELAB_USER}@${HOMELAB_SERVER}" \
         -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
         "kang@${vm_ip}" "echo 'SSH_TEST_SUCCESS'" 2>/dev/null | grep -q "SSH_TEST_SUCCESS"; then
      log_success "SSH connection to VM successful!"
      return 0
    fi

    attempt=$((attempt + 1))
    log_info "SSH not ready yet, waiting... (attempt $attempt/$max_attempts)"
    sleep 10
  done

  log_error "SSH connection failed after $max_attempts attempts"
  return 1
}

# Function to create ansible inventory with proper proxy configuration
create_ansible_inventory() {
  local vm_ip="$1"

  log_info "Creating Ansible inventory for VM..."

  local inventory_file="$PROJECT_ROOT/ansible/inventory/vm-test-inventory.yml"

  cat > "$inventory_file" <<EOF
---
all:
  children:
    homelab:
      hosts:
        homelab-server:
          ansible_host: ${HOMELAB_SERVER}
          ansible_user: ${HOMELAB_USER}
          ansible_become: true
    vm_test:
      hosts:
        test-vm:
          ansible_host: ${vm_ip}
          ansible_user: kang
          ansible_ssh_common_args: '-o ProxyJump=${HOMELAB_USER}@${HOMELAB_SERVER} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
          ansible_become: true
          node_role: worker
EOF

  log_success "Ansible inventory created at: $inventory_file"
}

# Main execution
main() {
  log_info "Starting VM network fix process..."

  # Check if VM exists and is running
  if ! check_vm_status; then
    exit 1
  fi

  # Get VM IP
  VM_IP=$(get_vm_ip)
  if [[ -z "$VM_IP" ]]; then
    exit 1
  fi

  # Setup SSH configuration
  setup_ssh_config "$VM_IP"

  # Test connectivity
  if test_ssh_connectivity "$VM_IP"; then
    # Create ansible inventory
    create_ansible_inventory "$VM_IP"

    log_success "VM network setup completed successfully!"
    echo
    echo "You can now:"
    echo "1. SSH to VM: ssh homelab-test-vm"
    echo "2. SSH with full command: ssh -o ProxyJump=${HOMELAB_USER}@${HOMELAB_SERVER} kang@${VM_IP}"
    echo "3. Run ansible playbooks with: ansible-playbook -i ansible/inventory/vm-test-inventory.yml <playbook>"
  else
    log_error "Failed to establish SSH connectivity"
    exit 1
  fi
}

# Run main function
main "$@"
