#!/bin/bash

# Script to update all branches and sync untracked files
# Usage: ./sync_all.sh [repo_path] [backup_dir]

set -euo pipefail

REPO_PATH="${1:-$(pwd)}"
BACKUP_DIR="${2:-${REPO_PATH}/untracked_backup}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# First, sync untracked files
echo "Step 1: Syncing untracked files across branches..."
"${SCRIPT_DIR}/sync_untracked.sh" "$BACKUP_DIR"

# Then, update all branches
echo -e "\nStep 2: Updating all branches from main..."
"${SCRIPT_DIR}/update_branches.sh" "$REPO_PATH"

echo -e "\nAll operations completed successfully!"
echo "1. Untracked files have been synced across all branches"
echo "2. All branches have been updated from main"
echo "3. Backups of original untracked files are stored in: $BACKUP_DIR"
