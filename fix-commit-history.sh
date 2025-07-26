#!/bin/bash
# Script to fix git commit history with correct author information and GPG signatures

set -e

# Configuration
CORRECT_NAME="Tyler Zervas"
CORRECT_EMAIL="tz-dev@vectorweight.com"
GITHUB_EMAIL="111450100+tzervas@users.noreply.github.com"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🔧 Git Commit History Cleanup${NC}"
echo "=================================="
echo -e "Correct Name: ${GREEN}$CORRECT_NAME${NC}"
echo -e "Correct Email: ${GREEN}$CORRECT_EMAIL${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes. Please commit or stash them first.${NC}"
    exit 1
fi

# Backup current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${YELLOW}Current branch: $CURRENT_BRANCH${NC}"

# Create a backup branch
BACKUP_BRANCH="backup-before-history-fix-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
echo -e "${GREEN}✅ Created backup branch: $BACKUP_BRANCH${NC}"

# Show commits that need fixing
echo ""
echo -e "${YELLOW}📋 Commits that will be fixed:${NC}"
git log --oneline --format="%h %an <%ae> %G? %s" | while read line; do
    if [[ "$line" =~ "$GITHUB_EMAIL" ]] || [[ "$line" =~ " N " ]] || [[ "$line" =~ " E " ]]; then
        echo -e "${RED}❌ $line${NC}"
    else
        echo -e "${GREEN}✅ $line${NC}"
    fi
done

echo ""
read -p "Continue with commit history rewrite? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Operation cancelled${NC}"
    git branch -D "$BACKUP_BRANCH"
    exit 0
fi

# Filter-branch to fix author information and add signatures
echo ""
echo -e "${YELLOW}🔄 Rewriting commit history...${NC}"

# Use git filter-repo if available, otherwise use filter-branch
if command -v git-filter-repo > /dev/null 2>&1; then
    echo -e "${GREEN}Using git-filter-repo (recommended)${NC}"

    # Create mailmap for author correction
    cat > .mailmap.tmp << EOF
$CORRECT_NAME <$CORRECT_EMAIL> <$GITHUB_EMAIL>
$CORRECT_NAME <$CORRECT_EMAIL> <$CORRECT_EMAIL>
EOF

    # Fix authors using mailmap
    git filter-repo --mailmap .mailmap.tmp --force
    rm .mailmap.tmp

else
    echo -e "${YELLOW}Using git filter-branch (git-filter-repo not available)${NC}"

    # Use filter-branch to fix authors
    git filter-branch --env-filter "
        if [ \"\$GIT_AUTHOR_EMAIL\" = \"$GITHUB_EMAIL\" ]; then
            export GIT_AUTHOR_NAME=\"$CORRECT_NAME\"
            export GIT_AUTHOR_EMAIL=\"$CORRECT_EMAIL\"
        fi
        if [ \"\$GIT_COMMITTER_EMAIL\" = \"$GITHUB_EMAIL\" ]; then
            export GIT_COMMITTER_NAME=\"$CORRECT_NAME\"
            export GIT_COMMITTER_EMAIL=\"$CORRECT_EMAIL\"
        fi
    " --tag-name-filter cat -- --branches --tags
fi

# Now re-sign all commits
echo ""
echo -e "${YELLOW}🔐 Re-signing all commits with GPG...${NC}"

# Get the root commit
ROOT_COMMIT=$(git rev-list --max-parents=0 HEAD)

# Re-sign commits starting from the root
git rebase --exec 'git commit --amend --no-edit -S' "$ROOT_COMMIT"^

echo ""
echo -e "${GREEN}✅ Commit history cleanup complete!${NC}"

# Verify the results
echo ""
echo -e "${YELLOW}📊 Verification Results:${NC}"
echo "========================"

TOTAL_COMMITS=$(git rev-list --count HEAD)
SIGNED_COMMITS=$(git log --format="%G?" | grep -c "G" || echo "0")
CORRECT_AUTHOR_COMMITS=$(git log --format="%ae" | grep -c "$CORRECT_EMAIL" || echo "0")

echo -e "Total commits: ${GREEN}$TOTAL_COMMITS${NC}"
echo -e "Signed commits: ${GREEN}$SIGNED_COMMITS${NC}"
echo -e "Correct author: ${GREEN}$CORRECT_AUTHOR_COMMITS${NC}"

if [ "$SIGNED_COMMITS" -eq "$TOTAL_COMMITS" ] && [ "$CORRECT_AUTHOR_COMMITS" -eq "$TOTAL_COMMITS" ]; then
    echo -e "${GREEN}🎉 All commits are now properly signed and have correct author information!${NC}"
else
    echo -e "${RED}⚠️  Some commits may still need attention${NC}"
fi

echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Review the commit history: git log --oneline --format=\"%h %an <%ae> %G? %s\" -10"
echo "2. If satisfied, force push: git push --force-with-lease origin $CURRENT_BRANCH"
echo "3. If there are issues, restore backup: git reset --hard $BACKUP_BRANCH"
echo "4. Clean up backup branch: git branch -D $BACKUP_BRANCH"

echo ""
echo -e "${GREEN}✅ Script completed successfully!${NC}"
