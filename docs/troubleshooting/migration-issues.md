# Migration Issues & Rollback Procedures

**Version:** 2.0  
**Date:** December 2024  
**Author:** Infrastructure Team  

## Overview

This comprehensive troubleshooting guide addresses common issues encountered during infrastructure modernization and provides detailed rollback procedures for each component. The guide is organized by component and includes both preventive measures and reactive solutions.

## Quick Reference

### Emergency Contacts

- **Infrastructure Team**: <tz-dev@vectorweight.com>
- **On-Call Escalation**: Available 24/7 for production issues
- **Slack Channel**: #infrastructure-alerts

### Critical Commands

```bash
# Stop all deployments immediately
kubectl scale deployment --replicas=0 -n argocd argocd-server
killall terraform helm helmfile

# Quick health check
kubectl get nodes
kubectl get pods -A | grep -v Running
curl -k https://prometheus.homelab.local/api/v1/query?query=up

# Emergency rollback trigger
./scripts/rollback/emergency-rollback.sh --environment production --component all
```

## Component-Specific Troubleshooting

### 1. Terraform Issues

#### 1.1 State Lock Problems

**Symptoms:**

- Error: "Another operation is already in progress"
- Terraform operations hang indefinitely
- Lock remains after failed operations

**Diagnosis:**

```bash
# Check current state
terraform show terraform.tfstate | head -20

# List terraform processes
ps aux | grep terraform

# Check lock information
terraform force-unlock --help
```

**Solutions:**

**Option A: Safe Unlock (Recommended)**

```bash
# Verify no other operations are running
ps aux | grep terraform

# Check who has the lock
terraform show terraform.tfstate | grep -A5 -B5 "lineage\|serial"

# Unlock only if safe
terraform force-unlock LOCK_ID

# Verify state integrity
terraform plan -detailed-exitcode
```

**Option B: Force Unlock (Caution Required)**

```bash
# Only if certain no other operations are running
terraform force-unlock -force LOCK_ID

# Immediately validate state
terraform refresh
terraform plan
```

**Rollback Procedure:**

```bash
# If state is corrupted, restore from backup
cp backup/terraform.tfstate.$(date -d "1 day ago" +%Y%m%d) terraform.tfstate

# Re-import critical resources if needed
terraform import kubernetes_namespace.metallb-system metallb-system
terraform import kubernetes_namespace.cert-manager cert-manager
```

#### 1.2 Resource Conflicts

**Symptoms:**

- Error: "Resource already exists"
- Import failures
- Plan shows unexpected changes

**Diagnosis:**

```bash
# Check actual cluster state
kubectl get all -A

# Compare with Terraform state
terraform state list | grep -E "(namespace|deployment|service)"

# Identify conflicts
terraform plan -detailed-exitcode | grep -E "(create|destroy|replace)"
```

**Solutions:**

**Option A: Import Existing Resources**

```bash
# Import conflicting resources
terraform import kubernetes_namespace.example example
terraform import kubernetes_deployment.app default/app-deployment

# Verify import success
terraform plan
```

**Option B: Remove from State and Recreate**

```bash
# Remove from Terraform state (resource remains in cluster)
terraform state rm kubernetes_deployment.problematic

# Re-apply to recreate in state
terraform apply -target=kubernetes_deployment.problematic
```

**Rollback Procedure:**

```bash
# Remove Terraform-managed resources
terraform destroy -target=kubernetes_namespace.new-namespace

# Restore previous configuration
git checkout HEAD~1 -- terraform/
terraform apply
```

#### 1.3 Provider Authentication Issues

**Symptoms:**

- Error: "Error authenticating with Kubernetes"
- Timeout connecting to cluster
- Permission denied errors

**Diagnosis:**

```bash
# Test kubectl connectivity
kubectl cluster-info
kubectl auth can-i create pods --as=system:serviceaccount:kube-system:terraform

# Check kubeconfig
cat ~/.kube/config | grep -A5 -B5 current-context

# Verify Terraform provider configuration
terraform providers
```

**Solutions:**

**Option A: Fix Kubeconfig**

```bash
# Update kubeconfig
k3s kubectl config view --raw > ~/.kube/config

# Or copy from server
scp kang@192.168.16.26:/etc/rancher/k3s/k3s.yaml ~/.kube/config
sed -i 's/127.0.0.1/192.168.16.26/g' ~/.kube/config
```

**Option B: Use Service Account**

```bash
# Create service account for Terraform
kubectl create serviceaccount terraform -n kube-system
kubectl create clusterrolebinding terraform --clusterrole=cluster-admin --serviceaccount=kube-system:terraform

# Get token
TOKEN=$(kubectl get secret $(kubectl get serviceaccount terraform -n kube-system -o jsonpath='{.secrets[0].name}') -n kube-system -o jsonpath='{.data.token}' | base64 -d)

# Update Terraform provider
cat >> terraform/provider.tf <<EOF
provider "kubernetes" {
  host = "https://192.168.16.26:6443"
  token = "$TOKEN"
  insecure = true
}
EOF
```

### 2. Helm/Helmfile Issues

#### 2.1 Release Conflicts

**Symptoms:**

- Error: "Release already exists"
- Helm hooks failing
- Unable to upgrade/rollback releases

**Diagnosis:**

```bash
# List all releases
helm list -A

# Check release history
helm history prometheus -n monitoring

# Check release status
helm status prometheus -n monitoring

# Identify stuck releases
helm list -A --pending
```

**Solutions:**

**Option A: Force Upgrade**

```bash
# Force upgrade to resolve conflicts
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --force \
  --wait

# If hooks are stuck, disable them
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --no-hooks \
  --force
```

**Option B: Delete and Reinstall**

```bash
# Delete release but keep data
helm uninstall prometheus -n monitoring --keep-history

# Reinstall
helmfile --environment production --selector name=prometheus sync
```

**Rollback Procedure:**

```bash
# Rollback to previous version
helm rollback prometheus 1 -n monitoring

# If rollback fails, restore from backup
kubectl apply -f backup/prometheus-manifests.yaml
```

#### 2.2 Dependency Issues

**Symptoms:**

- Charts fail to download
- Version conflicts
- Missing dependencies

**Diagnosis:**

```bash
# Check repository status
helm repo list
helm repo update

# Check chart dependencies
helm dependency list -n monitoring

# Verify chart versions
helmfile --environment production list
```

**Solutions:**

**Option A: Update Dependencies**

```bash
# Update Helm repositories
helm repo update

# Update Helmfile dependencies
helmfile --environment production deps

# Clean and rebuild
helmfile --environment production destroy
helmfile --environment production sync
```

**Option B: Pin Specific Versions**

```bash
# Lock chart versions in helmfile.yaml
releases:
  - name: prometheus
    chart: prometheus-community/kube-prometheus-stack
    version: "55.5.0"  # Pin specific version
```

### 3. Certificate Management Issues

#### 3.1 Let's Encrypt Rate Limiting

**Symptoms:**

- Certificate issuance fails
- Error: "too many certificates already issued"
- ACME challenge failures

**Diagnosis:**

```bash
# Check certificate status
kubectl get certificates -A
kubectl describe certificate problematic-cert

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Check Let's Encrypt rate limits
curl -s "https://letsencrypt.org/docs/rate-limits/"
```

**Solutions:**

**Option A: Use Staging Environment**

```bash
# Switch to staging for testing
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    email: tz-dev@vectorweight.com
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update certificate to use staging
kubectl patch certificate example-cert -p '{"spec":{"issuerRef":{"name":"letsencrypt-staging"}}}'
```

**Option B: Use Self-Signed Certificates Temporarily**

```bash
# Create self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=homelab.local"

# Create Kubernetes secret
kubectl create secret tls temp-cert --key=tls.key --cert=tls.crt
```

**Rollback Procedure:**

```bash
# Restore previous certificates
kubectl apply -f backup/certificates.yaml

# Delete problematic certificate requests
kubectl delete certificaterequest --all
```

#### 3.2 Certificate Validation Failures

**Symptoms:**

- Certificates not being issued
- HTTP01 challenge failures
- DNS validation errors

**Diagnosis:**

```bash
# Check certificate request details
kubectl describe certificaterequest problematic-cert-request

# Check ingress configuration
kubectl describe ingress -A

# Test HTTP01 challenge manually
curl -v http://example.homelab.local/.well-known/acme-challenge/test
```

**Solutions:**

**Option A: Fix Ingress Configuration**

```bash
# Ensure ingress class is correct
kubectl patch ingress example-ingress -p '{"metadata":{"annotations":{"kubernetes.io/ingress.class":"nginx"}}}'

# Verify MetalLB is working
kubectl get svc -n ingress-nginx
kubectl describe svc ingress-nginx-controller -n ingress-nginx
```

**Option B: Manual Certificate Creation**

```bash
# Create certificate manually
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: manual-cert
  namespace: default
spec:
  secretName: manual-cert-tls
  dnsNames:
  - example.homelab.local
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  acme:
    config:
    - http01:
        ingress:
          class: nginx
      domains:
      - example.homelab.local
EOF
```

### 4. Network and Connectivity Issues

#### 4.1 MetalLB IP Pool Exhaustion

**Symptoms:**

- Services stuck in "Pending" state
- No external IP assigned to LoadBalancer services
- MetalLB logs show no available IPs

**Diagnosis:**

```bash
# Check MetalLB configuration
kubectl get ipaddresspools -n metallb-system
kubectl describe ipaddresspool -n metallb-system

# Check service status
kubectl get svc -A | grep LoadBalancer
kubectl describe svc problematic-service

# Check MetalLB logs
kubectl logs -n metallb-system -l app=metallb --tail=50
```

**Solutions:**

**Option A: Expand IP Pool**

```bash
# Update IP pool configuration
kubectl patch ipaddresspool production-pool -n metallb-system --type='merge' -p='{"spec":{"addresses":["192.168.25.240-192.168.25.250","192.168.25.251-192.168.25.255"]}}'

# Or via Terraform
terraform apply -var="metallb_ip_range=192.168.25.240-192.168.25.255"
```

**Option B: Release Unused IPs**

```bash
# Find services using MetalLB IPs
kubectl get svc -A -o wide | grep LoadBalancer

# Delete unused services
kubectl delete svc unused-service -n namespace

# Force MetalLB to reassign
kubectl delete pod -n metallb-system -l app=metallb
```

#### 4.2 DNS Resolution Issues

**Symptoms:**

- Services cannot resolve each other
- External DNS lookups fail
- CoreDNS errors in logs

**Diagnosis:**

```bash
# Test DNS resolution
kubectl run debug-pod --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default

# Check CoreDNS status
kubectl get pods -n kube-system | grep coredns
kubectl logs -n kube-system -l k8s-app=kube-dns

# Check DNS configuration
kubectl get configmap coredns -n kube-system -o yaml
```

**Solutions:**

**Option A: Restart CoreDNS**

```bash
# Restart CoreDNS pods
kubectl delete pod -n kube-system -l k8s-app=kube-dns

# Wait for pods to restart
kubectl wait --for=condition=ready pod -l k8s-app=kube-dns -n kube-system --timeout=60s
```

**Option B: Fix DNS Configuration**

```bash
# Update CoreDNS configuration
kubectl edit configmap coredns -n kube-system

# Add custom DNS entries
kubectl patch configmap coredns -n kube-system --type='merge' -p='{"data":{"Corefile":".:53 {\n    errors\n    health\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n        pods insecure\n        fallthrough in-addr.arpa ip6.arpa\n    }\n    hosts {\n        192.168.25.240 homelab.local\n        fallthrough\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf\n    cache 30\n    loop\n    reload\n    loadbalance\n}"}}'
```

### 5. Storage Issues

#### 5.1 Longhorn Volume Problems

**Symptoms:**

- PVCs stuck in "Pending" state
- Volume attachment failures
- Storage node issues

**Diagnosis:**

```bash
# Check Longhorn system status
kubectl get pods -n longhorn-system
kubectl get pvc -A | grep Pending

# Check Longhorn manager logs
kubectl logs -n longhorn-system -l app=longhorn-manager --tail=50

# Check node storage
kubectl describe node | grep -A10 "Allocated resources"
```

**Solutions:**

**Option A: Restart Longhorn Components**

```bash
# Restart Longhorn manager
kubectl delete pod -n longhorn-system -l app=longhorn-manager

# Restart Longhorn UI
kubectl delete pod -n longhorn-system -l app=longhorn-ui

# Check volume health
kubectl get volumes -n longhorn-system
```

**Option B: Manual Volume Recovery**

```bash
# List problematic volumes
kubectl get volumes -n longhorn-system | grep -v Healthy

# Detach and reattach volume
kubectl patch volume problem-volume -n longhorn-system --type='merge' -p='{"spec":{"nodeID":""}}'

# Wait and check attachment
sleep 30
kubectl get volume problem-volume -n longhorn-system
```

#### 5.2 Storage Class Issues

**Symptoms:**

- PVCs cannot be provisioned
- Wrong storage class selected
- Performance issues

**Diagnosis:**

```bash
# Check available storage classes
kubectl get storageclass

# Check default storage class
kubectl get storageclass | grep "(default)"

# Check provisioner status
kubectl get pods -A | grep provisioner
```

**Solutions:**

**Option A: Fix Default Storage Class**

```bash
# Remove default from current class
kubectl patch storageclass current-default -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'

# Set new default
kubectl patch storageclass longhorn -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

**Option B: Create Temporary Storage Class**

```bash
# Create fast storage class for critical workloads
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: rancher.io/local-path
parameters:
  path: /mnt/fast-ssd
volumeBindingMode: WaitForFirstConsumer
EOF
```

## Comprehensive Rollback Procedures

### 1. Full Infrastructure Rollback

**Use Case:** Complete migration failure, need to return to Ansible-based deployment

**Prerequisites:**

- Complete backup of previous state
- Ansible playbooks available
- Access to original configuration

**Procedure:**

```bash
#!/bin/bash
# scripts/rollback/full-infrastructure-rollback.sh

set -euo pipefail

BACKUP_DATE=${1:-$(date -d "1 day ago" +%Y%m%d)}
ENVIRONMENT=${2:-production}

echo "🚨 CRITICAL: Full infrastructure rollback initiated"
echo "Backup date: $BACKUP_DATE"
echo "Environment: $ENVIRONMENT"

# 1. Stop all GitOps operations
echo "Stopping GitOps operations..."
kubectl scale deployment --replicas=0 -n argocd argocd-server || true
kubectl delete helmrelease --all -A || true

# 2. Scale down applications
echo "Scaling down applications..."
kubectl scale deployment --replicas=0 -A || true
kubectl scale statefulset --replicas=0 -A || true

# 3. Restore Kubernetes resources
echo "Restoring Kubernetes resources from backup..."
if [[ -d "backup/kubernetes-$BACKUP_DATE" ]]; then
    kubectl apply -f backup/kubernetes-$BACKUP_DATE/
else
    echo "❌ No Kubernetes backup found for $BACKUP_DATE"
    exit 1
fi

# 4. Restore Terraform state
echo "Restoring Terraform state..."
if [[ -f "backup/terraform.tfstate.$BACKUP_DATE" ]]; then
    cp backup/terraform.tfstate.$BACKUP_DATE terraform/terraform.tfstate
    cd terraform && terraform refresh
else
    echo "❌ No Terraform state backup found for $BACKUP_DATE"
fi

# 5. Revert to Ansible configuration
echo "Reverting to Ansible configuration..."
if [[ -d "backup/ansible-config-$BACKUP_DATE" ]]; then
    cp -r backup/ansible-config-$BACKUP_DATE/* ansible/
    cd ansible && ansible-playbook -i inventory/hosts.yml site.yml
else
    echo "❌ No Ansible backup found for $BACKUP_DATE"
fi

# 6. Verify rollback
echo "Verifying rollback..."
kubectl get nodes
kubectl get pods -A | grep -v Running | head -20

echo "✅ Full infrastructure rollback completed"
echo "Please verify all services are functioning correctly"
```

### 2. Partial Component Rollback

#### 2.1 Terraform Component Rollback

```bash
#!/bin/bash
# scripts/rollback/terraform-rollback.sh

COMPONENT=$1
TARGET_VERSION=$2

case $COMPONENT in
  "networking")
    terraform destroy -target=module.networking
    git checkout $TARGET_VERSION -- terraform/modules/networking/
    terraform apply -target=module.networking
    ;;
  "security")
    terraform destroy -target=module.security
    git checkout $TARGET_VERSION -- terraform/modules/security/
    terraform apply -target=module.security
    ;;
  "storage")
    # Storage rollback requires careful handling of data
    echo "⚠️  Storage rollback requires manual intervention"
    echo "1. Backup all PVC data"
    echo "2. Scale down applications using storage"
    echo "3. Destroy storage module"
    echo "4. Restore previous configuration"
    ;;
esac
```

#### 2.2 Helm Release Rollback

```bash
#!/bin/bash
# scripts/rollback/helm-rollback.sh

RELEASE=$1
NAMESPACE=$2
REVISION=${3:-0}  # 0 means previous revision

echo "Rolling back $RELEASE in namespace $NAMESPACE"

# Check release history
helm history $RELEASE -n $NAMESPACE

# Rollback to specific or previous revision
if [[ $REVISION -eq 0 ]]; then
    helm rollback $RELEASE -n $NAMESPACE
else
    helm rollback $RELEASE $REVISION -n $NAMESPACE
fi

# Verify rollback
helm status $RELEASE -n $NAMESPACE
kubectl get pods -n $NAMESPACE
```

### 3. Application-Specific Rollbacks

#### 3.1 Monitoring Stack Rollback

```bash
#!/bin/bash
# scripts/rollback/monitoring-rollback.sh

echo "Rolling back monitoring stack..."

# Rollback Prometheus
helm rollback prometheus -n monitoring

# Rollback Grafana
helm rollback grafana -n monitoring

# Rollback Loki
helm rollback loki -n monitoring

# Verify monitoring functionality
curl -s http://prometheus.homelab.local/api/v1/query?query=up | jq '.data.result | length'
```

#### 3.2 Storage Stack Rollback

```bash
#!/bin/bash
# scripts/rollback/storage-rollback.sh

echo "⚠️  CRITICAL: Storage rollback procedure"
echo "This will affect data persistence!"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 1. Backup all PV data
echo "Creating data backups..."
kubectl get pv -o json > backup/pvs-$(date +%Y%m%d-%H%M%S).json

# 2. Scale down applications
echo "Scaling down applications..."
kubectl scale deployment --replicas=0 -A

# 3. Rollback Longhorn
helm rollback longhorn -n longhorn-system

# 4. Verify storage functionality
kubectl get storageclass
kubectl get pv
```

### 4. Emergency Procedures

#### 4.1 Circuit Breaker - Stop All Operations

```bash
#!/bin/bash
# scripts/rollback/emergency-stop.sh

echo "🚨 EMERGENCY: Stopping all operations"

# Stop CI/CD pipelines
kubectl scale deployment --replicas=0 -n argocd argocd-server
kubectl scale deployment --replicas=0 -n flux-system flux-controller

# Stop Terraform operations
killall terraform || true

# Stop Helm operations
killall helm helmfile || true

# Create maintenance page
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: maintenance-page
  namespace: ingress-nginx
data:
  index.html: |
    <html>
    <body>
    <h1>Maintenance Mode</h1>
    <p>System is currently under maintenance. Please try again later.</p>
    </body>
    </html>
EOF

echo "✅ Emergency stop completed"
```

#### 4.2 Data Recovery Procedures

```bash
#!/bin/bash
# scripts/rollback/data-recovery.sh

RECOVERY_TYPE=$1  # full, selective, point-in-time

case $RECOVERY_TYPE in
  "full")
    echo "Performing full data recovery..."
    # Restore from complete backup
    kubectl apply -f backup/full-backup-$(date -d "1 day ago" +%Y%m%d)/
    ;;
  "selective")
    echo "Performing selective data recovery..."
    # Restore specific namespaces/resources
    kubectl apply -f backup/selective-backup/monitoring/
    kubectl apply -f backup/selective-backup/storage/
    ;;
  "point-in-time")
    TIMESTAMP=$2
    echo "Performing point-in-time recovery to $TIMESTAMP..."
    # Restore to specific timestamp
    kubectl apply -f backup/point-in-time/$TIMESTAMP/
    ;;
esac
```

## Preventive Measures

### 1. Automated Backup Strategy

```bash
#!/bin/bash
# scripts/backup/comprehensive-backup.sh

BACKUP_DIR="backup/$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup Kubernetes resources
kubectl get all -A -o yaml > $BACKUP_DIR/all-resources.yaml
kubectl get pv -o yaml > $BACKUP_DIR/persistent-volumes.yaml
kubectl get secrets -A -o yaml > $BACKUP_DIR/secrets.yaml
kubectl get configmaps -A -o yaml > $BACKUP_DIR/configmaps.yaml

# Backup Terraform state
cp terraform/terraform.tfstate $BACKUP_DIR/
cp -r terraform/modules $BACKUP_DIR/terraform-modules/

# Backup Helm releases
helm list -A -o yaml > $BACKUP_DIR/helm-releases.yaml

# Backup configuration files
cp -r config/ $BACKUP_DIR/config/
cp -r ansible/ $BACKUP_DIR/ansible/

echo "Backup completed: $BACKUP_DIR"
```

### 2. Health Monitoring

```bash
#!/bin/bash
# scripts/monitoring/health-check.sh

HEALTH=0

# Check cluster health
if ! kubectl cluster-info >/dev/null 2>&1; then
    echo "❌ Cluster unreachable"
    HEALTH=1
fi

# Check critical pods
CRITICAL_PODS=$(kubectl get pods -A | grep -E "(CrashLoopBackOff|Error|ImagePullBackOff)" | wc -l)
if [[ $CRITICAL_PODS -gt 0 ]]; then
    echo "❌ $CRITICAL_PODS critical pods found"
    HEALTH=1
fi

# Check storage
if ! kubectl get storageclass >/dev/null 2>&1; then
    echo "❌ Storage classes unavailable"
    HEALTH=1
fi

if [[ $HEALTH -eq 0 ]]; then
    echo "✅ System healthy"
else
    echo "🚨 System unhealthy - consider rollback"
    exit 1
fi
```

### 3. Testing Procedures

```bash
#!/bin/bash
# scripts/testing/pre-migration-tests.sh

echo "Running pre-migration tests..."

# Test Terraform
cd terraform
terraform validate
terraform plan -detailed-exitcode

# Test Helm
cd ../helm
helmfile --environment staging lint
helmfile --environment staging diff

# Test connectivity
kubectl run test-pod --image=busybox:1.28 --rm -it --restart=Never -- wget -qO- http://kubernetes.default

echo "✅ Pre-migration tests passed"
```

## Recovery Time Objectives (RTO)

| Component | Target RTO | Maximum RTO | Recovery Method |
|-----------|------------|-------------|-----------------|
| Full Infrastructure | 30 minutes | 2 hours | Full rollback + Ansible |
| Application Layer | 10 minutes | 30 minutes | Helm rollback |
| Storage Layer | 15 minutes | 1 hour | Backup restoration |
| Network Layer | 5 minutes | 15 minutes | Configuration revert |
| Security Layer | 10 minutes | 30 minutes | Certificate restoration |

## Communication Procedures

### Incident Response

1. **Immediate Notification** (0-5 minutes)
   - Slack: #infrastructure-alerts
   - Email: <tz-dev@vectorweight.com>
   - Status: "Investigating"

2. **Assessment** (5-15 minutes)
   - Determine impact scope
   - Assess rollback requirements
   - Update stakeholders

3. **Action** (15-45 minutes)
   - Execute rollback procedures
   - Monitor recovery progress
   - Document actions taken

4. **Resolution** (45-60 minutes)
   - Verify system functionality
   - Update status to "Resolved"
   - Schedule post-mortem

### Post-Incident Review

- **Timeline Documentation**: Complete incident timeline
- **Root Cause Analysis**: Identify failure points
- **Process Improvements**: Update procedures
- **Training Updates**: Share lessons learned

## Conclusion

This troubleshooting guide provides comprehensive procedures for handling migration issues and performing rollbacks. Key principles:

- **Prevention First**: Use automated backups and health checks
- **Quick Response**: Have emergency procedures ready
- **Complete Recovery**: Maintain multiple rollback options
- **Learn and Improve**: Document all incidents for future prevention

Regular practice of these procedures ensures rapid recovery when issues occur during the modernization process.

---

**Document Version:** 2.0  
**Last Updated:** December 2024  
**Next Review:** Post-incident or quarterly  
**Maintainer:** Infrastructure Team  
**Contact:** <tz-dev@vectorweight.com>
