#!/bin/bash

# Script to update branches in dependency order while maintaining GPG signatures
set -e

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Stash any changes
if ! git diff-index --quiet HEAD --; then
    echo "Stashing local changes..."
    git stash push -m "Auto stash before branch updates"
fi

# Start with core feature branches
echo "Updating core feature branches..."
core_branches=(
    "feature/core-orchestrator-foundation"
    "feature/configuration-management"
    "feature/security-cicd-infrastructure"
)

for branch in "${core_branches[@]}"; do
    echo "Updating $branch..."
    git checkout "$branch"
    git merge main --no-edit -S || {
        echo "Conflict in $branch. Please resolve manually."
        exit 1
    }
done

# Update infrastructure branches
infra_branches=(
    "feat/infra-base"
    "feat/infra-security"
    "feat/infra-apps"
)

for branch in "${infra_branches[@]}"; do
    echo "Updating $branch..."
    git checkout "$branch"
    git merge main --no-edit -S || {
        echo "Conflict in $branch. Please resolve manually."
        exit 1
    }
done

# Update configuration branches
config_branches=(
    "feat/config-base"
    "feat/config-environments"
    "feat/config-domains-env"
    "feat/config-network"
    "feat/config-resources"
    "feat/config-services"
)

for branch in "${config_branches[@]}"; do
    echo "Updating $branch..."
    git checkout "$branch"
    git merge main --no-edit -S || {
        echo "Conflict in $branch. Please resolve manually."
        exit 1
    }
done

# Update orchestration branches
orch_branches=(
    "feat/orch-core"
    "feat/orch-core-config"
    "feat/orch-core-gpu"
    "feat/orch-core-health"
    "feat/orch-core-state"
    "feat/orch-deployment"
    "feat/orch-deploy-base"
    "feat/orch-deploy-components"
    "feat/orch-deploy-core"
    "feat/orch-deploy-hooks"
    "feat/orch-deploy-lifecycle"
    "feat/orch-deploy-utils"
)

for branch in "${orch_branches[@]}"; do
    echo "Updating $branch..."
    git checkout "$branch"
    git merge main --no-edit -S || {
        echo "Conflict in $branch. Please resolve manually."
        exit 1
    }
done

# Update portal branches
portal_branches=(
    "feat/orch-portal-base"
    "feat/orch-portal-manager"
    "feat/orch-portal"
)

for branch in "${portal_branches[@]}"; do
    echo "Updating $branch..."
    git checkout "$branch"
    git merge main --no-edit -S || {
        echo "Conflict in $branch. Please resolve manually."
        exit 1
    }
done

# Return to main branch
git checkout main

# Restore stashed changes if any
if git stash list | grep -q "Auto stash before branch updates"; then
    git stash pop
fi

echo "Branch updates complete!"
