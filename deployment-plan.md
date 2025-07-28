# Homelab Deployment Plan

## Current State

- Homelab server: 192.168.16.26 (user: kang)
- Network: 192.168.16.0/16
- All VMs and K3s have been cleaned up
- Fresh environment ready for deployment

## Issues to Address

1. **Network Configuration Mismatch**
   - Inventory configured for 192.168.1.x network
   - Actual network is 192.168.16.x
   - MetalLB IP range needs adjustment

2. **Deployment Options**
   - Option 1: Deploy K3s directly on bare metal (192.168.16.26)
   - Option 2: Create VM first, then deploy K3s in VM
   - Option 3: Adjust network configuration for current subnet

## Recommended Approach

1. Update network configuration to use 192.168.16.x subnet
2. Adjust MetalLB range (e.g., 192.168.16.200-192.168.16.220)
3. Start with VM deployment for testing
4. Use port forwarding for external access if needed

## Network Configuration Changes Needed

- MetalLB range: 192.168.16.200-192.168.16.220
- GitLab IP: 192.168.16.201
- Keycloak IP: 192.168.16.202
- Registry IP: 192.168.16.203
- Prometheus IP: 192.168.16.204
- Grafana IP: 192.168.16.205
