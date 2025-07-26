#!/bin/bash
# Private Configuration Repository Sync Script
# Manages integration with private configuration repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    print_error ".env file not found in project root"
    exit 1
fi

# Configuration
PRIVATE_CONFIG_REPO="${PRIVATE_CONFIG_REPO:-}"
PRIVATE_CONFIG_BRANCH="${PRIVATE_CONFIG_BRANCH:-main}"
PRIVATE_CONFIG_DIR="${PRIVATE_CONFIG_DIR:-config}"
PRIVATE_REPO_LOCAL_PATH="$PROJECT_ROOT/.private-config"

print_header "🔐 Private Configuration Repository Sync"
echo "========================================"
echo ""

# Check if private repo is configured
if [ -z "$PRIVATE_CONFIG_REPO" ]; then
    print_warning "PRIVATE_CONFIG_REPO not configured in .env file"
    echo ""
    echo "To set up private configuration repository:"
    echo "1. Create a private repository for your sensitive configurations"
    echo "2. Set PRIVATE_CONFIG_REPO in your .env file"
    echo "3. Run this script again"
    echo ""
    echo "Example:"
    echo "PRIVATE_CONFIG_REPO=git@github.com:username/homelab-infra-private.git"
    exit 0
fi

print_info "Private repo: $PRIVATE_CONFIG_REPO"
print_info "Branch: $PRIVATE_CONFIG_BRANCH"
print_info "Config directory: $PRIVATE_CONFIG_DIR"
echo ""

# Function to clone or update private repo
sync_private_repo() {
    if [ -d "$PRIVATE_REPO_LOCAL_PATH" ]; then
        print_info "Updating existing private configuration repository..."
        cd "$PRIVATE_REPO_LOCAL_PATH"

        # Check if it's the correct repository
        CURRENT_ORIGIN=$(git remote get-url origin 2>/dev/null || echo "")
        if [ "$CURRENT_ORIGIN" != "$PRIVATE_CONFIG_REPO" ]; then
            print_warning "Local repo origin doesn't match configured repo"
            print_info "Removing and re-cloning..."
            cd "$PROJECT_ROOT"
            rm -rf "$PRIVATE_REPO_LOCAL_PATH"
            clone_private_repo
            return
        fi

        # Update the repository
        git fetch origin
        git reset --hard "origin/$PRIVATE_CONFIG_BRANCH"
        print_success "Private repository updated"
    else
        clone_private_repo
    fi
}

clone_private_repo() {
    print_info "Cloning private configuration repository..."
    if git clone -b "$PRIVATE_CONFIG_BRANCH" "$PRIVATE_CONFIG_REPO" "$PRIVATE_REPO_LOCAL_PATH"; then
        print_success "Private repository cloned successfully"
    else
        print_error "Failed to clone private repository"
        print_info "Make sure you have access to the repository and SSH keys are configured"
        exit 1
    fi
}

# Function to initialize private repo structure
init_private_repo() {
    local config_path="$PRIVATE_REPO_LOCAL_PATH/$PRIVATE_CONFIG_DIR"

    if [ ! -d "$config_path" ]; then
        print_info "Initializing private repository structure..."

        # Create directory structure
        mkdir -p "$config_path"/{values,secrets,environments}

        # Copy example configurations
        if [ -d "$PROJECT_ROOT/examples/basic-setup/config" ]; then
            cp -r "$PROJECT_ROOT/examples/basic-setup/config"/* "$config_path/"
            print_success "Example configurations copied"
        fi

        # Create README
        cat > "$PRIVATE_REPO_LOCAL_PATH/README.md" << 'EOF'
# Private Homelab Configuration

This repository contains sensitive configurations and customizations for your homelab infrastructure.

## Directory Structure

```
config/
├── values/              # Helm values overrides
│   ├── global.yaml     # Global configuration
│   ├── gitlab.yaml     # GitLab configuration
│   ├── keycloak.yaml   # Keycloak configuration
│   └── monitoring.yaml # Monitoring configuration
├── secrets/            # Encrypted secrets
│   ├── gitlab-secrets.yaml
│   ├── keycloak-secrets.yaml
│   └── tls-certificates.yaml
└── environments/       # Environment-specific configs
    ├── development.yaml
    ├── staging.yaml
    └── production.yaml
```

## Security

- Never commit plain-text passwords or secrets
- Use encryption for sensitive data
- Regularly rotate credentials
- Limit repository access to authorized users

## Usage

This repository is automatically synced by the homelab-infra deployment scripts.
EOF

        # Create .env.private template
        cat > "$PRIVATE_REPO_LOCAL_PATH/.env.private" << 'EOF'
# Private Environment Variables
# These override values in the main .env file

# Sensitive Configuration
GITLAB_ROOT_PASSWORD=
KEYCLOAK_ADMIN_PASSWORD=
POSTGRES_PASSWORD=

# SMTP Configuration
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_HOST=
SMTP_PORT=587

# Backup Configuration
BACKUP_S3_ACCESS_KEY=
BACKUP_S3_SECRET_KEY=
BACKUP_S3_ENDPOINT=
BACKUP_S3_BUCKET=

# SSL Certificates
SSL_CERT_EMAIL=admin@your-domain.com
EOF

        print_success "Private repository structure initialized"
        print_warning "Don't forget to customize the configurations and add your secrets!"
    else
        print_success "Private repository structure already exists"
    fi
}

# Function to validate private configuration
validate_private_config() {
    local config_path="$PRIVATE_REPO_LOCAL_PATH/$PRIVATE_CONFIG_DIR"

    print_info "Validating private configuration..."

    # Check required directories
    local required_dirs=("values" "secrets" "environments")
    for dir in "${required_dirs[@]}"; do
        if [ -d "$config_path/$dir" ]; then
            print_success "$dir/ directory exists"
        else
            print_warning "$dir/ directory missing"
        fi
    done

    # Check for required files
    local required_files=("values/global.yaml")
    for file in "${required_files[@]}"; do
        if [ -f "$config_path/$file" ]; then
            print_success "$file exists"
        else
            print_error "$file missing - please create this file"
        fi
    done
}

# Main execution
main() {
    case "${1:-sync}" in
        "sync")
            sync_private_repo
            init_private_repo
            validate_private_config
            echo ""
            print_success "Private configuration sync completed!"
            ;;
        "init")
            if [ -d "$PRIVATE_REPO_LOCAL_PATH" ]; then
                init_private_repo
            else
                print_error "Private repository not found. Run 'sync' first."
                exit 1
            fi
            ;;
        "validate")
            if [ -d "$PRIVATE_REPO_LOCAL_PATH" ]; then
                validate_private_config
            else
                print_error "Private repository not found. Run 'sync' first."
                exit 1
            fi
            ;;
        "clean")
            if [ -d "$PRIVATE_REPO_LOCAL_PATH" ]; then
                rm -rf "$PRIVATE_REPO_LOCAL_PATH"
                print_success "Private repository cache cleaned"
            else
                print_info "No private repository cache to clean"
            fi
            ;;
        *)
            echo "Usage: $0 {sync|init|validate|clean}"
            echo ""
            echo "Commands:"
            echo "  sync     - Clone/update private configuration repository"
            echo "  init     - Initialize private repository structure"
            echo "  validate - Validate private configuration"
            echo "  clean    - Remove private repository cache"
            exit 1
            ;;
    esac
}

main "$@"
