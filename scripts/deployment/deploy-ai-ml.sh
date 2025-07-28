#!/bin/bash

# AI/ML Infrastructure Deployment Script
# Deploy Ollama and Open WebUI to Kubernetes cluster

set -e

# Configuration
NAMESPACE="ai-ml"
DOMAIN="${AI_ML_DOMAIN:-ai.homelab.local}"
STORAGE_CLASS="${STORAGE_CLASS:-longhorn}"
DEPLOYMENT_METHOD="${DEPLOYMENT_METHOD:-kubectl}" # kubectl or helm

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
  log_info "Checking prerequisites..."

  # Check kubectl
  if ! command -v kubectl &>/dev/null; then
    log_error "kubectl is not installed or not in PATH"
    exit 1
  fi

  # Check cluster connection
  if ! kubectl cluster-info &>/dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
  fi

  # Check if helm is available for helm deployment
  if [ "$DEPLOYMENT_METHOD" = "helm" ] && ! command -v helm &>/dev/null; then
    log_error "helm is not installed or not in PATH (required for helm deployment)"
    exit 1
  fi

  # Check if storage class exists
  if ! kubectl get storageclass "$STORAGE_CLASS" &>/dev/null; then
    log_warning "Storage class '$STORAGE_CLASS' not found. Make sure it exists."
  fi

  log_success "Prerequisites check completed"
}

create_namespace() {
  log_info "Creating namespace '$NAMESPACE'..."

  if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_info "Namespace '$NAMESPACE' already exists"
  else
    kubectl apply -f kubernetes/base/namespaces.yaml
    log_success "Namespace '$NAMESPACE' created"
  fi
}

generate_secrets() {
  log_info "Generating secrets for Open WebUI..."

  if kubectl get secret open-webui-secrets -n "$NAMESPACE" &>/dev/null; then
    log_info "Secrets already exist"
    return 0
  fi

  # Generate random secrets
  SECRET_KEY=$(openssl rand -base64 32)
  JWT_SECRET_KEY=$(openssl rand -base64 32)

  kubectl create secret generic open-webui-secrets \
    --from-literal=secret-key="$SECRET_KEY" \
    --from-literal=jwt-secret-key="$JWT_SECRET_KEY" \
    -n "$NAMESPACE"

  log_success "Secrets generated and created"
}

deploy_with_kubectl() {
  log_info "Deploying AI/ML infrastructure using kubectl..."

  # Update domain in ingress if different from default
  if [ "$DOMAIN" != "ai.homelab.local" ]; then
    log_info "Updating domain to '$DOMAIN' in ingress configuration"
    sed -i.bak "s/ai\.homelab\.local/$DOMAIN/g" kubernetes/ai-ml/open-webui/ingress.yaml
  fi

  # Apply all manifests
  kubectl apply -f kubernetes/ai-ml/

  log_success "AI/ML infrastructure deployed using kubectl"
}

deploy_with_helm() {
  log_info "Deploying AI/ML infrastructure using Helm..."

  # Create temporary values file with domain
  cat >/tmp/ai-ml-values.yaml <<EOF
global:
  domain: $DOMAIN

openWebUI:
  ingress:
    host: $DOMAIN
EOF

  helm upgrade --install ai-ml ./helm/charts/ai-ml \
    --namespace "$NAMESPACE" \
    --create-namespace \
    --values ./helm/charts/ai-ml/values.yaml \
    --values /tmp/ai-ml-values.yaml

  # Clean up temporary file
  rm -f /tmp/ai-ml-values.yaml

  log_success "AI/ML infrastructure deployed using Helm"
}

wait_for_deployment() {
  log_info "Waiting for deployments to be ready..."

  # Wait for Ollama deployment
  kubectl wait --for=condition=available --timeout=300s deployment/ollama -n "$NAMESPACE"

  # Wait for Open WebUI deployment
  kubectl wait --for=condition=available --timeout=300s deployment/open-webui -n "$NAMESPACE"

  log_success "All deployments are ready"
}

setup_model_management() {
  log_info "Setting up model management..."

  # Apply model management configuration
  kubectl apply -f kubernetes/ai-ml/model-management.yaml

  log_info "Model management job created. To monitor progress:"
  log_info "kubectl logs -f job/model-downloader -n $NAMESPACE"
}

verify_deployment() {
  log_info "Verifying deployment..."

  # Check pods
  log_info "Checking pod status..."
  kubectl get pods -n "$NAMESPACE"

  # Check services
  log_info "Checking services..."
  kubectl get svc -n "$NAMESPACE"

  # Check ingress
  log_info "Checking ingress..."
  kubectl get ingress -n "$NAMESPACE"

  # Test Ollama API
  log_info "Testing Ollama API connectivity..."
  if kubectl run test-ollama --image=curlimages/curl --rm -i --restart=Never -n "$NAMESPACE" -- \
    curl -f http://ollama-service:11434/ &>/dev/null; then
    log_success "Ollama API is accessible"
  else
    log_warning "Ollama API test failed"
  fi

  log_success "Deployment verification completed"
}

print_access_info() {
  log_info "Deployment completed successfully!"
  echo
  log_info "Access Information:"
  echo "  Open WebUI: https://$DOMAIN"
  echo "  Ollama API: http://ollama-service.$NAMESPACE.svc.cluster.local:11434"
  echo
  log_info "Useful Commands:"
  echo "  Check pods: kubectl get pods -n $NAMESPACE"
  echo "  Check logs: kubectl logs -f deployment/ollama -n $NAMESPACE"
  echo "  Port forward: kubectl port-forward svc/ollama-service 11434:11434 -n $NAMESPACE"
  echo
  log_info "Model Management:"
  echo "  Monitor downloads: kubectl logs -f job/model-downloader -n $NAMESPACE"
  echo "  List models: kubectl port-forward svc/ollama-service 11434:11434 -n $NAMESPACE & curl http://localhost:11434/api/tags"
}

cleanup_on_failure() {
  if [ $? -ne 0 ]; then
    log_error "Deployment failed. Cleaning up..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    exit 1
  fi
}

# Main execution
main() {
  log_info "Starting AI/ML infrastructure deployment..."
  log_info "Domain: $DOMAIN"
  log_info "Namespace: $NAMESPACE"
  log_info "Storage Class: $STORAGE_CLASS"
  log_info "Deployment Method: $DEPLOYMENT_METHOD"
  echo

  # Set up cleanup on failure
  trap cleanup_on_failure ERR

  check_prerequisites
  create_namespace
  generate_secrets

  case "$DEPLOYMENT_METHOD" in
    "kubectl")
      deploy_with_kubectl
      ;;
    "helm")
      deploy_with_helm
      ;;
    *)
      log_error "Invalid deployment method: $DEPLOYMENT_METHOD (use 'kubectl' or 'helm')"
      exit 1
      ;;
  esac

  wait_for_deployment
  setup_model_management
  verify_deployment
  print_access_info
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --storage-class)
      STORAGE_CLASS="$2"
      shift 2
      ;;
    --method)
      DEPLOYMENT_METHOD="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --domain DOMAIN           Set the domain for Open WebUI (default: ai.homelab.local)"
      echo "  --namespace NAMESPACE     Set the Kubernetes namespace (default: ai-ml)"
      echo "  --storage-class CLASS     Set the storage class (default: longhorn)"
      echo "  --method METHOD           Deployment method: kubectl or helm (default: kubectl)"
      echo "  --help                    Show this help message"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Run main function
main
