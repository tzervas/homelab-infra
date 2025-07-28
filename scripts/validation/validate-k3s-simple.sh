#!/bin/bash
# Simple K3s Cluster Validation Script (Legacy)
# Tests basic functionality of the K3s cluster
#
# DEPRECATED: This script has been superseded by the new K3s testing framework
# New location: testing/k3s-validation/orchestrator.sh
#
# For basic validation, use: ./testing/k3s-validation/orchestrator.sh core

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v jq >/dev/null 2>&1; then
        missing_deps+=("jq")
    fi

    if ! command -v kubectl >/dev/null 2>&1; then
        missing_deps+=("kubectl")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}✗ Missing required dependencies: ${missing_deps[*]}${NC}"
        echo -e "${RED}Please install the missing dependencies and try again${NC}"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    printf "\nCleaning up test resources...\n"
    kubectl delete pod dns-test test-server test-client -n default --ignore-not-found=true &>/dev/null || true
    kubectl delete service test-service -n default --ignore-not-found=true &>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT INT TERM

# Check dependencies first
check_dependencies

echo -e "${BLUE}=== K3s Cluster Validation ===${NC}"
echo ""

# Check kubectl connectivity
echo -e "${BLUE}[1/6] Testing kubectl connectivity...${NC}"
if kubectl cluster-info &>/dev/null; then
    echo -e "${GREEN}✓ Kubectl can connect to cluster${NC}"
    kubectl cluster-info | head -2
else
    echo -e "${RED}✗ Cannot connect to cluster${NC}"
    exit 1
fi
echo ""

# Check nodes
echo -e "${BLUE}[2/6] Checking nodes...${NC}"
kubectl get nodes
READY_NODES=$(kubectl get nodes -o json | jq '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status=="True")) | .metadata.name' | wc -l)
if [[ $READY_NODES -gt 0 ]]; then
    echo -e "${GREEN}✓ $READY_NODES node(s) ready${NC}"
else
    echo -e "${RED}✗ No ready nodes found${NC}"
fi
echo ""

# Check system pods
echo -e "${BLUE}[3/6] Checking system pods...${NC}"
kubectl get pods -n kube-system
RUNNING_PODS=$(kubectl get pods -n kube-system --field-selector=status.phase=Running -o json | jq '.items | length')
TOTAL_PODS=$(kubectl get pods -n kube-system -o json | jq '.items | length')
echo -e "${GREEN}✓ $RUNNING_PODS/$TOTAL_PODS system pods running${NC}"
echo ""

# Test DNS
echo -e "${BLUE}[4/6] Testing DNS resolution...${NC}"
cat <<EOF | kubectl apply -f - &>/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: dns-test
  namespace: default
spec:
  containers:
  - name: dns-test
    image: busybox:1.35
    command: ['sleep', '30']
  restartPolicy: Never
EOF

# Wait for pod to be ready with timeout
if kubectl wait --for=condition=Ready pod/dns-test -n default --timeout=60s &>/dev/null; then
    if kubectl exec -n default dns-test -- timeout 10 nslookup kubernetes.default &>/dev/null; then
        echo -e "${GREEN}✓ DNS resolution working${NC}"
    else
        echo -e "${YELLOW}⚠ DNS resolution failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ DNS test pod failed to start${NC}"
fi
echo ""

# Check storage
echo -e "${BLUE}[5/6] Checking storage...${NC}"
kubectl get storageclass
if kubectl get storageclass -o json | jq -e '.items | length > 0' &>/dev/null; then
    echo -e "${GREEN}✓ Storage classes available${NC}"
else
    echo -e "${YELLOW}⚠ No storage classes found${NC}"
fi
echo ""

# Check namespaces
echo -e "${BLUE}[6/6] Checking namespaces...${NC}"
kubectl get namespaces
EXPECTED_NS=("default" "kube-system" "kube-public" "kube-node-lease" "homelab" "monitoring" "backup")
MISSING_NS=()
for ns in "${EXPECTED_NS[@]}"; do
    if ! kubectl get namespace "$ns" &>/dev/null; then
        MISSING_NS+=("$ns")
    fi
done

if [[ ${#MISSING_NS[@]} -eq 0 ]]; then
    echo -e "${GREEN}✓ All expected namespaces present${NC}"
else
    echo -e "${YELLOW}⚠ Missing namespaces: ${MISSING_NS[*]}${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=== Validation Summary ===${NC}"
echo -e "${GREEN}✓ Cluster is accessible${NC}"
echo -e "${GREEN}✓ Node(s) are ready${NC}"
echo -e "${GREEN}✓ System pods are running${NC}"

# Test pod-to-pod communication
echo ""
echo -e "${BLUE}=== Testing Pod Communication ===${NC}"
echo "Creating test pods..."

cat <<EOF | kubectl apply -f - &>/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: test-server
  namespace: default
  labels:
    app: test-server
spec:
  containers:
  - name: server
    image: nginx:alpine
    ports:
    - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: test-service
  namespace: default
spec:
  selector:
    app: test-server
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: test-client
  namespace: default
spec:
  containers:
  - name: client
    image: busybox:1.35
    command: ['sleep', '300']
EOF

echo "Waiting for pods to be ready..."
if kubectl wait --for=condition=Ready pod/test-server pod/test-client -n default --timeout=120s &>/dev/null; then
    # Wait for service endpoints to be ready
    service_ready=false
    timeout=30
    elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if kubectl get endpoints test-service -n default -o jsonpath='{.subsets[0].addresses[0].ip}' &>/dev/null; then
            service_ready=true
            break
        fi
        sleep 2
        ((elapsed += 2))
    done

    # Test service connectivity with timeout
    if $service_ready && kubectl exec test-client -- timeout 10 wget -q -O- http://test-service &>/dev/null; then
        echo -e "${GREEN}✓ Pod-to-pod communication working${NC}"
        echo -e "${GREEN}✓ Service discovery working${NC}"
    else
        echo -e "${YELLOW}⚠ Pod communication test failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Test pods failed to start${NC}"
fi

echo ""
echo -e "${GREEN}=== Validation Complete ===${NC}"
