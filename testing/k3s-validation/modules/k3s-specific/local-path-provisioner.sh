#!/bin/bash
# K3s Local Path Provisioner Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_local_path_provisioner_health() {
    start_test "Local Path Provisioner health check"

    # Check if local-path-provisioner deployment exists
    if $KUBECTL_CMD get deployment local-path-provisioner -n kube-system >/dev/null 2>&1; then
        if wait_for_deployment_ready local-path-provisioner kube-system 120; then
            log_success "Local Path Provisioner deployment is ready"
        else
            log_error "Local Path Provisioner deployment is not ready"
            return 1
        fi
    else
        log_error "Local Path Provisioner deployment not found"
        return 1
    fi

    # Check provisioner pod logs for errors
    local provisioner_pod
    provisioner_pod=$($KUBECTL_CMD get pods -n kube-system -l app=local-path-provisioner -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -n "$provisioner_pod" ]]; then
        local error_count
        error_count=$($KUBECTL_CMD logs "$provisioner_pod" -n kube-system --since=5m 2>/dev/null | grep -i error | wc -l)

        if [[ $error_count -eq 0 ]]; then
            log_success "No errors in provisioner logs"
        else
            log_warning "Found $error_count error entries in provisioner logs"
        fi
    fi
}

test_local_path_storage_class() {
    start_test "Local Path storage class configuration"

    # Check if local-path storage class exists
    if $KUBECTL_CMD get storageclass local-path >/dev/null 2>&1; then
        log_success "Local Path storage class exists"

        # Check if it's the default storage class
        local is_default
        is_default=$($KUBECTL_CMD get storageclass local-path -o jsonpath='{.metadata.annotations.storageclass\.kubernetes\.io/is-default-class}' 2>/dev/null)

        if [[ "$is_default" == "true" ]]; then
            log_success "Local Path is the default storage class"
        else
            log_info "Local Path is not the default storage class"
        fi

        # Check provisioner configuration
        local provisioner
        provisioner=$($KUBECTL_CMD get storageclass local-path -o jsonpath='{.provisioner}' 2>/dev/null)

        if [[ "$provisioner" == "rancher.io/local-path" ]]; then
            log_success "Storage class has correct provisioner"
        else
            log_error "Storage class has incorrect provisioner: $provisioner"
        fi
    else
        log_error "Local Path storage class not found"
        return 1
    fi
}

test_pvc_creation_and_binding() {
    start_test "PVC creation and binding with Local Path"

    # Create PVC
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: local-path-test-pvc
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Mi
EOF

    # Wait for PVC to be bound
    local timeout=60
    local elapsed=0
    local pvc_status=""

    while [[ $elapsed -lt $timeout ]]; do
        pvc_status=$($KUBECTL_CMD get pvc local-path-test-pvc -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)
        if [[ "$pvc_status" == "Bound" ]]; then
            break
        fi
        sleep 2
        ((elapsed += 2))
    done

    if [[ "$pvc_status" == "Bound" ]]; then
        log_success "PVC bound successfully"

        # Get PV name and check its properties
        local pv_name
        pv_name=$($KUBECTL_CMD get pvc local-path-test-pvc -n "$TEST_NAMESPACE" -o jsonpath='{.spec.volumeName}' 2>/dev/null)

        if [[ -n "$pv_name" ]]; then
            local pv_path
            pv_path=$($KUBECTL_CMD get pv "$pv_name" -o jsonpath='{.spec.local.path}' 2>/dev/null)

            if [[ -n "$pv_path" ]]; then
                log_success "PV created with local path: $pv_path"
            else
                log_error "PV local path not found"
            fi
        fi
    else
        log_error "PVC failed to bind within ${timeout}s, status: $pvc_status"
        return 1
    fi
}

test_pod_volume_mounting() {
    start_test "Pod volume mounting and data persistence"

    # Create pod with the PVC
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: volume-test-pod
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["/bin/sh", "-c"]
    args:
    - |
      echo "Initial test data" > /data/test-file.txt
      echo "Data written at \$(date)" >> /data/test-file.txt
      sleep 300
    volumeMounts:
    - name: test-volume
      mountPath: /data
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: local-path-test-pvc
  restartPolicy: Never
EOF

    if ! wait_for_pod_ready volume-test-pod "$TEST_NAMESPACE" 120; then
        log_error "Volume test pod failed to start"
        return 1
    fi

    # Wait a moment for data to be written
    sleep 5

    # Verify data was written
    if $KUBECTL_CMD exec volume-test-pod -n "$TEST_NAMESPACE" -- cat /data/test-file.txt >/dev/null 2>&1; then
        log_success "Data successfully written to persistent volume"

        # Get the content to verify
        local file_content
        file_content=$($KUBECTL_CMD exec volume-test-pod -n "$TEST_NAMESPACE" -- cat /data/test-file.txt 2>/dev/null)

        if echo "$file_content" | grep -q "Initial test data"; then
            log_success "Data integrity verified"
        else
            log_error "Data integrity check failed"
        fi
    else
        log_error "Failed to read data from persistent volume"
        return 1
    fi
}

test_volume_expansion() {
    start_test "Volume expansion capability"

    # Check if the storage class supports volume expansion
    local allow_expansion
    allow_expansion=$($KUBECTL_CMD get storageclass local-path -o jsonpath='{.allowVolumeExpansion}' 2>/dev/null)

    if [[ "$allow_expansion" == "true" ]]; then
        log_success "Storage class supports volume expansion"

        # Try to expand the existing PVC
        $KUBECTL_CMD patch pvc local-path-test-pvc -n "$TEST_NAMESPACE" -p '{"spec":{"resources":{"requests":{"storage":"200Mi"}}}}' >/dev/null 2>&1

        # Wait and check if expansion worked
        sleep 10
        local new_size
        new_size=$($KUBECTL_CMD get pvc local-path-test-pvc -n "$TEST_NAMESPACE" -o jsonpath='{.status.capacity.storage}' 2>/dev/null)

        if [[ "$new_size" == "200Mi" ]]; then
            log_success "Volume expansion successful: $new_size"
        else
            log_warning "Volume expansion may not be immediate (current size: $new_size)"
        fi
    else
        log_info "Storage class does not support volume expansion (expected for local storage)"
    fi
}

test_multiple_pods_same_volume() {
    start_test "Multiple pods accessing same volume (ReadWriteOnce behavior)"

    # Create second pod trying to use the same PVC
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: volume-test-pod-2
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["/bin/sh", "-c", "sleep 60"]
    volumeMounts:
    - name: test-volume
      mountPath: /data
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: local-path-test-pvc
  restartPolicy: Never
EOF

    # Wait and check pod status
    sleep 10

    local pod_status
    pod_status=$($KUBECTL_CMD get pod volume-test-pod-2 -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)

    # For ReadWriteOnce, the second pod should either be pending or fail if on different node
    if [[ "$pod_status" == "Pending" ]]; then
        log_success "ReadWriteOnce access mode properly enforced (second pod pending)"
    elif [[ "$pod_status" == "Running" ]]; then
        # Check if both pods are on the same node
        local node1 node2
        node1=$($KUBECTL_CMD get pod volume-test-pod -n "$TEST_NAMESPACE" -o jsonpath='{.spec.nodeName}' 2>/dev/null)
        node2=$($KUBECTL_CMD get pod volume-test-pod-2 -n "$TEST_NAMESPACE" -o jsonpath='{.spec.nodeName}' 2>/dev/null)

        if [[ "$node1" == "$node2" ]]; then
            log_success "Both pods running on same node (valid for ReadWriteOnce)"
        else
            log_warning "ReadWriteOnce volume accessed from multiple nodes (unexpected)"
        fi
    else
        log_info "Second pod status: $pod_status"
    fi
}

test_provisioner_node_affinity() {
    start_test "Provisioner node affinity and scheduling"

    # Get node information where volumes are created
    local pv_list
    pv_list=$($KUBECTL_CMD get pv -l "local-path-provisioner=local-path" -o json 2>/dev/null)

    if [[ -n "$pv_list" ]]; then
        local pv_count
        pv_count=$(echo "$pv_list" | jq '.items | length')

        if [[ $pv_count -gt 0 ]]; then
            log_success "Found $pv_count Local Path persistent volumes"

            # Check node affinity on PVs
            local node_affinity_count
            node_affinity_count=$(echo "$pv_list" | jq '[.items[] | select(.spec.nodeAffinity)] | length')

            if [[ $node_affinity_count -eq $pv_count ]]; then
                log_success "All PVs have proper node affinity configured"
            else
                log_warning "$node_affinity_count out of $pv_count PVs have node affinity"
            fi
        fi
    else
        log_skip "No Local Path PVs found for affinity testing"
    fi
}

# Main execution
run_local_path_validation() {
    start_test_module "Local Path Provisioner Validation"

    test_local_path_provisioner_health
    test_local_path_storage_class
    test_pvc_creation_and_binding
    test_pod_volume_mounting
    test_volume_expansion
    test_multiple_pods_same_volume
    test_provisioner_node_affinity
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    create_test_namespace
    run_local_path_validation
    cleanup_framework
fi
