#!/bin/bash

# Script to synchronize service names between config and K8s manifests
# This ensures consistent naming across the infrastructure

# Load service names from config
CONFIG_FILE="config/consolidated/services.yaml"
K8S_DIR="kubernetes/base"

# Function to parse service names from config
# Optionally takes a YAML key path as the first argument (default: ".services.discovery")
parse_service_names() {
    local key_path="${1:-.services.discovery}"
    echo "Parsing service names from config at path: $key_path"

    # Use yq to parse YAML if available, fallback to grep
    if command -v yq &> /dev/null; then
        # Validate that the key path exists
        if ! yq "$key_path" "$CONFIG_FILE" | grep -qv 'null'; then
            echo "Error: Key path '$key_path' not found in $CONFIG_FILE" >&2
            return 1
        fi
        yq "$key_path | keys" "$CONFIG_FILE"
    else
        # Fallback assumes the default path .services.discovery
        if [[ "$key_path" != ".services.discovery" ]]; then
            echo "Error: Custom key path parsing not supported without yq. Please install yq for advanced parsing." >&2
            return 1
        fi
        # Validate that the expected structure exists
        if ! grep -qE 'services:[[:space:]]*$' "$CONFIG_FILE" || ! grep -qE 'discovery:[[:space:]]*$' "$CONFIG_FILE"; then
            echo "Error: Expected structure 'services: -> discovery:' not found in $CONFIG_FILE" >&2
            return 1
        fi
        grep -E '^[[:space:]]+[a-zA-Z_]+:' "$CONFIG_FILE" | sed 's/[[:space:]]*\([a-zA-Z_]*\):.*/\1/'
    fi
}

# Function to update K8s manifests
update_manifest() {
    local old_name="$1"
    local new_name="$2"
    local manifest_file="$3"

    echo "Updating $manifest_file: $old_name -> $new_name"
    
    if command -v yq &> /dev/null; then
        # Use yq for more precise YAML updates
        # Update metadata.name if it matches
        yq -i "select(.metadata.name == \"$old_name\") .metadata.name = \"$new_name\"" "$manifest_file"
        
        # Update app label in metadata
        yq -i "select(.metadata.labels.app == \"$old_name\") .metadata.labels.app = \"$new_name\"" "$manifest_file"
        
        # Update app label in selector
        yq -i "select(.spec.selector.app == \"$old_name\") .spec.selector.app = \"$new_name\"" "$manifest_file"
        
        # Update app label in template metadata
        yq -i "select(.spec.template.metadata.labels.app == \"$old_name\") .spec.template.metadata.labels.app = \"$new_name\"" "$manifest_file"
    else
        # Fallback to sed with more precise patterns
        # Only replace exact matches with proper YAML indentation
        sed -i "/^[[:space:]]*name:[[:space:]]*$old_name$/s/$old_name/$new_name/" "$manifest_file"
        sed -i "/^[[:space:]]*app:[[:space:]]*$old_name$/s/$old_name/$new_name/" "$manifest_file"
        sed -i "s/\(app=\)$old_name\([[:space:]]\|$\)/\1$new_name\2/g" "$manifest_file"
    fi
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
