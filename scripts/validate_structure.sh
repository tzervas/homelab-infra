#!/bin/bash

# Script to validate repository structure and branch organization
# Usage: ./validate_structure.sh [--fix]

set -e

# Default values
FIX_ISSUES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_ISSUES=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--fix]"
            exit 1
            ;;
    esac
done

# Ensure we're in a Git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Initialize error counter
ERRORS=0
WARNINGS=0

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Helper function to print errors
print_error() {
    echo -e "${RED}ERROR:${NC} $1"
    ((ERRORS++))
}

# Helper function to print warnings
print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
    ((WARNINGS++))
}

# Helper function to print success
print_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

echo "Repository Structure Validation"
echo "=============================="

# Check for main branch
echo -e "\nChecking main branch..."
if ! git rev-parse --verify main > /dev/null 2>&1; then
    print_error "Main branch does not exist"
    if [ "$FIX_ISSUES" = true ]; then
        if git rev-parse --verify master > /dev/null 2>&1; then
            git branch -m master main
            print_success "Renamed 'master' branch to 'main'"
        else
            git checkout --orphan main
            git commit --allow-empty -m "Initial commit"
            print_success "Created main branch"
        fi
    fi
else
    print_success "Main branch exists"
fi

# Check for required files
echo -e "\nChecking required files..."
required_files=(".gitignore" "README.md" "LICENSE")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_warning "Missing $file file"
        if [ "$FIX_ISSUES" = true ]; then
            case "$file" in
                .gitignore)
                    echo "**/node_modules/" > .gitignore
                    echo "*.log" >> .gitignore
                    echo ".env" >> .gitignore
                    ;;
                README.md)
                    echo "# $(basename "$(git rev-parse --show-toplevel)")" > README.md
                    echo "\nAdd project description here." >> README.md
                    ;;
                LICENSE)
                    echo "MIT License" > LICENSE
                    echo "Copyright (c) $(date +%Y) $(git config user.name)" >> LICENSE
                    ;;
            esac
            print_success "Created $file with default content"
        fi
    fi
done

# Check branch naming conventions
echo -e "\nChecking branch naming conventions..."
git for-each-ref --format='%(refname:short)' refs/heads/ | while read -r branch; do
    if [[ "$branch" != "main" && ! "$branch" =~ ^(feature|bugfix|hotfix|release)/[a-z0-9-]+$ ]]; then
        print_warning "Branch '$branch' does not follow naming convention (feature/*, bugfix/*, hotfix/*, release/*)"
    fi
done

# Check for uncommitted changes
echo -e "\nChecking for uncommitted changes..."
if ! git diff --quiet HEAD; then
    print_warning "There are uncommitted changes in the working directory"
fi

# Check for untracked files
echo -e "\nChecking for untracked files..."
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    print_warning "There are untracked files in the working directory"
fi

# Check remote configuration
echo -e "\nChecking remote configuration..."
if ! git config --get remote.origin.url > /dev/null; then
    print_error "No remote 'origin' configured"
fi

# Check Git hooks
echo -e "\nChecking Git hooks..."
if [ ! -d ".git/hooks" ]; then
    print_warning "Git hooks directory not found"
elif [ -z "$(ls -A .git/hooks)" ]; then
    print_warning "No Git hooks configured"
fi

# Print summary
echo -e "\nValidation Summary"
echo "=================="
echo "Errors found: $ERRORS"
echo "Warnings found: $WARNINGS"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "\n${GREEN}All checks passed successfully!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "\n${YELLOW}Validation completed with warnings${NC}"
else
    echo -e "\n${RED}Validation failed with errors${NC}"
    exit 1
fi
