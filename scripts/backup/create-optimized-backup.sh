#!/bin/bash

# Script to create optimized backup snapshots while excluding unnecessary files and potential secrets
# Usage: ./create-optimized-backup.sh [backup_name]

set -euo pipefail

BACKUP_NAME="${1:-$(date +%Y%m%d_%H%M%S)}"
BACKUP_DIR="backups/${BACKUP_NAME}"
EXCLUDE_FILE=".backup-exclude"

# Create exclude file
cat > "${EXCLUDE_FILE}" << EOF
.git
.pytest_cache
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*,cover
.hypothesis/
.venv
venv/
ENV/
.env
.env.*
*.log
*.sqlite
*.sqlite3
.idea/
.vscode/
node_modules/
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
*.retry
.DS_Store
Thumbs.db
*.swp
*.swo
*~
*.tmp
*.temp
.tmp/
*.pem
*.key
*.crt
*.csr
*.p12
*.pfx
*.backup
*.bak
*.orig
backups/
.mypy_cache/
.ruff_cache/
.pytest_cache/
EOF

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Create optimized snapshot
tar --exclude-from="${EXCLUDE_FILE}" \
    --exclude="${EXCLUDE_FILE}" \
    --exclude=".backup-exclude" \
    --exclude="*.tar.gz" \
    --exclude="*.zip" \
    --exclude="*.env*" \
    --exclude="**/secrets*" \
    --exclude="**/private*" \
    --exclude="**/.private*" \
    --exclude="**/*.secret*" \
    --exclude="**/*.key" \
    --exclude="**/*.pem" \
    --exclude="**/*.pfx" \
    --exclude="**/*.p12" \
    --exclude="**/*.crt" \
    --exclude="**/*.csr" \
    --transform="s,^\.,backup-snapshot," \
    -czf "${BACKUP_DIR}/working-directory-snapshot.tar.gz" .

# Calculate and store checksum
sha256sum "${BACKUP_DIR}/working-directory-snapshot.tar.gz" > "${BACKUP_DIR}/checksum.sha256"

# Create backup manifest
{
    echo "Backup created on: $(date)"
    echo "Backup name: ${BACKUP_NAME}"
    echo "Repository: $(git config --get remote.origin.url)"
    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Commit: $(git rev-parse HEAD)"
    echo "Files excluded: $(cat ${EXCLUDE_FILE} | grep -v '^#' | tr '\n' ' ')"
    echo
    echo "Important: This backup excludes all sensitive files, secrets, and credentials."
    echo "You will need to restore those separately from a secure storage location."
} > "${BACKUP_DIR}/manifest.txt"

# Cleanup
rm "${EXCLUDE_FILE}"

echo "Backup created successfully in ${BACKUP_DIR}"
echo "Backup size: $(du -h "${BACKUP_DIR}/working-directory-snapshot.tar.gz" | cut -f1)"
echo "Manifest and checksum files created"
