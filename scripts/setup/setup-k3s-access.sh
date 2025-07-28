#!/bin/bash
# Script to set up port forwarding for K3s access from local machine
# This enables kubectl access through SSH tunnel

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
HOMELAB_SERVER="192.168.16.26"
HOMELAB_USER="kang"
VM_IP="192.168.122.29"
LOCAL_PORT="${LOCAL_PORT:-6443}"
KUBECONFIG_PATH="$HOME/.kube/homelab-test-config"

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

# Function to check if port is already in use
check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    return 0  # Port is in use
  else
    return 1  # Port is free
  fi
}

# Function to setup SSH tunnel
setup_tunnel() {
  log_info "Setting up SSH tunnel for K3s access..."

  # Check if port is already in use
  if check_port $LOCAL_PORT; then
    log_info "Port $LOCAL_PORT is already in use. Checking if it's our tunnel..."

    # Check if it's our SSH tunnel
    if ps aux | grep -v grep | grep -q "ssh.*-L.*$LOCAL_PORT:$VM_IP:6443.*$HOMELAB_USER@$HOMELAB_SERVER"; then
      log_success "SSH tunnel is already running"
      return 0
    else
      log_error "Port $LOCAL_PORT is in use by another process"
      return 1
    fi
  fi

  # Start SSH tunnel in background
  log_info "Starting SSH tunnel: localhost:$LOCAL_PORT -> $VM_IP:6443 (through $HOMELAB_SERVER)"

  ssh -f -N -L "$LOCAL_PORT:$VM_IP:6443" "$HOMELAB_USER@$HOMELAB_SERVER" \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3

  sleep 2

  if check_port $LOCAL_PORT; then
    log_success "SSH tunnel established successfully"
  else
    log_error "Failed to establish SSH tunnel"
    return 1
  fi
}

# Function to update kubeconfig
update_kubeconfig() {
  log_info "Updating kubeconfig to use local tunnel..."

  if [[ ! -f "$KUBECONFIG_PATH" ]]; then
    log_error "Kubeconfig not found at: $KUBECONFIG_PATH"
    log_info "Run: scp homelab-test-vm:/tmp/kubeconfig $KUBECONFIG_PATH"
    return 1
  fi

  # Create backup
  cp "$KUBECONFIG_PATH" "${KUBECONFIG_PATH}.backup"

  # Update server URL to use localhost tunnel
  sed -i "s|https://$VM_IP:6443|https://localhost:$LOCAL_PORT|g" "$KUBECONFIG_PATH"

  log_success "Kubeconfig updated to use local tunnel"
}

# Function to test connection
test_connection() {
  log_info "Testing K3s connection through tunnel..."

  export KUBECONFIG="$KUBECONFIG_PATH"

  if kubectl get nodes --request-timeout=10s >/dev/null 2>&1; then
    log_success "Connection successful!"

    echo ""
    echo "Cluster Information:"
    kubectl get nodes -o wide
    echo ""
    kubectl get namespaces

    return 0
  else
    log_error "Failed to connect to K3s cluster"
    return 1
  fi
}

# Function to stop tunnel
stop_tunnel() {
  log_info "Stopping SSH tunnel..."

  # Find and kill SSH tunnel process
  local tunnel_pid=$(ps aux | grep -v grep | grep "ssh.*-L.*$LOCAL_PORT:$VM_IP:6443.*$HOMELAB_USER@$HOMELAB_SERVER" | awk '{print $2}')

  if [[ -n "$tunnel_pid" ]]; then
    kill $tunnel_pid 2>/dev/null || true
    log_success "SSH tunnel stopped"
  else
    log_info "No SSH tunnel found"
  fi
}

# Main function
main() {
  local action="${1:-start}"

  case "$action" in
    start)
      setup_tunnel
      update_kubeconfig
      test_connection

      echo ""
      echo "K3s access is now configured!"
      echo ""
      echo "To use kubectl:"
      echo "  export KUBECONFIG=$KUBECONFIG_PATH"
      echo "  kubectl get nodes"
      echo ""
      echo "To stop the tunnel:"
      echo "  $0 stop"
      ;;

    stop)
      stop_tunnel
      ;;

    status)
      if check_port $LOCAL_PORT; then
        if ps aux | grep -v grep | grep -q "ssh.*-L.*$LOCAL_PORT:$VM_IP:6443.*$HOMELAB_USER@$HOMELAB_SERVER"; then
          log_success "SSH tunnel is running on port $LOCAL_PORT"
          test_connection
        else
          log_info "Port $LOCAL_PORT is in use by another process"
        fi
      else
        log_info "SSH tunnel is not running"
      fi
      ;;

    restart)
      stop_tunnel
      sleep 2
      setup_tunnel
      update_kubeconfig
      test_connection
      ;;

    *)
      echo "Usage: $0 {start|stop|status|restart}"
      exit 1
      ;;
  esac
}

# Run main function
main "$@"
