#!/bin/bash
# Deployment script with proper privilege management
# This script handles privilege escalation for homelab deployment operations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_USER="${HOMELAB_USER:-homelab-deploy}"
LOG_DIR="${HOME}/.local/log"
LOG_FILE="${LOG_DIR}/homelab-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  # Create log directory if it doesn't exist
  mkdir -p "$LOG_DIR"

  # Log to file
  echo "[$timestamp] [$level] $message" >>"$LOG_FILE"

  # Log to console with colors
  case "$level" in
    ERROR)
      echo -e "${RED}[$level]${NC} $message" >&2
      ;;
    WARN)
      echo -e "${YELLOW}[$level]${NC} $message"
      ;;
    INFO)
      echo -e "${GREEN}[$level]${NC} $message"
      ;;
    DEBUG)
      if [[ ${DEBUG:-false} == "true" ]]; then
        echo -e "${BLUE}[$level]${NC} $message"
      fi
      ;;
  esac
}

# Function to check if running as correct user
check_user() {
  local current_user=$(whoami)
  local requested_command="${1:-}"
  local root_allowed_commands=("user-setup")

  if [[ $current_user == "root" ]]; then
    # Check if this is a root-allowed command
    if [[ $requested_command == "user-setup" ]]; then
      log "INFO" "Running as root for initial setup: $requested_command"
      return 0
    else
      log "ERROR" "This script should not be run as root for security reasons"
      log "INFO" "Please run as the deployment user: $DEPLOYMENT_USER"
      log "INFO" "Root is only allowed for initial setup commands: ${root_allowed_commands[*]}"
      return 1
    fi
  fi

  # For non-root users, warn if not running as deployment user
  if [[ $current_user != "$DEPLOYMENT_USER" ]]; then
    # For setup commands, this is an error
    if [[ $requested_command == "user-setup" ]]; then
      log "ERROR" "Setup must be run as root: $requested_command"
      log "INFO" "Please run with: sudo $0 deploy user-setup"
      return 1
    else
      log "WARN" "Running as '$current_user' instead of recommended '$DEPLOYMENT_USER'"
      log "INFO" "Consider switching to the deployment user for better security"
    fi
  fi

  log "INFO" "Running as user: $current_user"
}

# Function to check sudo permissions
check_sudo_permissions() {
  log "INFO" "Checking sudo permissions for deployment operations..."

  local current_user=$(whoami)
  local sudo_example="$current_user ALL=(ALL) NOPASSWD:ALL"

  # Test sudo access without prompting for password
  if ! sudo -n true 2>/dev/null; then
    log "WARN" "Passwordless sudo is not configured."
    log "INFO" "To enable passwordless sudo, add this line to /etc/sudoers using 'visudo':"
    log "INFO" "  $sudo_example"
    log "INFO" "Falling back to interactive sudo. You may be prompted for your password."

    # Try interactive sudo
    if ! sudo -v; then
      log "ERROR" "Interactive sudo failed. Please ensure the user has sudo access."
      log "INFO" "Run 'visudo' as root and ensure your user is in the sudoers file."
      return 1
    fi
  fi

  # Test specific commands that we need
  local test_commands=(
    "systemctl status"
    "mkdir -p /tmp/homelab-test"
    "kubectl apply"
    "helm install"
  )

  local failed_commands=()
  for cmd in "${test_commands[@]}"; do
    if sudo -n $cmd >/dev/null 2>&1; then
      log "DEBUG" "Sudo access verified for: $cmd"
    else
      failed_commands+=("$cmd")
      log "WARN" "Limited sudo access for: $cmd"
    fi
  done

  # Report on failed commands
  if [[ ${#failed_commands[@]} -gt 0 ]]; then
    log "WARN" "Some commands require additional sudo permissions:"
    for cmd in "${failed_commands[@]}"; do
      log "INFO" "  $current_user ALL=(ALL) NOPASSWD: $cmd"
    done
    log "INFO" "Add these lines to /etc/sudoers using 'visudo'"
  fi

  # Cleanup test directory
  sudo rm -rf /tmp/homelab-test 2>/dev/null || true

  log "INFO" "Sudo permissions check completed"
}

# Function to set up environment
setup_environment() {
  log "INFO" "Setting up deployment environment..."

  # Source environment configuration if it exists
  local env_file="${HOME}/.environment"
  if [[ -f $env_file ]]; then
    log "DEBUG" "Sourcing environment from: $env_file"
    source "$env_file"
  fi

  # Set up required environment variables
  export KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/config}"
  export HOMELAB_DEPLOYMENT_MODE="rootless"
  export HOMELAB_USER="$DEPLOYMENT_USER"

  # Verify required tools are available
  local required_tools=("kubectl" "helm" "helmfile" "terraform" "ansible-playbook" "python3")
  local missing_tools=()

  for tool in "${required_tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
      log "DEBUG" "Found required tool: $tool"
    else
      missing_tools+=("$tool")
      log "ERROR" "Required tool not found: $tool"
    fi
  done

  # Exit if any required tools are missing
  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log "ERROR" "Missing required tools: ${missing_tools[*]}"
    log "INFO" "Please install the missing tools before continuing:"
    for tool in "${missing_tools[@]}"; do
      case "$tool" in
        kubectl)
          log "INFO" "  kubectl: https://kubernetes.io/docs/tasks/tools/"
          ;;
        helm)
          log "INFO" "  helm: https://helm.sh/docs/intro/install/"
          ;;
        ansible-playbook)
          log "INFO" "  ansible: pip install ansible"
          ;;
        python3)
          log "INFO" "  python3: Use your system's package manager"
          ;;
      esac
    done
    return 1
  fi

  log "INFO" "Environment setup completed - all required tools found"
}

# Function to run Ansible playbook with proper privilege handling
run_ansible_playbook() {
  local playbook="$1"
  shift
  local extra_args=("$@")

  log "INFO" "Running Ansible playbook: $playbook"

  # Change to project root
  cd "$PROJECT_ROOT"

  # Prepare Ansible command
  # Define Ansible command as an array and properly escape paths
  local ansible_cmd=(
    "ansible-playbook"
    "-i"
    "ansible/inventory/hosts.yml"
    "${playbook}"
  )

  # Add extra arguments if present, maintaining array structure
  if [[ ${#extra_args[@]} -gt 0 ]]; then
    ansible_cmd+=("${extra_args[@]}")
  fi

  # Execute command with proper array expansion to preserve argument separation
  "${ansible_cmd[@]}"

  # Add verbosity if in debug mode
  if [[ ${DEBUG:-false} == "true" ]]; then
    ansible_cmd+=("-vvv")
  fi

  log "INFO" "Executing: ${ansible_cmd[*]}"

  # Log full command for debugging
  if [[ ${DEBUG:-false} == "true" ]]; then
    log "DEBUG" "Full command: ${ansible_cmd[*]}"
    log "DEBUG" "Number of arguments: ${#ansible_cmd[@]}"
    for i in "${!ansible_cmd[@]}"; do
      log "DEBUG" "  Arg $i: ${ansible_cmd[$i]}"
    done
  fi

  # Execute Ansible playbook with proper array expansion
  if "${ansible_cmd[@]}"; then
    log "INFO" "Playbook execution completed successfully"
    return 0
  else
    local exit_code=$?
    log "ERROR" "Playbook execution failed with exit code: $exit_code"
    return $exit_code
  fi
}

# Function to deploy specific components
deploy_component() {
  local component="$1"

  log "INFO" "Deploying component: $component"

  case "$component" in
    "user-setup")
      # This requires initial root access to create the deployment user
      log "INFO" "Setting up deployment user (requires initial root access)"
      run_ansible_playbook "ansible/playbooks/setup-deployment-user.yml"
      ;;
    "terraform")
      log "INFO" "Provisioning infrastructure with Terraform"
      cd "$PROJECT_ROOT/terraform"
      terraform init
      terraform plan -out=tfplan
      if terraform apply "tfplan"; then
        log "INFO" "Terraform provisioning successful"
      else
        log "ERROR" "Terraform provisioning failed"
        return 1
      fi
      ;;
    "helmfile")
      log "INFO" "Deploying applications with Helmfile"
      cd "$PROJECT_ROOT/helm"
      helmfile sync
      ;;
    "k3s")
      log "INFO" "Deploying K3s cluster"
      run_ansible_playbook "ansible/playbooks/deploy-k3s.yml"
      ;;
    "metallb")
      log "INFO" "Deploying MetalLB load balancer"
      run_ansible_playbook "ansible/playbooks/deploy-metallb.yml"
      ;;
    "cert-manager")
      log "INFO" "Deploying cert-manager"
      run_ansible_playbook "ansible/playbooks/deploy-cert-manager.yml"
      ;;
    "nginx-ingress")
      log "INFO" "Deploying nginx ingress controller"
      run_ansible_playbook "ansible/playbooks/deploy-nginx-ingress.yml"
      ;;
    "gitlab")
      log "INFO" "Deploying GitLab"
      run_ansible_playbook "ansible/playbooks/deploy-gitlab.yml"
      ;;
    "keycloak")
      log "INFO" "Deploying Keycloak"
      run_ansible_playbook "ansible/playbooks/deploy-keycloak.yml"
      ;;
    "monitoring")
      log "INFO" "Deploying monitoring stack"
      run_ansible_playbook "ansible/playbooks/deploy-monitoring.yml"
      ;;
    "all")
      log "INFO" "Deploying all components"
      for comp in "terraform" "helmfile" "k3s" "metallb" "cert-manager" "nginx-ingress" "gitlab" "keycloak" "monitoring"; do
        deploy_component "$comp"
      done
      ;;
    *)
      log "ERROR" "Unknown component: $component"
      return 1
      ;;
  esac
}

# Function to show usage
usage() {
  cat <<EOF
Usage: $0 [OPTIONS] COMMAND [COMPONENT]

Deploy homelab infrastructure with proper privilege management.

OPTIONS:
    -h, --help          Show this help message
    -d, --debug         Enable debug output
    -u, --user USER     Specify deployment user (default: $DEPLOYMENT_USER)

COMMANDS:
    deploy COMPONENT    Deploy specific component
    check              Check deployment prerequisites
    test               Run deployment tests
    status             Show deployment status

COMPONENTS:
    user-setup         Set up deployment user (requires initial root access)
    terraform          Provision infrastructure with Terraform
    helmfile           Deploy applications with Helmfile
    k3s                Deploy K3s Kubernetes cluster
    metallb            Deploy MetalLB load balancer
    cert-manager       Deploy cert-manager for TLS
    nginx-ingress      Deploy nginx ingress controller
    gitlab             Deploy GitLab instance
    keycloak           Deploy Keycloak identity provider
    monitoring         Deploy monitoring stack (Prometheus, Grafana)
    all                Deploy all components (except user-setup)

EXAMPLES:
    $0 check                    # Check prerequisites
    $0 deploy user-setup        # Set up deployment user
    $0 deploy k3s              # Deploy K3s cluster
    $0 deploy all              # Deploy all components
    $0 -d deploy gitlab        # Deploy GitLab with debug output

EOF
}

# Function to check deployment prerequisites
check_prerequisites() {
  log "INFO" "Checking deployment prerequisites..."

  local errors=0
  local requested_command="${1:-}"

  # Check if we're running as the right user
  check_user "$requested_command" || ((errors++))

  # Check sudo permissions
  check_sudo_permissions || ((errors++))

  # Check if required directories exist
  local required_dirs=("$PROJECT_ROOT/ansible" "$PROJECT_ROOT/helm")
  for dir in "${required_dirs[@]}"; do
    if [[ -d $dir ]]; then
      log "DEBUG" "Found required directory: $dir"
    else
      log "ERROR" "Required directory not found: $dir"
      ((errors++))
    fi
  done

  # Check if kubeconfig exists (for non-initial deployments)
  if [[ -f $KUBECONFIG ]]; then
    log "INFO" "Kubeconfig found at: $KUBECONFIG"
    # Test kubectl access
    if kubectl cluster-info >/dev/null 2>&1; then
      log "INFO" "Kubernetes cluster is accessible"
    else
      log "WARN" "Kubernetes cluster is not accessible"
    fi
  else
    log "INFO" "Kubeconfig not found (expected for initial deployment)"
  fi

  if [[ $errors -eq 0 ]]; then
    log "INFO" "All prerequisites check passed"
    return 0
  else
    log "ERROR" "Prerequisites check failed with $errors errors"
    return 1
  fi
}

# Function to show deployment status
show_status() {
  log "INFO" "Checking deployment status..."

  # Check if kubectl is available and cluster is accessible
  if command -v kubectl >/dev/null 2>&1 && kubectl cluster-info >/dev/null 2>&1; then
    log "INFO" "Kubernetes cluster status:"
    kubectl get nodes -o wide 2>/dev/null || log "WARN" "Could not get node status"

    log "INFO" "Deployed applications:"
    kubectl get deployments,statefulsets -A 2>/dev/null || log "WARN" "Could not get application status"
  else
    log "WARN" "Kubernetes cluster not accessible"
  fi

  # Show systemd services status
  if command -v systemctl >/dev/null 2>&1; then
    log "INFO" "System services status:"
    for service in "k3s" "docker"; do
      if systemctl is-active "$service" >/dev/null 2>&1; then
        log "INFO" "Service $service is active"
      else
        log "INFO" "Service $service is not active"
      fi
    done
  fi
}

# Main function
main() {
  local command=""
  local component=""

  # Define valid commands and options
  local valid_commands=("deploy" "check" "test" "status")
  local valid_options=("-h" "--help" "-d" "--debug" "-u" "--user")
  local requires_value=("-u" "--user")

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    # Check if argument is an option
    if [[ $1 == -* ]]; then
      # Validate option
      if [[ ! " ${valid_options[*]} " =~ " $1 " ]]; then
        log "ERROR" "Unknown option: $1"
        usage
        exit 1
      fi

      case $1 in
        -h | --help)
          usage
          exit 0
          ;;
        -d | --debug)
          export DEBUG=true
          log "DEBUG" "Debug mode enabled"
          shift
          ;;
        -u | --user)
          # Check if value is provided
          if [[ -z $2 || $2 == -* ]]; then
            log "ERROR" "Option $1 requires a value"
            usage
            exit 1
          fi
          DEPLOYMENT_USER="$2"
          log "INFO" "Using deployment user: $DEPLOYMENT_USER"
          shift 2
          ;;
      esac
    else
      # Not an option, must be command or component
      if [[ -z $command ]]; then
        # Validate command
        if [[ ! " ${valid_commands[*]} " =~ " $1 " ]]; then
          log "ERROR" "Unknown command: $1"
          usage
          exit 1
        fi
        command="$1"
        shift
      elif [[ -z $component && $command == "deploy" ]]; then
        component="$1"
        shift
      else
        log "ERROR" "Unexpected argument: $1"
        usage
        exit 1
      fi
    fi
  done

  # Validate command
  if [[ -z $command ]]; then
    log "ERROR" "No command specified"
    usage
    exit 1
  fi

  # Set up environment
  setup_environment

  # Execute command
  case "$command" in
    check)
      check_prerequisites
      ;;
    deploy)
      if [[ -z $component ]]; then
        log "ERROR" "No component specified for deployment"
        usage
        exit 1
      fi
      check_prerequisites "$component" && deploy_component "$component"
      ;;
    test)
      log "INFO" "Running deployment tests..."
      # Add test execution here
      python3 "$PROJECT_ROOT/scripts/testing/test_reporter.py"
      ;;
    status)
      show_status
      ;;
    *)
      log "ERROR" "Unknown command: $command"
      usage
      exit 1
      ;;
  esac
}

# Execute main function with all arguments
main "$@"
