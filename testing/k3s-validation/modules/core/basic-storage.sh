#!/bin/bash
# Core Kubernetes Basic Storage Validation Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_storage_classes() {
    start_test "Storage classes availability"

    local storage_classes
    if storage_classes=$($KUBECTL_CMD get storageclass --no-headers 2>/dev/null); then
        local class_count=0
        local default_class=""

        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((class_count++))
                local class_name=$(echo "$line" | awk '{print $1}')
                local default_marker=$(echo "$line" | awk '{print $2}')

                log_info "Found storage class: $class_name"

                if [[ "$default_marker" == "(default)" ]]; then
                    default_class="$class_name"
                fi
            fi
        done <<< "$storage_classes"

        if [[ $class_count -gt 0 ]]; then
            log_success "Found $class_count storage class(es)"
            if [[ -n "$default_class" ]]; then
                log_success "Default storage class: $default_class"
            else
                log_warning "No default storage class configured"
            fi
        else
            log_warning "No storage classes found"
        fi
    else
        log_error "Failed to retrieve storage classes"
    fi
}

test_persistent_volume_provisioning() {
    start_test "Persistent volume provisioning"

    local pvc_name="storage-test-pvc-$(date +%s)"
    local pod_name="storage-test-pod-$(date +%s)"

    # Create PVC
    log_info "Creating persistent volume claim: $pvc_name"

    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $pvc_name
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

    if [[ $? -eq 0 ]]; then
        # Wait for PVC to be bound
        local timeout=60
        local elapsed=0
        local pvc_status=""

        while [[ $elapsed -lt $timeout ]]; do
            pvc_status=$($KUBECTL_CMD get pvc "$pvc_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")

            if [[ "$pvc_status" == "Bound" ]]; then
                log_success "PVC successfully bound to persistent volume"
                break
            elif [[ "$pvc_status" == "Pending" ]]; then
                log_debug "PVC still pending, waiting..."
                sleep 5
                ((elapsed += 5))
            else
                log_error "PVC in unexpected state: $pvc_status"
                break
            fi
        done

        if [[ "$pvc_status" == "Bound" ]]; then
            # Test pod mounting the volume
            log_info "Testing volume mount with pod"

            cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $pod_name
  namespace: $TEST_NAMESPACE
  labels:
    test-framework: k3s-testing
spec:
  containers:
  - name: storage-test
    image: busybox:1.35
    command: ["/bin/sh", "-c", "echo 'storage test' > /data/test.txt && sleep 60"]
    volumeMounts:
    - name: test-volume
      mountPath: /data
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: $pvc_name
  restartPolicy: Never
EOF

            if wait_for_pod_ready "$pod_name" "$TEST_NAMESPACE" 60; then
                # Verify file was written
                if $KUBECTL_CMD exec "$pod_name" -n "$TEST_NAMESPACE" -- cat /data/test.txt >/dev/null 2>&1; then
                    log_success "Storage volume successfully mounted and writable"
                else
                    log_error "Failed to write to mounted volume"
                fi
            else
                log_error "Pod with mounted volume failed to become ready"
            fi
        else
            log_error "PVC failed to bind within timeout"
        fi
    else
        log_error "Failed to create persistent volume claim"
    fi
}

test_local_path_provisioner() {
    start_test "Local path provisioner (K3s specific)"

    # Check if local-path-provisioner exists (K3s specific)
    if $KUBECTL_CMD get deployment local-path-provisioner -n kube-system >/dev/null 2>&1; then
        local ready_replicas
        ready_replicas=$($KUBECTL_CMD get deployment local-path-provisioner -n kube-system -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

        if [[ "$ready_replicas" -gt 0 ]]; then
            log_success "Local path provisioner is running"

            # Check if local-path storage class exists
            if $KUBECTL_CMD get storageclass local-path >/dev/null 2>&1; then
                log_success "Local path storage class available"
            else
                log_warning "Local path storage class not found"
            fi
        else
            log_warning "Local path provisioner deployment exists but no replicas ready"
        fi
    else
        log_info "Local path provisioner not found (not K3s or different storage setup)"
    fi
}

test_volume_node_affinity() {
    start_test "Volume node affinity"

    # Get persistent volumes and check node affinity
    local pv_list
    if pv_list=$($KUBECTL_CMD get pv --no-headers 2>/dev/null); then
        local pv_count=0
        local affinity_count=0

        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((pv_count++))
                local pv_name=$(echo "$line" | awk '{print $1}')

                # Check if PV has node affinity
                local affinity
                affinity=$($KUBECTL_CMD get pv "$pv_name" -o jsonpath='{.spec.nodeAffinity}' 2>/dev/null || echo "")

                if [[ -n "$affinity" && "$affinity" != "null" ]]; then
                    ((affinity_count++))
                    log_debug "PV $pv_name has node affinity"
                fi
            fi
        done <<< "$pv_list"

        if [[ $pv_count -gt 0 ]]; then
            log_success "Found $pv_count persistent volume(s), $affinity_count with node affinity"
        else
            log_info "No persistent volumes found (normal for new cluster)"
        fi
    else
        log_info "No persistent volumes found or unable to list them"
    fi
}

test_csi_drivers() {
    start_test "CSI drivers"

    # Check for CSI drivers
    if $KUBECTL_CMD get csidriver >/dev/null 2>&1; then
        local csi_drivers
        if csi_drivers=$($KUBECTL_CMD get csidriver --no-headers 2>/dev/null); then
            local driver_count=0

            while IFS= read -r line; do
                if [[ -n "$line" ]]; then
                    ((driver_count++))
                    local driver_name=$(echo "$line" | awk '{print $1}')
                    log_info "Found CSI driver: $driver_name"
                fi
            done <<< "$csi_drivers"

            if [[ $driver_count -gt 0 ]]; then
                log_success "Found $driver_count CSI driver(s)"
            else
                log_info "No CSI drivers found"
            fi
        else
            log_info "No CSI drivers found"
        fi
    else
        log_info "CSI drivers not supported or not available"
    fi
}

# Main execution
run_basic_storage() {
    start_test_module "Basic Storage Validation"

    test_storage_classes
    test_persistent_volume_provisioning
    test_local_path_provisioner
    test_volume_node_affinity
    test_csi_drivers
}

# Allow running this module independently
# Main function for orchestrator compatibility
main() {
    run_basic_storage
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_basic_storage
    cleanup_framework
fi
