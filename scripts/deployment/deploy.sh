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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
DRY_RUN=false
SKIP_DEPS=false

# Help function
show_help() {
  cat <<EOF
Usage: $0 [OPTIONS]

Deploy homelab infrastructure using Helmfile

OPTIONS:
    -e, --environment ENV    Environment to deploy (development|staging|production) [default: development]
    -d, --dry-run           Perform a dry run without making changes
    -s, --skip-deps         Skip Helm dependency updates
    -h, --help              Show this help message

EXAMPLES:
    $0 -e development
    $0 -e production --dry-run
    $0 --skip-deps

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e | --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -d | --dry-run)
      DRY_RUN=true
      shift
      ;;
    -s | --skip-deps)
      SKIP_DEPS=true
      shift
      ;;
    -h | --help)
      show_help
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

# Validate environment
if [[ ! $ENVIRONMENT =~ ^(development|staging|production)$ ]]; then
  echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
  echo "Valid environments: development, staging, production"
  exit 1
fi

echo -e "${GREEN}Starting deployment for environment: $ENVIRONMENT${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if kubectl is available and configured
if ! command -v kubectl &>/dev/null; then
  echo -e "${RED}kubectl not found. Please install kubectl.${NC}"
  exit 1
fi

# Check if helmfile is available
if ! command -v helmfile &>/dev/null; then
  echo -e "${RED}helmfile not found. Please install helmfile.${NC}"
  exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &>/dev/null; then
  echo -e "${RED}Cannot connect to Kubernetes cluster. Please check your kubeconfig.${NC}"
  exit 1
fi

echo -e "${GREEN}Prerequisites check passed.${NC}"

# Change to the helm directory
cd "$(dirname "$0")/../helm"

# Update Helm repositories
echo -e "${YELLOW}Updating Helm repositories...${NC}"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo add metallb https://metallb.github.io/metallb
helm repo add longhorn https://charts.longhorn.io
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update

# Update dependencies
if [[ $SKIP_DEPS == false ]]; then
  echo -e "${YELLOW}Updating Helm dependencies...${NC}"
  for chart_dir in charts/*/; do
    if [[ -f "$chart_dir/Chart.yaml" ]]; then
      echo "Updating dependencies for $(basename "$chart_dir")"
      helm dependency update "$chart_dir"
    fi
  done
fi

# Apply base Kubernetes manifests
echo -e "${YELLOW}Applying base Kubernetes manifests...${NC}"
kubectl apply -f ../kubernetes/base/namespaces.yaml
kubectl apply -f ../kubernetes/base/rbac.yaml

# Deploy using Helmfile
echo -e "${YELLOW}Deploying infrastructure with Helmfile...${NC}"
if [[ $DRY_RUN == true ]]; then
  echo -e "${YELLOW}Performing dry run...${NC}"
  helmfile --environment "$ENVIRONMENT" diff
else
  helmfile --environment "$ENVIRONMENT" apply --wait --timeout 600
fi

# Apply post-deployment manifests
if [[ $DRY_RUN == false ]]; then
  echo -e "${YELLOW}Applying post-deployment manifests...${NC}"

  # Wait for cert-manager to be ready
  echo "Waiting for cert-manager to be ready..."
  kubectl wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=300s
  kubectl wait --for=condition=Available deployment/cert-manager-webhook -n cert-manager --timeout=300s
  kubectl wait --for=condition=Available deployment/cert-manager-cainjector -n cert-manager --timeout=300s

  # Apply cluster issuers
  kubectl apply -f ../kubernetes/base/cluster-issuers.yaml

  # Wait for MetalLB to be ready
  echo "Waiting for MetalLB to be ready..."
  kubectl wait --for=condition=Available deployment/metallb-controller -n metallb-system --timeout=300s

  # Apply MetalLB configuration
  kubectl apply -f ../kubernetes/base/metallb-config.yaml

  # Apply network policies
  kubectl apply -f ../kubernetes/base/network-policies.yaml

  echo -e "${GREEN}Deployment completed successfully!${NC}"

  # Show status
  echo -e "${YELLOW}Checking deployment status...${NC}"
  kubectl get nodes -o wide
  kubectl get pods -A | grep -E "(metallb|cert-manager|ingress-nginx|longhorn|monitoring)"

  echo -e "${GREEN}Infrastructure URLs (adjust IPs based on your MetalLB assignment):${NC}"
  echo "Grafana: https://grafana.$ENVIRONMENT.homelab.local"
  echo "Longhorn: https://longhorn.$ENVIRONMENT.homelab.local"
  echo "Prometheus: https://prometheus.$ENVIRONMENT.homelab.local"

else
  echo -e "${YELLOW}Dry run completed.${NC}"
fi
