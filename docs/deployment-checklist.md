# Homelab Deployment Checklist

This checklist ensures all security and deployment requirements are met for a successful rootless homelab deployment.

## Pre-Deployment Checklist

### Server Preparation

- [ ] **Server Access**: SSH access to homelab server (192.168.16.26) with sudo privileges
- [ ] **System Updates**: Server is running latest OS updates
- [ ] **Network Configuration**: Static IP and DNS configuration verified
- [ ] **Storage**: Adequate storage space available (minimum 50GB)
- [ ] **Resources**: Minimum 4GB RAM, 2 CPU cores available

### Repository Setup

- [ ] **Repository Cloned**: Latest homelab-infra repository cloned to server
- [ ] **Branch**: On correct branch (main or feature branch)
- [ ] **Dependencies**: All required tools available (git, curl, wget)

## Security Setup Checklist

### Deployment User Creation

- [ ] **Run Setup Script**: `sudo ./scripts/deployment/setup-secure-deployment.sh`
- [ ] **User Created**: homelab-deploy user exists with proper UID (1001)
- [ ] **Directory Structure**: All required directories created with correct permissions
- [ ] **SSH Configuration**: SSH keys generated and authorized_keys configured
- [ ] **Sudo Configuration**: Sudoers file created and validated
- [ ] **Docker Access**: User added to docker group with working access

### Environment Configuration

- [ ] **Environment File**: `.env` created from template with actual values
- [ ] **Credentials**: Sensitive values configured in `.credentials/`
- [ ] **File Permissions**: All credential files have 600 permissions
- [ ] **Environment Variables**: All required variables set

### Security Validation

- [ ] **Compatibility Check**: `python3 scripts/testing/rootless_compatibility.py` passes
- [ ] **Permission Tests**: `python3 scripts/testing/permission_verifier.py` passes
- [ ] **Security Contexts**: All Helm values files have security contexts
- [ ] **No Privileged Containers**: No containers running as root unnecessarily

## Infrastructure Deployment Checklist

### Core Infrastructure

- [ ] **K3s Cluster**: `./scripts/deployment/deploy-with-privileges.sh deploy k3s`
- [ ] **Cluster Healthy**: `kubectl cluster-info` shows healthy cluster
- [ ] **MetalLB**: `./scripts/deployment/deploy-with-privileges.sh deploy metallb`
- [ ] **Load Balancer Working**: IP addresses assigned from pool
- [ ] **Cert-Manager**: `./scripts/deployment/deploy-with-privileges.sh deploy cert-manager`
- [ ] **TLS Issuer**: Cluster issuer configured and working
- [ ] **Ingress Controller**: `./scripts/deployment/deploy-with-privileges.sh deploy nginx-ingress`
- [ ] **Ingress Working**: External access to services available

### Storage

- [ ] **Longhorn Deployed**: Storage system installed and configured
- [ ] **Storage Classes**: Default storage class available
- [ ] **Persistent Volumes**: Can create and mount PVCs
- [ ] **Backup Configuration**: Backup target configured (if required)

### Monitoring Stack

- [ ] **Prometheus**: Metrics collection working
- [ ] **Grafana**: Dashboard accessible with correct credentials
- [ ] **Loki**: Log aggregation working
- [ ] **Alertmanager**: Alert routing configured
- [ ] **ServiceMonitors**: All services being monitored

### Applications

- [ ] **GitLab**: `./scripts/deployment/deploy-with-privileges.sh deploy gitlab`
- [ ] **GitLab Accessible**: Can access GitLab UI and login
- [ ] **GitLab Configuration**: OIDC, SMTP, and other integrations working
- [ ] **Keycloak**: `./scripts/deployment/deploy-with-privileges.sh deploy keycloak`
- [ ] **Keycloak Accessible**: Can access Keycloak admin console
- [ ] **SSO Integration**: GitLab-Keycloak SSO working

## Post-Deployment Validation

### Security Verification

- [ ] **Security Scan**: `python3 scripts/testing/network_security.py` passes
- [ ] **No Critical Issues**: No critical security issues found
- [ ] **Pod Security**: All pods running with appropriate security contexts
- [ ] **Network Policies**: Appropriate network restrictions in place
- [ ] **RBAC**: Proper role-based access controls configured

### Functional Testing

- [ ] **Service Health**: `python3 scripts/testing/service_checker.py` passes
- [ ] **Integration Tests**: `python3 scripts/testing/integration_tester.py` passes
- [ ] **End-to-End**: Can perform complete workflows (login, git operations, etc.)
- [ ] **Monitoring**: All services showing up in monitoring dashboards
- [ ] **Logs**: Application logs flowing to Loki

### Performance Validation

- [ ] **Resource Usage**: CPU and memory usage within acceptable limits
- [ ] **Storage Performance**: Disk I/O performance adequate
- [ ] **Network Performance**: Network connectivity and latency acceptable
- [ ] **Response Times**: Application response times acceptable

## Operational Readiness

### Backup and Recovery

- [ ] **Configuration Backup**: Critical configurations backed up
- [ ] **Data Backup**: Application data backup strategy implemented
- [ ] **Recovery Procedures**: Disaster recovery procedures documented and tested
- [ ] **Backup Testing**: Backup and restore procedures validated

### Monitoring and Alerting

- [ ] **Dashboard Access**: All monitoring dashboards accessible
- [ ] **Alert Configuration**: Critical alerts configured and tested
- [ ] **Log Retention**: Log retention policies configured
- [ ] **Metrics Retention**: Metrics retention policies configured

### Documentation

- [ ] **Deployment Notes**: Deployment process documented
- [ ] **Configuration Changes**: Any customizations documented
- [ ] **Access Credentials**: Service credentials securely stored
- [ ] **Operational Procedures**: Day-to-day operations documented

## Troubleshooting Checklist

### Common Issues

- [ ] **User Creation Failed**: Check sudo permissions and system packages
- [ ] **Docker Access Failed**: Verify user in docker group, logout/login may be needed
- [ ] **Kubernetes Connection Failed**: Check k3s service status and kubeconfig
- [ ] **Permission Denied**: Verify sudo configuration and allowed commands
- [ ] **Pod Startup Failed**: Check security contexts and resource limits
- [ ] **Service Not Accessible**: Check ingress configuration and DNS

### Debug Commands

```bash
# Check deployment user setup
./scripts/deployment/setup-secure-deployment.sh --verify-only

# Test deployment prerequisites  
./scripts/deployment/deploy-with-privileges.sh check

# Run comprehensive compatibility check
python3 scripts/testing/rootless_compatibility.py --log-level DEBUG

# Verify permissions
python3 scripts/testing/permission_verifier.py --log-level DEBUG

# Check deployment status
./scripts/deployment/deploy-with-privileges.sh status

# Run complete test suite
python3 scripts/testing/test_reporter.py --output-format all --export-issues
```

## Sign-off Checklist

### Technical Validation

- [ ] **All Tests Pass**: Comprehensive test suite passes with no critical issues
- [ ] **Security Hardened**: All security contexts and policies properly applied
- [ ] **Performance Acceptable**: System performance meets requirements
- [ ] **Monitoring Active**: All monitoring and alerting systems operational

### Operational Readiness

- [ ] **Documentation Complete**: All procedures and configurations documented
- [ ] **Backup Verified**: Backup and recovery procedures tested
- [ ] **Access Configured**: All necessary access and credentials configured
- [ ] **Support Prepared**: Operational support procedures established

### Final Sign-off

- [ ] **Technical Lead Approval**: Technical implementation approved
- [ ] **Security Review**: Security configuration reviewed and approved
- [ ] **Operational Acceptance**: Operations team accepts the deployment
- [ ] **Go-Live Authorization**: Authorized for production use

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Reviewed By**: _______________
**Approved By**: _______________

## Post-Deployment Tasks

### Immediate (Day 1)

- [ ] Monitor system stability and performance
- [ ] Verify all services are accessible
- [ ] Check logs for any errors or warnings
- [ ] Validate backup processes

### Short-term (Week 1)

- [ ] Performance tuning based on actual usage
- [ ] User training and onboarding
- [ ] Documentation updates based on lessons learned
- [ ] Security audit and penetration testing

### Long-term (Month 1)

- [ ] Capacity planning review
- [ ] Disaster recovery testing
- [ ] Security patch management
- [ ] Operational process optimization
