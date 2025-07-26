#!/bin/bash

# Script to find and fix all unsigned commits across all branches
# This will iterate through every local branch and fix unsigned commits

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current branch to return to it later
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}Current branch: $ORIGINAL_BRANCH${NC}"

# Stash any uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Stashing uncommitted changes...${NC}"
    git stash push -m "Auto-stash before fixing unsigned commits - $(date)"
    STASHED=true
else
    STASHED=false
fi

# Get all local branches (excluding current branch marker)
BRANCHES=($(git branch | sed 's/^[ *]*//'))

echo -e "${BLUE}Found ${#BRANCHES[@]} branches to check:${NC}"
for branch in "${BRANCHES[@]}"; do
    echo "  - $branch"
done
echo

# Function to check and fix unsigned commits in a branch
fix_unsigned_commits_in_branch() {
    local branch=$1
    echo -e "${BLUE}=== Checking branch: $branch ===${NC}"

    # Checkout the branch
    git checkout "$branch" || {
        echo -e "${RED}Failed to checkout branch $branch${NC}"
        return 1
    }

    # Get all commits in this branch
    echo "Checking for unsigned commits..."

    # Find unsigned commits using git log with format that shows signature verification
    UNSIGNED_COMMITS=$(git log --pretty=format:"%H %G?" --all | grep -E " [NU]$" | cut -d' ' -f1 || true)

    if [ -z "$UNSIGNED_COMMITS" ]; then
        echo -e "${GREEN}✓ All commits in $branch are signed${NC}"
        return 0
    fi

    echo -e "${YELLOW}Found unsigned commits in $branch:${NC}"
    for commit in $UNSIGNED_COMMITS; do
        # Check if this commit is in the current branch
        if git merge-base --is-ancestor "$commit" HEAD 2>/dev/null; then
            echo "  - $commit ($(git log --oneline -1 $commit | cut -c1-60)...)"
        fi
    done

    # Get unsigned commits that are actually in this branch
    BRANCH_UNSIGNED=$(git log --pretty=format:"%H %G?" HEAD | grep -E " [NU]$" | cut -d' ' -f1 || true)

    if [ -z "$BRANCH_UNSIGNED" ]; then
        echo -e "${GREEN}✓ No unsigned commits found in current branch $branch${NC}"
        return 0
    fi

    echo -e "${YELLOW}Fixing unsigned commits in $branch...${NC}"

    # Use filter-branch to sign all commits
    echo "Running git filter-branch to sign commits..."

    # Create a temporary script for the commit filter
    cat > /tmp/sign_commits_filter.sh << 'EOF'
#!/bin/bash
# Check if this is one of the unsigned commits
if [ "$GIT_COMMIT" = "$1" ] || echo "$UNSIGNED_COMMITS" | grep -q "$GIT_COMMIT"; then
    # Re-commit with signature
    git commit-tree "$GIT_COMMIT^{tree}" $(echo "$GIT_COMMIT" | sed 's/^/-p /') -S < /tmp/commit_msg_$GIT_COMMIT
else
    # Keep the original commit
    git commit-tree "$GIT_COMMIT^{tree}" $(echo "$GIT_COMMIT" | sed 's/^/-p /')
fi
EOF

    # For each unsigned commit, save its message
    for commit in $BRANCH_UNSIGNED; do
        git log --format=%B -n 1 "$commit" > "/tmp/commit_msg_$commit"
    done

    # Use git filter-branch with a simpler approach - just re-sign all commits
    FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --commit-filter '
        if echo "'"$BRANCH_UNSIGNED"'" | grep -q "$GIT_COMMIT"; then
            git commit-tree -S "$@"
        else
            git commit-tree "$@"
        fi
    ' HEAD

    # Clean up temporary files
    rm -f /tmp/commit_msg_* /tmp/sign_commits_filter.sh

    echo -e "${GREEN}✓ Fixed unsigned commits in $branch${NC}"

    # Verify the fixes
    REMAINING_UNSIGNED=$(git log --pretty=format:"%H %G?" HEAD | grep -E " [NU]$" | cut -d' ' -f1 || true)
    if [ -z "$REMAINING_UNSIGNED" ]; then
        echo -e "${GREEN}✓ All commits in $branch are now signed${NC}"
    else
        echo -e "${RED}⚠ Some commits may still be unsigned:${NC}"
        for commit in $REMAINING_UNSIGNED; do
            echo "  - $commit"
        done
    fi

    return 0
}

# Process each branch
FAILED_BRANCHES=()
for branch in "${BRANCHES[@]}"; do
    if ! fix_unsigned_commits_in_branch "$branch"; then
        FAILED_BRANCHES+=("$branch")
    fi
    echo
done

# Return to original branch
echo -e "${BLUE}Returning to original branch: $ORIGINAL_BRANCH${NC}"
git checkout "$ORIGINAL_BRANCH"

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo -e "${YELLOW}Restoring stashed changes...${NC}"
    git stash pop || echo -e "${RED}Warning: Failed to restore stash. Check manually.${NC}"
fi

# Summary
echo -e "${BLUE}=== SUMMARY ===${NC}"
if [ ${#FAILED_BRANCHES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully processed all ${#BRANCHES[@]} branches${NC}"
else
    echo -e "${YELLOW}Processed ${#BRANCHES[@]} branches with ${#FAILED_BRANCHES[@]} failures:${NC}"
    for branch in "${FAILED_BRANCHES[@]}"; do
        echo -e "${RED}  ✗ $branch${NC}"
    done
fi

echo
echo -e "${BLUE}To push the updated branches to remote:${NC}"
echo "git push --force-with-lease origin --all"
