#!/bin/bash

# Script to consolidate Git branches by merging or removing stale ones
# Usage: ./consolidate_branches.sh [--dry-run] [--stale-days N]

set -e

# Default values
DRY_RUN=false
STALE_DAYS=30

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --stale-days)
            STALE_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--stale-days N]"
            exit 1
            ;;
    esac
done

# Ensure we're in a Git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Store current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Function to check if a branch is stale
is_stale() {
    local branch=$1
    local last_commit_date
    last_commit_date=$(git log -1 --format=%ct "$branch")
    local current_date
    current_date=$(date +%s)
    local days_old=$(( (current_date - last_commit_date) / 86400 ))
    
    [[ $days_old -gt $STALE_DAYS ]]
}

# Function to check if a branch is merged
is_merged() {
    local branch=$1
    git branch --merged main | grep -q "^[* ]*$branch$"
}

echo "Branch Consolidation Analysis"
echo "============================"
echo "Analyzing branches..."

# Get all branches except main
BRANCHES=$(git branch | grep -v '^[* ]*main$' | sed 's/^[* ]*//')

# Initialize counters
STALE_COUNT=0
MERGED_COUNT=0

# Process each branch
while IFS= read -r branch; do
    [[ -z "$branch" ]] && continue
    
    echo -e "\nAnalyzing branch: $branch"
    
    if is_merged "$branch"; then
        echo "Status: Merged into main"
        if [ "$DRY_RUN" = false ]; then
            echo "Action: Deleting merged branch"
            git branch -d "$branch"
        else
            echo "Action: Would delete merged branch (dry run)"
        fi
        ((MERGED_COUNT++))
    elif is_stale "$branch"; then
        echo "Status: Stale (no commits for $STALE_DAYS days)"
        if [ "$DRY_RUN" = false ]; then
            echo "Action: Creating backup and marking for review"
            git tag "archive/${branch}_$(date +%Y%m%d)" "$branch"
        else
            echo "Action: Would create backup tag (dry run)"
        fi
        ((STALE_COUNT++))
    else
        echo "Status: Active branch"
        echo "Action: None needed"
    fi
done <<< "$BRANCHES"

# Print summary
echo -e "\nConsolidation Summary"
echo "===================="
echo "Total branches analyzed: $(echo "$BRANCHES" | wc -l)"
echo "Merged branches: $MERGED_COUNT"
echo "Stale branches: $STALE_COUNT"

if [ "$DRY_RUN" = true ]; then
    echo -e "\nThis was a dry run. No changes were made."
fi

# Return to original branch
git checkout "$CURRENT_BRANCH" > /dev/null 2>&1
