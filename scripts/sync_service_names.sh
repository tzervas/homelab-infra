#!/bin/bash

# Script to synchronize service names between config and K8s manifests
# This ensures consistent naming across the infrastructure

# Load service names from config
CONFIG_FILE="config/consolidated/services.yaml"
K8S_DIR="kubernetes/base"

# Function to parse service names from config
parse_service_names() {
    echo "Parsing service names from config..."
    # Use yq to parse YAML if available, fallback to grep
    if command -v yq &> /dev/null; then
        yq '.services.discovery | keys' "$CONFIG_FILE"
    else
        grep -E '^[[:space:]]+[a-zA-Z_]+:' "$CONFIG_FILE" | sed 's/[[:space:]]*\([a-zA-Z_]*\):.*/\1/'
    fi
}

# Function to update K8s manifests
update_manifests() {
    local old_name="$1"
    local new_name="$2"
    local manifest_file="$3"

    echo "Updating $manifest_file: $old_name -> $new_name"
    sed -i "s/name: $old_name/name: $new_name/g" "$manifest_file"
    sed -i "s/app: $old_name/app: $new_name/g" "$manifest_file"
    sed -i "s/app=$old_name/app=$new_name/g" "$manifest_file"
}

# Main execution
echo "Starting service name synchronization..."

# Get list of manifest files
manifest_files=$(find "$K8S_DIR" -name "*.yaml")

# Get configured service names
service_names=$(parse_service_names)

# Update each manifest file
for manifest in $manifest_files; do
    echo "Processing $manifest..."
    
    # Extract current service names from manifest
    current_names=$(grep -E '^ *name:' "$manifest" | sed 's/[[:space:]]*name:[[:space:]]*//')
    
    # Compare and update names
    for name in $current_names; do
        if [[ $service_names =~ $name ]]; then
            config_name=$(echo "$service_names" | grep -w "$name")
            if [[ "$name" != "$config_name" ]]; then
                update_manifests "$name" "$config_name" "$manifest"
            fi
        fi
    done
done

echo "Service name synchronization complete."
