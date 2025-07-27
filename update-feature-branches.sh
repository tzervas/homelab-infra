#!/bin/bash

# Script to update all feature branches by merging main into them
set -euo pipefail

echo "=== Updating Feature Branches with Main ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Stash any uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Stashing uncommitted changes...${NC}"
    git stash push -m "Auto-stash before branch updates $(date +%Y%m%d-%H%M%S)"
    STASHED=true
else
    STASHED=false
fi

# Update main first
echo -e "\n${GREEN}Updating main branch...${NC}"
git checkout main
git pull origin main

# Get all remote feature branches
FEATURE_BRANCHES=$(git branch -r | grep origin/feature/ | grep -v HEAD | sed 's/origin\///')

# Branches to skip (stale or already merged)
SKIP_BRANCHES=(
    "feature/comprehensive-testing-framework"
    "feature/comprehensive-testing-framework-clean"
    "feature/documentation-consolidation-for-main"
    "feature/comprehensive-documentation-consolidation"
    "feature/merge-local-commits"
)

# Function to check if branch should be skipped
should_skip() {
    local branch=$1
    for skip in "${SKIP_BRANCHES[@]}"; do
        if [[ "$branch" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

# Process each feature branch
for branch in $FEATURE_BRANCHES; do
    # Skip if in skip list
    if should_skip "$branch"; then
        echo -e "\n${YELLOW}Skipping $branch (stale or already processed)${NC}"
        continue
    fi
    
    echo -e "\n${GREEN}Processing $branch...${NC}"
    
    # Check out the branch, creating local tracking branch if needed
    if git show-ref --verify --quiet refs/heads/"$branch"; then
        git checkout "$branch"
    else
        git checkout -b "$branch" "origin/$branch"
    fi
    
    # Try to merge main
    echo "Merging main into $branch..."
    if git merge main --no-edit; then
        echo -e "${GREEN}Successfully merged main into $branch${NC}"
        
        # Push the updated branch
        echo "Pushing $branch to origin..."
        if git push origin "$branch"; then
            echo -e "${GREEN}Successfully pushed $branch${NC}"
        else
            echo -e "${RED}Failed to push $branch${NC}"
        fi
    else
        echo -e "${RED}Merge conflict in $branch!${NC}"
        echo "Please resolve conflicts manually, then run:"
        echo "  git add ."
        echo "  git commit"
        echo "  git push origin $branch"
        
        # Abort the merge
        git merge --abort
        echo -e "${YELLOW}Aborted merge for $branch${NC}"
    fi
done

# Return to original branch
echo -e "\n${GREEN}Returning to original branch: $CURRENT_BRANCH${NC}"
git checkout "$CURRENT_BRANCH"

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo -e "${YELLOW}Restoring stashed changes...${NC}"
    if git stash pop; then
        echo -e "${GREEN}Successfully restored stashed changes${NC}"
    else
        echo -e "${RED}Failed to restore stash. Use 'git stash list' and 'git stash pop' manually${NC}"
    fi
fi

echo -e "\n${GREEN}=== Branch Update Complete ===${NC}"
echo -e "Updated branches:"
git branch -r | grep origin/feature/ | grep -v -E "($(IFS='|'; echo "${SKIP_BRANCHES[*]}"))" | sed 's/origin\//  - /'
