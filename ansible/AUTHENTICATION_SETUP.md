# Homelab Ansible Authentication Setup

This document provides comprehensive documentation for the authentication setup implemented in the homelab infrastructure, covering SSH key authentication, passwordless sudo configuration, and automated validation procedures.

## Table of Contents

1. [Overview](#overview)
2. [Ansible Configuration](#ansible-configuration)
3. [User Authentication Setup](#user-authentication-setup)
4. [Passwordless Sudo Configuration](#passwordless-sudo-configuration)
5. [Validation Playbooks](#validation-playbooks)
6. [Usage Instructions](#usage-instructions)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Security Considerations](#security-considerations)
9. [Best Practices](#best-practices)

## Overview

The homelab infrastructure uses a multi-layered authentication approach designed for secure automated deployments:

- **SSH Key Authentication**: Passwordless SSH access using Ed25519 keys
- **Dual User System**: Primary user (`kang`) and deployment user (`homelab-deploy`)
- **Passwordless Sudo**: Configured for both users to enable automated privilege escalation
- **Comprehensive Validation**: Automated testing of all authentication components

### Architecture

```
┌─────────────────┐    SSH Key Auth    ┌──────────────────┐
│   Control Node  │ ──────────────────→│   Target Host    │
│   (Ansible)     │                    │  (homelab-server)│
└─────────────────┘                    └──────────────────┘
                                              │
                                              ├── kang (primary user)
                                              │   └── Passwordless sudo
                                              └── homelab-deploy (automation user)
                                                  └── Passwordless sudo
```

## Ansible Configuration

### ansible.cfg

Located at: `ansible/ansible.cfg`

```ini
[defaults]
host_key_checking = False           # Disable SSH host key verification
inventory = inventory/hosts.yml     # Default inventory location
remote_user = kang                  # Default SSH user
timeout = 30                        # Connection timeout
gathering = smart                   # Smart fact gathering
fact_caching = memory              # Cache facts in memory
stdout_callback = default          # Standard output format
stderr_callback = default          # Standard error format
deprecation_warnings = False       # Suppress deprecation warnings
force_color = True                 # Enable colored output

[inventory]
enable_plugins = yaml              # Enable YAML inventory plugin

[ssh_connection]
ssh_args = -C -o ControlMaster=auto -o ControlPersist=60s
pipelining = True                  # Enable SSH pipelining for performance
control_path = ~/.ansible/cp/%%h-%%p-%%r

[privilege_escalation]
become = False                     # Don't become by default (security)
become_method = sudo               # Use sudo for privilege escalation
become_ask_pass = False           # Don't prompt for sudo password
```

### Key Configuration Decisions

- **`host_key_checking = False`**: Disabled for homelab environment to avoid interactive prompts
- **`become = False`**: Security-first approach requiring explicit privilege escalation
- **`pipelining = True`**: Improves performance by reducing SSH connections
- **Smart fact gathering**: Optimizes playbook execution speed

## User Authentication Setup

### Primary User: kang

The primary user `kang` serves as the main administrative account:

- **SSH Access**: Ed25519 key-based authentication
- **Sudo Privileges**: Full passwordless sudo access
- **Home Directory**: `/home/kang`
- **SSH Key Location**: `~/.ssh/id_ed25519`

### Deployment User: homelab-deploy

The deployment user `homelab-deploy` is designed specifically for automated operations:

- **Purpose**: Dedicated automation account
- **SSH Access**: Generated Ed25519 key pair
- **Sudo Privileges**: Full passwordless sudo access
- **Home Directory**: `/home/homelab-deploy`
- **SSH Key Location**: `/home/homelab-deploy/.ssh/id_ed25519`

### Inventory Configuration

Located at: `inventory/hosts.yml`

```yaml
homelab-server:
  ansible_host: 192.168.16.26
  ansible_user: kang
  ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

## Passwordless Sudo Configuration

### Setup Script: setup-passwordless-sudo.sh

A comprehensive script that automates sudo configuration:

**Location**: `ansible/setup-passwordless-sudo.sh`

#### Key Features

- **Safety First**: Validates syntax before applying changes
- **Backup System**: Creates backups of existing configurations
- **User Validation**: Ensures target user exists before configuration
- **Permission Management**: Sets proper file permissions (440)
- **Testing**: Validates sudo access after configuration

#### Usage

```bash
# Setup for default user (kang)
sudo ./setup-passwordless-sudo.sh

# Setup for specific user
sudo ./setup-passwordless-sudo.sh homelab-deploy
```

#### Generated Configuration

The script creates `/etc/sudoers.d/<username>-ansible` with:

```bash
# Sudoers configuration for <username> - Ansible automation
# Created by setup-passwordless-sudo.sh on <date>
# This file allows passwordless sudo for ALL commands needed by Ansible
# Appropriate for homelab automation environment

<username> ALL=(ALL) NOPASSWD: ALL
```

#### Script Safety Features

1. **Root Validation**: Ensures script runs with root privileges
2. **User Existence Check**: Verifies target user exists
3. **Syntax Validation**: Uses `visudo -c` to validate configuration
4. **Backup Creation**: Automatic backup of existing configurations
5. **Rollback Capability**: Restores backup if validation fails
6. **Permission Setting**: Enforces secure file permissions
7. **Access Testing**: Validates sudo functionality post-setup

## Validation Playbooks

### test-authentication.yml

**Purpose**: Basic authentication and privilege escalation testing

**Location**: `playbooks/test-authentication.yml`

#### Test Coverage

1. **SSH Connectivity**: Basic ping test to verify SSH access
2. **User Authentication**: Validates current user identity
3. **SSH Key Authentication**: Confirms passwordless SSH access
4. **Passwordless Sudo**: Tests `sudo -n` functionality
5. **Ansible Become**: Validates privilege escalation
6. **Deployment User**: Checks homelab-deploy user existence and sudo access
7. **Configuration Validation**: Verifies ansible.cfg settings

#### Usage

```bash
# Run all tests
ansible-playbook playbooks/test-authentication.yml

# Run specific test categories
ansible-playbook playbooks/test-authentication.yml --tags connectivity
ansible-playbook playbooks/test-authentication.yml --tags sudo
ansible-playbook playbooks/test-authentication.yml --tags deployment_user
```

### validate-deployment-setup.yml

**Purpose**: Comprehensive deployment readiness validation

**Location**: `playbooks/validate-deployment-setup.yml`

#### Comprehensive Test Suite

**Phase 1: SSH Key Authentication Tests**

- SSH connection verification
- Password-free authentication validation

**Phase 2: Main User Authentication & Sudo**

- User identity verification
- Passwordless sudo testing
- Ansible become functionality

**Phase 3: Deployment User Management**

- User existence checking
- Automatic user creation if missing
- SSH key generation
- Sudo configuration
- Permission validation

**Phase 4: Ansible Modules Testing**

- File operations with privilege escalation
- Copy operations with become
- Package facts gathering
- Service facts collection
- Systemd module testing

**Phase 5: Deployment Readiness Tests**

- Essential tool availability (git, curl, wget, python3)
- Network connectivity testing
- Disk space validation
- System resource checks

#### Advanced Features

- **Automated Remediation**: Creates missing users and configurations
- **Comprehensive Reporting**: Generates detailed JSON and Markdown reports
- **Error Recovery**: Handles failures gracefully with detailed error information
- **Cleanup Operations**: Removes test artifacts after completion

#### Usage

```bash
# Full validation suite
ansible-playbook playbooks/validate-deployment-setup.yml

# Phase-specific testing
ansible-playbook playbooks/validate-deployment-setup.yml --tags ssh
ansible-playbook playbooks/validate-deployment-setup.yml --tags modules
ansible-playbook playbooks/validate-deployment-setup.yml --tags readiness
```

## Usage Instructions

### Initial Setup

1. **Generate SSH Keys** (if not already present):

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
   ```

2. **Copy SSH Key to Target Host**:

   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub kang@192.168.16.26
   ```

3. **Configure Passwordless Sudo**:

   ```bash
   # On target host
   sudo ./setup-passwordless-sudo.sh kang
   sudo ./setup-passwordless-sudo.sh homelab-deploy
   ```

4. **Validate Configuration**:

   ```bash
   ansible-playbook playbooks/test-authentication.yml
   ```

### Running Tests and Deployments

#### Authentication Testing

```bash
# Quick authentication test
ansible-playbook playbooks/test-authentication.yml

# Comprehensive validation
ansible-playbook playbooks/validate-deployment-setup.yml

# Test specific components
ansible-playbook playbooks/test-authentication.yml --tags sudo,become
```

#### Deployment Operations

```bash
# Standard deployment (using validated authentication)
ansible-playbook playbooks/deploy-homelab.yml

# Deploy specific components
ansible-playbook playbooks/deploy-homelab.yml --tags k3s,metallb

# Deploy with different user (if configured)
ansible-playbook playbooks/deploy-homelab.yml -u homelab-deploy
```

#### Maintenance Operations

```bash
# Verify ongoing authentication health
ansible-playbook playbooks/test-authentication.yml --tags connectivity,sudo

# Update configurations
ansible-playbook playbooks/update-system.yml

# Check system status
ansible-playbook playbooks/system-health-check.yml
```

## Troubleshooting Guide

### Common Issues and Solutions

#### SSH Connection Failures

**Symptoms:**

- "Permission denied (publickey)"
- Connection timeouts
- Host key verification failures

**Solutions:**

```bash
# Verify SSH key is loaded
ssh-add -l

# Test SSH connection manually
ssh -i ~/.ssh/id_ed25519 kang@192.168.16.26

# Check SSH agent
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519

# Verify authorized_keys on target
cat ~/.ssh/authorized_keys  # on target host
```

#### Sudo Permission Issues

**Symptoms:**

- "sudo: a password is required"
- Permission denied errors
- Ansible become failures

**Diagnosis:**

```bash
# Test sudo manually
ssh kang@192.168.16.26 'sudo -n whoami'

# Check sudoers configuration
sudo visudo -c -f /etc/sudoers.d/kang-ansible

# Verify file permissions
ls -la /etc/sudoers.d/kang-ansible
```

**Solutions:**

```bash
# Reconfigure sudo
sudo ./setup-passwordless-sudo.sh kang

# Manual sudoers fix (if needed)
echo "kang ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/kang-ansible
sudo chmod 440 /etc/sudoers.d/kang-ansible
```

#### Ansible Configuration Issues

**Symptoms:**

- Inventory not found
- Wrong user connection attempts
- Module execution failures

**Diagnosis:**

```bash
# Verify ansible configuration
ansible-config dump

# Test inventory
ansible-inventory --list

# Check host connectivity
ansible all -m ping
```

**Solutions:**

```bash
# Verify ansible.cfg location
ansible-config view

# Test with explicit configuration
ansible-playbook -i inventory/hosts.yml playbooks/test-authentication.yml

# Debug connection issues
ansible all -m ping -vvv
```

#### User Management Issues

**Symptoms:**

- homelab-deploy user not found
- SSH key generation failures
- Home directory permission issues

**Solutions:**

```bash
# Create deployment user manually
sudo useradd -m -s /bin/bash homelab-deploy
sudo usermod -aG sudo homelab-deploy

# Generate SSH keys for deployment user
sudo -u homelab-deploy ssh-keygen -t ed25519 -f /home/homelab-deploy/.ssh/id_ed25519 -N ""

# Fix permissions
sudo chown -R homelab-deploy:homelab-deploy /home/homelab-deploy/.ssh
sudo chmod 700 /home/homelab-deploy/.ssh
sudo chmod 600 /home/homelab-deploy/.ssh/id_ed25519*
```

### Validation Failures

#### Running Diagnostics

```bash
# Basic connectivity test
ansible all -m ping

# Comprehensive validation
ansible-playbook playbooks/validate-deployment-setup.yml

# Generate detailed reports
ansible-playbook playbooks/validate-deployment-setup.yml --extra-vars "detailed_logging=true"
```

#### Interpreting Results

- **PASS**: Component working correctly
- **FAIL**: Critical issue requiring attention
- **WARN**: Non-critical issue, deployment may still work

#### Common Validation Failures

1. **SSH Key Authentication Failure**:
   - Solution: Recopy SSH keys, check permissions

2. **Sudo Permission Failure**:
   - Solution: Run setup-passwordless-sudo.sh script

3. **Network Connectivity Failure**:
   - Solution: Check firewall, DNS, routing

4. **Tool Availability Failure**:
   - Solution: Install missing packages (git, curl, wget, python3)

## Security Considerations

### SSH Security

#### Key Management

- **Use Ed25519 Keys**: More secure than RSA
- **Protect Private Keys**: Proper file permissions (600)
- **Key Rotation**: Regularly rotate SSH keys
- **Agent Forwarding**: Avoid when possible

#### Configuration Security

```bash
# Secure SSH client configuration
Host homelab-server
    HostName 192.168.16.26
    User kang
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    PubkeyAuthentication yes
    PasswordAuthentication no
```

### Sudo Security

#### Risk Assessment

- **Full Sudo Access**: Necessary for automation but increases attack surface
- **NOPASSWD Configuration**: Convenient but requires careful access control
- **User Isolation**: Separate users for different functions

#### Mitigation Strategies

1. **Network Isolation**: Homelab network segmentation
2. **Access Monitoring**: Log sudo usage
3. **Regular Audits**: Review sudo configurations
4. **Principle of Least Privilege**: Limit where possible

#### Monitoring Sudo Usage

```bash
# Monitor sudo logs
sudo tail -f /var/log/auth.log | grep sudo

# Audit sudo access
sudo -l -U kang
sudo -l -U homelab-deploy
```

### Access Control

#### User Access Matrix

| User | SSH Access | Sudo Access | Purpose | Risk Level |
|------|------------|-------------|---------|------------|
| kang | Full | Full | Administration | Medium |
| homelab-deploy | Full | Full | Automation | Medium |

#### Network Security

- **Internal Network**: 192.168.16.0/24 (homelab network)
- **Firewall Rules**: Restrict SSH access to management networks
- **VPN Access**: Consider VPN for remote management

## Best Practices

### Authentication Management

#### SSH Key Management

1. **Use Strong Keys**: Ed25519 or RSA 4096-bit minimum
2. **Unique Keys**: Different keys for different purposes
3. **Regular Rotation**: Rotate keys periodically
4. **Secure Storage**: Protect private keys with passphrases when possible

#### User Account Management

1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Regular Audits**: Review user accounts and permissions
3. **Account Lifecycle**: Disable unused accounts
4. **Documentation**: Maintain user account documentation

### Ansible Operations

#### Playbook Best Practices

1. **Idempotency**: Ensure playbooks can run multiple times safely
2. **Error Handling**: Implement proper error handling and rollback
3. **Validation**: Always validate before making changes
4. **Logging**: Maintain detailed logs of all operations

#### Security Practices

1. **Secrets Management**: Use Ansible Vault for sensitive data
2. **Variable Validation**: Validate all input variables
3. **Task Isolation**: Use appropriate privilege escalation per task
4. **Regular Updates**: Keep Ansible and modules updated

### Monitoring and Maintenance

#### Regular Validation

```bash
# Weekly authentication health check
ansible-playbook playbooks/test-authentication.yml

# Monthly comprehensive validation
ansible-playbook playbooks/validate-deployment-setup.yml

# Quarterly security audit
ansible-playbook playbooks/security-audit.yml
```

#### Log Management

```bash
# Ansible operation logs
tail -f ~/.ansible.log

# System authentication logs
sudo tail -f /var/log/auth.log

# Sudo usage logs
sudo grep sudo /var/log/auth.log | tail -20
```

#### Performance Optimization

1. **SSH Multiplexing**: Configure ControlMaster for connection reuse
2. **Fact Caching**: Enable fact caching to reduce gather time
3. **Parallel Execution**: Use appropriate forks setting
4. **Pipelining**: Enable SSH pipelining where supported

### Disaster Recovery

#### Backup Procedures

1. **SSH Keys**: Backup private keys securely
2. **Configurations**: Version control all configuration files
3. **User Accounts**: Document all user account configurations
4. **Sudo Rules**: Backup sudoers configurations

#### Recovery Procedures

1. **Key Loss**: Process for SSH key recovery/regeneration
2. **User Account Issues**: Steps to recreate user accounts
3. **Sudo Problems**: Emergency sudo access procedures
4. **Complete Rebuild**: Full authentication setup from scratch

---

## Appendix

### File Locations Reference

```
ansible/
├── ansible.cfg                          # Main Ansible configuration
├── inventory/hosts.yml                  # Inventory definition
├── setup-passwordless-sudo.sh          # Sudo setup script
├── playbooks/
│   ├── test-authentication.yml         # Basic auth testing
│   └── validate-deployment-setup.yml   # Comprehensive validation
└── AUTHENTICATION_SETUP.md             # This documentation
```

### Quick Reference Commands

```bash
# Test basic connectivity
ansible all -m ping

# Run authentication tests
ansible-playbook playbooks/test-authentication.yml

# Full deployment validation
ansible-playbook playbooks/validate-deployment-setup.yml

# Setup sudo for user
sudo ./setup-passwordless-sudo.sh <username>

# Debug connection issues
ansible all -m ping -vvv

# Check sudo configuration
sudo visudo -c

# Test SSH key authentication
ssh -i ~/.ssh/id_ed25519 kang@192.168.16.26 'whoami'
```

### Environment Variables

```bash
# Optional Ansible configuration overrides
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_REMOTE_USER=kang
export ANSIBLE_PRIVATE_KEY_FILE=~/.ssh/id_ed25519
export ANSIBLE_BECOME_ASK_PASS=False
```

---

*This document is maintained as part of the homelab infrastructure project. Last updated: Generated dynamically with validation playbooks.*
