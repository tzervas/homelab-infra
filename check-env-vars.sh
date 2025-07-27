#!/bin/bash

# Check environment variables configuration
echo "Checking environment configuration..."
echo "====================================="

# Check if files exist
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    exit 1
fi

if [ ! -f ".env.private.local" ]; then
    echo "ERROR: .env.private.local file not found!"
    exit 1
fi

# Check file permissions
env_perms=$(stat -c "%a" .env)
priv_perms=$(stat -c "%a" .env.private.local)

if [ "$env_perms" != "600" ]; then
    echo "WARNING: .env permissions are $env_perms (should be 600)"
else
    echo "✓ .env permissions: 600"
fi

if [ "$priv_perms" != "600" ]; then
    echo "WARNING: .env.private.local permissions are $priv_perms (should be 600)"
else
    echo "✓ .env.private.local permissions: 600"
fi

echo ""
echo "Checking required variables..."
echo "=============================="

# Required variables from templates
required_vars=(
    "APP_ENVIRONMENT"
    "DEBUG_MODE"
    "DEFAULT_CPU_LIMIT"
    "DEFAULT_CPU_REQUEST"
    "DEFAULT_MEMORY_LIMIT"
    "DEFAULT_MEMORY_REQUEST"
    "ENABLE_GRAFANA"
    "ENABLE_MONITORING"
    "K8S_CLUSTER_TYPE"
    "K8S_NAMESPACE"
    "LOCAL_KUBECONFIG_PATH"
    "PROMETHEUS_RETENTION_DAYS"
    "REMOTE_HOST_IP"
    "REMOTE_KUBECONFIG_PATH"
    "REMOTE_SSH_KEY_PATH"
    "REMOTE_SSH_PORT"
    "REMOTE_USER"
)

# Sensitive variables that should be in .env.private.local
sensitive_vars=(
    "GITLAB_ROOT_PASSWORD"
    "GITLAB_DB_PASSWORD"
    "GRAFANA_ADMIN_PASSWORD"
    "KEYCLOAK_ADMIN_PASSWORD"
    "KEYCLOAK_DB_PASSWORD"
    "POSTGRES_PASSWORD"
)

missing_vars=0

# Check required variables in .env
echo "Checking required variables in .env:"
for var in "${required_vars[@]}"; do
    if grep -q "^$var=" .env; then
        value=$(grep "^$var=" .env | cut -d'=' -f2)
        if [ -z "$value" ] || [ "$value" = "\${HOMELAB_SERVER_IP}" ] || [ "$value" = "\${HOMELAB_SSH_USER}" ] || [ "$value" = "\${HOMELAB_SSH_KEY_PATH}" ] || [ "$value" = "\${HOME}/.kube/config" ]; then
            # Check if it's a variable reference that needs to be resolved
            echo "✓ $var (uses variable reference)"
        else
            echo "✓ $var"
        fi
    else
        echo "✗ $var - MISSING"
        ((missing_vars++))
    fi
done

echo ""
echo "Checking sensitive variables in .env.private.local:"
for var in "${sensitive_vars[@]}"; do
    if grep -q "^$var=" .env.private.local; then
        echo "✓ $var (exists)"
    else
        echo "✗ $var - MISSING"
        ((missing_vars++))
    fi
done

echo ""
if [ $missing_vars -eq 0 ]; then
    echo "✅ All required environment variables are configured!"
else
    echo "❌ Found $missing_vars missing variables. Please configure them before deployment."
    exit 1
fi

# Check for empty sensitive values
echo ""
echo "Checking for empty sensitive values..."
empty_count=0
while IFS='=' read -r key value; do
    if [[ "$key" =~ ^[A-Z_]+$ ]] && [ -z "$value" ]; then
        echo "WARNING: $key is empty in .env.private.local"
        ((empty_count++))
    fi
done < .env.private.local

if [ $empty_count -gt 0 ]; then
    echo "⚠️  Found $empty_count empty sensitive values. Make sure to set them before deployment."
fi

echo ""
echo "Environment configuration check complete!"
