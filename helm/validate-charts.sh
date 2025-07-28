#!/bin/bash
set -euo pipefail

# Helm Chart Validation Script
# This script validates the enhanced Helm architecture for security and best practices

echo "🔍 Starting Helm chart validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if required tools are installed
check_dependencies() {
    print_status $BLUE "📋 Checking dependencies..."

    local deps=("helm" "helmfile" "kubectl" "yq")
    for dep in "${deps[@]}"; do
        if command -v "$dep" &> /dev/null; then
            print_status $GREEN "✅ $dep is installed"
        else
            print_status $RED "❌ $dep is not installed"
            exit 1
        fi
    done
}

# Function to validate Chart.yaml files
validate_chart_metadata() {
    print_status $BLUE "📊 Validating Chart.yaml files..."

    find charts/ -name "Chart.yaml" | while read -r chart_file; do
        local chart_dir=$(dirname "$chart_file")
        local chart_name=$(basename "$chart_dir")

        echo "  Validating $chart_name..."

        # Check required fields
        if ! yq e '.apiVersion' "$chart_file" | grep -q "v2"; then
            print_status $RED "❌ $chart_name: Missing or invalid apiVersion"
        fi

        if ! yq e '.name' "$chart_file" | grep -q "$chart_name"; then
            print_status $RED "❌ $chart_name: Chart name doesn't match directory"
        fi

        if ! yq e '.description' "$chart_file" | grep -q "."; then
            print_status $RED "❌ $chart_name: Missing description"
        fi

        print_status $GREEN "✅ $chart_name metadata validated"
    done
}

# Function to validate security baseline integration
validate_security_baseline() {
    print_status $BLUE "🔒 Validating security baseline integration..."

    # Check if security-baseline chart exists
    if [[ ! -d "charts/security-baseline" ]]; then
        print_status $RED "❌ Security baseline chart not found"
        exit 1
    fi

    # Check security baseline templates
    local required_templates=(
        "charts/security-baseline/templates/_helpers.tpl"
        "charts/security-baseline/templates/network-policies.yaml"
        "charts/security-baseline/templates/rbac.yaml"
        "charts/security-baseline/templates/hooks/pre-deployment-validation.yaml"
        "charts/security-baseline/templates/hooks/post-deployment-health.yaml"
        "charts/security-baseline/templates/hooks/cert-rotation.yaml"
    )

    for template in "${required_templates[@]}"; do
        if [[ -f "$template" ]]; then
            print_status $GREEN "✅ $template exists"
        else
            print_status $RED "❌ $template missing"
        fi
    done

    # Check if other charts inherit from security baseline
    for chart in charts/*/Chart.yaml; do
        if [[ "$chart" == "charts/security-baseline/Chart.yaml" ]]; then
            continue
        fi

        local chart_name=$(basename $(dirname "$chart"))
        if yq e '.dependencies[] | select(.name == "security-baseline")' "$chart" | grep -q "security-baseline"; then
            print_status $GREEN "✅ $chart_name inherits from security-baseline"
        else
            print_status $YELLOW "⚠️  $chart_name doesn't inherit from security-baseline"
        fi
    done
}

# Function to validate Helm templates
validate_templates() {
    print_status $BLUE "🔧 Validating Helm templates..."

    for chart_dir in charts/*/; do
        local chart_name=$(basename "$chart_dir")
        echo "  Validating templates for $chart_name..."

        if [[ -d "$chart_dir/templates" ]]; then
            # Try to render templates (dry-run)
            if helm template "$chart_name" "$chart_dir" --dry-run &>/dev/null; then
                print_status $GREEN "✅ $chart_name templates render successfully"
            else
                print_status $RED "❌ $chart_name template rendering failed"
                helm template "$chart_name" "$chart_dir" --dry-run || true
            fi
        fi
    done
}

# Function to validate helmfile
validate_helmfile() {
    print_status $BLUE "🚀 Validating helmfile configuration..."

    if [[ -f "helmfile.yaml" ]]; then
        # Check helmfile syntax
        if helmfile -e development lint &>/dev/null; then
            print_status $GREEN "✅ Helmfile syntax is valid"
        else
            print_status $RED "❌ Helmfile syntax validation failed"
            helmfile -e development lint || true
        fi

        # Check if security baseline is deployed first
        if yq e '.releases[0].name' helmfile.yaml | grep -q "security-baseline"; then
            print_status $GREEN "✅ Security baseline is deployed first"
        else
            print_status $YELLOW "⚠️  Security baseline should be deployed first"
        fi

        # Check for hooks
        if yq e '.hooks' helmfile.yaml | grep -q "presync"; then
            print_status $GREEN "✅ Pre-sync hooks configured"
        else
            print_status $YELLOW "⚠️  No pre-sync hooks found"
        fi

        if yq e '.hooks' helmfile.yaml | grep -q "postsync"; then
            print_status $GREEN "✅ Post-sync hooks configured"
        else
            print_status $YELLOW "⚠️  No post-sync hooks found"
        fi
    else
        print_status $RED "❌ helmfile.yaml not found"
        exit 1
    fi
}

# Function to validate environment configurations
validate_environments() {
    print_status $BLUE "🌍 Validating environment configurations..."

    local environments=("dev" "staging" "prod")

    for env in "${environments[@]}"; do
        local env_file="environments/values-${env}.yaml"
        if [[ -f "$env_file" ]]; then
            print_status $GREEN "✅ $env environment configuration exists"

            # Check for security-related configurations
            if yq e '.podSecurityStandards' "$env_file" | grep -q "enforce"; then
                print_status $GREEN "✅ $env has Pod Security Standards configured"
            else
                print_status $YELLOW "⚠️  $env missing Pod Security Standards configuration"
            fi

            if yq e '.global.securityContext' "$env_file" | grep -q "runAsNonRoot"; then
                print_status $GREEN "✅ $env has security context configured"
            else
                print_status $YELLOW "⚠️  $env missing security context configuration"
            fi
        else
            print_status $RED "❌ $env environment configuration missing"
        fi
    done

    # Check for secret templates
    if [[ -f "environments/secrets-dev.yaml.template" ]]; then
        print_status $GREEN "✅ Development secret template exists"
    else
        print_status $YELLOW "⚠️  Development secret template missing"
    fi

    if [[ -f "environments/secrets-prod.yaml.template" ]]; then
        print_status $GREEN "✅ Production secret template exists"
    else
        print_status $YELLOW "⚠️  Production secret template missing"
    fi
}

# Function to validate security configurations
validate_security() {
    print_status $BLUE "🛡️  Validating security configurations..."

    # Check for hardcoded secrets (basic check)
    if grep -r "password.*:" charts/ environments/ --include="*.yaml" | grep -v template | grep -v "CHANGE_ME" | grep -v "example"; then
        print_status $RED "❌ Potential hardcoded secrets found"
    else
        print_status $GREEN "✅ No obvious hardcoded secrets found"
    fi

    # Check for privileged containers
    local privileged_count=$(grep -r "privileged.*true" charts/ --include="*.yaml" | wc -l)
    if [[ "$privileged_count" -gt 0 ]]; then
        print_status $YELLOW "⚠️  Found $privileged_count privileged container configurations"
        print_status $YELLOW "    Review these for necessity and security implications"
    else
        print_status $GREEN "✅ No privileged containers found"
    fi

    # Check for root user configurations
    local root_count=$(grep -r "runAsUser.*0" charts/ --include="*.yaml" | wc -l)
    if [[ "$root_count" -gt 0 ]]; then
        print_status $YELLOW "⚠️  Found $root_count root user configurations"
        print_status $YELLOW "    Review these for necessity and security implications"
    else
        print_status $GREEN "✅ No root user configurations found"
    fi
}

# Function to generate security report
generate_security_report() {
    print_status $BLUE "📊 Generating security report..."

    local report_file="security-report-$(date +%Y%m%d-%H%M%S).txt"

    {
        echo "Helm Security Baseline Report"
        echo "Generated: $(date)"
        echo "==============================="
        echo

        echo "Chart Security Summary:"
        echo "-----------------------"
        for chart_dir in charts/*/; do
            local chart_name=$(basename "$chart_dir")
            echo "Chart: $chart_name"

            # Count security contexts
            local sec_contexts=$(find "$chart_dir" -name "*.yaml" -exec grep -l "securityContext" {} \; | wc -l)
            echo "  Security contexts: $sec_contexts files"

            # Count network policies
            local net_policies=$(find "$chart_dir" -name "*.yaml" -exec grep -l "NetworkPolicy" {} \; | wc -l)
            echo "  Network policies: $net_policies files"

            # Count RBAC resources
            local rbac_resources=$(find "$chart_dir" -name "*.yaml" -exec grep -l "rbac.authorization.k8s.io" {} \; | wc -l)
            echo "  RBAC resources: $rbac_resources files"

            echo
        done

        echo "Environment Security Configuration:"
        echo "-----------------------------------"
        for env in dev staging prod; do
            local env_file="environments/values-${env}.yaml"
            if [[ -f "$env_file" ]]; then
                echo "Environment: $env"
                echo "  Pod Security Standard: $(yq e '.podSecurityStandards.enforce // "not configured"' "$env_file")"
                echo "  TLS Enabled: $(yq e '.global.tls.enabled // "not configured"' "$env_file")"
                echo
            fi
        done

    } > "$report_file"

    print_status $GREEN "✅ Security report generated: $report_file"
}

# Main validation function
main() {
    print_status $BLUE "🚀 Enhanced Helm Architecture Validation"
    print_status $BLUE "=========================================="
    echo

    check_dependencies
    validate_chart_metadata
    validate_security_baseline
    validate_templates
    validate_helmfile
    validate_environments
    validate_security
    generate_security_report

    echo
    print_status $GREEN "🎉 Validation completed!"
    print_status $BLUE "Review any warnings above and address them as needed."
}

# Run main function
main "$@"
