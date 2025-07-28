#!/bin/bash

# Script to sync untracked files across branches
# Usage: ./sync_untracked.sh [backup_dir]

set -euo pipefail

# Default backup directory
BACKUP_DIR="${1:-./untracked_backup}"
TEMP_DIR="/tmp/untracked_temp_$$"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Function to get all branches
get_branches() {
    git branch | sed 's/^[ *]*//'
}

# Function to get untracked files
get_untracked_files() {
    git ls-files --others --exclude-standard | grep -v "untracked_backup/"
}

# Function to backup untracked files
backup_untracked() {
    local dest_dir="$1"
    mkdir -p "$dest_dir"

    while IFS= read -r file; do
        if [ -n "$file" ]; then
            mkdir -p "$(dirname "$dest_dir/$file")"
            cp --parents "$file" "$dest_dir/"
        fi
    done < <(get_untracked_files)
}

# Function to restore untracked files
restore_untracked() {
    local src_dir="$1"
    if [ ! -d "$src_dir" ]; then
        echo "No files to restore from $src_dir"
        return
    fi
    cp -r "$src_dir/"* ./ 2>/dev/null || true
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup current untracked files
echo "Backing up untracked files from current branch ($CURRENT_BRANCH)..."
backup_untracked "$TEMP_DIR"

# Process each branch
for branch in $(get_branches); do
    echo "Processing branch: $branch"
    git checkout "$branch"

    echo "Creating backup of existing untracked files in $branch..."
    backup_untracked "$BACKUP_DIR/$branch"

    echo "Restoring untracked files to $branch..."
    restore_untracked "$TEMP_DIR"
done

# Return to original branch
git checkout "$CURRENT_BRANCH"

# Cleanup temp directory
rm -rf "$TEMP_DIR"

echo "Backups of all untracked files stored in: $BACKUP_DIR"
echo "Untracked files have been synced across all branches"
echo
echo "Note: Original backups of untracked files from each branch"
echo "are preserved in branch-specific directories under: $BACKUP_DIR"
