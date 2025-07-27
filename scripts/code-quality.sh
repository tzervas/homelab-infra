#!/bin/bash
# Comprehensive code quality script for homelab infrastructure
# Supports both local development and CI environments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
export PROJECT_ROOT

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

# Default options
FIX_MODE=false
VERBOSE=false
CI_MODE=false
SKIP_TESTS=false
FAIL_FAST=${FAIL_FAST:-${CI_MODE}}
TARGETS=()

# Configuration with defaults
MAX_PYTHON_FILES=${MAX_PYTHON_FILES:-0}  # 0 means no limit
MAX_SHELL_FILES=${MAX_SHELL_FILES:-0}   # 0 means no limit
MAX_JSON_FILES=${MAX_JSON_FILES:-0}     # 0 means no limit

# Parse command line arguments
show_help() {
  cat << EOF
Usage: $0 [OPTIONS] [TARGETS...]

Comprehensive code quality checking and fixing for homelab infrastructure.

OPTIONS:
    --fix              Apply safe auto-fixes where possible
    --verbose          Enable verbose output
    --ci               Run in CI mode (stricter, no fixes)
    --skip-tests       Skip running tests
    --max-py-files N   Maximum Python files to check (0 = no limit)
    --max-sh-files N   Maximum shell files to check (0 = no limit)
    --max-json-files N Maximum JSON files to check (0 = no limit)
    --fail-fast       Exit immediately on test failures (default: true in CI)
    --no-fail-fast    Continue on test failures
    --help             Show this help message

TARGETS:
    python          Run Python-specific checks (ruff, mypy, bandit)
    shell           Run shell script checks (shellcheck, shfmt)
    yaml            Run YAML/JSON validation (yamllint, prettier)
    ansible         Run Ansible-specific validation (ansible-lint)
    terraform       Run Terraform validation (fmt, validate, tflint)
    security        Run security scans (gitleaks, detect-secrets, bandit)
    docs            Run documentation checks (markdownlint)
    pre-commit      Run all pre-commit hooks
    homelab         Run homelab-specific validations
    all             Run all checks (default)

EXAMPLES:
    $0                          # Run all checks
    $0 --fix python shell       # Fix Python and shell issues
    $0 --ci all                 # Run in CI mode
    $0 --verbose security       # Verbose security scan

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --fix)
      FIX_MODE=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --ci)
      CI_MODE=true
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --max-py-files)
      shift
      MAX_PYTHON_FILES=$1
      shift
      ;;
    --max-sh-files)
      shift
      MAX_SHELL_FILES=$1
      shift
      ;;
    --max-json-files)
      shift
      MAX_JSON_FILES=$1
      shift
      ;;
    --fail-fast)
      FAIL_FAST=true
      shift
      ;;
    --no-fail-fast)
      FAIL_FAST=false
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      TARGETS+=("$1")
      shift
      ;;
  esac
done

# Default to 'all' if no targets specified
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=("all")
fi

# Check dependencies
check_dependencies() {
  local deps=("uv" "python3")
  local missing=()

  for dep in "${deps[@]}"; do
    if ! command -v "$dep" &> /dev/null; then
      missing+=("$dep")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    log_error "Missing dependencies: ${missing[*]}"
    log_info "Install with: uv tool install pre-commit ruff mypy bandit"
    exit 1
  fi
}

# Python code quality
run_python_checks() {
  log_info "Running Python code quality checks..."

  local python_files
  local find_cmd="find . -type f -name \"*.py\" -not -path \"./untracked_backup/*\" -not -path \"./examples/*\" -not -path \"./venv/*\" -not -path \"./.pytest_cache/*\" -not -path \"*/__pycache__/*\""

  if [[ "$MAX_PYTHON_FILES" -gt 0 ]]; then
    if [[ "$VERBOSE" == true ]]; then
      log_info "Limiting to $MAX_PYTHON_FILES Python files"
    fi
    python_files=$(eval "$find_cmd" | head -n "$MAX_PYTHON_FILES")
  else
    python_files=$(eval "$find_cmd")
  fi

  local total_files
  total_files=$(echo "$python_files" | wc -l)
  log_info "Found $total_files Python files to check"

  if [[ -z "$python_files" ]]; then
    log_warning "No Python files found"
    return 0
  fi

  # Ruff linting and formatting
  if command -v ruff &> /dev/null; then
    log_info "Running Ruff linter..."
    if [[ "$FIX_MODE" == true ]]; then
      ruff check --fix --unsafe-fixes . || log_warning "Ruff found issues (some may be fixed)"
      ruff format . || log_warning "Ruff formatting had issues"
    else
      ruff check . || log_error "Ruff found linting issues"
      ruff format --check . || log_error "Ruff found formatting issues"
    fi
  else
    log_warning "Ruff not available, skipping Python linting"
  fi

  # Type checking with MyPy
  if command -v mypy &> /dev/null && [[ "$CI_MODE" == false ]]; then
    log_info "Running MyPy type checking..."
    mypy scripts/testing/ --ignore-missing-imports || log_warning "MyPy found type issues"
  fi

  # Security scanning with Bandit
  if command -v bandit &> /dev/null; then
    log_info "Running Bandit security scan..."
    bandit -r scripts/ -f json -o bandit-report.json || log_warning "Bandit found security issues"
  fi

  log_success "Python checks completed"
}

# Shell script quality
run_shell_checks() {
  log_info "Running shell script quality checks..."

  local shell_files
  local find_cmd="find . -type f -name \"*.sh\" -not -path \"./untracked_backup/*\" -not -path \"./venv/*\""

  if [[ "$MAX_SHELL_FILES" -gt 0 ]]; then
    if [[ "$VERBOSE" == true ]]; then
      log_info "Limiting to $MAX_SHELL_FILES shell files"
    fi
    shell_files=$(eval "$find_cmd" | head -n "$MAX_SHELL_FILES")
  else
    shell_files=$(eval "$find_cmd")
  fi

  local total_files
  total_files=$(echo "$shell_files" | wc -l)
  log_info "Found $total_files shell files to check"

  if [[ -z "$shell_files" ]]; then
    log_warning "No shell files found"
    return 0
  fi

  # ShellCheck linting
  if command -v shellcheck &> /dev/null; then
    log_info "Running ShellCheck..."
    # shellcheck disable=SC2086
    shellcheck -e SC1091 -e SC2034 -e SC2086 -e SC2155 $shell_files || log_warning "ShellCheck found issues"
  else
    log_warning "ShellCheck not available"
  fi

  # Shell formatting with shfmt
  if command -v shfmt &> /dev/null; then
    log_info "Running shfmt..."
    if [[ "$FIX_MODE" == true ]]; then
      # shellcheck disable=SC2086
      shfmt -w -s -i 2 -ci $shell_files || log_warning "shfmt formatting had issues"
    else
      # shellcheck disable=SC2086
      shfmt -d -s -i 2 -ci $shell_files || log_error "Shell files need formatting"
    fi
  else
    log_warning "shfmt not available"
  fi

  log_success "Shell checks completed"
}

# YAML/JSON validation
run_yaml_checks() {
  log_info "Running YAML/JSON validation..."

  # YAML linting
  if command -v yamllint &> /dev/null; then
    log_info "Running yamllint..."
    yamllint -d relaxed helm/ kubernetes/ || log_warning "YAML files have formatting issues"
  else
    log_warning "yamllint not available"
  fi

  # JSON validation
  log_info "Checking JSON syntax..."
  
  local json_files
  local find_cmd="find . -type f -name \"*.json\" -not -path \"./untracked_backup/*\" -not -path \"./.vscode/*\" -not -path \"./node_modules/*\" -not -path \"*/.pytest_cache/*\""
  
  if [[ "$MAX_JSON_FILES" -gt 0 ]]; then
    if [[ "$VERBOSE" == true ]]; then
      log_info "Limiting to $MAX_JSON_FILES JSON files"
    fi
    json_files=$(eval "$find_cmd" | head -n "$MAX_JSON_FILES")
  else
    json_files=$(eval "$find_cmd")
  fi

  local total_files
  total_files=$(echo "$json_files" | wc -l)
  log_info "Found $total_files JSON files to check"

  if [[ -z "$json_files" ]]; then
    log_warning "No JSON files found"
    return 0
  fi

  # Check each JSON file for validity
  local invalid_count=0
  for file in $json_files; do
    if ! python3 -m json.tool "$file" > /dev/null 2>/dev/null; then
      log_error "Invalid JSON: $file"
      ((invalid_count++))
    elif [[ "$VERBOSE" == true ]]; then
      log_info "Valid JSON: $file"
    fi
  done

  # Report results
  if [[ $invalid_count -eq 0 ]]; then
    log_success "All JSON files are valid"
  else
    log_warning "Found $invalid_count invalid JSON files"
  fi

  # Check if we hit the file limit
  if [[ "$MAX_JSON_FILES" -gt 0 ]]; then
    local actual_total
    actual_total=$(eval "$find_cmd" | wc -l)
    if [[ $actual_total -gt $total_files ]]; then
      log_warning "Only checked $total_files of $actual_total JSON files (increase --max-json-files to check more)"
    fi
  fi

  log_success "YAML/JSON checks completed"
}

# Ansible validation
run_ansible_checks() {
  log_info "Running Ansible validation..."

  if [[ ! -d "ansible" ]]; then
    log_warning "No ansible directory found"
    return 0
  fi

  if command -v ansible-lint &> /dev/null; then
    log_info "Running ansible-lint..."
    if [[ "$FIX_MODE" == true ]]; then
      ansible-lint --fix ansible/ || log_warning "Ansible-lint found issues (some may be fixed)"
    else
      ansible-lint ansible/ || log_warning "Ansible-lint found issues"
    fi
  else
    log_warning "ansible-lint not available"
  fi

  log_success "Ansible checks completed"
}

# Terraform validation
run_terraform_checks() {
  log_info "Running Terraform validation..."

  if [[ ! -d "terraform" ]]; then
    log_warning "No terraform directory found"
    return 0
  fi

  cd terraform || return 1

  if command -v terraform &> /dev/null; then
    log_info "Running terraform fmt..."
    if [[ "$FIX_MODE" == true ]]; then
      terraform fmt -recursive .
    else
      terraform fmt -check -recursive . || log_error "Terraform files need formatting"
    fi

    log_info "Running terraform validate..."
    terraform init -backend=false > /dev/null
    terraform validate || log_error "Terraform validation failed"
  else
    log_warning "terraform not available"
  fi

  cd "$PROJECT_ROOT" || return 1
  log_success "Terraform checks completed"
}

# Security scans
run_security_checks() {
  log_info "Running security scans..."

  # Gitleaks
  if command -v gitleaks &> /dev/null; then
    log_info "Running gitleaks..."
    gitleaks detect --verbose || log_warning "Gitleaks found potential secrets"
  else
    log_warning "gitleaks not available"
  fi

  # detect-secrets
  if command -v detect-secrets &> /dev/null; then
    log_info "Running detect-secrets..."
    if [[ ! -f .secrets.baseline ]]; then
      detect-secrets scan --baseline .secrets.baseline
    fi
    detect-secrets audit .secrets.baseline || log_warning "Secrets detection found issues"
  else
    log_warning "detect-secrets not available"
  fi

  log_success "Security checks completed"
}

# Documentation checks
run_docs_checks() {
  log_info "Running documentation checks..."

  local md_files
  md_files=$(find . -name "*.md" -not -path "./untracked_backup/*" -not -path "./examples/*")

  if command -v markdownlint &> /dev/null; then
    log_info "Running markdownlint..."
    if [[ "$FIX_MODE" == true ]]; then
      # shellcheck disable=SC2086
      markdownlint --fix $md_files || log_warning "Markdown files had issues (some may be fixed)"
    else
      # shellcheck disable=SC2086
      markdownlint $md_files || log_warning "Markdown files have formatting issues"
    fi
  else
    log_warning "markdownlint not available"
  fi

  log_success "Documentation checks completed"
}

# Pre-commit hooks
run_precommit_checks() {
  log_info "Running pre-commit hooks..."

  if command -v pre-commit &> /dev/null; then
    if [[ "$FIX_MODE" == true ]]; then
      pre-commit run --all-files || log_warning "Pre-commit found issues (some may be fixed)"
    else
      pre-commit run --all-files || log_error "Pre-commit hooks failed"
    fi
  else
    log_warning "pre-commit not available"
  fi

  log_success "Pre-commit checks completed"
}

# Homelab-specific validations
run_homelab_checks() {
  log_info "Running homelab-specific validations..."

  # Configuration validation
  if [[ -f "scripts/testing/config_validator.py" ]]; then
    log_info "Running configuration validator..."
    python3 scripts/testing/config_validator.py || log_warning "Configuration validation found issues"
  fi

  # Security context check
  log_info "Running security context check..."
  python3 scripts/testing/rootless_compatibility.py --deployment-mode auto --log-level WARN || log_warning "Security context check found issues"

  # Helm chart validation
  if command -v helm &> /dev/null; then
    log_info "Running Helm chart validation..."
    find helm/charts -name "Chart.yaml" -exec dirname {} \; | while read -r chart; do
      helm lint "$chart" || log_warning "Helm chart validation failed for $chart"
    done
  fi

  log_success "Homelab checks completed"
}

# Run tests
run_tests() {
  if [[ "$SKIP_TESTS" == true ]]; then
    log_info "Skipping tests (--skip-tests)"
    return 0
  fi

  log_info "Running tests..."
  log_info "Fail-fast mode: $FAIL_FAST"

  if ! command -v pytest &> /dev/null; then
    if [[ "$CI_MODE" == true ]] || [[ "$FAIL_FAST" == true ]]; then
      log_error "pytest not available in CI/fail-fast mode. Exiting."
      exit 1
    else
      log_warning "pytest not available, skipping tests"
      return 0
    fi
  fi

  # Run pytest with detailed output
  if ! pytest scripts/testing/ -v; then
    if [[ "$FAIL_FAST" == true ]]; then
      log_error "Tests failed in fail-fast mode. Exiting."
      exit 1
    else
      log_warning "Tests failed but continuing due to no-fail-fast mode."
    fi
  else
    log_success "All tests passed!"
  fi

  log_success "Tests completed"
}

# Main execution
main() {
  log_info "Starting code quality checks for homelab infrastructure"
  log_info "Project root: $PROJECT_ROOT"
  log_info "Fix mode: $FIX_MODE"
  log_info "CI mode: $CI_MODE"
  log_info "Fail-fast mode: $FAIL_FAST"
  log_info "Targets: ${TARGETS[*]}"
  [[ "$MAX_PYTHON_FILES" -gt 0 ]] && log_info "Max Python files: $MAX_PYTHON_FILES"
  [[ "$MAX_SHELL_FILES" -gt 0 ]] && log_info "Max shell files: $MAX_SHELL_FILES"
  [[ "$MAX_JSON_FILES" -gt 0 ]] && log_info "Max JSON files: $MAX_JSON_FILES"

  check_dependencies

  cd "$PROJECT_ROOT" || exit 1

  # Run selected targets
  for target in "${TARGETS[@]}"; do
    case $target in
      python)
        run_python_checks
        ;;
      shell)
        run_shell_checks
        ;;
      yaml)
        run_yaml_checks
        ;;
      ansible)
        run_ansible_checks
        ;;
      terraform)
        run_terraform_checks
        ;;
      security)
        run_security_checks
        ;;
      docs)
        run_docs_checks
        ;;
      pre-commit)
        run_precommit_checks
        ;;
      homelab)
        run_homelab_checks
        ;;
      all)
        run_python_checks
        run_shell_checks
        run_yaml_checks
        run_ansible_checks
        run_terraform_checks
        run_security_checks
        run_docs_checks
        run_homelab_checks
        run_tests
        ;;
      *)
        log_error "Unknown target: $target"
        show_help
        exit 1
        ;;
    esac
  done

  log_success "Code quality checks completed!"

  if [[ "$FIX_MODE" == true ]]; then
    log_info "Some issues may have been automatically fixed"
    log_info "Review changes and commit if appropriate"
  fi
}

# Run main function
main "$@"
