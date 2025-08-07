#!/bin/bash

# Script to update branch protection rules using GitHub CLI
# Usage: ./update_protection.sh [--branch branch_name] [--required-reviews N] [--enforce-admins]

set -e

# Default values
BRANCH="main"
REQUIRED_REVIEWS=1
ENFORCE_ADMINS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --required-reviews)
            REQUIRED_REVIEWS="$2"
            shift 2
            ;;
        --enforce-admins)
            ENFORCE_ADMINS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--branch branch_name] [--required-reviews N] [--enforce-admins]"
            exit 1
            ;;
    esac
done

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub"
    echo "Please run 'gh auth login' first"
    exit 1
fi

# Get repository information
REPO_URL=$(git config --get remote.origin.url)
if [[ $REPO_URL =~ github\.com[/:]([^/]+)/([^/]+)(\.git)?$ ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]%.git}"
else
    echo "Error: Could not determine GitHub repository information"
    exit 1
fi

echo "Updating branch protection rules"
echo "==============================="
echo "Repository: $OWNER/$REPO"
echo "Branch: $BRANCH"
echo "Required reviews: $REQUIRED_REVIEWS"
echo "Enforce admins: $ENFORCE_ADMINS"

# Build protection rule arguments
PROTECTION_ARGS=(
    --required-approving-review-count "$REQUIRED_REVIEWS"
    --require-last-push-approval
    --dismiss-stale-reviews
    --require-conversation-resolution
)

if [ "$ENFORCE_ADMINS" = true ]; then
    PROTECTION_ARGS+=(--strict)
fi

# Update branch protection
echo -e "\nApplying protection rules..."
if gh api --method PUT "/repos/$OWNER/$REPO/branches/$BRANCH/protection" \
    -f required_status_checks='{"strict":true,"contexts":[]}' \
    -f enforce_admins="$ENFORCE_ADMINS" \
    -f required_pull_request_reviews="{\"required_approving_review_count\":$REQUIRED_REVIEWS,\"dismiss_stale_reviews\":true,\"require_code_owner_reviews\":false}" \
    -f restrictions='null' \
    -F allow_force_pushes=false \
    -F allow_deletions=false \
    -F required_linear_history=true \
    -F required_conversation_resolution=true > /dev/null; then
    echo "Successfully updated branch protection rules!"
else
    echo "Error: Failed to update branch protection rules"
    exit 1
fi

# Verify protection settings
echo -e "\nCurrent protection settings for $BRANCH:"
gh api "/repos/$OWNER/$REPO/branches/$BRANCH/protection" | jq -r '
    "Required reviews: " + (.required_pull_request_reviews.required_approving_review_count | tostring),
    "Enforce admins: " + (.enforce_admins.enabled | tostring),
    "Require linear history: " + (.required_linear_history.enabled | tostring),
    "Allow force pushes: " + (.allow_force_pushes.enabled | tostring),
    "Allow deletions: " + (.allow_deletions.enabled | tostring)'
