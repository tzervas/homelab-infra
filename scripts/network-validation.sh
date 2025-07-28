#!/bin/bash

# Network and Service Validation Script
# Step 10: Network and Service Validation

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Create results directory
RESULTS_DIR="./network-validation-results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Main validation function
main() {
    log_info "Starting Network and Service Validation - $(date)"

    # Test 1: MetalLB Configuration and IP Allocation
    test_metallb_configuration

    # Test 2: Validate Ingress Controller Routing
    test_ingress_controller_routing

    # Test 3: Check DNS Resolution for Services
    test_dns_resolution

    # Test 4: Test Network Policies Enforcement
    test_network_policies

    # Test 5: Verify Service Mesh Connectivity (if applicable)
    test_service_mesh_connectivity

    # Generate final report
    generate_report

    log_info "Network validation completed - $(date)"
}

# Test 1: MetalLB Configuration and IP Allocation
test_metallb_configuration() {
    log_info "=== Testing MetalLB Configuration and IP Allocation ==="

    local test_file="$RESULTS_DIR/metallb_test_${TIMESTAMP}.log"

    # Check if MetalLB is installed
    if ! kubectl get namespace metallb-system &>/dev/null; then
        log_error "MetalLB namespace not found"
        echo "FAIL: MetalLB namespace not found" >> "$test_file"
        return 1
    fi

    # Check MetalLB pods status
    log_info "Checking MetalLB pods status..."
    kubectl get pods -n metallb-system >> "$test_file" 2>&1

    if kubectl get pods -n metallb-system | grep -q "Running"; then
        log_success "MetalLB pods are running"
        echo "PASS: MetalLB pods are running" >> "$test_file"
    else
        log_error "MetalLB pods are not running properly"
        echo "FAIL: MetalLB pods not running" >> "$test_file"
    fi

    # Check IP Address Pool configuration
    log_info "Checking MetalLB IP Address Pool..."
    if kubectl get ipaddresspool -n metallb-system homelab-pool &>/dev/null; then
        log_success "MetalLB IP Address Pool found"
        kubectl describe ipaddresspool homelab-pool -n metallb-system >> "$test_file" 2>&1
        echo "PASS: IP Address Pool configured" >> "$test_file"
    else
        log_error "MetalLB IP Address Pool not found"
        echo "FAIL: IP Address Pool not configured" >> "$test_file"
    fi

    # Check L2Advertisement
    log_info "Checking MetalLB L2Advertisement..."
    if kubectl get l2advertisement -n metallb-system homelab-l2 &>/dev/null; then
        log_success "MetalLB L2Advertisement found"
        kubectl describe l2advertisement homelab-l2 -n metallb-system >> "$test_file" 2>&1
        echo "PASS: L2Advertisement configured" >> "$test_file"
    else
        log_error "MetalLB L2Advertisement not found"
        echo "FAIL: L2Advertisement not configured" >> "$test_file"
    fi

    # Test actual IP allocation by creating a test LoadBalancer service
    log_info "Testing IP allocation with test service..."
    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: v1
kind: Service
metadata:
  name: metallb-test-service
  namespace: default
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: metallb-test
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metallb-test-deployment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: metallb-test
  template:
    metadata:
      labels:
        app: metallb-test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
EOF

    # Wait for IP allocation
    log_info "Waiting for IP allocation..."
    sleep 30

    EXTERNAL_IP=$(kubectl get service metallb-test-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

    if [[ -n "$EXTERNAL_IP" && "$EXTERNAL_IP" != "null" ]]; then
        log_success "MetalLB successfully allocated IP: $EXTERNAL_IP"
        echo "PASS: IP allocated - $EXTERNAL_IP" >> "$test_file"

        # Test connectivity to allocated IP
        if curl -s --max-time 10 "http://$EXTERNAL_IP" &>/dev/null; then
            log_success "Service accessible via allocated IP"
            echo "PASS: Service accessible via MetalLB IP" >> "$test_file"
        else
            log_warning "Service not accessible via allocated IP (may be expected if not routable)"
            echo "WARN: Service not accessible via allocated IP" >> "$test_file"
        fi
    else
        log_error "MetalLB failed to allocate IP"
        echo "FAIL: No IP allocated by MetalLB" >> "$test_file"
    fi

    # Cleanup test resources
    kubectl delete service metallb-test-service --ignore-not-found=true >> "$test_file" 2>&1
    kubectl delete deployment metallb-test-deployment --ignore-not-found=true >> "$test_file" 2>&1
}

# Test 2: Validate Ingress Controller Routing
test_ingress_controller_routing() {
    log_info "=== Testing Ingress Controller Routing ==="

    local test_file="$RESULTS_DIR/ingress_test_${TIMESTAMP}.log"

    # Check if ingress controller is installed
    log_info "Checking for ingress controller..."
    if kubectl get namespace ingress-nginx &>/dev/null; then
        log_success "ingress-nginx namespace found"
        echo "PASS: ingress-nginx namespace exists" >> "$test_file"
    else
        log_error "ingress-nginx namespace not found"
        echo "FAIL: ingress-nginx namespace not found" >> "$test_file"
        return 1
    fi

    # Check ingress controller pods
    log_info "Checking ingress controller pods..."
    kubectl get pods -n ingress-nginx >> "$test_file" 2>&1

    if kubectl get pods -n ingress-nginx | grep -q "Running"; then
        log_success "Ingress controller pods are running"
        echo "PASS: Ingress controller pods running" >> "$test_file"
    else
        log_error "Ingress controller pods are not running properly"
        echo "FAIL: Ingress controller pods not running" >> "$test_file"
    fi

    # Check ingress controller service
    log_info "Checking ingress controller service..."
    kubectl get service -n ingress-nginx >> "$test_file" 2>&1

    # Create test ingress and service
    log_info "Creating test ingress configuration..."
    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: v1
kind: Service
metadata:
  name: ingress-test-service
  namespace: default
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: ingress-test
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingress-test-deployment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ingress-test
  template:
    metadata:
      labels:
        app: ingress-test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-test
  namespace: default
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: test.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ingress-test-service
            port:
              number: 80
EOF

    # Wait for resources to be ready
    sleep 30

    # Check if ingress was created
    if kubectl get ingress ingress-test &>/dev/null; then
        log_success "Test ingress created successfully"
        kubectl describe ingress ingress-test >> "$test_file" 2>&1
        echo "PASS: Test ingress created" >> "$test_file"

        # Get ingress IP
        INGRESS_IP=$(kubectl get ingress ingress-test -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        if [[ -n "$INGRESS_IP" && "$INGRESS_IP" != "null" ]]; then
            log_success "Ingress has IP address: $INGRESS_IP"
            echo "PASS: Ingress has IP - $INGRESS_IP" >> "$test_file"
        else
            log_warning "Ingress IP not yet assigned"
            echo "WARN: Ingress IP not assigned" >> "$test_file"
        fi
    else
        log_error "Failed to create test ingress"
        echo "FAIL: Test ingress creation failed" >> "$test_file"
    fi

    # Cleanup test resources
    kubectl delete ingress ingress-test --ignore-not-found=true >> "$test_file" 2>&1
    kubectl delete service ingress-test-service --ignore-not-found=true >> "$test_file" 2>&1
    kubectl delete deployment ingress-test-deployment --ignore-not-found=true >> "$test_file" 2>&1
}

# Test 3: Check DNS Resolution for Services
test_dns_resolution() {
    log_info "=== Testing DNS Resolution for Services ==="

    local test_file="$RESULTS_DIR/dns_test_${TIMESTAMP}.log"

    # Check CoreDNS status
    log_info "Checking CoreDNS status..."
    kubectl get pods -n kube-system -l k8s-app=kube-dns >> "$test_file" 2>&1

    if kubectl get pods -n kube-system -l k8s-app=kube-dns | grep -q "Running"; then
        log_success "CoreDNS pods are running"
        echo "PASS: CoreDNS pods running" >> "$test_file"
    else
        log_error "CoreDNS pods are not running properly"
        echo "FAIL: CoreDNS pods not running" >> "$test_file"
    fi

    # Test DNS resolution from within cluster
    log_info "Testing DNS resolution from within cluster..."

    # Create test pod for DNS testing
    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: dns-test-pod
  namespace: default
spec:
  containers:
  - name: dns-test
    image: busybox:1.35
    command: ['sleep', '300']
  restartPolicy: Never
EOF

    # Wait for pod to be ready
    kubectl wait --for=condition=Ready pod/dns-test-pod --timeout=60s >> "$test_file" 2>&1

    # Test various DNS resolutions
    log_info "Testing service DNS resolution..."

    # Test kubernetes service resolution
    if kubectl exec dns-test-pod -- nslookup kubernetes.default.svc.cluster.local >> "$test_file" 2>&1; then
        log_success "Kubernetes service DNS resolution works"
        echo "PASS: kubernetes.default.svc.cluster.local resolves" >> "$test_file"
    else
        log_error "Kubernetes service DNS resolution failed"
        echo "FAIL: kubernetes.default.svc.cluster.local resolution failed" >> "$test_file"
    fi

    # Test external DNS resolution
    if kubectl exec dns-test-pod -- nslookup google.com >> "$test_file" 2>&1; then
        log_success "External DNS resolution works"
        echo "PASS: External DNS resolution works" >> "$test_file"
    else
        log_error "External DNS resolution failed"
        echo "FAIL: External DNS resolution failed" >> "$test_file"
    fi

    # Test CoreDNS service resolution
    if kubectl exec dns-test-pod -- nslookup kube-dns.kube-system.svc.cluster.local >> "$test_file" 2>&1; then
        log_success "CoreDNS service resolution works"
        echo "PASS: CoreDNS service resolution works" >> "$test_file"
    else
        log_error "CoreDNS service resolution failed"
        echo "FAIL: CoreDNS service resolution failed" >> "$test_file"
    fi

    # Check DNS configuration
    log_info "Checking DNS configuration in test pod..."
    kubectl exec dns-test-pod -- cat /etc/resolv.conf >> "$test_file" 2>&1

    # Cleanup
    kubectl delete pod dns-test-pod --ignore-not-found=true >> "$test_file" 2>&1
}

# Test 4: Test Network Policies Enforcement
test_network_policies() {
    log_info "=== Testing Network Policies Enforcement ==="

    local test_file="$RESULTS_DIR/network_policies_test_${TIMESTAMP}.log"

    # Check if network policies are present
    log_info "Checking existing network policies..."
    kubectl get networkpolicy --all-namespaces >> "$test_file" 2>&1

    # Create test namespace and pods for network policy testing
    log_info "Creating test environment for network policy validation..."

    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: v1
kind: Namespace
metadata:
  name: netpol-test-source
---
apiVersion: v1
kind: Namespace
metadata:
  name: netpol-test-target
---
apiVersion: v1
kind: Pod
metadata:
  name: source-pod
  namespace: netpol-test-source
  labels:
    app: source
spec:
  containers:
  - name: netshoot
    image: nicolaka/netshoot:latest
    command: ['sleep', '300']
---
apiVersion: v1
kind: Pod
metadata:
  name: target-pod
  namespace: netpol-test-target
  labels:
    app: target
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    ports:
    - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: target-service
  namespace: netpol-test-target
spec:
  selector:
    app: target
  ports:
  - port: 80
    targetPort: 80
EOF

    # Wait for pods to be ready
    kubectl wait --for=condition=Ready pod/source-pod -n netpol-test-source --timeout=60s >> "$test_file" 2>&1
    kubectl wait --for=condition=Ready pod/target-pod -n netpol-test-target --timeout=60s >> "$test_file" 2>&1

    # Test connectivity before applying restrictive policy
    log_info "Testing connectivity before network policy..."
    TARGET_IP=$(kubectl get pod target-pod -n netpol-test-target -o jsonpath='{.status.podIP}')

    if kubectl exec source-pod -n netpol-test-source -- curl -s --max-time 5 "http://$TARGET_IP" &>/dev/null; then
        log_success "Connectivity works before network policy"
        echo "PASS: Pre-policy connectivity works" >> "$test_file"
    else
        log_warning "No connectivity before network policy (unexpected)"
        echo "WARN: No pre-policy connectivity" >> "$test_file"
    fi

    # Apply restrictive network policy
    log_info "Applying restrictive network policy..."
    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: netpol-test-target
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF

    # Wait for policy to take effect
    sleep 10

    # Test connectivity after applying restrictive policy
    log_info "Testing connectivity after restrictive network policy..."
    if ! kubectl exec source-pod -n netpol-test-source -- curl -s --max-time 5 "http://$TARGET_IP" &>/dev/null; then
        log_success "Network policy successfully blocks traffic"
        echo "PASS: Network policy blocks traffic" >> "$test_file"
    else
        log_error "Network policy failed to block traffic"
        echo "FAIL: Network policy not enforcing" >> "$test_file"
    fi

    # Apply permissive policy
    log_info "Applying permissive network policy..."
    cat <<EOF | kubectl apply -f - >> "$test_file" 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-source
  namespace: netpol-test-target
spec:
  podSelector:
    matchLabels:
      app: target
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: netpol-test-source
    ports:
    - protocol: TCP
      port: 80
EOF

    # Wait for policy to take effect
    sleep 10

    # Test connectivity after applying permissive policy
    log_info "Testing connectivity after permissive network policy..."
    if kubectl exec source-pod -n netpol-test-source -- curl -s --max-time 5 "http://$TARGET_IP" &>/dev/null; then
        log_success "Permissive network policy allows traffic"
        echo "PASS: Permissive policy allows traffic" >> "$test_file"
    else
        log_warning "Permissive network policy still blocks traffic"
        echo "WARN: Permissive policy still blocking" >> "$test_file"
    fi

    # Cleanup test resources
    kubectl delete namespace netpol-test-source --ignore-not-found=true >> "$test_file" 2>&1
    kubectl delete namespace netpol-test-target --ignore-not-found=true >> "$test_file" 2>&1
}

# Test 5: Verify Service Mesh Connectivity (if applicable)
test_service_mesh_connectivity() {
    log_info "=== Testing Service Mesh Connectivity ==="

    local test_file="$RESULTS_DIR/service_mesh_test_${TIMESTAMP}.log"

    # Check for common service mesh installations
    log_info "Checking for service mesh installations..."

    # Check for Istio
    if kubectl get namespace istio-system &>/dev/null; then
        log_info "Istio found, testing Istio connectivity..."
        echo "INFO: Istio service mesh detected" >> "$test_file"

        # Check Istio components
        kubectl get pods -n istio-system >> "$test_file" 2>&1

        # Check if all Istio pods are running
        if kubectl get pods -n istio-system | grep -v Running | grep -v Completed | grep -v "NAME" | wc -l | grep -q "0"; then
            log_success "All Istio components are running"
            echo "PASS: Istio components running" >> "$test_file"
        else
            log_error "Some Istio components are not running"
            echo "FAIL: Istio components not all running" >> "$test_file"
        fi

    # Check for Linkerd
    elif kubectl get namespace linkerd &>/dev/null; then
        log_info "Linkerd found, testing Linkerd connectivity..."
        echo "INFO: Linkerd service mesh detected" >> "$test_file"

        # Check Linkerd components
        kubectl get pods -n linkerd >> "$test_file" 2>&1

        if kubectl get pods -n linkerd | grep -v Running | grep -v Completed | grep -v "NAME" | wc -l | grep -q "0"; then
            log_success "All Linkerd components are running"
            echo "PASS: Linkerd components running" >> "$test_file"
        else
            log_error "Some Linkerd components are not running"
            echo "FAIL: Linkerd components not all running" >> "$test_file"
        fi

    # Check for Consul Connect
    elif kubectl get namespace consul &>/dev/null; then
        log_info "Consul found, testing Consul Connect..."
        echo "INFO: Consul service mesh detected" >> "$test_file"

        kubectl get pods -n consul >> "$test_file" 2>&1

        if kubectl get pods -n consul | grep -v Running | grep -v Completed | grep -v "NAME" | wc -l | grep -q "0"; then
            log_success "All Consul components are running"
            echo "PASS: Consul components running" >> "$test_file"
        else
            log_error "Some Consul components are not running"
            echo "FAIL: Consul components not all running" >> "$test_file"
        fi

    else
        log_info "No service mesh detected"
        echo "INFO: No service mesh installation found" >> "$test_file"
        return 0
    fi
}

# Generate comprehensive report
generate_report() {
    log_info "=== Generating Network Validation Report ==="

    local report_file="$RESULTS_DIR/network_validation_report_${TIMESTAMP}.md"

    cat > "$report_file" <<EOF
# Network and Service Validation Report

**Generated:** $(date)
**Cluster:** $(kubectl config current-context)

## Summary

This report contains the results of comprehensive network and service validation tests.

## Test Results

### 1. MetalLB Configuration and IP Allocation
EOF

    if [[ -f "$RESULTS_DIR/metallb_test_${TIMESTAMP}.log" ]]; then
        echo "#### Results:" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(PASS|FAIL|WARN):" "$RESULTS_DIR/metallb_test_${TIMESTAMP}.log" >> "$report_file" 2>/dev/null || echo "No results found" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

### 2. Ingress Controller Routing
EOF

    if [[ -f "$RESULTS_DIR/ingress_test_${TIMESTAMP}.log" ]]; then
        echo "#### Results:" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(PASS|FAIL|WARN):" "$RESULTS_DIR/ingress_test_${TIMESTAMP}.log" >> "$report_file" 2>/dev/null || echo "No results found" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

### 3. DNS Resolution for Services
EOF

    if [[ -f "$RESULTS_DIR/dns_test_${TIMESTAMP}.log" ]]; then
        echo "#### Results:" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(PASS|FAIL|WARN):" "$RESULTS_DIR/dns_test_${TIMESTAMP}.log" >> "$report_file" 2>/dev/null || echo "No results found" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

### 4. Network Policies Enforcement
EOF

    if [[ -f "$RESULTS_DIR/network_policies_test_${TIMESTAMP}.log" ]]; then
        echo "#### Results:" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(PASS|FAIL|WARN):" "$RESULTS_DIR/network_policies_test_${TIMESTAMP}.log" >> "$report_file" 2>/dev/null || echo "No results found" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

### 5. Service Mesh Connectivity
EOF

    if [[ -f "$RESULTS_DIR/service_mesh_test_${TIMESTAMP}.log" ]]; then
        echo "#### Results:" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(PASS|FAIL|WARN|INFO):" "$RESULTS_DIR/service_mesh_test_${TIMESTAMP}.log" >> "$report_file" 2>/dev/null || echo "No results found" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

## Detailed Logs

Detailed logs for each test can be found in the following files:
- MetalLB: \`metallb_test_${TIMESTAMP}.log\`
- Ingress: \`ingress_test_${TIMESTAMP}.log\`
- DNS: \`dns_test_${TIMESTAMP}.log\`
- Network Policies: \`network_policies_test_${TIMESTAMP}.log\`
- Service Mesh: \`service_mesh_test_${TIMESTAMP}.log\`

## Recommendations

### Connectivity Issues Found:
EOF

    # Add any specific recommendations based on test results
    local has_issues=false

    for log_file in "$RESULTS_DIR"/*_test_${TIMESTAMP}.log; do
        if [[ -f "$log_file" ]] && grep -q "FAIL:" "$log_file"; then
            has_issues=true
            echo "- Issues found in $(basename "$log_file" | sed 's/_test_.*\.log//')" >> "$report_file"
        fi
    done

    if [[ "$has_issues" == "false" ]]; then
        echo "- No critical connectivity issues detected" >> "$report_file"
    fi

    cat >> "$report_file" <<EOF

### Next Steps:
1. Review detailed logs for any failed tests
2. Address any network policy misconfigurations
3. Verify MetalLB IP pool ranges are appropriate for your network
4. Ensure DNS resolution is working for all critical services
5. Validate ingress controller is properly configured with TLS

---
*Report generated by network-validation.sh*
EOF

    log_success "Report generated: $report_file"

    # Display summary
    log_info "=== VALIDATION SUMMARY ==="
    for log_file in "$RESULTS_DIR"/*_test_${TIMESTAMP}.log; do
        if [[ -f "$log_file" ]]; then
            local test_name=$(basename "$log_file" | sed 's/_test_.*\.log//')
            local passes=$(grep -c "PASS:" "$log_file" 2>/dev/null || echo "0")
            local failures=$(grep -c "FAIL:" "$log_file" 2>/dev/null || echo "0")
            local warnings=$(grep -c "WARN:" "$log_file" 2>/dev/null || echo "0")

            echo "  $test_name: $passes passes, $failures failures, $warnings warnings"
        fi
    done
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
