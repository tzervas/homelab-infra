#!/bin/bash

# Kubernetes Manifest and Template Validation Script
# This script validates Helmfile templates for syntax, security, and compliance

set -e

ENVIRONMENT="${1:-development}"
LOG_FILE="validation-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"

echo "🔍 Starting Kubernetes template validation for environment: $ENVIRONMENT" | tee "$LOG_FILE"
echo "📝 Log file: $LOG_FILE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Validation counters
ERRORS=0
WARNINGS=0
SUCCESSES=0

# Function to increment counters
increment_error() {
    ((ERRORS++))
    log_error "$1"
}

increment_warning() {
    ((WARNINGS++))
    log_warning "$1"
}

increment_success() {
    ((SUCCESSES++))
    log_success "$1"
}

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v helmfile &> /dev/null; then
    increment_error "helmfile command not found"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    increment_error "helm command not found"
    exit 1
fi

if ! command -v yq &> /dev/null; then
    log_warning "yq command not found - some validations will be skipped"
fi

increment_success "Prerequisites check completed"

# Check Helmfile syntax
log_info "Validating Helmfile syntax..."
if helmfile --environment "$ENVIRONMENT" list &>> "$LOG_FILE"; then
    increment_success "Helmfile syntax is valid"
else
    increment_error "Helmfile syntax validation failed"
fi

# Template rendering validation for each release
RELEASES=("metallb" "cert-manager" "ingress-nginx" "sealed-secrets" "longhorn" "kube-prometheus-stack" "loki" "promtail" "grafana")

for release in "${RELEASES[@]}"; do
    log_info "Validating release: $release"

    # Template rendering
    if helmfile --environment "$ENVIRONMENT" template --selector "name=$release" --skip-deps > "/tmp/${release}-templates.yaml" 2>> "$LOG_FILE"; then
        increment_success "Templates rendered successfully for $release"

        # YAML syntax validation
        if command -v yq &> /dev/null; then
            if yq eval . "/tmp/${release}-templates.yaml" > /dev/null 2>> "$LOG_FILE"; then
                increment_success "YAML syntax is valid for $release"
            else
                increment_error "YAML syntax validation failed for $release"
            fi
        fi

        # Check for required fields
        if grep -q "apiVersion:" "/tmp/${release}-templates.yaml" && \
           grep -q "kind:" "/tmp/${release}-templates.yaml" && \
           grep -q "metadata:" "/tmp/${release}-templates.yaml"; then
            increment_success "Required Kubernetes fields present for $release"
        else
            increment_error "Missing required Kubernetes fields for $release"
        fi

        # Security context validation
        log_info "Checking security contexts for $release..."

        # Check for runAsNonRoot
        if grep -q "runAsNonRoot.*true" "/tmp/${release}-templates.yaml"; then
            increment_success "runAsNonRoot security context found for $release"
        else
            increment_warning "runAsNonRoot not explicitly set to true for $release"
        fi

        # Check for dropped capabilities
        if grep -q "drop:" "/tmp/${release}-templates.yaml"; then
            increment_success "Capability dropping configured for $release"
        else
            increment_warning "No capability dropping found for $release"
        fi

        # Check for readOnlyRootFilesystem
        if grep -q "readOnlyRootFilesystem.*true" "/tmp/${release}-templates.yaml"; then
            increment_success "readOnlyRootFilesystem configured for $release"
        else
            increment_warning "readOnlyRootFilesystem not configured for $release"
        fi

        # Check for resource limits
        if grep -q "limits:" "/tmp/${release}-templates.yaml"; then
            increment_success "Resource limits configured for $release"
        else
            increment_warning "No resource limits found for $release"
        fi

        # Check for liveness and readiness probes
        if grep -q "livenessProbe:" "/tmp/${release}-templates.yaml" && \
           grep -q "readinessProbe:" "/tmp/${release}-templates.yaml"; then
            increment_success "Health probes configured for $release"
        else
            increment_warning "Health probes missing or incomplete for $release"
        fi

        # Namespace validation
        NAMESPACE=$(grep "namespace:" "/tmp/${release}-templates.yaml" | head -1 | awk '{print $2}' | tr -d '"')
        if [[ -n "$NAMESPACE" ]]; then
            log_info "Release $release uses namespace: $NAMESPACE"
            increment_success "Namespace defined for $release"
        else
            increment_warning "No namespace defined for $release"
        fi

    else
        increment_error "Template rendering failed for $release"
    fi
done

# API version validation
log_info "Validating API versions..."
TEMP_FILE="/tmp/all-templates.yaml"
helmfile --environment "$ENVIRONMENT" template --skip-deps > "$TEMP_FILE" 2>> "$LOG_FILE" || true

if [[ -f "$TEMP_FILE" ]]; then
    # Check for deprecated API versions (common ones)
    DEPRECATED_APIS=(
        "extensions/v1beta1"
        "apps/v1beta1"
        "apps/v1beta2"
        "policy/v1beta1"
        "networking.k8s.io/v1beta1"
    )

    for api in "${DEPRECATED_APIS[@]}"; do
        if grep -q "$api" "$TEMP_FILE"; then
            increment_warning "Deprecated API version found: $api"
        fi
    done

    if ! grep -q "extensions/v1beta1\|apps/v1beta1\|apps/v1beta2\|policy/v1beta1\|networking.k8s.io/v1beta1" "$TEMP_FILE"; then
        increment_success "No deprecated API versions detected"
    fi
fi

# Namespace validation
log_info "Validating namespace definitions..."
REQUIRED_NAMESPACES=("metallb-system" "cert-manager" "ingress-nginx" "longhorn-system" "monitoring" "security-system")

for ns in "${REQUIRED_NAMESPACES[@]}"; do
    if grep -q "namespace.*$ns" helmfile.yaml; then
        increment_success "Required namespace $ns is defined"
    else
        increment_error "Required namespace $ns is missing"
    fi
done

# Security baseline validation
log_info "Validating security baseline configurations..."

# Check for pod security standards in helmfile hooks
if grep -q "pod-security.kubernetes.io/enforce" helmfile.yaml; then
    increment_success "Pod security standards are configured"
else
    increment_warning "Pod security standards not found in helmfile hooks"
fi

# Check for security contexts in values
if grep -q "securityContext" environments/values-"$ENVIRONMENT".yaml 2>/dev/null; then
    increment_success "Security contexts defined in environment values"
else
    increment_warning "Security contexts not found in environment values"
fi

# Final report
echo "" | tee -a "$LOG_FILE"
echo "=================================" | tee -a "$LOG_FILE"
echo "🏁 VALIDATION SUMMARY" | tee -a "$LOG_FILE"
echo "=================================" | tee -a "$LOG_FILE"
echo -e "${GREEN}✅ Successes: $SUCCESSES${NC}" | tee -a "$LOG_FILE"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}❌ Errors: $ERRORS${NC}" | tee -a "$LOG_FILE"
echo "=================================" | tee -a "$LOG_FILE"

# Cleanup temporary files
rm -f /tmp/*-templates.yaml /tmp/all-templates.yaml

# Exit with appropriate code
if [[ $ERRORS -gt 0 ]]; then
    log_error "Validation completed with errors. Check the log file: $LOG_FILE"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    log_warning "Validation completed with warnings. Check the log file: $LOG_FILE"
    exit 0
else
    log_success "Validation completed successfully!"
    exit 0
fi
