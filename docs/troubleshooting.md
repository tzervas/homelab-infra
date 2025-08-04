# Troubleshooting Guide

Comprehensive troubleshooting guide for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## 🚨 Emergency Quick Fixes

### System Not Responding
```bash
# Check orchestrator status
python -m homelab_orchestrator status

# Check Kubernetes cluster
kubectl cluster-info

# Check system resources
df -h && free -h

# Restart if needed
sudo systemctl restart k3s
```

### Cannot Access Services
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check service endpoints
kubectl get svc -A

# Check DNS resolution
nslookup grafana.homelab.local
```

## 🔧 Installation Issues

### Python Version Problems

**Problem**: `python: command not found` or version < 3.10

**Solution**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv

# Check version
python3.10 --version

# Create alias if needed
echo 'alias python=python3.10' >> ~/.bashrc
source ~/.bashrc
```

### Virtual Environment Issues

**Problem**: Cannot activate virtual environment or packages not found

**Solution**:
```bash
# Remove and recreate virtual environment
rm -rf .venv
python3.10 -m venv .venv
source .venv/bin/activate

# Upgrade pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Verify installation
python -m homelab_orchestrator --version
```

### Permission Denied Errors

**Problem**: Permission denied when running scripts or accessing kubectl

**Solution**:
```bash
# Fix script permissions
chmod +x scripts/security/generate-secrets.sh
find scripts/ -name "*.sh" -exec chmod +x {} \;

# Fix kubectl permissions
sudo chown $USER:$USER ~/.kube/config
chmod 600 ~/.kube/config

# Fix .env permissions
chmod 600 .env
```

## 🔐 Security & Secrets Issues

### Missing .env File

**Problem**: Configuration validation fails, secrets not found

**Solution**:
```bash
# Generate secrets
./scripts/security/generate-secrets.sh

# Verify .env file was created
ls -la .env

# Check contents (be careful not to expose secrets)
head -5 .env
```

### Invalid Secrets Format

**Problem**: Base64 encoding errors or invalid secret format

**Solution**:
```bash
# Regenerate all secrets
rm .env
./scripts/security/generate-secrets.sh

# Manual secret generation if needed
echo -n "your-secret" | base64

# Verify OAuth2 secrets are base64 encoded
echo "$OAUTH2_CLIENT_SECRET" | base64 -d
```

### Hardcoded Secrets Detected

**Problem**: Gitleaks or security scan finds hardcoded secrets

**Solution**:
```bash
# Check for hardcoded secrets
gitleaks detect --no-git

# Remove hardcoded secrets from files
# Update kubernetes/base/oauth2-proxy.yaml to use ${OAUTH2_CLIENT_SECRET}
# Update kubernetes/keycloak/oauth2-proxy-multi-client.yaml

# Regenerate secrets
./scripts/security/generate-secrets.sh
```

## ⚙️ Configuration Issues

### Configuration Validation Fails

**Problem**: `python -m homelab_orchestrator config validate` fails

**Solution**:
```bash
# Check specific validation errors
python -m homelab_orchestrator config validate --verbose

# Common fixes:
# 1. Missing environment field in helm environments
find helm/environments/ -name "*.yaml" -exec grep -L "environment:" {} \;

# 2. Invalid YAML syntax
find config/ -name "*.yaml" -exec python -c "import yaml; yaml.safe_load(open('{}'))" \;

# 3. Missing required configuration files
ls -la config/consolidated/
```

### Environment Variable Issues

**Problem**: Variables not being substituted in configuration files

**Solution**:
```bash
# Check .env file exists and has correct format
cat .env | grep -E "^[A-Z_]+=.*"

# Source environment variables
source .env

# Test variable substitution
echo ${OAUTH2_CLIENT_SECRET}

# Verify orchestrator loads variables
python -c "
from homelab_orchestrator.core.config_manager import ConfigManager
cm = ConfigManager.from_environment()
print(cm.get_deployment_config())
"
```

### Missing Configuration Files

**Problem**: Required configuration files not found

**Solution**:
```bash
# Check for missing consolidated configs
ls -la config/consolidated/

# Create symlinks if missing
ln -sf ../../../config/consolidated/networking.yaml homelab_orchestrator/config/consolidated/
ln -sf ../../../config/consolidated/storage.yaml homelab_orchestrator/config/consolidated/
ln -sf ../../../config/consolidated/resources.yaml homelab_orchestrator/config/consolidated/
ln -sf ../../../config/consolidated/namespaces.yaml homelab_orchestrator/config/consolidated/
ln -sf ../../../config/consolidated/services.yaml homelab_orchestrator/config/consolidated/
```

## 🚢 Kubernetes Issues

### Cluster Not Available

**Problem**: `kubectl cluster-info` fails or connection refused

**Solution**:
```bash
# Check K3s service status
sudo systemctl status k3s

# Restart K3s if needed
sudo systemctl restart k3s

# Check K3s logs
sudo journalctl -u k3s -f

# Reconfigure kubectl
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
export KUBECONFIG=~/.kube/config
```

### Pods Stuck in Pending

**Problem**: Pods remain in Pending state

**Solution**:
```bash
# Check pod status and events
kubectl describe pod <pod-name> -n <namespace>

# Common causes and fixes:
# 1. Resource constraints
kubectl top nodes
kubectl describe nodes

# 2. Image pull issues
kubectl get events --sort-by=.metadata.creationTimestamp

# 3. Taints and tolerations
kubectl describe nodes | grep -i taint
```

### Node Not Ready

**Problem**: `kubectl get nodes` shows NotReady

**Solution**:
```bash
# Check node status
kubectl describe node <node-name>

# Check kubelet logs
sudo journalctl -u k3s -f | grep kubelet

# Common fixes:
# 1. Disk space
df -h

# 2. Memory pressure
free -h

# 3. Network issues
sudo systemctl restart k3s
```

## 📜 Certificate Issues

### Let's Encrypt Rate Limiting

**Problem**: Certificate requests failing due to rate limits

**Solution**:
```bash
# Switch to staging issuer temporarily
kubectl patch certificate homelab-wildcard-tls \
  --type='merge' \
  --patch='{"spec":{"issuerRef":{"name":"letsencrypt-staging"}}}'

# Check rate limit status
python -m homelab_orchestrator certificates check-expiry

# Monitor certificate status
kubectl describe certificate homelab-wildcard-tls
```

### Certificate Not Ready

**Problem**: Certificates stuck in "Not Ready" state

**Solution**:
```bash
# Check certificate status
kubectl get certificates -A
kubectl describe certificate <cert-name>

# Check ACME orders and challenges
kubectl get orders,challenges -A

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Force certificate renewal
python -m homelab_orchestrator certificates renew <cert-name>
```

### HTTP-01 Challenge Failing

**Problem**: ACME HTTP-01 challenge validation fails

**Solution**:
```bash
# Check ingress controller status
kubectl get pods -n ingress-nginx

# Verify ingress configuration
kubectl get ingress -A

# Check challenge details
kubectl describe challenge <challenge-name>

# Test HTTP endpoint manually
curl -I http://yourdomain.com/.well-known/acme-challenge/test

# Verify DNS resolution
nslookup yourdomain.com
```

### Self-Signed Certificate Issues

**Problem**: Browser shows certificate warnings for self-signed certs

**Solution**:
```bash
# Check certificate issuer
kubectl get certificates -o yaml | grep issuerRef

# Verify self-signed CA certificate
kubectl get secret selfsigned-ca-secret -n cert-manager -o yaml

# For development, add certificate exception in browser
# Or install CA certificate system-wide:
kubectl get secret selfsigned-ca-secret -n cert-manager -o jsonpath='{.data.ca\.crt}' | base64 -d > homelab-ca.crt
sudo cp homelab-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

## 🌐 Networking Issues

### Services Not Accessible

**Problem**: Cannot reach services via ingress or load balancer

**Solution**:
```bash
# Check ingress controller
kubectl get svc -n ingress-nginx

# Verify MetalLB assigned IP
kubectl get svc -n ingress-nginx nginx-ingress-controller

# Check ingress rules
kubectl get ingress -A
kubectl describe ingress <ingress-name>

# Test service directly
kubectl port-forward svc/<service-name> 8080:80

# Check network policies
kubectl get networkpolicy -A
```

### DNS Resolution Issues

**Problem**: Services cannot resolve internal DNS names

**Solution**:
```bash
# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Test DNS resolution from pod
kubectl run test-dns --image=busybox --restart=Never -- nslookup kubernetes.default

# Check DNS configuration
kubectl get configmap coredns -n kube-system -o yaml

# Restart CoreDNS if needed
kubectl rollout restart deployment/coredns -n kube-system
```

### Load Balancer IP Pending

**Problem**: MetalLB not assigning external IPs

**Solution**:
```bash
# Check MetalLB pods
kubectl get pods -n metallb-system

# Check MetalLB configuration
kubectl get configmap config -n metallb-system -o yaml

# Verify IP pool configuration
kubectl get ipaddresspool -A

# Check MetalLB logs
kubectl logs -n metallb-system -l app=metallb
```

## 🗃️ Storage Issues

### PVC Stuck in Pending

**Problem**: Persistent Volume Claims not being bound

**Solution**:
```bash
# Check PVC status
kubectl get pvc -A

# Check available PVs
kubectl get pv

# Check storage classes
kubectl get storageclass

# For local-path-provisioner issues
kubectl get pods -n kube-system -l app=local-path-provisioner

# Check local-path-provisioner logs
kubectl logs -n kube-system -l app=local-path-provisioner
```

### Longhorn Issues

**Problem**: Longhorn storage not working properly

**Solution**:
```bash
# Check Longhorn system pods
kubectl get pods -n longhorn-system

# Check Longhorn manager logs
kubectl logs -n longhorn-system -l app=longhorn-manager

# Access Longhorn UI
kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80

# Check node disk space
df -h
```

## 🖥️ GPU Issues

### GPU Resources Not Detected

**Problem**: GPU resources not available in cluster

**Solution**:
```bash
# Check GPU detection
python -m homelab_orchestrator gpu discover

# Verify NVIDIA drivers
nvidia-smi

# Check device plugin
kubectl get pods -n kube-system | grep nvidia

# Install NVIDIA device plugin if missing
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

## 🔍 Monitoring Issues

### Prometheus Not Scraping Targets

**Problem**: Prometheus shows targets as down

**Solution**:
```bash
# Check Prometheus pods
kubectl get pods -n monitoring

# Check service monitors
kubectl get servicemonitor -A

# Check Prometheus configuration
kubectl get secret prometheus-config -n monitoring -o yaml

# Access Prometheus UI
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

### Grafana Dashboards Not Loading

**Problem**: Grafana shows empty dashboards or connection errors

**Solution**:
```bash
# Check Grafana pods
kubectl get pods -n monitoring

# Check Grafana data source configuration
kubectl get configmap grafana-datasources -n monitoring -o yaml

# Reset Grafana admin password
kubectl patch secret grafana-secret -n monitoring --type='json' \
  -p='[{"op": "replace", "path": "/data/admin-password", "value": "NEWPASSWORD_BASE64"}]'

# Access Grafana UI
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

## 🧪 Testing & Validation Issues

### MVP Tests Failing

**Problem**: `python scripts/testing/test_mvp_deployment.py` shows failures

**Solution**:
```bash
# Run tests with debug output
python scripts/testing/test_mvp_deployment.py --verbose

# Check specific test failures:

# 1. Security Configuration test fails
./scripts/security/generate-secrets.sh
chmod +x scripts/security/generate-secrets.sh

# 2. Version Information test fails
pip install -e .
python -m homelab_orchestrator --version

# 3. Configuration Validation test fails
python -m homelab_orchestrator config validate

# 4. Cluster Connectivity test fails
kubectl cluster-info

# 5. Orchestrator Functionality test fails
python -m homelab_orchestrator deploy infrastructure --dry-run
```

## 🔄 Recovery Procedures

### Complete System Reset

If all else fails, perform a complete reset:

```bash
# 1. Stop all services
sudo systemctl stop k3s

# 2. Clean up Kubernetes
sudo rm -rf /var/lib/rancher/k3s/
sudo rm -rf ~/.kube/

# 3. Clean up application data
rm -rf .venv/
rm .env

# 4. Reinstall from scratch
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 5. Reinstall K3s
curl -sfL https://get.k3s.io | sh -

# 6. Reconfigure
./scripts/security/generate-secrets.sh
python -m homelab_orchestrator config validate
```

### Backup and Restore

```bash
# Create backup before major changes
tar -czf homelab-backup-$(date +%Y%m%d).tar.gz \
  .env config/ kubernetes/ scripts/

# Restore from backup
tar -xzf homelab-backup-*.tar.gz
./scripts/security/generate-secrets.sh  # If secrets were lost
```

## 📞 Getting Help

### Collect Diagnostic Information

```bash
# System info
uname -a
python --version
kubectl version

# Orchestrator info
python -m homelab_orchestrator --version
python -m homelab_orchestrator status

# Cluster info
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A

# Create support bundle
mkdir -p /tmp/homelab-debug
kubectl cluster-info dump > /tmp/homelab-debug/cluster-info.txt
python -m homelab_orchestrator config validate > /tmp/homelab-debug/config-validation.txt
tar -czf homelab-debug-$(date +%Y%m%d).tar.gz -C /tmp homelab-debug/
```

### Where to Get Help

1. **Check Logs First**:
   ```bash
   # Orchestrator logs
   python -m homelab_orchestrator --log-level DEBUG <command>
   
   # Kubernetes logs
   kubectl logs -n <namespace> <pod-name>
   
   # System logs
   sudo journalctl -u k3s -f
   ```

2. **Search Documentation**:
   - [Installation Guide](installation.md)
   - [Configuration Guide](configuration.md)
   - [Certificate Management](certificates.md)

3. **Community Support**:
   - [GitHub Issues](https://github.com/tzervas/homelab-infra/issues)
   - [GitHub Discussions](https://github.com/tzervas/homelab-infra/discussions)

4. **Bug Reports**:
   Include the diagnostic bundle and specific error messages when reporting issues.

---

**💡 Pro Tip**: Most issues can be resolved by checking logs, validating configuration, and ensuring all prerequisites are met. Start with the basics and work your way up!