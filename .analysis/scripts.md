# Branch Management Scripts

This directory contains scripts for managing and analyzing Git branches in the repository.

## Scripts Overview

### analyze_branches.py

A Python script that analyzes the current state of branches in the repository.

**Usage:**
```bash
./scripts/analyze_branches.py
```

**Features:**
- Lists all branches with their last commit information
- Shows the number of commits in each branch
- Identifies the base branch (if main)
- Displays last modified date and author
- Sorts branches by last activity

### backup_branches.sh

Creates backups of all Git branches in the repository.

**Usage:**
```bash
./scripts/backup_branches.sh [backup_dir]
```

**Features:**
- Creates timestamped backups of all branches
- Saves branch metadata and content
- Creates patches against main branch
- Generates a backup manifest
- Default backup location: ./branch-backups

### consolidate_branches.sh

Helps consolidate branches by identifying and handling stale or merged branches.

**Usage:**
```bash
./scripts/consolidate_branches.sh [--dry-run] [--stale-days N]
```

**Features:**
- Identifies merged branches
- Detects stale branches (default: 30 days without commits)
- Creates backup tags for stale branches
- Supports dry-run mode
- Provides detailed analysis report

### update_protection.sh

Updates branch protection rules using the GitHub CLI.

**Usage:**
```bash
./scripts/update_protection.sh [--branch branch_name] [--required-reviews N] [--enforce-admins]
```

**Features:**
- Configures branch protection rules
- Sets required review count
- Enables/disables admin enforcement
- Verifies protection settings
- Requires GitHub CLI (gh) to be installed and authenticated

### validate_structure.sh

Validates repository structure and branch organization.

**Usage:**
```bash
./scripts/validate_structure.sh [--fix]
```

**Features:**
- Checks for main branch existence
- Validates required files (README.md, LICENSE, .gitignore)
- Enforces branch naming conventions
- Detects uncommitted changes
- Verifies remote configuration
- Checks Git hooks
- Can automatically fix common issues with --fix flag

## Usage in Cleanup Workflow

1. Start by analyzing the current state:
```bash
./scripts/analyze_branches.py
```

2. Create a backup before making changes:
```bash
./scripts/backup_branches.sh
```

3. Validate repository structure:
```bash
./scripts/validate_structure.sh --fix
```

4. Consolidate branches:
```bash
# First run in dry-run mode
./scripts/consolidate_branches.sh --dry-run
# Then run for real if changes look good
./scripts/consolidate_branches.sh
```

5. Update branch protection:
```bash
./scripts/update_protection.sh --branch main --required-reviews 1 --enforce-admins
```

## Testing

To test these scripts in an isolated environment:

```bash
# Create test environment
git worktree add ../test-cleanup test-branch

# Change to test directory
cd ../test-cleanup

# Run validation
./scripts/validate_structure.sh

# Test other scripts as needed
./scripts/analyze_branches.py
./scripts/backup_branches.sh ./test-backups
```

## Requirements

- Python 3.12+ for analyze_branches.py
- Bash shell for shell scripts
- Git
- GitHub CLI (gh) for update_protection.sh
- jq for JSON processing in update_protection.sh

## Error Handling

All scripts include:
- Input validation
- Error checking
- Status reporting
- Safe defaults
- Dry-run options where applicable

## Maintenance

- Keep scripts updated with repository changes
- Review and adjust thresholds (e.g., stale days) as needed
- Update protection rules based on team size and workflow
- Regular testing in isolated environment
