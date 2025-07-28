#!/bin/bash
# K3s Storage I/O Performance Testing Module

source "$(dirname "${BASH_SOURCE[0]}")/../../lib/common.sh"

test_pvc_io_performance() {
    start_test "PVC I/O performance"

    local pvc_name="storage-perf-pvc-$(date +%s)"
    local test_pod="storage-perf-pod-$(date +%s)"

    # Create PVC for testing
    cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: $pvc_name
  namespace: $TEST_NAMESPACE
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

        while [[ $elapsed -lt $timeout ]]; do
            local pvc_status
            pvc_status=$($KUBECTL_CMD get pvc "$pvc_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")

            if [[ "$pvc_status" == "Bound" ]]; then
                break
            fi

            sleep 2
            ((elapsed += 2))
        done

        if [[ "$pvc_status" == "Bound" ]]; then
            # Create pod to test I/O
            create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 300"

            # Add volume mount
            $KUBECTL_CMD patch pod "$test_pod" -n "$TEST_NAMESPACE" --type='json' -p='[
                {
                    "op": "add",
                    "path": "/spec/volumes",
                    "value": [{"name": "test-storage", "persistentVolumeClaim": {"claimName": "'$pvc_name'"}}]
                },
                {
                    "op": "add",
                    "path": "/spec/containers/0/volumeMounts",
                    "value": [{"name": "test-storage", "mountPath": "/data"}]
                }
            ]' >/dev/null 2>&1 || {
                # If patch fails, recreate pod with volume
                $KUBECTL_CMD delete pod "$test_pod" -n "$TEST_NAMESPACE" >/dev/null 2>&1
                cat <<EOF | $KUBECTL_CMD apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: $test_pod
  namespace: $TEST_NAMESPACE
spec:
  containers:
  - name: test-container
    image: busybox:1.35
    command: ["/bin/sh", "-c", "sleep 300"]
    volumeMounts:
    - name: test-storage
      mountPath: /data
  volumes:
  - name: test-storage
    persistentVolumeClaim:
      claimName: $pvc_name
  restartPolicy: Never
EOF
            }

            if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then
                # Test write performance
                local write_start=$(date +%s.%N)
                if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- dd if=/dev/zero of=/data/testfile bs=1M count=10 >/dev/null 2>&1; then
                    local write_end=$(date +%s.%N)
                    local write_time=$(echo "$write_end - $write_start" | bc -l 2>/dev/null || echo "0")
                    local write_throughput=$(echo "scale=2; 10 / $write_time" | bc -l 2>/dev/null || echo "0")
                    log_success "Write performance: ${write_throughput} MB/s"

                    # Test read performance
                    local read_start=$(date +%s.%N)
                    if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- dd if=/data/testfile of=/dev/null bs=1M >/dev/null 2>&1; then
                        local read_end=$(date +%s.%N)
                        local read_time=$(echo "$read_end - $read_start" | bc -l 2>/dev/null || echo "0")
                        local read_throughput=$(echo "scale=2; 10 / $read_time" | bc -l 2>/dev/null || echo "0")
                        log_success "Read performance: ${read_throughput} MB/s"

                        # Performance assessment
                        if (( $(echo "$write_throughput > 50" | bc -l 2>/dev/null || echo "0") )); then
                            log_success "Storage write performance: Excellent"
                        elif (( $(echo "$write_throughput > 20" | bc -l 2>/dev/null || echo "0") )); then
                            log_success "Storage write performance: Good"
                        else
                            log_warning "Storage write performance: Moderate"
                        fi
                    else
                        log_error "Failed to test read performance"
                    fi
                else
                    log_error "Failed to test write performance"
                fi
            else
                log_error "Storage test pod failed to become ready"
            fi
        else
            log_error "PVC failed to bind within timeout"
        fi
    else
        log_error "Failed to create PVC for storage testing"
    fi
}

test_local_path_performance() {
    start_test "Local path storage performance"

    local test_pod="local-path-perf-$(date +%s)"

    create_test_pod "$test_pod" "busybox:1.35" "$TEST_NAMESPACE" "sleep 300"

    if wait_for_pod_ready "$test_pod" "$TEST_NAMESPACE" 60; then
        # Test local filesystem performance (emptyDir)
        local local_write_start=$(date +%s.%N)
        if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- dd if=/dev/zero of=/tmp/local-testfile bs=1M count=50 >/dev/null 2>&1; then
            local local_write_end=$(date +%s.%N)
            local local_write_time=$(echo "$local_write_end - $local_write_start" | bc -l 2>/dev/null || echo "0")
            local local_write_throughput=$(echo "scale=2; 50 / $local_write_time" | bc -l 2>/dev/null || echo "0")
            log_success "Local path write performance: ${local_write_throughput} MB/s"

            # Test local read performance
            local local_read_start=$(date +%s.%N)
            if $KUBECTL_CMD exec "$test_pod" -n "$TEST_NAMESPACE" -- dd if=/tmp/local-testfile of=/dev/null bs=1M >/dev/null 2>&1; then
                local local_read_end=$(date +%s.%N)
                local local_read_time=$(echo "$local_read_end - $local_read_start" | bc -l 2>/dev/null || echo "0")
                local local_read_throughput=$(echo "scale=2; 50 / $local_read_time" | bc -l 2>/dev/null || echo "0")
                log_success "Local path read performance: ${local_read_throughput} MB/s"
            else
                log_error "Failed to test local path read performance"
            fi
        else
            log_error "Failed to test local path write performance"
        fi
    else
        log_error "Local path test pod failed to become ready"
    fi
}

# Main execution
run_storage_io() {
    start_test_module "Storage I/O Performance"

    test_pvc_io_performance
    test_local_path_performance
}

# Allow running this module independently
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    init_framework
    run_storage_io
    cleanup_framework
fi
