#!/bin/bash

# Script to update remaining feature branches
set -euo pipefail

echo "=== Updating Remaining Feature Branches ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Remaining branches to update
BRANCHES=(
    "feature/ansible-simplification"
    "feature/infrastructure-cleanup"
    "feature/vm-management-refactor"
)

# First, let's analyze each branch
echo -e "\n${YELLOW}=== Analyzing branches ===${NC}"
for branch in "${BRANCHES[@]}"; do
    echo -e "\n${GREEN}Branch: $branch${NC}"
    echo "Unique commits in this branch:"
    git log --oneline origin/$branch ^main | head -5
    echo "---"
done

echo -e "\n${YELLOW}These branches contain the problematic 'allow-unrelated-histories' merge.${NC}"
echo "We'll need to cherry-pick the valuable commits onto new branches based on main."

# Ask for confirmation
read -p "Do you want to proceed with recreating these branches? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Process each branch
for branch in "${BRANCHES[@]}"; do
    echo -e "\n${GREEN}=== Processing $branch ===${NC}"
    
    # Create new branch name
    new_branch="${branch}-clean"
    
    # Get the valuable commits (excluding merge commits)
    echo "Identifying valuable commits..."
    commits=$(git log --oneline --no-merges origin/$branch ^main --reverse | awk '{print $1}')
    
    if [ -z "$commits" ]; then
        echo -e "${YELLOW}No unique commits found in $branch${NC}"
        continue
    fi
    
    echo "Found commits to cherry-pick:"
    echo "$commits"
    
    # Create new clean branch from main
    echo -e "\n${GREEN}Creating clean branch: $new_branch${NC}"
    git checkout -b "$new_branch" main
    
    # Cherry-pick the commits
    echo "Cherry-picking commits..."
    for commit in $commits; do
        echo -e "\n${YELLOW}Cherry-picking: $(git log --oneline -1 $commit)${NC}"
        if git cherry-pick "$commit"; then
            echo -e "${GREEN}✓ Successfully cherry-picked $commit${NC}"
        else
            echo -e "${RED}✗ Conflict while cherry-picking $commit${NC}"
            echo "Please resolve the conflict, then run:"
            echo "  git add ."
            echo "  git cherry-pick --continue"
            echo ""
            echo "Or skip this commit with:"
            echo "  git cherry-pick --skip"
            echo ""
            echo "After resolving, continue with the remaining commits."
            exit 1
        fi
    done
    
    # Push the new clean branch
    echo -e "\n${GREEN}Pushing $new_branch to origin...${NC}"
    if git push origin "$new_branch"; then
        echo -e "${GREEN}✓ Successfully created and pushed $new_branch${NC}"
        
        # Optionally delete the old branch
        echo -e "\n${YELLOW}The old branch $branch can now be deleted.${NC}"
        echo "To delete it, run:"
        echo "  git push origin --delete $branch"
    else
        echo -e "${RED}✗ Failed to push $new_branch${NC}"
    fi
done

# Return to original branch
echo -e "\n${GREEN}Returning to original branch: $CURRENT_BRANCH${NC}"
git checkout "$CURRENT_BRANCH"

echo -e "\n${GREEN}=== Update Complete ===${NC}"
echo "New clean branches created:"
for branch in "${BRANCHES[@]}"; do
    if git show-ref --verify --quiet refs/heads/"${branch}-clean"; then
        echo "  - ${branch}-clean"
    fi
done
