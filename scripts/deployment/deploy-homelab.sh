#!/bin/bash
# Comprehensive GitLab + Keycloak Homelab Deployment Orchestrator
# This script manages the entire deployment lifecycle using Ansible

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANSIBLE_DIR="$PROJECT_ROOT/ansible"

# Default values
DEPLOYMENT_PHASE="${1:-vm-test}"
VERBOSE=${VERBOSE:-false}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
  echo -e "${PURPLE}$1${NC}"
}

# Function to sync private configuration
sync_private_config() {
  print_header "🔐 Syncing Private Configuration"
  echo "===================================="

  # Run the private config sync script if it exists
  if [ -f "$PROJECT_ROOT/scripts/maintenance/sync-private-config.sh" ]; then
    "$PROJECT_ROOT/scripts/maintenance/sync-private-config.sh" sync
  else
    print_warning "Private config sync script not found"
    print_status "Skipping private configuration sync"
  fi

  # Load environment variables from .env
  if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    print_success "Environment variables loaded from .env"
  else
    print_warning ".env file not found"
  fi

  # Load private environment variables if available
  local private_env_file="$PROJECT_ROOT/.private-config/.env.private"
  if [ -f "$private_env_file" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$private_env_file"
    set +a
    print_success "Private environment variables loaded"
  else
    print_status "No private environment file found (this is normal for initial setup)"
  fi

  # Load local-only environment variables (highest priority)
  local local_env_file="$PROJECT_ROOT/.env.private.local"
  if [ -f "$local_env_file" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$local_env_file"
    set +a
    print_success "Local-only environment variables loaded (highest priority)"
  else
    print_status "No local-only environment file found (.env.private.local)"
  fi

  echo ""
}

# Function to check prerequisites
check_prerequisites() {
  print_header "🔍 Checking Prerequisites"
  echo "================================"

  local missing_tools=()

  # Check for required tools
  for tool in ansible ansible-playbook ssh scp; do
    if ! command -v "$tool" &>/dev/null; then
      missing_tools+=("$tool")
    fi
  done

  if [ ${#missing_tools[@]} -ne 0 ]; then
    print_error "Missing required tools: ${missing_tools[*]}"
    print_status "Please install missing tools and try again"
    echo "  Ubuntu/Debian: sudo apt install ansible openssh-client"
    exit 1
  fi

  # Check SSH connectivity
  print_status "Testing SSH connectivity to homelab server..."
  if ssh -o ConnectTimeout=5 -o BatchMode=yes kang@192.168.16.26 'echo "SSH connection successful"' >/dev/null 2>&1; then
    print_success "SSH connection to homelab server: OK"
  else
    print_warning "SSH connection failed - you may need to set up SSH keys"
    print_status "Run: ssh-copy-id kang@192.168.16.26"
  fi

  # Check if we have our tools installed locally
  if [ -f "$HOME/.local/bin/kubectl" ] && [ -f "$HOME/.local/bin/helm" ] && [ -f "$HOME/.local/bin/helmfile" ]; then
    print_success "Local deployment tools: OK"
  else
    print_warning "Local deployment tools not found"
    print_status "They will be used from PATH or installed during deployment"
  fi

  echo ""
}

# Function to display usage
show_usage() {
  cat <<EOF
GitLab + Keycloak Homelab Deployment Orchestrator

USAGE:
    $0 <phase> [options]

PHASES:
    vm-test           Create VM and deploy K3s + applications for testing
    full-vm-test      Complete VM test deployment (same as vm-test)
    bare-metal        Deploy directly to bare metal server
    cleanup-vm        Remove test VM and cleanup
    cleanup-bare-metal Cleanup bare metal K3s installation

EXAMPLES:
    # Test deployment in VM
    $0 vm-test

    # Deploy to bare metal (after VM testing)
    $0 bare-metal

    # Clean up test VM
    $0 cleanup-vm

ENVIRONMENT VARIABLES:
    VERBOSE=true      Enable verbose Ansible output
    ANSIBLE_CONFIG    Custom Ansible configuration file

NETWORK CONFIGURATION:
    - Server: 192.168.16.26 (user: kang)
    - MetalLB Range: 192.168.25.50 - 192.168.35.250
    - GitLab: 192.168.25.204
    - Keycloak: 192.168.25.205
    - Registry: 192.168.25.206

REQUIREMENTS:
    - Ansible installed locally
    - SSH key access to homelab server
    - Server with KVM/libvirt support (for VM testing)
    - At least 16GB RAM and 200GB disk space on server
EOF
}

# Function to run Ansible playbook
run_ansible() {
  local playbook="$1"
  local extra_vars="$2"

  cd "$ANSIBLE_DIR"

  local ansible_cmd="ansible-playbook"

  # Add verbose flag if requested
  if [ "$VERBOSE" = "true" ]; then
    ansible_cmd="$ansible_cmd -vv"
  fi

  # Add extra vars if provided
  if [ -n "$extra_vars" ]; then
    ansible_cmd="$ansible_cmd --extra-vars '$extra_vars'"
  fi

  # Add sudo password prompt
  ansible_cmd="$ansible_cmd --ask-become-pass"

  # Run the playbook
  eval "$ansible_cmd $playbook"
}

# Function to display post-deployment information
show_post_deployment_info() {
  local phase="$1"

  print_header "🎉 Deployment Complete!"
  echo "=========================="
  echo ""

  case "$phase" in
    "vm-test" | "full-vm-test")
      print_status "VM Test Environment Ready"
      echo ""
      echo "📋 Next Steps:"
      echo "  1. Add DNS entries to your router or /etc/hosts:"
      echo "     192.168.25.204  gitlab.dev.homelab.local"
      echo "     192.168.25.205  keycloak.dev.homelab.local"
      echo "     192.168.25.206  registry.dev.homelab.local"
      echo ""
      echo "  2. Access services:"
      echo "     🔐 Keycloak: https://keycloak.dev.homelab.local"
      echo "     🦊 GitLab: https://gitlab.dev.homelab.local"
      echo "     📦 Registry: https://registry.dev.homelab.local"
      echo ""
      echo "  3. Configure Keycloak SSO (see documentation)"
      echo ""
      echo "  4. Test the deployment:"
      echo "     ./scripts/validation/test-sso-flow.sh"
      echo ""
      echo "  5. When ready for production:"
      echo "     $0 bare-metal"
      ;;
    "bare-metal")
      print_status "Bare Metal Production Environment Ready"
      echo ""
      echo "📋 Production Deployment Complete:"
      echo "  • K3s cluster running on bare metal"
      echo "  • GitLab with container registry deployed"
      echo "  • Keycloak SSO integrated"
      echo "  • MetalLB load balancer configured"
      echo "  • Cert-manager for SSL certificates"
      echo ""
      echo "🔧 Management Commands:"
      echo "  kubectl get nodes                    # Check cluster status"
      echo "  kubectl get pods -A                  # View all pods"
      echo "  kubectl get svc -A                   # View services"
      echo "  ./scripts/validation/test-sso-flow.sh          # Test functionality"
      ;;
    "cleanup-vm")
      print_success "Test VM cleaned up successfully"
      echo "  • VM destroyed and storage removed"
      echo "  • Ready for fresh testing or bare metal deployment"
      ;;
    "cleanup-bare-metal")
      print_success "Bare metal K3s cluster cleaned up"
      echo "  • K3s services stopped and removed"
      echo "  • Configuration and data directories cleaned"
      echo "  • Server ready for fresh deployment"
      ;;
  esac

  echo ""
  print_status "For troubleshooting, check:"
  echo "  • kubectl logs -n <namespace> <pod-name>"
  echo "  • ./scripts/utilities/cleanup-failed.sh (for stuck resources)"
  echo "  • Documentation in docs/ directory"
  echo ""
}

# Main execution
main() {
  # Handle help requests
  if [[ $1 == "-h" || $1 == "--help" || -z $1 ]]; then
    show_usage
    exit 0
  fi

  # Validate phase
  case "$DEPLOYMENT_PHASE" in
    "vm-test" | "full-vm-test" | "bare-metal" | "cleanup-vm" | "cleanup-bare-metal") ;;
    *)
      print_error "Invalid deployment phase: $DEPLOYMENT_PHASE"
      echo ""
      show_usage
      exit 1
      ;;
  esac

  print_header "🏗️  GitLab + Keycloak Homelab Deployment"
  echo "========================================"
  echo "Phase: $DEPLOYMENT_PHASE"
  echo "Verbose: $VERBOSE"
  echo "Project: $PROJECT_ROOT"
  echo ""

  # Sync private configuration
  sync_private_config

  # Check prerequisites
  check_prerequisites

  # Confirm deployment
  if [[ $DEPLOYMENT_PHASE != "cleanup-vm" && $DEPLOYMENT_PHASE != "cleanup-bare-metal" ]]; then
    print_warning "This will deploy/modify infrastructure on your homelab server"
    read -p "Continue? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      print_status "Deployment cancelled"
      exit 0
    fi
  fi

  # Run the deployment
  print_status "Starting deployment phase: $DEPLOYMENT_PHASE"

  case "$DEPLOYMENT_PHASE" in
    "vm-test" | "full-vm-test")
      print_status "Creating test VM and deploying K3s cluster..."
      run_ansible "site.yml" "phase=$DEPLOYMENT_PHASE"

      # Test bastion host access pattern after VM creation
      print_status "🔗 Testing bastion host access pattern..."
      if run_ansible "playbooks/test-bastion-access.yml" ""; then
        print_success "Bastion host access verified"
      else
        print_warning "Bastion access test failed, but deployment continues"
      fi
      ;;
    "bare-metal")
      print_status "Deploying K3s cluster to bare metal..."
      run_ansible "site.yml" "phase=bare-metal"
      ;;
    "cleanup-vm")
      print_status "Cleaning up test VM..."
      run_ansible "site.yml" "phase=cleanup-vm"
      ;;
    "cleanup-bare-metal")
      print_status "Cleaning up bare metal K3s..."
      run_ansible "site.yml" "phase=cleanup-bare-metal"
      ;;
  esac

  # Show post-deployment information
  show_post_deployment_info "$DEPLOYMENT_PHASE"
}

# Execute main function
main "$@"
