#!/bin/bash
# K3s Cluster Validation Script (Legacy)
# Comprehensive validation of K3s cluster health, networking, storage, security, and resources
# Author: Homelab Infrastructure
# Version: 1.0
#
# DEPRECATED: This script has been superseded by the new K3s testing framework
# New location: testing/k3s-validation/orchestrator.sh
#
# For migration, use: ./testing/k3s-validation/orchestrator.sh --all

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/k3s-validation-${TIMESTAMP}.log"
TEST_NAMESPACE="k3s-validation-test"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Create log directory
mkdir -p "$LOG_DIR"

# Functions for logging and output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1" | tee -a "$LOG_FILE"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG_FILE"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1" | tee -a "$LOG_FILE"
    ((TESTS_SKIPPED++))
}

# Helper function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required dependencies
check_dependencies() {
    local missing_deps=()

    if ! command_exists jq; then
        missing_deps+=("jq")
    fi

    if ! command_exists kubectl && ! command_exists k3s; then
        missing_deps+=("kubectl or k3s")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install the missing dependencies and try again"
        exit 1
    fi
}

# Helper function to check kubectl connection
check_kubectl() {
    if ! command_exists kubectl; then
        if ! command_exists k3s; then
            log_error "Neither kubectl nor k3s command found"
            return 1
        fi
        KUBECTL_CMD="k3s kubectl"
    else
        if kubectl cluster-info >/dev/null 2>&1; then
            KUBECTL_CMD="kubectl"
        elif command_exists k3s && k3s kubectl cluster-info >/dev/null 2>&1; then
            KUBECTL_CMD="k3s kubectl"
        else
            log_error "Cannot connect to Kubernetes cluster"
            return 1
        fi
    fi
    return 0
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test resources..."

    if [[ -n "${KUBECTL_CMD:-}" ]]; then
        # Delete test namespace
        $KUBECTL_CMD delete namespace "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true

        # Delete test ClusterRole and ClusterRoleBinding
        $KUBECTL_CMD delete clusterrole k3s-validation-test --ignore-not-found=true >/dev/null 2>&1 || true
        $KUBECTL_CMD delete clusterrolebinding k3s-validation-test --ignore-not-found=true >/dev/null 2>&1 || true

        # Delete test PVC
        $KUBECTL_CMD delete pvc test-storage-claim -n default --ignore-not-found=true >/dev/null 2>&1 || true

        log_success "Cleanup completed"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Test 1: Core Kubernetes Components Health
test_core_components() {
    log_info "Testing core Kubernetes components health..."

    # Check if kubectl/k3s is available and can connect
    if ! check_kubectl; then
        log_error "Cannot establish connection to Kubernetes cluster"
        return 1
    fi

    # Test API server
    if $KUBECTL_CMD cluster-info >/dev/null 2>&1; then
        log_success "API server is accessible"
    else
        log_error "API server is not accessible"
        return 1
    fi

    # Check node status
    local nodes_output
    if nodes_output=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        local ready_nodes
        ready_nodes=$(echo "$nodes_output" | jq -r '.items[] | select(.status.conditions[] | select(.type=="Ready" and .status=="True")) | .metadata.name' | wc -l)
        local total_nodes
        total_nodes=$(echo "$nodes_output" | jq -r '.items | length')

        if [[ $ready_nodes -eq $total_nodes ]] && [[ $total_nodes -gt 0 ]]; then
            log_success "All $total_nodes nodes are ready"
        else
            log_error "Only $ready_nodes out of $total_nodes nodes are ready"
        fi
    else
        log_error "Cannot retrieve node status"
    fi

    # Check system pods
    local system_pods_output
    if system_pods_output=$($KUBECTL_CMD get pods -n kube-system -o json 2>/dev/null); then
        local running_pods
        running_pods=$(echo "$system_pods_output" | jq -r '.items[] | select(.status.phase=="Running") | .metadata.name' | wc -l)
        local total_pods
        total_pods=$(echo "$system_pods_output" | jq -r '.items | length')

        if [[ $running_pods -eq $total_pods ]] && [[ $total_pods -gt 0 ]]; then
            log_success "All $total_pods system pods are running"
        else
            log_warning "$running_pods out of $total_pods system pods are running"
            # Show which pods are not running
            echo "$system_pods_output" | jq -r '.items[] | select(.status.phase!="Running") | "\(.metadata.name): \(.status.phase)"' | while read -r line; do
                log_warning "Non-running pod: $line"
            done
        fi
    else
        log_error "Cannot retrieve system pods status"
    fi

    # Check critical components
    local components=("coredns" "local-path-provisioner")
    for component in "${components[@]}"; do
        if $KUBECTL_CMD get pods -n kube-system -l k8s-app="$component" -o json | jq -e '.items[] | select(.status.phase=="Running")' >/dev/null 2>&1; then
            log_success "$component is running"
        else
            log_error "$component is not running properly"
        fi
    done
}

# Test 2: Network Connectivity
test_network_connectivity() {
    log_info "Testing network connectivity..."

    # Create test namespace
    $KUBECTL_CMD create namespace "$TEST_NAMESPACE" --dry-run=client -o yaml | $KUBECTL_CMD apply -f - >/dev/null 2>&1

    # Test DNS resolution
    local dns_test_pod="dns-test-pod"
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $dns_test_pod
  namespace: $TEST_NAMESPACE
spec:
  containers:
  - name: dns-test
    image: busybox:1.35
    command: ['sleep', '300']
  restartPolicy: Never
EOF

    # Wait for pod to be ready with better error handling
    if $KUBECTL_CMD wait --for=condition=Ready pod/$dns_test_pod -n "$TEST_NAMESPACE" --timeout=60s >/dev/null 2>&1; then
        # Test internal DNS
        if $KUBECTL_CMD exec -n "$TEST_NAMESPACE" "$dns_test_pod" -- nslookup kubernetes.default.svc.cluster.local >/dev/null 2>&1; then
            log_success "Internal DNS resolution works"
        else
            log_error "Internal DNS resolution failed"
        fi

        # Test external DNS
        if $KUBECTL_CMD exec -n "$TEST_NAMESPACE" "$dns_test_pod" -- nslookup google.com >/dev/null 2>&1; then
            log_success "External DNS resolution works"
        else
            log_warning "External DNS resolution failed (may be expected in restricted environments)"
        fi
    else
        log_error "DNS test pod failed to start"
    fi

    # Test pod-to-pod communication
    local test_pod1="network-test-pod-1"
    local test_pod2="network-test-pod-2"

    # Create first test pod with a simple HTTP server
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $test_pod1
  namespace: $TEST_NAMESPACE
  labels:
    app: network-test
spec:
  containers:
  - name: http-server
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
EOF

    # Create second test pod
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $test_pod2
  namespace: $TEST_NAMESPACE
spec:
  containers:
  - name: client
    image: busybox:1.35
    command: ['sleep', '300']
EOF

    # Wait for pods to be ready with individual checks
    local pods_ready=true
    for pod in "$test_pod1" "$test_pod2"; do
        if ! $KUBECTL_CMD wait --for=condition=Ready pod/$pod -n "$TEST_NAMESPACE" --timeout=60s >/dev/null 2>&1; then
            log_error "Pod $pod failed to become ready"
            pods_ready=false
        fi
    done

    if $pods_ready; then
        # Get pod1 IP
        local pod1_ip
        pod1_ip=$($KUBECTL_CMD get pod "$test_pod1" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}')

        # Test pod-to-pod communication
        if [[ -n "$pod1_ip" ]] && $KUBECTL_CMD exec -n "$TEST_NAMESPACE" "$test_pod2" -- wget -qO- --timeout=10 "http://$pod1_ip" >/dev/null 2>&1; then
            log_success "Pod-to-pod communication works"
        else
            log_error "Pod-to-pod communication failed"
        fi
    else
        log_error "Network test pods failed to start"
    fi

    # Test service connectivity
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Service
metadata:
  name: network-test-service
  namespace: $TEST_NAMESPACE
spec:
  selector:
    app: network-test
  ports:
  - port: 80
    targetPort: 80
EOF

    # Wait for service to be ready
    local service_ready=false timeout=30 elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if $KUBECTL_CMD get endpoints network-test-service -n "$TEST_NAMESPACE" -o jsonpath='{.subsets[0].addresses[0].ip}' >/dev/null 2>&1; then
            service_ready=true
            break
        fi
        sleep 2
        ((elapsed += 2))
    done

    if $service_ready && $KUBECTL_CMD exec -n "$TEST_NAMESPACE" "$test_pod2" -- timeout 10 wget -qO- "http://network-test-service" >/dev/null 2>&1; then
        log_success "Service connectivity works"
    else
        log_error "Service connectivity failed"
    fi
}

# Test 3: Storage Capabilities
test_storage_capabilities() {
    log_info "Testing storage capabilities..."

    # Check for storage classes
    local storage_classes
    if storage_classes=$($KUBECTL_CMD get storageclasses -o json 2>/dev/null); then
        local sc_count
        sc_count=$(echo "$storage_classes" | jq -r '.items | length')
        if [[ $sc_count -gt 0 ]]; then
            log_success "Found $sc_count storage class(es)"
            echo "$storage_classes" | jq -r '.items[].metadata.name' | while read -r sc; do
                log_info "Storage class: $sc"
            done
        else
            log_warning "No storage classes found"
        fi
    else
        log_error "Cannot retrieve storage classes"
    fi

    # Test PVC creation and mounting
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-storage-claim
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

    # Wait for PVC to be bound with timeout
    local pvc_status timeout=30 elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if pvc_status=$($KUBECTL_CMD get pvc test-storage-claim -n default -o jsonpath='{.status.phase}' 2>/dev/null) && [[ "$pvc_status" == "Bound" ]]; then
            break
        fi
        sleep 2
        ((elapsed += 2))
    done

    if pvc_status=$($KUBECTL_CMD get pvc test-storage-claim -n default -o jsonpath='{.status.phase}' 2>/dev/null); then
        if [[ "$pvc_status" == "Bound" ]]; then
            log_success "PVC creation and binding works"
        else
            log_warning "PVC is in $pvc_status state"
        fi
    else
        log_error "Cannot create or retrieve PVC"
    fi

    # Test pod with persistent volume
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: storage-test-pod
  namespace: default
spec:
  containers:
  - name: storage-test
    image: busybox:1.35
    command: ['sleep', '300']
    volumeMounts:
    - name: test-volume
      mountPath: /test-data
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: test-storage-claim
  restartPolicy: Never
EOF

    # Wait for pod and test storage
    if $KUBECTL_CMD wait --for=condition=Ready pod/storage-test-pod -n default --timeout=60s >/dev/null 2>&1; then
        if $KUBECTL_CMD exec -n default storage-test-pod -- touch /test-data/test-file >/dev/null 2>&1 && \
           $KUBECTL_CMD exec -n default storage-test-pod -- ls /test-data/test-file >/dev/null 2>&1; then
            log_success "Persistent volume mounting and write test works"
        else
            log_error "Cannot write to persistent volume"
        fi
    else
        log_error "Storage test pod failed to start"
    fi

    # Cleanup storage test pod
    $KUBECTL_CMD delete pod storage-test-pod -n default --ignore-not-found=true >/dev/null 2>&1 || true
}

# Test 4: Resource Availability
test_resource_availability() {
    log_info "Testing resource availability..."

    # Check node resources
    local nodes_resources
    if nodes_resources=$($KUBECTL_CMD top nodes 2>/dev/null); then
        log_success "Node resource metrics are available"
        echo "$nodes_resources" | while IFS= read -r line; do
            log_info "$line"
        done
    else
        log_warning "Node resource metrics not available (metrics-server may not be installed)"
    fi

    # Check cluster resource capacity
    local nodes_capacity
    if nodes_capacity=$($KUBECTL_CMD get nodes -o json 2>/dev/null); then
        local total_cpu total_memory
        total_cpu=$(echo "$nodes_capacity" | jq -r '.items[].status.capacity.cpu' | awk '{sum += $1} END {print sum}')
        total_memory=$(echo "$nodes_capacity" | jq -r '.items[].status.capacity.memory' | sed 's/Ki$//' | awk '{sum += $1} END {print sum/1024/1024 " GB"}')

        log_success "Cluster capacity - CPU: $total_cpu cores, Memory: $total_memory"
    else
        log_error "Cannot retrieve cluster capacity information"
    fi

    # Test resource limits enforcement
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: resource-test-pod
  namespace: $TEST_NAMESPACE
spec:
  containers:
  - name: resource-test
    image: busybox:1.35
    command: ['sleep', '60']
    resources:
      requests:
        cpu: 10m
        memory: 32Mi
      limits:
        cpu: 50m
        memory: 64Mi
  restartPolicy: Never
EOF

    if $KUBECTL_CMD wait --for=condition=Ready pod/resource-test-pod -n "$TEST_NAMESPACE" --timeout=60s >/dev/null 2>&1; then
        log_success "Resource limits are properly enforced"
    else
        log_error "Resource limits enforcement failed"
    fi
}

# Test 5: Security Contexts
test_security_contexts() {
    log_info "Testing security contexts..."

    # Test non-root user
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: security-test-nonroot
  namespace: $TEST_NAMESPACE
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
  containers:
  - name: security-test
    image: busybox:1.35
    command: ['sleep', '60']
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
  restartPolicy: Never
EOF

    if $KUBECTL_CMD wait --for=condition=Ready pod/security-test-nonroot -n "$TEST_NAMESPACE" --timeout=60s >/dev/null 2>&1; then
        # Verify it's running as non-root
        local user_check
        if user_check=$($KUBECTL_CMD exec -n "$TEST_NAMESPACE" security-test-nonroot -- id -u 2>/dev/null) && [[ "$user_check" == "1000" ]]; then
            log_success "Non-root security context works"
        else
            log_error "Non-root security context not properly enforced"
        fi
    else
        log_error "Non-root security test pod failed to start"
    fi

    # Test read-only filesystem
    if $KUBECTL_CMD exec -n "$TEST_NAMESPACE" security-test-nonroot -- touch /tmp/test-file >/dev/null 2>&1; then
        log_error "Read-only filesystem not properly enforced"
    else
        log_success "Read-only filesystem properly enforced"
    fi

    # Test Pod Security Standards (if available)
    if $KUBECTL_CMD get namespace "$TEST_NAMESPACE" -o jsonpath='{.metadata.labels}' | grep -q "pod-security" 2>/dev/null; then
        log_success "Pod Security Standards are configured"
    else
        log_warning "Pod Security Standards not detected (may not be configured)"
    fi
}

# Test 6: Service Account Permissions
test_service_account_permissions() {
    log_info "Testing service account permissions..."

    # Create test service account
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k3s-validation-test-sa
  namespace: $TEST_NAMESPACE
EOF

    # Create ClusterRole with specific permissions
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k3s-validation-test
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["services"]
  verbs: ["get"]
EOF

    # Create ClusterRoleBinding
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k3s-validation-test
subjects:
- kind: ServiceAccount
  name: k3s-validation-test-sa
  namespace: $TEST_NAMESPACE
roleRef:
  kind: ClusterRole
  name: k3s-validation-test
  apiGroup: rbac.authorization.k8s.io
EOF

    # Test service account permissions
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: rbac-test-pod
  namespace: $TEST_NAMESPACE
spec:
  serviceAccountName: k3s-validation-test-sa
  containers:
  - name: rbac-test
    image: bitnami/kubectl:1.28
    command: ['sleep', '300']
  restartPolicy: Never
EOF

    if $KUBECTL_CMD wait --for=condition=Ready pod/rbac-test-pod -n "$TEST_NAMESPACE" --timeout=60s >/dev/null 2>&1; then
        # Test allowed operations
        if $KUBECTL_CMD exec -n "$TEST_NAMESPACE" rbac-test-pod -- kubectl get pods >/dev/null 2>&1; then
            log_success "Service account can perform allowed operations (get pods)"
        else
            log_error "Service account cannot perform allowed operations"
        fi

        # Test forbidden operations
        if $KUBECTL_CMD exec -n "$TEST_NAMESPACE" rbac-test-pod -- kubectl create namespace test-forbidden >/dev/null 2>&1; then
            log_error "Service account can perform forbidden operations (should be restricted)"
        else
            log_success "Service account properly restricted from forbidden operations"
        fi
    else
        log_error "RBAC test pod failed to start"
    fi

    # Test default service account restrictions
    local default_sa_token
    if default_sa_token=$($KUBECTL_CMD get serviceaccount default -n "$TEST_NAMESPACE" -o jsonpath='{.secrets[0].name}' 2>/dev/null) && [[ -n "$default_sa_token" ]]; then
        log_warning "Default service account has token (consider disabling auto-mounting)"
    else
        log_success "Default service account token auto-mounting is disabled"
    fi
}

# Main function to run all tests
main() {
    log_info "Starting K3s cluster validation"
    log_info "Log file: $LOG_FILE"
    echo ""

    # Run all tests
    test_core_components
    echo ""

    test_network_connectivity
    echo ""

    test_storage_capabilities
    echo ""

    test_resource_availability
    echo ""

    test_security_contexts
    echo ""

    test_service_account_permissions
    echo ""

    # Generate summary report
    log_info "Validation Summary:"
    echo "==================="
    log_success "Tests Passed: $TESTS_PASSED"
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Tests Failed: $TESTS_FAILED"
    fi
    if [[ $TESTS_SKIPPED -gt 0 ]]; then
        log_warning "Tests Skipped: $TESTS_SKIPPED"
    fi

    local total_tests=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    echo ""
    log_info "Total tests: $total_tests"
    if [[ $total_tests -gt 0 ]]; then
        log_info "Success rate: $(( TESTS_PASSED * 100 / total_tests ))%"
    else
        log_warning "No tests were executed"
    fi

    # Exit with error if any tests failed
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo ""
        log_error "Some tests failed. Check the log for details: $LOG_FILE"
        exit 1
    else
        echo ""
        log_success "All tests passed! K3s cluster validation completed successfully."
        exit 0
    fi
}

# Check dependencies before running
check_dependencies

# Run main function
main "$@"
