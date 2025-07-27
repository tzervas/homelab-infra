# Security Best Practices

This guide covers the key security practices implemented in the homelab infrastructure to ensure robust protection of your environment.

## Topics

* [Bastion Host Pattern](#bastion-host-pattern)
* [Network Security](#network-security)
* [Authentication & Authorization](#authentication--authorization)
* [Monitoring & Auditing](#monitoring--auditing)

## Bastion Host Pattern

The homelab infrastructure implements a **bastion host security pattern** where all cluster access is routed through the homelab server. This provides enhanced security, centralized access control, and simplified network management.

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Machine  │────│  Homelab Server │────│  Cluster Nodes  │
│                 │SSH │   (Bastion)     │SSH │                 │
│  • Ansible      │    │  • KVM/libvirt  │    │  • Test VM      │
│  • kubectl      │    │  • Docker       │    │  • Bare Metal   │
│  • Management   │    │  • Monitoring   │    │  • Future Nodes │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Security Benefits

#### 🔒 **Single Point of Access**

- All cluster access must go through the homelab server
- Centralized authentication and authorization
- Easy to monitor and audit all cluster access

#### 🏰 **Network Isolation**

- Cluster nodes can be on private networks
- No direct external access to cluster nodes
- Reduced attack surface

#### 🔑 **SSH Key Management**

- SSH keys only need to be configured on the bastion host
- Bastion host manages access to all cluster nodes
- Simplified key rotation and management

#### 📊 **Audit Trail**

- All cluster access logged on the bastion host
- Easy to track who accessed what and when
- Centralized logging and monitoring

### Implementation

#### Ansible Configuration

The inventory is configured with bastion host settings:

```yaml
cluster:
  hosts:
    test-vm:
      ansible_host: "192.168.122.100"  # VM IP on libvirt network
      ansible_user: kang
      ansible_ssh_common_args: '-o ProxyJump=kang@192.168.16.26 -o StrictHostKeyChecking=no'
```

#### SSH ProxyJump

All SSH connections use the ProxyJump feature:

- **Direct**: `ssh kang@192.168.16.26` (to bastion)
- **Via Bastion**: `ssh -o ProxyJump=kang@192.168.16.26 kang@192.168.122.100` (to cluster node)

### Network Scenarios

#### VM Test Environment

- **Homelab Server**: 192.168.16.26 (your main network)
- **Test VM**: 192.168.122.x (libvirt default network)
- **Access**: Your machine → Homelab server → Test VM

#### Bare Metal Environment

- **Homelab Server**: 192.168.16.26 (bastion)
- **Cluster Nodes**: 192.168.16.x or private subnet
- **Access**: Your machine → Homelab server → Cluster nodes

#### Future Cloud/Hybrid

- **Homelab Server**: Public IP or VPN endpoint
- **Cluster Nodes**: Private cloud network
- **Access**: Internet → Homelab server → Private cloud

### Management & Troubleshooting

#### Direct Bastion Access

```bash
# Connect to bastion host
ssh kang@192.168.16.26

# Run commands on bastion
ssh kang@192.168.16.26 'docker ps'
```

#### Cluster Node Access via Bastion

```bash
# Connect to cluster node through bastion
ssh -o ProxyJump=kang@192.168.16.26 kang@192.168.122.100

# Run Ansible on cluster through bastion
ansible-playbook -i inventory/hosts.yml playbooks/deploy-k3s.yml
```

#### Kubernetes Management

```bash
# kubectl configured to use bastion for cluster access
kubectl --kubeconfig ~/.kube/homelab-config get nodes

# Port forwarding through bastion
kubectl --kubeconfig ~/.kube/homelab-config port-forward svc/grafana 3000:3000
```

### Security Hardening

#### ✅ **Best Practices Implemented**

- SSH key authentication only (no passwords)
- StrictHostKeyChecking disabled only for automation (not manual access)
- Centralized access logging on bastion host
- Network isolation between management and cluster networks

#### 🔧 **Additional Hardening Options**

- Configure fail2ban on bastion host
- Implement SSH connection rate limiting
- Add bastion host monitoring and alerting
- Regular SSH key rotation procedures

#### 📋 **Monitoring & Maintenance**

- Monitor SSH connection logs: `/var/log/auth.log`
- Regular security updates on bastion host
- Periodic access review and key rotation
- Backup bastion host configuration

## Network Security

*This section to be expanded with network security practices*

## Authentication & Authorization

*This section to be expanded with authentication and authorization practices*

## Monitoring & Auditing

*This section to be expanded with monitoring and auditing practices*
