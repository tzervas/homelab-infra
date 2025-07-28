#!/bin/bash
# Unified deployment script for automated infrastructure and application deployment
# Validates prerequisites, runs Terraform plan/apply, executes Helmfile sync with security validations,
# and performs post-deployment testing

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="${HOME}/.local/log"
LOG_FILE="${LOG_DIR}/unified-deploy.log"

# Default values
ENVIRONMENT="development"
DRY_RUN=false
SKIP_TERRAFORM=false
SKIP_HELMFILE=false
SKIP_TESTS=false

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
      if [[ ${DEBUG:-false} == "true" ]]; then
        echo -e "${BLUE}[$level]${NC} $message"
      fi
      ;;
  esac
}

# Show usage information
show_usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Unified deployment script for homelab infrastructure and applications.

OPTIONS:
    -e, --environment ENV    Environment to deploy (development|staging|production) [default: development]
    -d, --dry-run           Perform a dry run without making changes
    --skip-terraform        Skip Terraform provisioning
    --skip-helmfile         Skip Helmfile deployment
    --skip-tests           Skip post-deployment tests
    --debug                Enable debug output
    -h, --help             Show this help message

EXAMPLES:
    $0 -e production
    $0 --dry-run --skip-tests
    $0 --skip-terraform -e staging

EOF
}

# Parse command line arguments
parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      -e | --environment)
        ENVIRONMENT="$2"
        shift 2
        ;;
      -d | --dry-run)
        DRY_RUN=true
        shift
        ;;
      --skip-terraform)
        SKIP_TERRAFORM=true
        shift
        ;;
      --skip-helmfile)
        SKIP_HELMFILE=true
        shift
        ;;
      --skip-tests)
        SKIP_TESTS=true
        shift
        ;;
      --debug)
        export DEBUG=true
        shift
        ;;
      -h | --help)
        show_usage
        exit 0
        ;;
      *)
        log "ERROR" "Unknown option: $1"
        show_usage
        exit 1
        ;;
    esac
  done

  # Validate environment
  if [[ ! $ENVIRONMENT =~ ^(development|staging|production)$ ]]; then
    log "ERROR" "Invalid environment: $ENVIRONMENT"
    log "INFO" "Valid environments: development, staging, production"
    exit 1
  fi

  log "INFO" "Configuration: environment=$ENVIRONMENT, dry_run=$DRY_RUN"
}

# Validate prerequisites
validate_prerequisites() {
  log "INFO" "Validating deployment prerequisites..."

  local errors=0

  # Check required tools
  local required_tools=("terraform" "helmfile" "kubectl" "helm" "python3")
  for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" > /dev/null 2>&1; then
      log "ERROR" "Required tool not found: $tool"
      ((errors++))
    else
      log "DEBUG" "Found required tool: $tool"
    fi
  done

  # Check if kubeconfig exists and cluster is accessible
  export KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/config}"
  if [[ ! -f $KUBECONFIG ]]; then
    log "ERROR" "Kubeconfig not found at $KUBECONFIG"
    ((errors++))
  else
    log "DEBUG" "Found kubeconfig at: $KUBECONFIG"
    if ! kubectl cluster-info > /dev/null 2>&1; then
      log "ERROR" "Cannot access Kubernetes cluster"
      ((errors++))
    else
      log "INFO" "Kubernetes cluster is accessible"
    fi
  fi

  # Check if required directories exist
  local required_dirs=("$PROJECT_ROOT/terraform" "$PROJECT_ROOT/helm")
  for dir in "${required_dirs[@]}"; do
    if [[ ! -d $dir ]]; then
      log "ERROR" "Required directory not found: $dir"
      ((errors++))
    else
      log "DEBUG" "Found required directory: $dir"
    fi
  done

  # Check if Terraform state directory exists or can be created
  if [[ ! -d "$PROJECT_ROOT/terraform/.terraform" ]]; then
    log "WARN" "Terraform not initialized - will initialize during deployment"
  fi

  if [[ $errors -eq 0 ]]; then
    log "INFO" "All prerequisites validation passed"
    return 0
  else
    log "ERROR" "Prerequisites validation failed with $errors errors"
    exit 1
  fi
}

# Validate Terraform state
validate_terraform_state() {
  log "INFO" "Validating Terraform state..."
  cd "$PROJECT_ROOT/terraform"
  
  if terraform show > /dev/null 2>&1; then
    log "INFO" "Terraform state is valid"
  else
    log "WARN" "Terraform state validation failed or no state exists"
  fi
}

# Run Terraform plan/apply
run_terraform() {
  if [[ $SKIP_TERRAFORM == true ]]; then
    log "INFO" "Skipping Terraform provisioning"
    return 0
  fi

  log "INFO" "Running Terraform for environment: $ENVIRONMENT"
  cd "$PROJECT_ROOT/terraform"
  
  # Initialize Terraform
  log "INFO" "Initializing Terraform..."
  terraform init
  
  # Run terraform plan with environment-specific variables
  log "INFO" "Creating Terraform plan..."
  if [[ $DRY_RUN == true ]]; then
    terraform plan -var="environment=$ENVIRONMENT"
  else
    terraform plan -var="environment=$ENVIRONMENT" -out=tfplan
    
    # Apply the plan
    log "INFO" "Applying Terraform plan..."
    terraform apply "tfplan"
    
    # Validate the state after apply
    validate_terraform_state
  fi
  
  log "INFO" "Terraform provisioning completed"
}

# Execute Helmfile sync with security validations
sync_helmfile() {
  if [[ $SKIP_HELMFILE == true ]]; then
    log "INFO" "Skipping Helmfile deployment"
    return 0
  fi

  log "INFO" "Running Helmfile sync for environment: $ENVIRONMENT"
  cd "$PROJECT_ROOT/helm"
  
  # Validate Helmfile configuration
  log "INFO" "Validating Helmfile configuration..."
  if ! helmfile --environment "$ENVIRONMENT" list > /dev/null 2>&1; then
    log "ERROR" "Helmfile configuration validation failed"
    return 1
  fi
  
  if [[ $DRY_RUN == true ]]; then
    log "INFO" "Performing Helmfile diff (dry run)..."
    helmfile --environment "$ENVIRONMENT" diff
  else
    log "INFO" "Syncing Helmfile releases..."
    helmfile --environment "$ENVIRONMENT" sync --wait --timeout 600
  fi
  
  log "INFO" "Helmfile sync completed"
}

# Perform comprehensive post-deployment testing
post_deployment_tests() {
  if [[ $SKIP_TESTS == true ]]; then
    log "INFO" "Skipping post-deployment tests"
    return 0
  fi

  if [[ $DRY_RUN == true ]]; then
    log "INFO" "Skipping tests in dry-run mode"
    return 0
  fi

  log "INFO" "Running comprehensive post-deployment tests..."
  
  # Run the comprehensive test suite with enhanced security testing
  local test_args=("--log-level" "INFO")
  
  # Add environment-specific test configuration if available
  if [[ -f "$PROJECT_ROOT/config/test-$ENVIRONMENT.yaml" ]]; then
    test_args+=("--config" "$PROJECT_ROOT/config/test-$ENVIRONMENT.yaml")
  fi
  
  # Run all test modules including security validation
  if python3 "$PROJECT_ROOT/scripts/testing/test_reporter.py" "${test_args[@]}"; then
    log "INFO" "All post-deployment tests passed"
  else
    log "ERROR" "Some post-deployment tests failed"
    return 1
  fi
}

# Deployment smoke tests
run_deployment_smoke_tests() {
  log "INFO" "Running deployment smoke tests..."
  
  # Use the Python smoke test module for comprehensive testing
  if python3 "$PROJECT_ROOT/scripts/testing/deployment_smoke_tests.py" --log-level INFO; then
    log "INFO" "All deployment smoke tests passed"
    return 0
  else
    log "ERROR" "Some deployment smoke tests failed"
    return 1
  fi
}

# Main deployment function
main() {
  local start_time=$(date +%s)
  
  log "INFO" "🚀 Starting unified homelab deployment..."
  log "INFO" "Environment: $ENVIRONMENT"
  log "INFO" "Dry run: $DRY_RUN"
  
  # Parse command line arguments
  parse_arguments "$@"
  
  # Validate prerequisites
  validate_prerequisites
  
  # Run deployment phases
  if ! run_terraform; then
    log "ERROR" "Terraform deployment failed"
    exit 1
  fi
  
  if ! run_deployment_smoke_tests; then
    log "ERROR" "Deployment smoke tests failed"
    exit 1
  fi
  
  if ! sync_helmfile; then
    log "ERROR" "Helmfile deployment failed"
    exit 1
  fi
  
  if ! post_deployment_tests; then
    log "ERROR" "Post-deployment tests failed"
    exit 1
  fi
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  
  log "INFO" "✅ Unified deployment completed successfully in ${duration}s"
  
  # Show deployment summary
  log "INFO" "📊 Deployment Summary:"
  log "INFO" "  Environment: $ENVIRONMENT"
  log "INFO" "  Terraform: $([ $SKIP_TERRAFORM == true ] && echo 'skipped' || echo 'completed')"
  log "INFO" "  Helmfile: $([ $SKIP_HELMFILE == true ] && echo 'skipped' || echo 'completed')"
  log "INFO" "  Tests: $([ $SKIP_TESTS == true ] && echo 'skipped' || echo 'completed')"
  log "INFO" "  Duration: ${duration}s"
}

# Execute main function with all arguments
main "$@"

