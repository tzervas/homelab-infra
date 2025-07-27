# Security Best Practices

This guide covers the key security practices implemented in the homelab infrastructure to ensure
robust protection of your environment.

## Topics

- [Bastion Host Pattern](#bastion-host-pattern)
- [Network Security](#network-security)
- [Authentication & Authorization](#authentication--authorization)
- [Monitoring & Auditing](#monitoring--auditing)

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
      ansible_host: "192.168.100.10"  # VM IP on private network
      ansible_user: homelab-user
      ansible_ssh_common_args: '-o ProxyJump=homelab-user@192.168.1.10 -o StrictHostKeyChecking=no'
```

#### SSH ProxyJump

All SSH connections use the ProxyJump feature:

- **Direct**: `ssh homelab-user@192.168.1.10` (to bastion)
- **Via Bastion**: `ssh -o ProxyJump=homelab-user@192.168.1.10 homelab-user@192.168.100.10` (to cluster node)

### Network Scenarios

#### VM Test Environment

- **Homelab Server**: 192.168.1.10 (your main network)
- **Test VM**: 192.168.100.x (private network)
- **Access**: Your machine → Homelab server → Test VM

#### Bare Metal Environment

- **Homelab Server**: 192.168.1.10 (bastion)
- **Cluster Nodes**: 192.168.1.x or private subnet
- **Access**: Your machine → Homelab server → Cluster nodes

#### Future Cloud/Hybrid

- **Homelab Server**: Public IP or VPN endpoint
- **Cluster Nodes**: Private cloud network
- **Access**: Internet → Homelab server → Private cloud

### Management & Troubleshooting

#### Direct Bastion Access

```bash
# Connect to bastion host
ssh homelab-user@192.168.1.10

# Run commands on bastion
ssh homelab-user@192.168.1.10 'docker ps'
```

#### Cluster Node Access via Bastion

```bash
# Connect to cluster node through bastion
ssh -o ProxyJump=homelab-user@192.168.1.10 homelab-user@192.168.100.10

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

### Network Policies

- Use restrictive network policies by default
- Implement network segmentation between environments
- Control ingress/egress traffic with explicit rules
- Monitor and log network activity

### Firewall Configuration

- Implement stateful firewalls at network boundaries
- Allow only required ports and protocols
- Regular review and audit of firewall rules
- Log and monitor firewall events

## Authentication & Authorization

### Access Control

- Use role-based access control (RBAC)
- Implement least privilege principle
- Regular access review and cleanup
- Centralized identity management

### Multi-Factor Authentication

- Enable MFA for all administrative access
- Use hardware security keys where possible
- Regular audit of authentication methods
- Secure credential storage

## Monitoring & Auditing

### Security Monitoring

- Implement comprehensive logging
- Use security information and event management (SIEM)
- Set up alerts for suspicious activities
- Regular security assessments

### Compliance Auditing

- Maintain audit trails for all changes
- Regular compliance checks
- Automated security scanning
- Incident response procedures
