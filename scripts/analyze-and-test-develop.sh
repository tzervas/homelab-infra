#!/bin/bash

# Comprehensive Analysis and Testing Script for Develop Branch
# This script critically analyzes the codebase for best practices,
# runs simulations, and validates the infrastructure as code

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*"
}

# Main analysis function
main() {
  log_info "Starting comprehensive analysis and testing for develop branch"

  cd "$PROJECT_ROOT"

  # Run code quality checks
  log_info "Running code quality checks..."
  if ./scripts/code-quality.sh all; then
    log_success "Code quality checks passed"
  else
    log_error "Code quality checks failed"
    exit 1
  fi

  # Run validation
  log_info "Running deployment validation..."
  if ./scripts/validate-deployment.py; then
    log_success "Deployment validation passed"
  else
    log_error "Deployment validation failed"
    exit 1
  fi

  log_success "All tests and analysis completed successfully"
}

# Execute main function
main "$@"
