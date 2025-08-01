#!/bin/bash

# Save the current branch to return to it later
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get all branches
BRANCHES=$(git branch | sed 's/^[ *]*//')

echo "Starting branch analysis..."

while IFS= read -r branch; do
    if [ "$branch" != "main" ]; then
        echo "Analyzing branch: $branch"

        # Checkout the branch
        git checkout "$branch" >/dev/null 2>&1

        # Check if branch can be fast-forwarded
        if git merge-base --is-ancestor main HEAD >/dev/null 2>&1; then
            FF_STATUS="Can fast-forward"
        else
            FF_STATUS="Needs rebase"
        fi

        # Check for security-related commits
        SECURITY_COMMITS=$(git log main..."$branch" --grep="security" --grep="CVE" --grep="vulnerability" --pretty=format:"%h" 2>/dev/null)
        if [ -n "$SECURITY_COMMITS" ]; then
            SECURITY_STATUS="Yes"
        else
            SECURITY_STATUS="No"
        fi

        # Append to branch mapping file
        echo "| $branch | $FF_STATUS | $SECURITY_STATUS |" >> docs/branch_mapping.md
    fi
done <<< "$BRANCHES"

# Return to original branch
git checkout "$ORIGINAL_BRANCH" >/dev/null 2>&1

echo "Analysis complete!"
