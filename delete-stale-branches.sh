#!/bin/bash

# List of branches to delete (stale or already merged)
STALE_BRANCHES=(
    "feature/comprehensive-testing-framework"
    "feature/documentation-consolidation-for-main"
    "feature/comprehensive-documentation-consolidation"
    "feature/merge-local-commits"
    "feature/comprehensive-deployment-validation"
    "feature/private-config-integration"
    "feature/private-config-integration-clean"
    "feature/validation-framework"
)

echo "=== Deleting Stale Remote Branches ==="

for branch in "${STALE_BRANCHES[@]}"; do
    echo "Deleting origin/$branch..."
    if git push origin --delete "$branch" 2>/dev/null; then
        echo "✓ Deleted $branch"
    else
        echo "✗ Failed to delete $branch (may already be deleted)"
    fi
done

echo -e "\n=== Cleaning up local branches ==="
# Delete local branches that track the deleted remotes
for branch in "${STALE_BRANCHES[@]}"; do
    if git show-ref --verify --quiet refs/heads/"$branch"; then
        echo "Deleting local $branch..."
        git branch -D "$branch" 2>/dev/null || echo "Failed to delete local $branch"
    fi
done

echo -e "\n=== Remaining feature branches ==="
git branch -r | grep origin/feature/ | sed 's/origin\///'
