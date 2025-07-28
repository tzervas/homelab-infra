#!/bin/bash

# Sync private documentation across git branches
# This script should be excluded from git tracking

set -euo pipefail

PRIVATE_DOCS_DIR=".private/docs"
BACKUP_DIR=".private_backup"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to backup private docs
backup_private_docs() {
  if [ -d "$PRIVATE_DOCS_DIR" ]; then
    echo "Backing up private documentation..."
    cp -r "$PRIVATE_DOCS_DIR" "$BACKUP_DIR/"
  fi
}

# Function to restore private docs
restore_private_docs() {
  if [ -d "$BACKUP_DIR/docs" ]; then
    echo "Restoring private documentation..."
    rm -rf "$PRIVATE_DOCS_DIR"
    mkdir -p "$PRIVATE_DOCS_DIR"
    cp -r "$BACKUP_DIR/docs/"* "$PRIVATE_DOCS_DIR/"
  fi
}

# Get current branch
current_branch=$(git rev-parse --abbrev-ref HEAD)

# Backup current private docs
backup_private_docs

# Get all branches
branches=$(git branch --format="%(refname:short)")

for branch in $branches; do
  if [ "$branch" != "$current_branch" ]; then
    echo "Syncing private documentation to branch: $branch"
    git checkout "$branch"
    restore_private_docs
  fi
done

# Return to original branch
git checkout "$current_branch"
restore_private_docs

echo "Private documentation sync complete"
