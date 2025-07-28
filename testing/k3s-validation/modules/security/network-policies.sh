#!/bin/bash
# Network Policy Validation for K3s Clusters
# Tests network policy enforcement and configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../lib/common.sh"
source "$SCRIPT_DIR/../../lib/debug.sh"

run_network_policies() {
    start_test_module "Network Policy Validation"

    # Test 1: Check if network policies are supported
    start_test "Network Policy Support"
    if check_network_policy_support; then
        log_success "Network policies are supported"
    else
        log_error "Network policies are not supported or CNI plugin is misconfigured"
    fi

    # Test 2: Test default deny policy
    start_test "Default Deny Policy Test"
    if test_default_deny_policy; then
        log_success "Default deny network policy works correctly"
    else
        log_error "Default deny network policy is not working"
    fi

    # Test 3: Test pod-to-pod communication with policies
    start_test "Pod-to-Pod Communication with Policies"
    if test_pod_communication_with_policies; then
        log_success "Network policies correctly control pod communication"
    else
        log_error "Network policy enforcement has issues"
    fi

    # Test 4: Namespace isolation test
    start_test "Namespace Isolation"
    if test_namespace_isolation; then
        log_success "Namespace isolation with network policies works"
    else
        log_warning "Namespace isolation may not be properly configured"
    fi
}

check_network_policy_support() {
    debug_enter "Checking network policy support"

    # Create a simple network policy to test support
    local test_policy="test-netpol-${RANDOM}"

    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1 || true
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: $test_policy
spec:
  podSelector:
    matchLabels:
      app: test-netpol
  policyTypes:
  - Ingress
  - Egress
EOF

    # Check if the policy was created successfully
    if $KUBECTL_CMD get networkpolicy "$test_policy" -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        # Cleanup
        $KUBECTL_CMD delete networkpolicy "$test_policy" -n "$TEST_NAMESPACE" >/dev/null 2>&1 || true
        debug_exit 0
        return 0
    fi

    debug_exit 1
    return 1
}

test_default_deny_policy() {
    debug_enter "Testing default deny policy"

    # Create test pods
    local server_pod="netpol-server-${RANDOM}"
    local client_pod="netpol-client-${RANDOM}"

    # Create server pod
    create_test_pod "$server_pod" "nginx:alpine" "$TEST_NAMESPACE"

    # Create client pod
    create_test_pod "$client_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 3600"

    # Wait for pods to be ready
    if ! wait_for_pod_ready "$server_pod" "$TEST_NAMESPACE" 60; then
        log_error "Server pod failed to start"
        debug_exit 1
        return 1
    fi

    if ! wait_for_pod_ready "$client_pod" "$TEST_NAMESPACE" 60; then
        log_error "Client pod failed to start"
        debug_exit 1
        return 1
    fi

    # Get server pod IP
    local server_ip
    server_ip=$($KUBECTL_CMD get pod "$server_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}')

    # Test connectivity before applying policy
    local initial_connection
    initial_connection=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- timeout 5 wget -q -O- "http://$server_ip" 2>/dev/null || echo "failed")

    if [[ "$initial_connection" == "failed" ]]; then
        log_warning "Initial connection failed - network might already be restricted"
    fi

    # Apply default deny policy
    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF

    # Test connectivity after policy
    sleep 5
    local blocked_connection
    blocked_connection=$($KUBECTL_CMD exec "$client_pod" -n "$TEST_NAMESPACE" -- timeout 5 wget -q -O- "http://$server_ip" 2>/dev/null || echo "blocked")

    # Cleanup
    $KUBECTL_CMD delete pod "$server_pod" "$client_pod" -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
    $KUBECTL_CMD delete networkpolicy default-deny-all -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true

    if [[ "$blocked_connection" == "blocked" ]]; then
        debug_exit 0
        return 0
    else
        log_warning "Connection was not blocked by default deny policy"
        debug_exit 1
        return 1
    fi
}

test_pod_communication_with_policies() {
    debug_enter "Testing pod communication with policies"

    # Create labeled pods
    local app1_pod="app1-${RANDOM}"
    local app2_pod="app2-${RANDOM}"

    # Create app1 pod
    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $app1_pod
  labels:
    app: app1
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    ports:
    - containerPort: 80
EOF

    # Create app2 pod
    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $app2_pod
  labels:
    app: app2
spec:
  containers:
  - name: busybox
    image: busybox:1.35
    command: ["sleep", "3600"]
EOF

    # Wait for pods
    wait_for_pod_ready "$app1_pod" "$TEST_NAMESPACE" 60 || true
    wait_for_pod_ready "$app2_pod" "$TEST_NAMESPACE" 60 || true

    # Get app1 IP
    local app1_ip
    app1_ip=$($KUBECTL_CMD get pod "$app1_pod" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}')

    # Apply network policy allowing only app2 to access app1
    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app1-allow-app2
spec:
  podSelector:
    matchLabels:
      app: app1
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: app2
    ports:
    - protocol: TCP
      port: 80
EOF

    # Test if app2 can access app1
    sleep 5
    local allowed_connection
    allowed_connection=$($KUBECTL_CMD exec "$app2_pod" -n "$TEST_NAMESPACE" -- timeout 5 wget -q -O- "http://$app1_ip" 2>/dev/null || echo "failed")

    # Cleanup
    $KUBECTL_CMD delete pod "$app1_pod" "$app2_pod" -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
    $KUBECTL_CMD delete networkpolicy app1-allow-app2 -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true

    if [[ "$allowed_connection" != "failed" ]]; then
        debug_exit 0
        return 0
    else
        debug_exit 1
        return 1
    fi
}

test_namespace_isolation() {
    debug_enter "Testing namespace isolation"

    # Create a second test namespace
    local test_ns2="k3s-netpol-test-${RANDOM}"
    $KUBECTL_CMD create namespace "$test_ns2" >/dev/null 2>&1 || true

    # Create pods in both namespaces
    local pod_ns1="pod-ns1-${RANDOM}"
    local pod_ns2="pod-ns2-${RANDOM}"

    create_test_pod "$pod_ns1" "nginx:alpine" "$TEST_NAMESPACE"
    create_test_pod "$pod_ns2" "busybox:1.35" "$test_ns2" "sleep 3600"

    # Wait for pods
    wait_for_pod_ready "$pod_ns1" "$TEST_NAMESPACE" 60 || true
    wait_for_pod_ready "$pod_ns2" "$test_ns2" 60 || true

    # Apply namespace isolation policy
    cat <<EOF | $KUBECTL_CMD apply -f - -n "$TEST_NAMESPACE" >/dev/null 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-from-other-namespaces
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector: {}
EOF

    # Get pod IP
    local pod_ns1_ip
    pod_ns1_ip=$($KUBECTL_CMD get pod "$pod_ns1" -n "$TEST_NAMESPACE" -o jsonpath='{.status.podIP}')

    # Test cross-namespace connectivity (should be blocked)
    sleep 5
    local cross_ns_connection
    cross_ns_connection=$($KUBECTL_CMD exec "$pod_ns2" -n "$test_ns2" -- timeout 5 wget -q -O- "http://$pod_ns1_ip" 2>/dev/null || echo "blocked")

    # Cleanup
    $KUBECTL_CMD delete pod "$pod_ns1" -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
    $KUBECTL_CMD delete pod "$pod_ns2" -n "$test_ns2" --ignore-not-found=true >/dev/null 2>&1 || true
    $KUBECTL_CMD delete networkpolicy deny-from-other-namespaces -n "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
    $KUBECTL_CMD delete namespace "$test_ns2" --ignore-not-found=true >/dev/null 2>&1 || true

    if [[ "$cross_ns_connection" == "blocked" ]]; then
        debug_exit 0
        return 0
    else
        log_warning "Cross-namespace communication was not blocked"
        debug_exit 1
        return 1
    fi
}

# Main execution
main() {
    init_framework
    create_test_namespace

    run_network_policies

    cleanup_test_namespace
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
