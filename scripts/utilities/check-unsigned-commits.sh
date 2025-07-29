#!/bin/bash

# MIT License
#
# Copyright (c) 2025 Tyler Zervas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Quick check for unsigned commits across all branches
#
# USAGE:
#   ./check-unsigned-commits.sh
#
# DESCRIPTION:
#   Scans all local Git branches to identify commits that are not properly
#   GPG signed. Reports a summary of unsigned commits per branch.
#
# DEPENDENCIES:
#   - git (with GPG signing configured)
#   - Standard Unix utilities (grep, sed, head)
#
# EXIT CODES:
#   0: Success (analysis completed, may have found unsigned commits)
#   1: Error (missing dependencies or Git repository issues)

set -euo pipefail

# Logging functions
log_info() {
    echo -e "\033[0;34m[INFO]\033[0m $*" >&2
}

log_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $*" >&2
}

log_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $*" >&2
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $*" >&2
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current branch to return to it later
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get all local branches (excluding current branch marker)
mapfile -t BRANCHES < <(git branch | sed 's/^[ *]*//')

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
