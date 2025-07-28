#!/bin/bash
# Automated K3s deployment script with progress monitoring and error handling
# This script deploys K3s to the test VM with full automation and logging

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANSIBLE_DIR="$PROJECT_ROOT/ansible"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/k3s-deployment-${TIMESTAMP}.log"
PROGRESS_FILE="$LOG_DIR/k3s-deployment-progress-${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Progress indicators
SPINNER='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
SPINNER_POS=0

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_progress() {
  echo -e "${GREEN}[PROGRESS]${NC} $1" | tee -a "$PROGRESS_FILE"
}

show_spinner() {
  local pid=$1
  local message=$2

  while kill -0 $pid 2>/dev/null; do
    printf "\r${BLUE}[${SPINNER:SPINNER_POS:1}]${NC} ${message}..."
    SPINNER_POS=$(( (SPINNER_POS + 1) % ${#SPINNER} ))
    sleep 0.1
  done

  printf "\r"
}

# Function to monitor ansible output in real-time
monitor_ansible_output() {
  local pipe_file="/tmp/ansible-output-$$"
  mkfifo "$pipe_file"

  # Start ansible in background with output to pipe
  (cd "$ANSIBLE_DIR" && \
   ANSIBLE_HOST_KEY_CHECKING=False \
   ANSIBLE_STDOUT_CALLBACK=yaml \
   ansible-playbook -i inventory/vm-test-inventory.yml \
   playbooks/deploy-k3s-fixed.yml \
   -vv > "$pipe_file" 2>&1) &

  local ansible_pid=$!

  # Process output line by line
  while IFS= read -r line; do
    echo "$line" >> "$LOG_FILE"

    # Extract and display key information
    if [[ "$line" =~ TASK.*\[(.*)\] ]]; then
      log_progress "Running: ${BASH_REMATCH[1]}"
    elif [[ "$line" =~ "ok:" ]] || [[ "$line" =~ "changed:" ]]; then
      echo -e "${GREEN}✓${NC} $line" | tee -a "$PROGRESS_FILE"
    elif [[ "$line" =~ "failed:" ]] || [[ "$line" =~ "FAILED" ]]; then
      echo -e "${RED}✗${NC} $line" | tee -a "$PROGRESS_FILE"
    elif [[ "$line" =~ "skipping:" ]]; then
      echo -e "${YELLOW}↷${NC} $line" | tee -a "$PROGRESS_FILE"
    elif [[ "$line" =~ "msg:" ]]; then
      echo -e "${BLUE}ℹ${NC} $line" | tee -a "$PROGRESS_FILE"
    fi
  done < "$pipe_file"

  # Wait for ansible to complete
  wait $ansible_pid
  local ansible_exit=$?

  # Clean up
  rm -f "$pipe_file"

  return $ansible_exit
}

# Function to verify deployment
verify_deployment() {
  log_info "Verifying K3s deployment..."

  # Test SSH connectivity
  if ssh homelab-test-vm "k3s kubectl get nodes" &>/dev/null; then
    log_success "K3s is accessible via SSH"
  else
    log_error "Cannot access K3s via SSH"
    return 1
  fi

  # Get cluster status
  local cluster_status=$(ssh homelab-test-vm "k3s kubectl get nodes -o json" 2>/dev/null)

  if [[ -n "$cluster_status" ]]; then
    log_success "Cluster is responding"

    # Extract node status
    local node_ready=$(echo "$cluster_status" | jq -r '.items[0].status.conditions[] | select(.type=="Ready") | .status' 2>/dev/null || echo "Unknown")

    if [[ "$node_ready" == "True" ]]; then
      log_success "Node is ready"
    else
      log_warning "Node status: $node_ready"
    fi
  else
    log_error "Could not get cluster status"
    return 1
  fi

  # Check namespaces
  local namespaces=$(ssh homelab-test-vm "k3s kubectl get namespaces -o json" 2>/dev/null)

  if echo "$namespaces" | jq -r '.items[].metadata.name' | grep -q "homelab"; then
    log_success "Homelab namespace exists"
  else
    log_warning "Homelab namespace not found"
  fi

  return 0
}

# Function to generate deployment report
generate_report() {
  local report_file="$LOG_DIR/k3s-deployment-report-${TIMESTAMP}.txt"

  {
    echo "K3s Deployment Report"
    echo "===================="
    echo "Timestamp: $(date)"
    echo ""

    echo "Deployment Summary:"
    echo "------------------"

    # Count task results from progress file
    local tasks_ok=$(grep -c "✓" "$PROGRESS_FILE" || echo 0)
    local tasks_changed=$(grep -c "changed:" "$PROGRESS_FILE" || echo 0)
    local tasks_failed=$(grep -c "✗" "$PROGRESS_FILE" || echo 0)
    local tasks_skipped=$(grep -c "↷" "$PROGRESS_FILE" || echo 0)

    echo "Tasks OK: $tasks_ok"
    echo "Tasks Changed: $tasks_changed"
    echo "Tasks Failed: $tasks_failed"
    echo "Tasks Skipped: $tasks_skipped"
    echo ""

    if [[ -f "$LOG_FILE" ]]; then
      echo "Cluster Information:"
      echo "------------------"

      # Extract cluster info from logs
      sed -n '/=== Cluster Nodes ===/,/=== System Pods ===/p' "$LOG_FILE" | tail -n +2 || true

      echo ""
      echo "Issues Found:"
      echo "------------"
      grep -i "error\|failed\|warning" "$LOG_FILE" | tail -10 || echo "No issues found"
    fi

    echo ""
    echo "Log Files:"
    echo "---------"
    echo "Full log: $LOG_FILE"
    echo "Progress log: $PROGRESS_FILE"
    echo "This report: $report_file"

  } > "$report_file"

  cat "$report_file"
}

# Main deployment function
main() {
  log_info "Starting automated K3s deployment"
  log_info "Logs will be saved to: $LOG_DIR"
  echo ""

  # Pre-flight checks
  log_info "Running pre-flight checks..."

  # Check if VM is accessible
  if ! ssh homelab-test-vm "echo 'VM accessible'" &>/dev/null; then
    log_error "Cannot connect to test VM. Please check VM status and SSH configuration."
    exit 1
  fi
  log_success "VM is accessible"

  # Check if ansible is installed
  if ! command -v ansible-playbook &>/dev/null; then
    log_error "ansible-playbook not found. Please install Ansible."
    exit 1
  fi
  log_success "Ansible is installed"

  # Check inventory file
  if [[ ! -f "$ANSIBLE_DIR/inventory/vm-test-inventory.yml" ]]; then
    log_error "Inventory file not found: $ANSIBLE_DIR/inventory/vm-test-inventory.yml"
    exit 1
  fi
  log_success "Inventory file found"

  # Check playbook file
  if [[ ! -f "$ANSIBLE_DIR/playbooks/deploy-k3s-fixed.yml" ]]; then
    log_error "Playbook file not found: $ANSIBLE_DIR/playbooks/deploy-k3s-fixed.yml"
    exit 1
  fi
  log_success "Playbook file found"

  echo ""
  log_info "Starting K3s deployment..."
  echo ""

  # Run deployment with monitoring
  if monitor_ansible_output; then
    log_success "Ansible playbook completed successfully"

    echo ""
    log_info "Running post-deployment verification..."

    if verify_deployment; then
      log_success "Deployment verification passed"
    else
      log_warning "Deployment verification had issues"
    fi
  else
    log_error "Ansible playbook failed"
    log_info "Check the logs for details: $LOG_FILE"
  fi

  echo ""
  log_info "Generating deployment report..."
  echo ""

  generate_report

  echo ""
  log_info "K3s deployment process completed"

  # Provide next steps
  echo ""
  echo "Next steps:"
  echo "1. Review the deployment report above"
  echo "2. Access the cluster: ssh homelab-test-vm 'k3s kubectl get nodes'"
  echo "3. Copy kubeconfig: scp homelab-test-vm:~/.kube/config ~/.kube/homelab-test-config"
  echo "4. Use kubectl: export KUBECONFIG=~/.kube/homelab-test-config && kubectl get nodes"
}

# Run main function
main "$@"
