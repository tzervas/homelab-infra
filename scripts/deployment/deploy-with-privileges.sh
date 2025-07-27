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
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
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
            if [[ "${DEBUG:-false}" == "true" ]]; then
                echo -e "${BLUE}[$level]${NC} $message"
            fi
            ;;
    esac
}

# Function to check if running as correct user
check_user() {
    local current_user=$(whoami)
    
    if [[ "$current_user" == "root" ]]; then
        log "ERROR" "This script should not be run as root for security reasons"
        log "INFO" "Please run as the deployment user: $DEPLOYMENT_USER"
        exit 1
    fi
    
    if [[ "$current_user" != "$DEPLOYMENT_USER" ]]; then
        log "WARN" "Running as '$current_user' instead of recommended '$DEPLOYMENT_USER'"
        log "INFO" "Consider switching to the deployment user for better security"
    fi
    
    log "INFO" "Running as user: $current_user"
}

# Function to check sudo permissions
check_sudo_permissions() {
    log "INFO" "Checking sudo permissions for deployment operations..."
    
    # Test sudo access without prompting for password
    if ! sudo -n true 2>/dev/null; then
        log "ERROR" "Passwordless sudo is not configured or user is not in sudoers"
        log "INFO" "Please ensure the deployment user is properly configured with sudo access"
        return 1
    fi
    
    # Test specific commands that we need
    local test_commands=(
        "systemctl status"
        "mkdir -p /tmp/homelab-test"
    )
    
    for cmd in "${test_commands[@]}"; do
        if sudo -n $cmd >/dev/null 2>&1; then
            log "DEBUG" "Sudo access verified for: $cmd"
        else
            log "WARN" "Limited sudo access for: $cmd"
        fi
    done
    
    # Cleanup test directory
    sudo rm -rf /tmp/homelab-test 2>/dev/null || true
    
    log "INFO" "Sudo permissions check completed"
}

# Function to set up environment
setup_environment() {
    log "INFO" "Setting up deployment environment..."
    
    # Source environment configuration if it exists
    local env_file="${HOME}/.environment"
    if [[ -f "$env_file" ]]; then
        log "DEBUG" "Sourcing environment from: $env_file"
        source "$env_file"
    fi
    
    # Set up required environment variables
    export KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/config}"
    export HOMELAB_DEPLOYMENT_MODE="rootless"
    export HOMELAB_USER="$DEPLOYMENT_USER"
    
    # Verify required tools are available
    local required_tools=("kubectl" "helm" "ansible-playbook")
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            log "DEBUG" "Found required tool: $tool"
        else
            log "WARN" "Required tool not found: $tool"
        fi
    done
    
    log "INFO" "Environment setup completed"
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
    local ansible_cmd=(
        "ansible-playbook"
        "-i" "ansible/inventory/hosts.yml"
        "$playbook"
    )
    
    # Add extra arguments
    if [[ ${#extra_args[@]} -gt 0 ]]; then
        ansible_cmd+=("${extra_args[@]}")
    fi
    
    # Add verbosity if in debug mode
    if [[ "${DEBUG:-false}" == "true" ]]; then
        ansible_cmd+=("-vvv")
    fi
    
    log "INFO" "Executing: ${ansible_cmd[*]}"
    
    # Execute Ansible playbook
    if "${ansible_cmd[@]}"; then
        log "INFO" "Playbook execution completed successfully"
        return 0
    else
        log "ERROR" "Playbook execution failed"
        return 1
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
            for comp in "k3s" "metallb" "cert-manager" "nginx-ingress" "gitlab" "keycloak" "monitoring"; do
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
    cat << EOF
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
    
    # Check if we're running as the right user
    check_user || ((errors++))
    
    # Check sudo permissions
    check_sudo_permissions || ((errors++))
    
    # Check if required directories exist
    local required_dirs=("$PROJECT_ROOT/ansible" "$PROJECT_ROOT/helm")
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log "DEBUG" "Found required directory: $dir"
        else
            log "ERROR" "Required directory not found: $dir"
            ((errors++))
        fi
    done
    
    # Check if kubeconfig exists (for non-initial deployments)
    if [[ -f "$KUBECONFIG" ]]; then
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
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -d|--debug)
                export DEBUG=true
                log "DEBUG" "Debug mode enabled"
                shift
                ;;
            -u|--user)
                DEPLOYMENT_USER="$2"
                log "INFO" "Using deployment user: $DEPLOYMENT_USER"
                shift 2
                ;;
            deploy|check|test|status)
                command="$1"
                shift
                ;;
            *)
                if [[ -z "$component" && -n "$command" ]]; then
                    component="$1"
                else
                    log "ERROR" "Unknown argument: $1"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate command
    if [[ -z "$command" ]]; then
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
            if [[ -z "$component" ]]; then
                log "ERROR" "No component specified for deployment"
                usage
                exit 1
            fi
            check_prerequisites && deploy_component "$component"
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