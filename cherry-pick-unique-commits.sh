#!/bin/bash

# Script to cherry-pick only the unique commits from each branch
set -euo pipefail

echo "=== Cherry-picking Unique Commits ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Branches and their unique commits
declare -A BRANCH_COMMITS=(
    ["feature/ansible-simplification"]="beb2617"
    ["feature/infrastructure-cleanup"]="6cf51db"
    ["feature/vm-management-refactor"]="2ceec52"
)

# Process each branch
for branch in "${!BRANCH_COMMITS[@]}"; do
    commit="${BRANCH_COMMITS[$branch]}"
    new_branch="${branch}-clean"
    
    echo -e "\n${GREEN}=== Processing $branch ===${NC}"
    echo "Unique commit: $(git log --oneline -1 $commit)"
    
    # Create new clean branch from main
    echo -e "\n${GREEN}Creating clean branch: $new_branch${NC}"
    git checkout -b "$new_branch" main
    
    # Cherry-pick the unique commit
    echo -e "\n${YELLOW}Cherry-picking commit...${NC}"
    if git cherry-pick "$commit"; then
        echo -e "${GREEN}✓ Successfully cherry-picked $commit${NC}"
        
        # Push the new clean branch
        echo -e "\n${GREEN}Pushing $new_branch to origin...${NC}"
        if git push origin "$new_branch"; then
            echo -e "${GREEN}✓ Successfully created and pushed $new_branch${NC}"
        else
            echo -e "${RED}✗ Failed to push $new_branch${NC}"
        fi
    else
        echo -e "${RED}✗ Conflict while cherry-picking $commit${NC}"
        echo "Attempting to resolve automatically..."
        
        # Show conflict status
        git status --short
        
        # Abort and continue
        git cherry-pick --abort
        echo -e "${YELLOW}Cherry-pick aborted. Manual intervention may be needed.${NC}"
    fi
done

# Return to original branch
echo -e "\n${GREEN}Returning to original branch: $CURRENT_BRANCH${NC}"
git checkout "$CURRENT_BRANCH"

echo -e "\n${GREEN}=== Cherry-pick Complete ===${NC}"
echo "Clean branches created:"
git branch | grep -- -clean || echo "No clean branches found"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Delete the old branches:"
for branch in "${!BRANCH_COMMITS[@]}"; do
    echo "   git push origin --delete $branch"
done
echo "2. Create PRs for the clean branches"
