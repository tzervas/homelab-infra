#!/bin/bash

# Script to create optimized backup snapshots while excluding unnecessary files and potential secrets
# Usage: ./create-optimized-backup.sh [backup_name] [max_size_mb]

set -euo pipefail

BACKUP_NAME="${1:-$(date +%Y%m%d_%H%M%S)}"
MAX_SIZE_MB="${2:-45}"  # Default to 45MB to stay under GitHub's 50MB limit
BACKUP_DIR="backups/${BACKUP_NAME}"
EXCLUDE_FILE=".backup-exclude"
MAX_SIZE_BYTES=$((MAX_SIZE_MB * 1024 * 1024))

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

# Additional exclusions for large files
find . -type f -size +${MAX_SIZE_MB}M 2>/dev/null | while read -r large_file; do
    echo "Excluding large file: $large_file ($(du -h "$large_file" | cut -f1))" >> "${BACKUP_DIR}/large_files_excluded.txt"
    echo "$large_file" >> "${EXCLUDE_FILE}"
done
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

# Check if the backup exceeds max size
BACKUP_SIZE=$(stat -f%z "${BACKUP_DIR}/working-directory-snapshot.tar.gz" 2>/dev/null || stat -c%s "${BACKUP_DIR}/working-directory-snapshot.tar.gz")
if [ "$BACKUP_SIZE" -gt "$MAX_SIZE_BYTES" ]; then
    echo "Error: Backup size ($(numfmt --to=iec-i --suffix=B $BACKUP_SIZE)) exceeds maximum allowed size (${MAX_SIZE_MB}MB)"
    echo "Consider excluding more files or increasing compression"
    rm -f "${BACKUP_DIR}/working-directory-snapshot.tar.gz"
    exit 1
fi
# Calculate and store checksum
sha256sum "${BACKUP_DIR}/working-directory-snapshot.tar.gz" > "${BACKUP_DIR}/checksum.sha256"

# Create backup manifest
{
    echo "Backup created on: $(date)"
    echo "Backup name: ${BACKUP_NAME}"
    echo "Repository: $(git config --get remote.origin.url)"
    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Commit: $(git rev-parse HEAD)"
    echo "Maximum file size: ${MAX_SIZE_MB}MB"
    echo "Actual backup size: $(numfmt --to=iec-i --suffix=B $BACKUP_SIZE)"
    echo "Files excluded: $(cat ${EXCLUDE_FILE} | grep -v '^#' | tr '\n' ' ')"
    echo
    if [ -f "${BACKUP_DIR}/large_files_excluded.txt" ]; then
        echo "Large files excluded:"
        cat "${BACKUP_DIR}/large_files_excluded.txt"
        echo
    fi
    echo "Important: This backup excludes all sensitive files, secrets, and credentials."
    echo "You will need to restore those separately from a secure storage location."
} > "${BACKUP_DIR}/manifest.txt"

# Cleanup
rm "${EXCLUDE_FILE}"

echo "Backup created successfully in ${BACKUP_DIR}"
echo "Backup size: $(du -h "${BACKUP_DIR}/working-directory-snapshot.tar.gz" | cut -f1)"
echo "Manifest and checksum files created"
