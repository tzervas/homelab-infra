#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BLUE}=== $* ===${NC}\n"; }

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Verify cluster connection
log_section "Verifying Cluster Connection"
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi
log_info "Successfully connected to cluster"

# Create all required namespaces
log_section "Creating Namespaces"
namespaces=(
    "homelab"
    "homelab-portal"
    "monitoring"
    "keycloak"
    "gitlab"
    "jupyter"
    "ai-tools"
    "databases"
    "longhorn-system"
)

for ns in "${namespaces[@]}"; do
    if kubectl get namespace "$ns" &> /dev/null; then
        log_info "Namespace $ns already exists"
    else
        kubectl create namespace "$ns"
        log_info "Created namespace $ns"
    fi
done

# Apply priority classes first
log_section "Creating Priority Classes"
cat <<EOF | kubectl apply -f -
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: infrastructure-critical
value: 1000
globalDefault: false
description: "Critical infrastructure components"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: core-services
value: 900
globalDefault: false
description: "Core application services"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: standard-apps
value: 500
globalDefault: true
description: "Standard applications"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-jobs
value: 100
globalDefault: false
description: "Batch and background jobs"
EOF

# Update MetalLB resources
log_section "Updating MetalLB Resources"
kubectl patch deployment controller -n metallb-system --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "100m", "memory": "100Mi"},
      "requests": {"cpu": "50m", "memory": "50Mi"}
    }
  }
]' || log_warn "Failed to patch MetalLB controller"

kubectl patch daemonset speaker -n metallb-system --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "100m", "memory": "100Mi"},
      "requests": {"cpu": "50m", "memory": "50Mi"}
    }
  }
]' || log_warn "Failed to patch MetalLB speaker"

# Update Cert-Manager resources
log_section "Updating Cert-Manager Resources"
kubectl patch deployment cert-manager -n cert-manager --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "100m", "memory": "128Mi"},
      "requests": {"cpu": "50m", "memory": "64Mi"}
    }
  }
]' || log_warn "Failed to patch cert-manager"

kubectl patch deployment cert-manager-webhook -n cert-manager --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "50m", "memory": "64Mi"},
      "requests": {"cpu": "10m", "memory": "32Mi"}
    }
  }
]' || log_warn "Failed to patch cert-manager-webhook"

kubectl patch deployment cert-manager-cainjector -n cert-manager --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "100m", "memory": "128Mi"},
      "requests": {"cpu": "50m", "memory": "64Mi"}
    }
  }
]' || log_warn "Failed to patch cert-manager-cainjector"

# Update NGINX Ingress resources
log_section "Updating NGINX Ingress Resources"
kubectl patch deployment ingress-nginx-controller -n ingress-nginx --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "500m", "memory": "512Mi"},
      "requests": {"cpu": "100m", "memory": "256Mi"}
    }
  }
]' || log_warn "Failed to patch ingress-nginx-controller"

# Update Sealed Secrets resources
log_section "Updating Sealed Secrets Resources"
kubectl patch deployment sealed-secrets -n kube-system --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources",
    "value": {
      "limits": {"cpu": "100m", "memory": "128Mi"},
      "requests": {"cpu": "50m", "memory": "64Mi"}
    }
  }
]' || log_warn "Failed to patch sealed-secrets"

# Deploy/Update OAuth2 Proxy
log_section "Deploying OAuth2 Proxy"
kubectl apply -f kubernetes/base/oauth2-proxy.yaml

# Deploy/Update Enhanced Portal
log_section "Deploying Enhanced Portal"
kubectl apply -f kubernetes/enhanced-portal.yaml

# Apply the ingress without OAuth2 for now
log_section "Updating Portal Ingress"
kubectl apply -f kubernetes/portal-ingress-noauth.yaml

# Create resource quotas for namespaces
log_section "Creating Resource Quotas"
cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: homelab-portal-quota
  namespace: homelab-portal
spec:
  hard:
    requests.cpu: "500m"
    requests.memory: "500Mi"
    limits.cpu: "1"
    limits.memory: "1Gi"
    persistentvolumeclaims: "5"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: monitoring-quota
  namespace: monitoring
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "4Gi"
    limits.cpu: "8"
    limits.memory: "8Gi"
    persistentvolumeclaims: "20"
    requests.storage: "200Gi"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: keycloak-quota
  namespace: keycloak
spec:
  hard:
    requests.cpu: "1"
    requests.memory: "1Gi"
    limits.cpu: "2"
    limits.memory: "2Gi"
    persistentvolumeclaims: "5"
    requests.storage: "20Gi"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: gitlab-quota
  namespace: gitlab
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "4Gi"
    limits.cpu: "8"
    limits.memory: "8Gi"
    persistentvolumeclaims: "10"
    requests.storage: "500Gi"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ai-tools-quota
  namespace: ai-tools
spec:
  hard:
    requests.cpu: "6"
    requests.memory: "8Gi"
    limits.cpu: "12"
    limits.memory: "16Gi"
    persistentvolumeclaims: "10"
    requests.storage: "200Gi"
EOF

# Wait for deployments to be ready
log_section "Waiting for Deployments"
deployments=(
    "metallb-system/controller"
    "cert-manager/cert-manager"
    "cert-manager/cert-manager-webhook"
    "cert-manager/cert-manager-cainjector"
    "ingress-nginx/ingress-nginx-controller"
    "homelab-portal/enhanced-portal"
)

for deployment in "${deployments[@]}"; do
    namespace=$(echo "$deployment" | cut -d'/' -f1)
    name=$(echo "$deployment" | cut -d'/' -f2)
    log_info "Waiting for $deployment to be ready..."
    kubectl rollout status deployment/"$name" -n "$namespace" --timeout=120s || log_warn "$deployment not ready"
done

# Check the status of all pods
log_section "Pod Status Check"
kubectl get pods --all-namespaces | grep -E "(metallb|cert-manager|ingress-nginx|homelab-portal|oauth2-proxy)" | \
    awk '{printf "%-30s %-20s %-10s %s\n", $1, $2, $3, $4}'

# Check services
log_section "Service Status Check"
kubectl get svc -n ingress-nginx
kubectl get svc -n homelab-portal

# Check ingress
log_section "Ingress Status Check"
kubectl get ingress --all-namespaces

# Display access information
log_section "Access Information"
EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "192.168.16.100")

cat <<EOF
${GREEN}Deployment Complete!${NC}

To access the Homelab Portal:

1. Add this line to your /etc/hosts file:
   ${EXTERNAL_IP} homelab.local

2. Access the portal at:
   https://homelab.local

Current Services Status:
EOF

# Show resource usage
log_section "Resource Usage Summary"
kubectl top nodes 2>/dev/null || log_info "Metrics server not available"
echo ""
kubectl top pods --all-namespaces 2>/dev/null | grep -E "(NAME|metallb|cert-manager|ingress|homelab|oauth2)" || log_info "Pod metrics not available"

log_info "Deployment completed successfully!"
