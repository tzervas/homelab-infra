#!/bin/bash

# Script to backup Git branches and create a manifest
# Stores backups in .analysis/backup/

# Ensure required directories exist
mkdir -p .analysis/backup

# Get timestamp for backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR=".analysis/backup/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

# Initialize manifest
MANIFEST_FILE="${BACKUP_DIR}/manifest.yaml"
echo "backup:" > "${MANIFEST_FILE}"
echo "  timestamp: ${TIMESTAMP}" >> "${MANIFEST_FILE}"
echo "  branches:" >> "${MANIFEST_FILE}"

# Function to create bundle for a branch
create_branch_bundle() {
    local branch=$1
    local safe_name=$(echo "${branch}" | tr '/' '_')
    local bundle_file="${BACKUP_DIR}/${safe_name}.bundle"
    
    # Create bundle
    git bundle create "${bundle_file}" "${branch}"

    # Add to manifest
    echo "    - name: ${branch}" >> "${MANIFEST_FILE}"
    echo "      bundle: ${safe_name}.bundle" >> "${MANIFEST_FILE}"
    echo "      commit: $(git rev-parse "${branch}")" >> "${MANIFEST_FILE}"
}

# Backup local branches
echo "Backing up local branches..."
for branch in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
    echo "Creating bundle for ${branch}"
    create_branch_bundle "${branch}"
done

# Backup remote branches
echo "Backing up remote branches..."
for branch in $(git for-each-ref --format='%(refname:short)' refs/remotes/); do
    # Skip remote HEAD reference
    if [[ "${branch}" != "origin/HEAD" ]]; then
        echo "Creating bundle for ${branch}"
        create_branch_bundle "${branch}"
    fi
done

echo "Backup completed successfully!"
echo "Backup location: ${BACKUP_DIR}"
echo "Manifest file: ${MANIFEST_FILE}"
