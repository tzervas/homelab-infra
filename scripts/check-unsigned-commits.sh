#!/bin/bash

# Quick check for unsigned commits across all branches

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current branch to return to it later
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get all local branches (excluding current branch marker)
BRANCHES=($(git branch | sed 's/^[ *]*//'))

echo -e "${BLUE}Checking ${#BRANCHES[@]} branches for unsigned commits...${NC}"
echo

BRANCHES_WITH_UNSIGNED=()

for branch in "${BRANCHES[@]}"; do
  echo -n "Checking $branch... "

  # Checkout the branch quietly
  git checkout "$branch" &>/dev/null || {
    echo -e "${RED}Failed to checkout${NC}"
    continue
  }

  # Check for unsigned commits in this branch
  UNSIGNED_COUNT=$(git log --pretty=format:"%H %G?" HEAD | grep -cE " [NU]$" 2>/dev/null || echo 0)

  if [ "$UNSIGNED_COUNT" -gt 0 ]; then
    echo -e "${RED}$UNSIGNED_COUNT unsigned commits${NC}"
    BRANCHES_WITH_UNSIGNED+=("$branch")

    # Show the unsigned commits
    echo -e "${YELLOW}  Unsigned commits:${NC}"
    git log --pretty=format:"    %h %G? %s" HEAD | grep -E " [NU] " | head -5
    if [ "$UNSIGNED_COUNT" -gt 5 ]; then
      echo "    ... and $((UNSIGNED_COUNT - 5)) more"
    fi
  else
    echo -e "${GREEN}All signed${NC}"
  fi
done

# Return to original branch
git checkout "$ORIGINAL_BRANCH" &>/dev/null

echo
echo -e "${BLUE}=== SUMMARY ===${NC}"
if [ ${#BRANCHES_WITH_UNSIGNED[@]} -eq 0 ]; then
  echo -e "${GREEN}✓ All branches have properly signed commits${NC}"
else
  echo -e "${YELLOW}Branches with unsigned commits (${#BRANCHES_WITH_UNSIGNED[@]}/${#BRANCHES[@]}):${NC}"
  for branch in "${BRANCHES_WITH_UNSIGNED[@]}"; do
    echo -e "${RED}  ✗ $branch${NC}"
  done
  echo
  echo -e "${BLUE}Run ./scripts/fix-all-unsigned-commits.sh to fix these issues${NC}"
fi
