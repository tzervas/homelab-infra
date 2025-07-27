# k3s Setup Guide

This guide provides the recommended k3s configuration for your homelab infrastructure.

## Server Configuration (192.168.16.26)

### k3s Installation

```bash
# Install k3s on the server node
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.30.6+k3s1 sh -s - server \
  --cluster-init \
  --disable traefik \
  --disable servicelb \
  --write-kubeconfig-mode 644 \
  --tls-san homelab.local \
  --tls-san 192.168.16.26 \
  --node-taint CriticalAddonsOnly=true:NoExecute \
  --kube-apiserver-arg default-not-ready-toleration-seconds=30 \
  --kube-apiserver-arg default-unreachable-toleration-seconds=30 \
  --kubelet-arg max-pods=110 \
  --kubelet-arg system-reserved=cpu=200m,memory=512Mi
```

### Alternative: Configuration File Method

Create `/etc/rancher/k3s/config.yaml`:

```yaml
cluster-init: true
disable:
  - traefik
  - servicelb
write-kubeconfig-mode: "0644"
tls-san:
  - "homelab.local"
  - "192.168.16.26"
node-taint:
  - "CriticalAddonsOnly=true:NoExecute"
kube-apiserver-arg:
  - "default-not-ready-toleration-seconds=30"
  - "default-unreachable-toleration-seconds=30"
kubelet-arg:
  - "max-pods=110"
  - "system-reserved=cpu=200m,memory=512Mi"
```

Then install with:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.30.6+k3s1 sh -
```

## Post-Installation Setup

### 1. Copy kubeconfig

```bash
# Copy kubeconfig for local access
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(whoami):$(whoami) ~/.kube/config
```

### 2. Install Required Tools

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Helmfile
wget -O helmfile https://github.com/helmfile/helmfile/releases/download/v0.165.0/helmfile_0.165.0_linux_amd64.tar.gz
tar -xzf helmfile_0.165.0_linux_amd64.tar.gz
sudo mv helmfile /usr/local/bin/
sudo chmod +x /usr/local/bin/helmfile
```

### 3. Verify Installation

```bash
# Check k3s status
sudo systemctl status k3s

# Check cluster nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -A
```

## Network Configuration

### MetalLB IP Ranges

The following IP ranges are configured for MetalLB load balancer:

- **Development**: 192.168.25.200-192.168.25.210
- **Staging**: 192.168.25.220-192.168.25.235
- **Production**: 192.168.25.240-192.168.25.250

### DNS Configuration

Add the following entries to your local DNS or hosts file:

```
# Development
192.168.25.201  grafana.dev.homelab.local
192.168.25.202  longhorn.dev.homelab.local
192.168.25.203  prometheus.dev.homelab.local

# Staging
192.168.25.221  grafana.staging.homelab.local
192.168.25.222  longhorn.staging.homelab.local
192.168.25.223  prometheus.staging.homelab.local

# Production
192.168.25.241  grafana.homelab.local
192.168.25.242  longhorn.homelab.local
192.168.25.243  prometheus.homelab.local
```

## Resource Requirements

### Minimum System Requirements

- **CPU**: 4 cores (2 reserved for k3s, 2 for workloads)
- **Memory**: 8GB (2GB reserved for k3s, 6GB for workloads)
- **Storage**: 100GB+ SSD storage
- **Network**: Gigabit Ethernet recommended

### Recommended Resource Allocation

- **k3s System Components**: 1 CPU core, 2GB RAM
- **Workload Allocation**: 70% of remaining resources
- **Storage**: Use local-path provisioner for non-critical data, Longhorn for persistent storage

## Security Considerations

### Firewall Configuration

```bash
# Allow k3s API server
sudo ufw allow 6443/tcp

# Allow MetalLB speaker
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp

# Allow Longhorn
sudo ufw allow 9500-9504/tcp
```

### Pod Security Standards

The cluster is configured with Pod Security Standards:

- **Privileged**: metallb-system, longhorn-system
- **Baseline**: ingress-nginx
- **Restricted**: monitoring, cert-manager (default)

## Troubleshooting

### Common Issues

1. **k3s fails to start**

   ```bash
   sudo journalctl -u k3s -f
   ```

2. **Pods stuck in Pending state**

   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   ```

3. **LoadBalancer services stuck in Pending**
   - Check MetalLB controller logs
   - Verify IP range configuration
   - Ensure L2Advertisement is applied

### Log Locations

- k3s logs: `/var/log/syslog` or `journalctl -u k3s`
- Container logs: `kubectl logs <pod-name> -n <namespace>`
- Audit logs: `/var/lib/rancher/k3s/server/logs/audit.log` (if enabled)
