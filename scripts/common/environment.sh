#!/bin/bash

# MIT License
#
# Copyright (c) 2025 Tyler Zervas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Centralized Environment Configuration Loader
# Provides idempotent environment variable loading with priority support
# Priority: CLI args > .env.private.local > .env.local > .env.{environment} > .env

set -euo pipefail

# Script directory detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default environment values
DEFAULT_ENVIRONMENT="development"
DEFAULT_LOG_LEVEL="INFO"
DEFAULT_DEBUG="false"

# Environment configuration state
ENV_LOADED=""
ENV_FILES_LOADED=()

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_debug() {
    [[ "${DEBUG:-false}" == "true" ]] && echo -e "${BLUE}[DEBUG]${NC} $*" >&2
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Check if environment is already loaded
is_env_loaded() {
    [[ -n "${ENV_LOADED:-}" ]]
}

# Validate environment file format
validate_env_file() {
    local env_file="$1"

    if [[ ! -f "$env_file" ]]; then
        return 1
    fi

    # Check for common syntax issues
    if grep -q "^[[:space:]]*[^#=]*=" "$env_file" 2>/dev/null; then
        # Basic validation passed
        log_debug "Environment file format validated: $env_file"
        return 0
    else
        log_warn "Environment file format validation failed: $env_file"
        return 1
    fi
}

# Load a single environment file if it exists and is valid
load_env_file() {
    local env_file="$1"
    local priority="${2:-standard}"

    if [[ ! -f "$env_file" ]]; then
        log_debug "Environment file not found: $env_file"
        return 0
    fi

    if ! validate_env_file "$env_file"; then
        log_warn "Skipping invalid environment file: $env_file"
        return 0
    fi

    log_debug "Loading environment file ($priority): $env_file"

    # Create a temporary file with only valid variable assignments
    local temp_env
    temp_env=$(mktemp)

    # Extract valid environment variable assignments
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$env_file" | grep -v '^#' > "$temp_env" || true

    if [[ -s "$temp_env" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$temp_env"
        set +a

        ENV_FILES_LOADED+=("$env_file")
        log_debug "Successfully loaded: $env_file"
    fi

    rm -f "$temp_env"
}

# Initialize default environment variables
init_defaults() {
    # Only set if not already defined
    export ENVIRONMENT="${ENVIRONMENT:-${DEFAULT_ENVIRONMENT}}"
    export LOG_LEVEL="${LOG_LEVEL:-${DEFAULT_LOG_LEVEL}}"
    export DEBUG="${DEBUG:-${DEFAULT_DEBUG}}"

    # Project-specific defaults
    export PROJECT_ROOT="${PROJECT_ROOT}"
    export HOMELAB_SERVER_IP="${HOMELAB_SERVER_IP:-192.168.16.26}"
    export METALLB_IP="${METALLB_IP:-192.168.16.100}"
    export KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/config}"

    log_debug "Default environment variables initialized"
}

# Load environment configuration with priority
load_environment() {
    local environment="${1:-${ENVIRONMENT:-${DEFAULT_ENVIRONMENT}}}"
    local force_reload="${2:-false}"

    # Skip if already loaded and not forcing reload
    if is_env_loaded && [[ "$force_reload" != "true" ]]; then
        log_debug "Environment already loaded, skipping"
        return 0
    fi

    log_info "Loading environment configuration for: $environment"

    # Initialize defaults first
    init_defaults

    # Load environment files in priority order (lowest to highest priority)

    # 1. Base .env file (lowest priority)
    load_env_file "$PROJECT_ROOT/.env" "base"

    # 2. Environment-specific .env file
    load_env_file "$PROJECT_ROOT/.env.$environment" "environment-specific"

    # 3. Local .env file (overrides environment-specific)
    load_env_file "$PROJECT_ROOT/.env.local" "local"

    # 4. Private configuration from external source
    load_env_file "$PROJECT_ROOT/.private-config/.env.private" "private"

    # 5. Private local configuration (highest priority)
    load_env_file "$PROJECT_ROOT/.env.private.local" "private-local"

    # Update ENVIRONMENT variable in case it was overridden
    export ENVIRONMENT="$environment"

    # Mark environment as loaded
    ENV_LOADED="$environment"

    log_info "Environment configuration loaded successfully"

    # Show loaded files if debug is enabled
    if [[ "${DEBUG:-false}" == "true" ]]; then
        log_debug "Loaded environment files:"
        for file in "${ENV_FILES_LOADED[@]}"; do
            log_debug "  - $file"
        done
    fi
}

# Validate required environment variables
validate_required_vars() {
    local required_vars=("$@")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        log_error "Please set these variables in your .env file or environment"
        return 1
    fi

    log_debug "All required environment variables are set"
    return 0
}

# Show current environment configuration
show_environment() {
    local show_sensitive="${1:-false}"

    echo "Environment Configuration:"
    echo "========================="
    echo "Environment: ${ENVIRONMENT}"
    echo "Project Root: ${PROJECT_ROOT}"
    echo "Debug: ${DEBUG}"
    echo "Log Level: ${LOG_LEVEL}"
    echo ""

    if [[ ${#ENV_FILES_LOADED[@]} -gt 0 ]]; then
        echo "Loaded Files:"
        for file in "${ENV_FILES_LOADED[@]}"; do
            echo "  - $file"
        done
        echo ""
    fi

    if [[ "$show_sensitive" == "true" ]]; then
        echo "Key Variables:"
        echo "  HOMELAB_SERVER_IP: ${HOMELAB_SERVER_IP}"
        echo "  METALLB_IP: ${METALLB_IP}"
        echo "  KUBECONFIG: ${KUBECONFIG}"
    fi
}

# Check if we're being sourced or executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being executed directly
    case "${1:-load}" in
        "load")
            load_environment "${2:-}"
            show_environment
            ;;
        "show")
            if is_env_loaded; then
                show_environment "${2:-false}"
            else
                log_warn "Environment not loaded yet"
                exit 1
            fi
            ;;
        "validate")
            shift
            validate_required_vars "$@"
            ;;
        "help"|"-h"|"--help")
            cat <<EOF
Environment Configuration Loader

USAGE:
    source $0                    # Load environment (in sourcing script)
    $0 load [environment]        # Load and show environment
    $0 show [show_sensitive]     # Show current environment
    $0 validate VAR1 VAR2...     # Validate required variables

ENVIRONMENTS:
    development (default)
    staging
    production

ENVIRONMENT FILES (in priority order):
    .env                        # Base configuration
    .env.[environment]          # Environment-specific
    .env.local                  # Local overrides
    .private-config/.env.private # Private configuration
    .env.private.local          # Local private (highest priority)

EXAMPLES:
    source $0                           # Load default environment
    $0 load production                  # Load production environment
    $0 show true                        # Show environment with sensitive vars
    $0 validate REQUIRED_VAR OTHER_VAR  # Validate required variables
EOF
            ;;
        *)
            log_error "Unknown command: $1"
            exit 1
            ;;
    esac
else
    # Script is being sourced - load environment automatically
    load_environment "${ENVIRONMENT:-${DEFAULT_ENVIRONMENT}}"
fi
