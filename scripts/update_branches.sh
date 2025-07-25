#!/bin/bash

# Script to update all branches in a Git repository by merging main.
# Usage: ./update_branches.sh [repo_path]

# Set repository path (default to current directory if not provided)
REPO_PATH="${1:-$(pwd)}"

# Ensure we're in a Git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: '$REPO_PATH' is not a Git repository."
    exit 1
fi

# Navigate to repository
cd "$REPO_PATH" || { echo "Error: Failed to navigate to '$REPO_PATH'."; exit 1; }

# Get list of local branches, excluding the current branch marker (*)
BRANCHES=($(git branch | sed 's/^[ *]*//'))

# Ensure main branch exists
if ! git rev-parse --verify main > /dev/null 2>&1; then
    echo "Error: 'main' branch not found in repository."
    exit 1
fi

# Enumerate and display branches
echo "Branches to update:"
for i in "${!BRANCHES[@]}"; do
    printf "%2d: %s\n" "$((i+1))" "${BRANCHES[i]}"
done

# Stash any local changes on current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if ! git diff-index --quiet HEAD --; then
    echo "Stashing changes on current branch ($CURRENT_BRANCH)..."
    git stash push -m "Auto-stash before branch updates" || { echo "Error: Failed to stash changes."; exit 1; }
fi

# Update main branch first
echo -e "\nUpdating main branch..."
git checkout main || { echo "Error: Failed to checkout main."; exit 1; }
git pull origin main || { echo "Error: Failed to pull main."; exit 1; }

# Iterate through branches and update from main
for branch in "${BRANCHES[@]}"; do
    if [[ "$branch" != "main" ]]; then
        echo -e "\nUpdating branch: $branch"
        git checkout "$branch" || { echo "Error: Failed to checkout $branch."; continue; }
        git merge main --no-edit || { echo "Warning: Merge conflicts in $branch. Skipping push."; continue; }
        git push origin "$branch" || { echo "Error: Failed to push $branch."; continue; }
        echo "Successfully updated $branch."
    fi
done

# Return to original branch
echo -e "\nReturning to original branch: $CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH" || { echo "Error: Failed to return to $CURRENT_BRANCH."; exit 1; }

# Reapply stashed changes if any
if git stash list | grep -q "Auto-stash before branch updates"; then
    echo "Reapplying stashed changes..."
    git stash pop || { echo "Warning: Failed to reapply stash. Resolve manually."; }
fi

echo -e "\nAll branches updated successfully!"
