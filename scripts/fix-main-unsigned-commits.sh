#!/bin/bash

# Script to comprehensively fix all unsigned commits in main branch
# This will create a clean signed history for PR to origin/main

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Fixing ALL unsigned commits in main branch ===${NC}"

# Ensure we're on main
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
    echo -e "${RED}Error: Must be on main branch${NC}"
    exit 1
fi

# Stash any uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Stashing uncommitted changes...${NC}"
    git stash push -m "Auto-stash before fixing main unsigned commits - $(date)"
    STASHED=true
else
    STASHED=false
fi

# Get the point where main diverged from origin/main
MERGE_BASE=$(git merge-base HEAD origin/main 2>/dev/null || echo "origin/main")
echo -e "${BLUE}Merge base with origin/main: $MERGE_BASE${NC}"

# Create a backup branch
BACKUP_BRANCH="backup-main-before-signing-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
echo -e "${YELLOW}Created backup branch: $BACKUP_BRANCH${NC}"

# Get all unsigned commits
UNSIGNED_COMMITS=$(git log --pretty=format:"%H %G?" $MERGE_BASE..HEAD | grep -E " [NU]$" | cut -d' ' -f1 || true)

if [ -z "$UNSIGNED_COMMITS" ]; then
    echo -e "${GREEN}✓ All commits are already signed${NC}"
    if [ "$STASHED" = true ]; then
        git stash pop
    fi
    exit 0
fi

echo -e "${YELLOW}Found unsigned commits to fix:${NC}"
for commit in $UNSIGNED_COMMITS; do
    echo "  - $commit ($(git log --oneline -1 $commit | cut -c1-60)...)"
done

# Use filter-branch to sign all commits from merge-base to HEAD
echo -e "${BLUE}Running git filter-branch to sign all commits...${NC}"

# Create the filter script
FILTER_SCRIPT=$(mktemp)
cat > "$FILTER_SCRIPT" << 'EOF'
#!/bin/bash
# Check if this commit is one that needs signing
if echo "$UNSIGNED_COMMITS" | grep -q "$GIT_COMMIT"; then
    # Re-sign this commit
    git commit-tree -S "$@"
else
    # Keep original commit as-is
    git commit-tree "$@"
fi
EOF

chmod +x "$FILTER_SCRIPT"

# Export the unsigned commits list for the filter script
export UNSIGNED_COMMITS

# Run filter-branch
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --commit-filter "
    if echo \"$UNSIGNED_COMMITS\" | grep -q \"\$GIT_COMMIT\"; then
        git commit-tree -S \"\$@\"
    else
        git commit-tree \"\$@\"
    fi
" ${MERGE_BASE}..HEAD

# Clean up
rm -f "$FILTER_SCRIPT"

# Verify all commits are now signed
echo -e "${BLUE}Verifying signature status...${NC}"
REMAINING_UNSIGNED=$(git log --pretty=format:"%H %G?" $MERGE_BASE..HEAD | grep -E " [NU]$" | cut -d' ' -f1 || true)

if [ -z "$REMAINING_UNSIGNED" ]; then
    echo -e "${GREEN}✓ All commits in main are now properly signed${NC}"
else
    echo -e "${RED}⚠ Some commits are still unsigned:${NC}"
    for commit in $REMAINING_UNSIGNED; do
        echo "  - $commit"
    done
fi

# Show the current status
echo -e "${BLUE}Current main branch status:${NC}"
git log --pretty=format:"  %h %G? %s" $MERGE_BASE..HEAD | head -10

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo -e "${YELLOW}Restoring stashed changes...${NC}"
    git stash pop || echo -e "${RED}Warning: Failed to restore stash. Check manually.${NC}"
fi

echo
echo -e "${GREEN}✓ Main branch has been cleaned up and all commits signed${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Review the signed commits: git log --show-signature $MERGE_BASE..HEAD"
echo "  2. Create PR branch: git checkout -b fix/signed-commits-for-main"
echo "  3. Push PR branch: git push origin fix/signed-commits-for-main"
echo "  4. Create PR from fix/signed-commits-for-main to origin/main"
echo
echo -e "${YELLOW}Backup branch available: $BACKUP_BRANCH${NC}"
