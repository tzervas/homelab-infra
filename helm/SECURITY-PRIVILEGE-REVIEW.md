# Security Privilege Review - Homelab Infrastructure

**Review Date:** 2025-07-28  
**Scope:** All Helm charts with elevated privileges (runAsUser: 0, privileged: true)

## Summary

This document provides security justifications for all privileged containers and root user configurations found in the homelab infrastructure. Each elevated privilege has been reviewed and documented with specific business justification and mitigation strategies.

## Privilege Usage Statistics

- **Total runAsNonRoot: true configurations:** 17 (70.8% of security contexts)
- **Total runAsNonRoot: false configurations:** 7 (29.2% of security contexts)
- **Privileged containers:** 1 (Longhorn CSI driver only)

## Justified Privileged Configurations

### 1. Storage Chart (charts/storage/values.yaml)

#### Longhorn Manager (runAsUser: 0)
- **Lines:** 75, 103
- **Justification:** Required for volume lifecycle management, block device access, and host filesystem operations
- **Capabilities:** SYS_ADMIN, DAC_OVERRIDE, MKNOD (minimum required)
- **Risk Assessment:** Medium - Limited to storage operations only

#### Longhorn Driver (runAsUser: 0, privileged: true)  
- **Lines:** 104-105
- **Justification:** CSI driver requires privileged access for volume mounting, block device manipulation, and kernel module loading
- **Capabilities:** SYS_ADMIN, DAC_OVERRIDE, MKNOD, SYS_RESOURCE
- **Risk Assessment:** High - Privileged access with host volume mounting
- **Mitigation:** This is the minimum privilege level required for CSI functionality

### 2. Core Infrastructure Chart (charts/core-infrastructure/values.yaml)

#### MetalLB Speaker (runAsUser: 0)
- **Lines:** 78
- **Justification:** Network load balancer requires root for ARP/BGP operations and network interface manipulation  
- **Capabilities:** NET_ADMIN, NET_RAW, SYS_ADMIN (network operations only)
- **Risk Assessment:** Medium - Limited to network operations

### 3. Monitoring Chart (charts/monitoring/values.yaml)

#### Promtail (runAsUser: 0)
- **Lines:** 171
- **Justification:** Log collection agent requires root access to read system logs from /var/log/* and logs owned by different users
- **Capabilities:** DAC_READ_SEARCH (read-only operations)
- **Risk Assessment:** Low - Read-only access to log files

### 4. Security Baseline Chart (charts/security-baseline/values.yaml)

#### Privileged Security Context Template (runAsUser: 0)
- **Lines:** 76
- **Justification:** Template for system-level components requiring root access
- **Usage:** Only applied to components that explicitly require these privileges
- **Capabilities:** NET_ADMIN, NET_RAW, SYS_ADMIN
- **Risk Assessment:** Context-dependent - Used as template only

## Security Mitigations Applied

1. **Capability Dropping:** All privileged containers drop ALL capabilities first, then explicitly add only required ones
2. **Seccomp Profiles:** RuntimeDefault seccomp profile applied to all containers  
3. **Resource Limits:** CPU and memory limits defined for all privileged containers
4. **Minimal Scope:** Privileges granted only to specific components that require them
5. **Documentation:** Each privilege escalation includes detailed security justification

## Non-Privileged Components

The majority of components (70.8%) run as non-root users:
- Web UIs and dashboards
- Application containers  
- Database services
- Standard workloads

## Recommendations

1. **Regular Review:** Review privileged configurations quarterly
2. **Monitoring:** Implement runtime monitoring for privileged containers
3. **Alternatives:** Evaluate rootless alternatives as they mature (e.g., rootless storage drivers)
4. **Pod Security Standards:** Consider implementing restricted pod security standards where possible

## Compliance Notes

These configurations are necessary for infrastructure functionality and represent industry-standard practices for:
- Container storage interfaces (CSI)
- Load balancer controllers  
- Log collection agents
- Network infrastructure components

All privileges are documented, justified, and limited to minimum required capabilities.