#!/bin/bash
# Expanded Deployment Script
# Handles network and VM readiness issues more gracefully

set -e

export VERBOSE=true

log_info() {
  echo -e "\033[0;34m[INFO] $1\033[0m"
}

log_success() {
  echo -e "\033[0;32m[SUCCESS] $1\033[0m"
}

log_error() {
  echo -e "\033[0;31m[ERROR] $1\033[0m"
}

# Step 1: Validate Script Execution Environment
log_info "Starting deployment script with more robust handling."

# Run the deployment and network adjustment
VERBOSE=true ./scripts/deploy-and-validate.sh vm-test || true

# Step 2: Check for the known network issues and fix them
log_info "Running network fix script..."
./scripts/fix-vm-network.sh

log_success "Deployment and network adjustment completed! Check VM access and configuration."

# Validate results through vm and ansible inventory access
./scripts/deploy-and-validate.sh vm-test
