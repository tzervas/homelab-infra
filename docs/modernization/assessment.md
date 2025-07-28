# Infrastructure Modernization Assessment

**Assessment Date:** December 2024  
**Project:** Homelab Infrastructure  
**Assessment Scope:** Ansible → Helm + potential Terraform migration  

## Executive Summary

This assessment analyzes the current homelab infrastructure to identify components for modernization and migration. The project has already migrated from Ansible-based deployment to Helm/Helmfile for application deployments, with Ansible retained for system-level bootstrapping. This assessment identifies opportunities for further modernization using Terraform for infrastructure management.

## Current Infrastructure Analysis

### 1. Ansible Playbooks Audit

#### 1.1 Existing Playbooks Status

**✅ Migrated to Helm (Legacy/Reference Only):**

- `deploy-gitlab.yml` → GitLab Helm chart
- `deploy-keycloak.yml` → Keycloak Helm chart  
- `deploy-cert-manager.yml` → cert-manager Helm chart
- `deploy-metallb.yml` → MetalLB Helm chart
- `deploy-monitoring.yml` → Prometheus/Grafana Helm charts
- `deploy-nginx-ingress.yml` → nginx-ingress Helm chart

**🔄 Current Active Playbooks:**

- `site.yml` - Main orchestration playbook
- `deploy-k3s.yml` / `deploy-k3s-fixed.yml` - K3s cluster installation
- `create-vm.yml` - VM creation and configuration
- `setup-deployment-user.yml` - User privilege setup
- `install-tools.yml` / `install-missing-tools.yml` - System tools installation
- `test-authentication.yml` - Authentication validation
- `validate-deployment-setup.yml` - Pre-deployment checks

#### 1.2 Components Suitable for Migration

**Infrastructure Bootstrapping (Keep in Ansible):**

- System package installation and updates
- User account and SSH key management
- Basic system configuration
- Initial K3s installation

**Infrastructure Management (Terraform Candidates):**

- VM lifecycle management
- Network configuration and IP allocation
- Storage provisioning and management
- DNS and certificate management
- Infrastructure monitoring and alerting

### 2. Helm Charts and Dependencies Analysis

#### 2.1 Current Helmfile Structure

**Repository Configuration (`helmfile.yaml`):**

```yaml
repositories:
  - prometheus-community: https://prometheus-community.github.io/helm-charts
  - grafana: https://grafana.github.io/helm-charts
  - ingress-nginx: https://kubernetes.github.io/ingress-nginx
  - jetstack: https://charts.jetstack.io
  - metallb: https://metallb.github.io/metallb
  - longhorn: https://charts.longhorn.io
  - sealed-secrets: https://bitnami-labs.github.io/sealed-secrets
```

**Release Dependencies:**

```
Core Infrastructure (Deploy First):
├── metallb (v0.14.8) - Load balancer
├── cert-manager (v1.15.3) - Certificate management
├── ingress-nginx (v4.11.2) - Ingress controller
└── sealed-secrets (v2.16.1) - Secret management

Storage Layer (Deploy Second):
└── longhorn (v1.7.1) - Distributed storage

Monitoring Stack (Deploy Last):
├── kube-prometheus-stack (v61.7.2) - Metrics collection
├── loki (v6.6.4) - Log aggregation
├── promtail (v6.16.4) - Log shipping
└── grafana (v8.4.2) - Visualization
```

#### 2.2 Chart Dependencies and Integration

**Security Dependencies:**

- cert-manager → TLS certificate lifecycle
- sealed-secrets → Encrypted secret management
- ingress-nginx → TLS termination and routing

**Storage Dependencies:**

- longhorn → Persistent volume provisioning
- All stateful applications depend on longhorn storage class

**Monitoring Dependencies:**

- kube-prometheus-stack → Base metrics infrastructure
- loki → Log aggregation backend
- promtail → Log collection from all pods
- grafana → Unified observability dashboard

### 3. Infrastructure Components for Terraform Management

#### 3.1 Current Infrastructure State

**Physical Infrastructure:**

- Homelab server: 192.168.16.26 (user: kang)
- Network: 192.168.16.0/16 subnet
- Storage: Local storage with Longhorn distributed layer

**Virtualization Layer:**

- VM creation currently handled by Ansible
- Manual IP allocation and network configuration
- Basic resource allocation without orchestration

#### 3.2 Terraform Migration Candidates

**High Priority - Infrastructure as Code:**

1. **VM Lifecycle Management**
   - VM provisioning and configuration
   - Resource allocation (CPU, memory, storage)
   - Network interface configuration
   - Automated scaling capabilities

2. **Network Infrastructure**
   - VLAN configuration and management
   - IP address pool management
   - Load balancer IP allocation
   - DNS record management

3. **Storage Infrastructure**
   - Storage pool provisioning
   - Backup storage configuration
   - Volume lifecycle management
   - Snapshot scheduling

**Medium Priority - Service Infrastructure:**

1. **Certificate Management**
   - Let's Encrypt integration
   - Internal CA certificate lifecycle
   - Certificate rotation automation
   - TLS policy enforcement

2. **Monitoring Infrastructure**
   - External monitoring endpoints
   - Alerting webhook configuration
   - Backup destination management
   - Log retention policies

**Low Priority - Application Configuration:**

1. **Application Secrets Management**
   - External secret store integration
   - Secret rotation policies
   - Access control policies

## Migration Priority Matrix

### Priority Level 1: Critical Security Infrastructure

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| cert-manager | Helm | **CRITICAL** | Required for all TLS | Low (Already Helm) |
| sealed-secrets | Helm | **HIGH** | Encrypts all secrets | Low (Already Helm) |
| ingress-nginx | Helm | **HIGH** | TLS termination point | Low (Already Helm) |
| K3s Installation | Ansible | **CRITICAL** | Cluster security foundation | Medium (System-level) |

**Deployment Frequency:** Daily to weekly  
**Recommendation:** Maintain current Helm approach, enhance with Terraform for infrastructure provisioning

### Priority Level 2: Core Infrastructure

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| MetalLB | Helm | **MEDIUM** | Network-level security | Low (Already Helm) |
| Longhorn Storage | Helm | **HIGH** | Data encryption at rest | Low (Already Helm) |
| VM Management | Ansible | **MEDIUM** | Host-level security | High (Infrastructure) |
| Network Config | Manual/Ansible | **HIGH** | Network isolation | High (Infrastructure) |

**Deployment Frequency:** Weekly to monthly  
**Recommendation:** Migrate VM and network management to Terraform

### Priority Level 3: Monitoring and Observability

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| Prometheus Stack | Helm | **MEDIUM** | Internal TLS preferred | Low (Already Helm) |
| Grafana | Helm | **MEDIUM** | HTTPS required | Low (Already Helm) |
| Loki/Promtail | Helm | **LOW** | Internal encryption | Low (Already Helm) |
| Alert Routing | Configuration | **MEDIUM** | Webhook TLS | Medium (External deps) |

**Deployment Frequency:** Monthly to quarterly  
**Recommendation:** Maintain Helm, add Terraform for external integrations

### Priority Level 4: System Management

| Component | Current State | Security Impact | TLS/mTLS Requirements | Migration Complexity |
|-----------|---------------|-----------------|----------------------|---------------------|
| System Bootstrap | Ansible | **LOW** | SSH key management | Low (Keep Ansible) |
| Tool Installation | Ansible | **LOW** | Package verification | Low (Keep Ansible) |
| User Management | Ansible | **MEDIUM** | SSH/sudo security | Low (Keep Ansible) |
| Backup Config | Manual | **HIGH** | Backup encryption | High (New implementation) |

**Deployment Frequency:** Quarterly to annually  
**Recommendation:** Keep system-level tasks in Ansible, add Terraform for backup infrastructure

## Security and Compliance Assessment

### TLS/mTLS Implementation Status

#### Current TLS Coverage

✅ **Implemented:**

- cert-manager with Let's Encrypt integration
- Ingress TLS termination for all web services
- Internal CA for cluster-internal communications
- Kubernetes API server TLS

✅ **Partially Implemented:**

- Service-to-service communication (some encrypted)
- Log shipping with TLS (configurable)
- Monitoring scrape endpoints (mixed)

⚠️ **Needs Enhancement:**

- Comprehensive mTLS between all services
- Certificate rotation automation
- Certificate transparency monitoring
- Backup data encryption in transit

#### HTTPS Requirements

- **External Services:** All require HTTPS with valid certificates
- **Internal Services:** TLS preferred, plaintext acceptable for non-sensitive
- **Admin Interfaces:** HTTPS mandatory (Grafana, Longhorn UI)
- **API Endpoints:** TLS required for external access

### Security Criticality Analysis

**Critical Security Components:**

1. **Certificate Authority Management** - Foundation for all TLS
2. **Secret Management** - Controls access to all sensitive data
3. **Network Policies** - Controls service-to-service communication
4. **RBAC Configuration** - Controls human and service account access

**High Security Components:**

1. **Storage Encryption** - Protects data at rest
2. **Ingress Security** - Controls external access
3. **Monitoring Security** - Prevents information disclosure

## Migration Recommendations

### Phase 1: Infrastructure Foundation (Terraform)

**Timeline:** 2-4 weeks  
**Scope:** Core infrastructure provisioning

**Actions:**

1. **VM Infrastructure Management**

   ```hcl
   # terraform/infrastructure/vms.tf
   resource "proxmox_vm_qemu" "homelab_nodes" {
     count = var.node_count
     name = "homelab-node-${count.index + 1}"
     # VM configuration
   }
   ```

2. **Network Infrastructure**

   ```hcl
   # terraform/infrastructure/network.tf
   resource "proxmox_vm_qemu" "metallb_pool" {
     # IP pool management for MetalLB
   }
   ```

3. **Storage Infrastructure**

   ```hcl
   # terraform/infrastructure/storage.tf
   resource "proxmox_lxc" "backup_storage" {
     # Backup storage configuration
   }
   ```

### Phase 2: Enhanced Security Infrastructure (Terraform)

**Timeline:** 2-3 weeks  
**Scope:** Certificate and secret management

**Actions:**

1. **External Certificate Management**
   - Terraform integration with DNS providers
   - Automated Let's Encrypt certificate provisioning
   - Certificate lifecycle management

2. **Backup Infrastructure**
   - Automated backup storage provisioning
   - Encryption key management
   - Backup retention policies

### Phase 3: Integration and Automation (Terraform + Helm)

**Timeline:** 1-2 weeks  
**Scope:** Workflow optimization

**Actions:**

1. **GitOps Integration**
   - Terraform Cloud/Enterprise setup
   - Automated Helm deployments
   - Infrastructure drift detection

2. **Monitoring Enhancement**
   - Infrastructure monitoring with Terraform
   - Compliance monitoring
   - Automated remediation workflows

### Phase 4: Advanced Features (Optional)

**Timeline:** 2-4 weeks  
**Scope:** Advanced automation and scaling

**Actions:**

1. **Auto-scaling Infrastructure**
   - Dynamic VM provisioning
   - Load-based resource allocation
   - Cost optimization automation

2. **Multi-environment Support**
   - Development/staging environment automation
   - Environment promotion workflows
   - Configuration drift management

## Implementation Strategy

### Current State Preservation

- **Keep Ansible for:** System bootstrapping, user management, tool installation
- **Keep Helm for:** Application deployments, Kubernetes resources
- **Add Terraform for:** Infrastructure provisioning, network management, external integrations

### Migration Approach

1. **Parallel Implementation:** Build Terraform infrastructure alongside existing Ansible
2. **Gradual Migration:** Move components one at a time to minimize disruption
3. **Validation at Each Step:** Ensure functionality before deprecating old methods
4. **Rollback Capability:** Maintain ability to return to previous state

### Risk Mitigation

- **Backup Strategy:** Full system backup before each migration phase
- **Testing Environment:** Validate all changes in isolated environment first
- **Documentation:** Comprehensive documentation of new workflows
- **Training:** Team familiarity with new tools and processes

## Conclusion

The homelab infrastructure is well-positioned for modernization with a strong foundation already in place through the Ansible-to-Helm migration. The primary opportunities for improvement lie in:

1. **Infrastructure as Code:** Terraform for VM and network management
2. **Enhanced Security:** Comprehensive TLS/mTLS and certificate lifecycle management
3. **Operational Efficiency:** Automated provisioning and configuration management
4. **Scalability:** Foundation for future growth and multi-environment support

The proposed phased approach minimizes risk while maximizing the benefits of modern infrastructure management practices. The current Helm-based application deployment strategy should be maintained as it provides excellent declarative management for Kubernetes workloads.

## Next Steps

1. **Review and Approve Assessment** - Stakeholder review of findings and recommendations
2. **Resource Planning** - Allocate time and resources for migration phases
3. **Environment Setup** - Prepare Terraform workspace and testing environment
4. **Phase 1 Implementation** - Begin with VM infrastructure management migration
5. **Iterative Improvement** - Continuous improvement based on lessons learned

---

**Assessment Prepared By:** Infrastructure Team  
**Review Date:** December 2024  
**Next Review:** Post Phase 1 completion
