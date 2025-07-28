#!/bin/bash

# MIT License
#
# Copyright (c) 2025 Tyler Zervas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# GitLab + Keycloak SSO Deployment Script
# This script deploys GitLab and Keycloak with SSO integration from your local workstation
#
# USAGE:
#   ./deploy-gitlab-keycloak.sh [ENVIRONMENT]
#
# DESCRIPTION:
#   Deploys GitLab and Keycloak with SSO integration to Kubernetes cluster.
#   Includes SSL certificate management and load balancer configuration.
#
# ENVIRONMENT VALUES:
#   development   Development environment (default)
#   staging       Staging environment
#   production    Production environment
#
# EXIT CODES:
#   0: Success
#   1: Deployment failed or prerequisites missing
#
# DEPENDENCIES:
#   - kubectl
#   - helm
#   - helmfile

set -euo pipefail

# Logging functions
log_info() {
    echo -e "\033[0;34m[INFO]\033[0m $*" >&2
}

log_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $*" >&2
}

log_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $*" >&2
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $*" >&2
}

ENVIRONMENT=${1:-development}
NAMESPACE_GITLAB="gitlab"
NAMESPACE_KEYCLOAK="keycloak"
CONTEXT_NAME="homelab-k3s"

echo "🚀 GitLab + Keycloak SSO Deployment"
echo "===================================="
echo "Environment: $ENVIRONMENT"
echo "Target cluster context: $CONTEXT_NAME"
echo ""

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."
if ! command_exists kubectl; then
  echo "❌ Error: kubectl is not installed"
  echo "Run: ./scripts/setup/setup-workstation.sh"
  exit 1
fi

if ! command_exists helm; then
  echo "❌ Error: helm is not installed"
  echo "Run: ./scripts/setup/setup-workstation.sh"
  exit 1
fi

if ! command_exists helmfile; then
  echo "❌ Error: helmfile is not installed"
  echo "Run: ./scripts/setup/setup-workstation.sh"
  exit 1
fi

# Check if we're connected to the right cluster
echo "🔗 Checking cluster connectivity..."
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "$CONTEXT_NAME" ]; then
  echo "⚠️  Warning: Current context is '$CURRENT_CONTEXT'"
  echo "Expected context: '$CONTEXT_NAME'"
  echo ""
  read -p "Do you want to switch to '$CONTEXT_NAME' context? [y/N]: " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl config use-context "$CONTEXT_NAME"
  else
    echo "Continuing with current context..."
  fi
fi

# Test cluster connectivity
if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "❌ Error: Cannot connect to Kubernetes cluster"
  echo "Please check your kubeconfig and cluster status"
  exit 1
fi

echo "✅ Connected to cluster: $(kubectl config current-context)"
echo "✅ Cluster nodes:"
kubectl get nodes --no-headers | while read -r line; do echo "   $line"; done

echo ""
echo "📦 Applying base Kubernetes configurations..."

# Apply configurations with better feedback
configs=(
  "kubernetes/base/metallb-config.yaml:MetalLB load balancer configuration"
  "kubernetes/base/cluster-issuers.yaml:SSL certificate issuers"
  "kubernetes/base/keycloak-secrets.yaml:Keycloak secrets"
  "kubernetes/base/gitlab-secrets.yaml:GitLab secrets"
  "kubernetes/base/gitlab-oidc-config.yaml:GitLab OIDC configuration"
  "kubernetes/base/backup-config.yaml:Backup job configuration"
)

for config in "${configs[@]}"; do
  file=$(echo "$config" | cut -d: -f1)
  desc=$(echo "$config" | cut -d: -f2)
  echo "   Applying $desc..."
  kubectl apply -f "$file"
done

echo "✅ Base configurations applied successfully"

# Wait for cert-manager to be ready
echo ""
echo "⏳ Waiting for cert-manager to be ready..."
if kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=cert-manager -n cert-manager --timeout=300s; then
  echo "✅ cert-manager is ready"
else
  echo "⚠️  cert-manager timeout - continuing anyway"
fi

# Update helm repositories
echo ""
echo "📚 Updating Helm repositories..."
echo "   This may take a moment..."

# Only add repos that aren't already added
helm repo list | grep -q bitnami || helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo list | grep -q gitlab || helm repo add gitlab https://charts.gitlab.io
helm repo update >/dev/null 2>&1

echo "✅ Helm repositories updated"

# Deploy using helmfile
echo ""
echo "🚀 Deploying services using helmfile..."
echo "   Environment: $ENVIRONMENT"
echo "   This will take 15-20 minutes..."
echo ""

cd helm
if helmfile -e "$ENVIRONMENT" sync; then
  echo "✅ Helmfile deployment completed successfully"
else
  echo "❌ Helmfile deployment failed"
  echo "Check the logs above for errors"
  exit 1
fi

cd ..

echo ""
echo "⏳ Waiting for services to be ready..."
echo "   This may take several minutes..."

# Wait for Keycloak
echo "   🔐 Waiting for Keycloak pods..."
if kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=keycloak -n $NAMESPACE_KEYCLOAK --timeout=600s; then
  echo "   ✅ Keycloak is ready"
else
  echo "   ⚠️  Keycloak timeout - checking status..."
  kubectl get pods -n $NAMESPACE_KEYCLOAK
fi

# Wait for GitLab
echo "   🦊 Waiting for GitLab pods..."
if kubectl wait --for=condition=ready pod -l app=webservice -n $NAMESPACE_GITLAB --timeout=1200s; then
  echo "   ✅ GitLab is ready"
else
  echo "   ⚠️  GitLab timeout - checking status..."
  kubectl get pods -n $NAMESPACE_GITLAB
fi

# Get service information
echo ""
echo "🎉 DEPLOYMENT SUMMARY"
echo "===================="
echo ""

# Get load balancer IPs
echo "📊 Service Status:"
kubectl get svc --all-namespaces | grep -E "(keycloak|gitlab|LoadBalancer|ClusterIP)" | head -10

echo ""
echo "🌐 Service URLs:"
echo "   🔐 Keycloak Admin Console: https://keycloak.dev.homelab.local"
echo "   🦊 GitLab: https://gitlab.dev.homelab.local"
echo "   📦 Container Registry: https://registry.dev.homelab.local"

echo ""
echo "🔑 Access Credentials:"
echo "   Keycloak Admin:"
echo "     Username: admin"
KEYCLOAK_PASSWORD=$(kubectl get secret keycloak-admin-secret -n $NAMESPACE_KEYCLOAK -o jsonpath='{.data.admin-password}' | base64 -d 2>/dev/null || echo "Failed to retrieve")
echo "     Password: $KEYCLOAK_PASSWORD"

echo ""
echo "   GitLab Root:"
echo "     Username: root"
GITLAB_PASSWORD=$(kubectl get secret gitlab-initial-root-password -n $NAMESPACE_GITLAB -o jsonpath='{.data.password}' | base64 -d 2>/dev/null || echo "Failed to retrieve")
echo "     Password: $GITLAB_PASSWORD"

echo ""
echo "📋 NEXT STEPS"
echo "============="
echo ""
echo "1. 🌐 Configure DNS entries:"
echo "     Add to your router DNS or /etc/hosts:"
echo "     192.168.25.204  gitlab.dev.homelab.local"
echo "     192.168.25.205  keycloak.dev.homelab.local"
echo "     192.168.25.206  registry.dev.homelab.local"
echo ""
echo "2. 🔐 Configure Keycloak SSO:"
echo "     • Access: https://keycloak.dev.homelab.local"
echo "     • Create 'gitlab' realm"
echo "     • Create 'gitlab' client (OIDC)"
echo "     • Copy client secret"
echo ""
echo "3. 🔗 Update GitLab OIDC integration:"
echo "     kubectl patch secret gitlab-oidc-secret -n $NAMESPACE_GITLAB -p '{\"stringData\":{\"client_secret\":\"YOUR_CLIENT_SECRET\"}}'"
echo "     kubectl rollout restart deployment/gitlab-webservice-default -n $NAMESPACE_GITLAB"
echo ""
echo "4. 🧪 Test the deployment:"
echo "     ./scripts/validation/test-sso-flow.sh"
echo ""
echo "🎯 Deployment completed successfully!"
