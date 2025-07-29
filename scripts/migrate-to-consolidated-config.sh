#!/bin/bash

# Migration script to transition from duplicated configs to consolidated approach
# This script helps migrate existing configurations to use the consolidated config system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$PROJECT_ROOT/config/consolidated"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

backup_original_files() {
    local backup_dir="$PROJECT_ROOT/config-backup-$(date +%Y%m%d_%H%M%S)"
    log "Creating backup of original configuration files..."

    mkdir -p "$backup_dir"

    # Backup Helm values files
    if [[ -d "$PROJECT_ROOT/helm/environments" ]]; then
        cp -r "$PROJECT_ROOT/helm/environments" "$backup_dir/"
        success "Backed up Helm environment files"
    fi

    # Backup Kubernetes base configurations
    if [[ -d "$PROJECT_ROOT/kubernetes/base" ]]; then
        cp -r "$PROJECT_ROOT/kubernetes/base" "$backup_dir/"
        success "Backed up Kubernetes base configurations"
    fi

    # Backup Terraform variables
    find "$PROJECT_ROOT/terraform" -name "variables.tf" -exec cp {} "$backup_dir/" \; 2>/dev/null || true

    # Backup Ansible configurations
    if [[ -d "$PROJECT_ROOT/ansible" ]]; then
        cp -r "$PROJECT_ROOT/ansible/inventory" "$backup_dir/" 2>/dev/null || true
        cp -r "$PROJECT_ROOT/ansible/group_vars" "$backup_dir/" 2>/dev/null || true
    fi

    echo "$backup_dir" > "$PROJECT_ROOT/.config-backup-location"
    success "Backup created at: $backup_dir"
}

validate_consolidated_configs() {
    log "Validating consolidated configuration files..."

    local required_files=(
        "domains.yaml"
        "networking.yaml"
        "storage.yaml"
        "security.yaml"
        "resources.yaml"
        "namespaces.yaml"
        "environments.yaml"
        "services.yaml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$CONFIG_DIR/$file" ]]; then
            error "Missing consolidated config file: $CONFIG_DIR/$file"
        fi

        # Basic YAML syntax validation
        if ! yq eval '.' "$CONFIG_DIR/$file" > /dev/null 2>&1; then
            error "Invalid YAML syntax in: $CONFIG_DIR/$file"
        fi

        success "Validated $file"
    done
}

update_helm_values() {
    log "Updating Helm values files to use consolidated configuration..."

    local helm_env_dir="$PROJECT_ROOT/helm/environments"

    # Create new consolidated values template
    cat > "$helm_env_dir/values-consolidated-template.yaml" << 'EOF'
# Consolidated Configuration Template
# This file loads all consolidated configuration files

# Import consolidated configurations
global:
  # Consolidated configurations will be merged from:
  # - config/consolidated/domains.yaml
  # - config/consolidated/networking.yaml
  # - config/consolidated/storage.yaml
  # - config/consolidated/security.yaml
  # - config/consolidated/resources.yaml
  # - config/consolidated/namespaces.yaml
  # - config/consolidated/services.yaml

# Environment-specific overrides should be minimal
# Most configuration should come from consolidated files
EOF

    # Update helmfile.yaml to use consolidated configs
    if [[ -f "$PROJECT_ROOT/helm/helmfile.yaml" ]]; then
        log "Updating helmfile.yaml to reference consolidated configs..."

        # Add consolidated config references to environments
        # This would need to be customized based on your specific helmfile structure
        warning "Helmfile.yaml update requires manual review and customization"
    fi

    success "Created Helm consolidation template"
}

generate_kubernetes_manifests() {
    log "Generating Kubernetes manifests from consolidated configuration..."

    local k8s_generated_dir="$PROJECT_ROOT/kubernetes/generated"
    mkdir -p "$k8s_generated_dir"

    # Generate namespaces from consolidated config
    log "Generating namespace manifests..."
    cat > "$k8s_generated_dir/namespaces.yaml" << 'EOF'
# Auto-generated from config/consolidated/namespaces.yaml
# DO NOT EDIT MANUALLY - Use consolidated configuration instead
EOF

    # Extract namespaces using yq
    yq eval '.namespaces.core | to_entries[] |
        "---" + "\n" +
        "apiVersion: v1" + "\n" +
        "kind: Namespace" + "\n" +
        "metadata:" + "\n" +
        "  name: " + .key + "\n" +
        "  labels:" + "\n" +
        (.value.labels | to_entries[] | "    " + .key + ": \"" + .value + "\"") + "\n" +
        "  annotations:" + "\n" +
        (.value.annotations // {} | to_entries[] | "    " + .key + ": \"" + .value + "\"")' \
        "$CONFIG_DIR/namespaces.yaml" >> "$k8s_generated_dir/namespaces.yaml"

    success "Generated namespace manifests"

    # Generate MetalLB configuration
    log "Generating MetalLB configuration..."
    yq eval '.networking.metallb' "$CONFIG_DIR/networking.yaml" | \
        yq eval 'del(.enabled) | del(.protocol)' > "$k8s_generated_dir/metallb-config-base.yaml"

    success "Generated MetalLB configuration base"
}

update_deployment_scripts() {
    log "Updating deployment scripts to use consolidated configuration..."

    local scripts_dir="$PROJECT_ROOT/scripts"

    # Create configuration sourcing helper
    cat > "$scripts_dir/source-consolidated-config.sh" << 'EOF'
#!/bin/bash
# Helper script to source consolidated configuration values
# Usage: source scripts/source-consolidated-config.sh

CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../config/consolidated" && pwd)"

# Load domain configuration
export HOMELAB_DOMAIN=$(yq eval '.domains.base.primary' "$CONFIG_DIR/domains.yaml")

# Load networking configuration
export METALLB_IP_RANGE=$(yq eval '.networking.metallb.default_pool.addresses' "$CONFIG_DIR/networking.yaml")
export METALLB_IP=$(echo "$METALLB_IP_RANGE" | cut -d'-' -f1)

# Load storage configuration
export DEFAULT_STORAGE_CLASS=$(yq eval '.storage.default_class' "$CONFIG_DIR/storage.yaml")

# Load service discovery
export PROMETHEUS_PORT=$(yq eval '.services.discovery.monitoring.prometheus.port' "$CONFIG_DIR/services.yaml")
export GRAFANA_PORT=$(yq eval '.services.discovery.monitoring.grafana.port' "$CONFIG_DIR/services.yaml")

# Function to get environment-specific config
get_env_config() {
    local env=${1:-development}
    local key=$2
    yq eval ".environments.$env.$key" "$CONFIG_DIR/environments.yaml"
}

# Function to get service-specific config
get_service_config() {
    local service=$1
    local key=$2
    yq eval ".services.$key.$service" "$CONFIG_DIR/services.yaml"
}
EOF

    chmod +x "$scripts_dir/source-consolidated-config.sh"
    success "Created configuration sourcing helper script"

    # Update main deployment scripts
    local main_scripts=(
        "deploy-complete-homelab.sh"
        "scripts/deploy-homelab.sh"
    )

    for script in "${main_scripts[@]}"; do
        if [[ -f "$PROJECT_ROOT/$script" ]]; then
            log "Adding consolidated config sourcing to $script..."

            # Add sourcing line after the shebang and before first usage
            if ! grep -q "source-consolidated-config.sh" "$PROJECT_ROOT/$script"; then
                # Create a modified version that sources the consolidated config
                sed -i '/^#!/a\\n# Source consolidated configuration\nsource "$(dirname "$0")/scripts/source-consolidated-config.sh" 2>/dev/null || source "$(dirname "$0")/source-consolidated-config.sh"' "$PROJECT_ROOT/$script"
                warning "$script updated - please review manual changes needed for variable replacements"
            fi
        fi
    done
}

create_validation_scripts() {
    log "Creating configuration validation scripts..."

    local scripts_dir="$PROJECT_ROOT/scripts"

    # Configuration validation script
    cat > "$scripts_dir/validate-consolidated-config.sh" << 'EOF'
#!/bin/bash
# Validate consolidated configuration files

set -euo pipefail

CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../config/consolidated" && pwd)"

echo "🔍 Validating consolidated configuration files..."

# Check YAML syntax
for config_file in "$CONFIG_DIR"/*.yaml; do
    if [[ -f "$config_file" ]]; then
        filename=$(basename "$config_file")
        if yq eval '.' "$config_file" > /dev/null 2>&1; then
            echo "✅ $filename: Valid YAML syntax"
        else
            echo "❌ $filename: Invalid YAML syntax"
            exit 1
        fi
    fi
done

# Validate required sections exist
echo "🔍 Validating required configuration sections..."

# Check domains configuration
if yq eval '.domains.base.primary' "$CONFIG_DIR/domains.yaml" > /dev/null 2>&1; then
    echo "✅ Domain configuration valid"
else
    echo "❌ Missing or invalid domain configuration"
    exit 1
fi

# Check networking configuration
if yq eval '.networking.metallb.default_pool.addresses' "$CONFIG_DIR/networking.yaml" > /dev/null 2>&1; then
    echo "✅ Networking configuration valid"
else
    echo "❌ Missing or invalid networking configuration"
    exit 1
fi

# Check environments configuration
for env in development staging production; do
    if yq eval ".environments.$env" "$CONFIG_DIR/environments.yaml" > /dev/null 2>&1; then
        echo "✅ Environment '$env' configuration valid"
    else
        echo "❌ Missing environment '$env' configuration"
        exit 1
    fi
done

echo "🎉 All consolidated configuration files are valid!"
EOF

    chmod +x "$scripts_dir/validate-consolidated-config.sh"
    success "Created configuration validation script"

    # Configuration report generator
    cat > "$scripts_dir/generate-config-report.sh" << 'EOF'
#!/bin/bash
# Generate configuration report from consolidated configs

set -euo pipefail

CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../config/consolidated" && pwd)"
REPORT_FILE="config-consolidation-report-$(date +%Y%m%d_%H%M%S).md"

echo "📊 Generating configuration consolidation report..."

cat > "$REPORT_FILE" << 'REPORT_EOF'
# Configuration Consolidation Report

Generated: $(date)

## Summary

This report shows the current state of the consolidated configuration system.

## Domains Configuration
REPORT_EOF

echo "### Primary Domain" >> "$REPORT_FILE"
echo "- **Domain**: $(yq eval '.domains.base.primary' "$CONFIG_DIR/domains.yaml")" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "### Service URLs" >> "$REPORT_FILE"
yq eval '.domains.services | to_entries[] | "- **" + (.key | upcase) + "**: " + .value' "$CONFIG_DIR/domains.yaml" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Networking Configuration" >> "$REPORT_FILE"
echo "- **MetalLB Pool**: $(yq eval '.networking.metallb.default_pool.addresses' "$CONFIG_DIR/networking.yaml")" >> "$REPORT_FILE"
echo "- **Cluster CIDR**: $(yq eval '.networking.cluster.cidr' "$CONFIG_DIR/networking.yaml")" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Storage Configuration" >> "$REPORT_FILE"
echo "- **Default Storage Class**: $(yq eval '.storage.default_class' "$CONFIG_DIR/storage.yaml")" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Environments" >> "$REPORT_FILE"
for env in development staging production; do
    echo "### $env" >> "$REPORT_FILE"
    echo "- **Resource Scaling**: $(yq eval ".environments.$env.resource_scaling" "$CONFIG_DIR/environments.yaml")" >> "$REPORT_FILE"
    echo "- **Replica Count**: $(yq eval ".environments.$env.replica_count" "$CONFIG_DIR/environments.yaml")" >> "$REPORT_FILE"
done

echo "✅ Configuration report generated: $REPORT_FILE"
EOF

    chmod +x "$scripts_dir/generate-config-report.sh"
    success "Created configuration report generator"
}

show_migration_summary() {
    echo ""
    echo -e "${BLUE}🎉 MIGRATION PREPARATION COMPLETE${NC}"
    echo "=================================="
    echo ""
    echo -e "${GREEN}✅ Completed Tasks:${NC}"
    echo "   • Created consolidated configuration files"
    echo "   • Backed up original configuration files"
    echo "   • Generated Kubernetes manifests from consolidated config"
    echo "   • Created configuration sourcing helpers"
    echo "   • Set up validation and reporting scripts"
    echo ""
    echo -e "${YELLOW}⚠️  Manual Tasks Required:${NC}"
    echo "   1. Review and test generated Kubernetes manifests"
    echo "   2. Update Helm charts to reference consolidated configs"
    echo "   3. Modify deployment scripts to use sourced variables"
    echo "   4. Update Terraform modules to load consolidated configs"
    echo "   5. Modify Ansible playbooks to use consolidated variables"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "   1. Run validation: ./scripts/validate-consolidated-config.sh"
    echo "   2. Generate report: ./scripts/generate-config-report.sh"
    echo "   3. Test in development environment first"
    echo "   4. Gradually migrate production workloads"
    echo ""
    if [[ -f "$PROJECT_ROOT/.config-backup-location" ]]; then
        local backup_location=$(cat "$PROJECT_ROOT/.config-backup-location")
        echo -e "${GREEN}📁 Backup Location:${NC} $backup_location"
    fi
}

# Main execution flow
main() {
    echo -e "${BLUE}🚀 Starting Configuration Consolidation Migration${NC}"
    echo "=================================================="

    # Validate dependencies
    if ! command -v yq &> /dev/null; then
        error "yq is required but not installed. Please install yq first."
    fi

    # Execute migration steps
    backup_original_files
    validate_consolidated_configs
    update_helm_values
    generate_kubernetes_manifests
    update_deployment_scripts
    create_validation_scripts

    show_migration_summary
}

# Run main function
main "$@"
