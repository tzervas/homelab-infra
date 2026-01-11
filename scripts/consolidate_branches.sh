#!/bin/bash

# Default values
DRY_RUN=false
STALE_DAYS=30
BASE_BRANCH="main"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --stale-days)
            STALE_DAYS="$2"
            shift 2
            ;;
        --base-branch)
            BASE_BRANCH="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Function to get branch last commit date
get_branch_date() {
    local branch=$1
    git log -1 --format=%ct "$branch"
}

# Function to get branch author
get_branch_author() {
    local branch=$1
    git log -1 --format=%an "$branch"
}

# Function to get total commit count
get_commit_count() {
    local branch=$1
    git rev-list --count "$branch"
}

# Function to check if a branch is merged
is_merged() {
    local branch=$1
    git branch --merged "$BASE_BRANCH" | grep -q "^[* ]*$branch$"
}

# Function to check if a branch is protected
is_protected() {
    local branch=$1
    [[ " ${PROTECTED_BRANCHES[*]} " =~ " ${branch} " ]]
}

# Function to check if a branch is stale
is_stale() {
    local branch=$1
    local last_commit=$(get_branch_date "$branch")
    local current_time=$(date +%s)
    local days_old=$(( (current_time - last_commit) / 86400 ))
    
    [[ $days_old -gt $STALE_DAYS ]]
}

# Get list of all branches
mapfile -t branches < <(git for-each-ref --format='%(refname:short)' refs/heads/)

# Protected branches
PROTECTED_BRANCHES=("main" "master" "dev" "develop" "staging" "production")

# Track branches to delete
declare -a branches_to_delete

# Process each branch
for branch in "${branches[@]}"; do
    # Skip protected branches
    if is_protected "$branch"; then
        echo "Skipping protected branch: $branch"
        continue
    fi

    # Check if branch is stale and merged
    if is_stale "$branch" && is_merged "$branch"; then
        branches_to_delete+=("$branch")
        
        # Get branch info for logging
        author=$(get_branch_author "$branch")
        commit_count=$(get_commit_count "$branch")
        last_commit_date=$(date -d "@$(get_branch_date "$branch")" "+%Y-%m-%d")
        
        echo "Found stale branch:"
        echo "  Name: $branch"
        echo "  Author: $author"
        echo "  Last commit: $last_commit_date"
        echo "  Total commits: $commit_count"
    fi
done

# Handle branch deletion
if [[ ${#branches_to_delete[@]} -eq 0 ]]; then
    echo "No stale branches found."
    exit 0
fi

# List branches to be deleted
echo -e "\nBranches to be deleted:"
printf '%s\n' "${branches_to_delete[@]}"

# Delete branches or show dry run
if [[ "$DRY_RUN" = true ]]; then
    echo -e "\nDRY RUN - No branches were deleted"
else
    echo -e "\nDeleting branches..."
    for branch in "${branches_to_delete[@]}"; do
        if git branch -d "$branch"; then
            echo "Deleted branch: $branch"
        else
            echo "Failed to delete branch: $branch"
        fi
    done
fi

exit 0
