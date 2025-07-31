# Homelab Infrastructure - Keycloak Integration Task

## Current State Summary

### Deployed Services

1. **Keycloak** - Running at `https://auth.homelab.local` with PostgreSQL backend
2. **OAuth2-Proxy** - Running at `https://homelab.local` (2 replicas)
3. **Landing Page** - Running at `https://homelab.local` (homelab-portal namespace)
4. **Grafana** - Running at `https://grafana.homelab.local`
5. **Prometheus** - Running at `https://prometheus.homelab.local`
6. **Ollama + Open-WebUI** - Running at `https://ollama.homelab.local`
7. **JupyterLab** - Running at `https://jupyter.homelab.local`
8. **GitLab** - Running at `https://gitlab.homelab.local` (status: initializing)

### Infrastructure Details

- **Cluster**: K3s on Ubuntu
- **Load Balancer IP**: 192.168.16.100
- **Ingress Controller**: NGINX
- **Certificate Manager**: cert-manager with self-signed CA
- **All TLS certificates**: Valid and Ready state

### Current Issues to Address

1. Keycloak is not set as the default authentication gateway for homelab.local
2. OAuth2-Proxy needs proper configuration to integrate with Keycloak
3. Services need to be configured to use Keycloak for SSO
4. GitLab needs baseline configuration and ARC runner integration
5. Ollama + Open-WebUI needs baseline RAG framework setup
6. Security dashboard needs to be implemented
7. Comprehensive orchestration script needs to be created/updated

## Requirements

### 1. Authentication Flow

- When accessing `https://homelab.local`, users should be redirected to Keycloak login
- After successful authentication, redirect to the landing page
- All services should use Keycloak SSO (Single Sign-On)
- Session management across all services

### 2. Keycloak Configuration

- Create realm for homelab
- Configure clients for each service (Grafana, Prometheus, GitLab, Ollama, JupyterLab)
- Set up user groups and roles
- Configure OAuth2-Proxy as the authentication proxy

### 3. Service Integration Requirements

#### GitLab

- Configure OIDC/OAuth2 integration with Keycloak
- Create default admin user and development group
- Set up GitLab Runner (ARC) deployment
- Register runners automatically with GitLab
- Configure baseline CI/CD templates

#### Ollama + Open-WebUI

- Configure authentication through Keycloak
- Set up baseline RAG framework
- Configure example workflows and models
- Ensure proper model storage and access

#### Monitoring Services (Grafana/Prometheus)

- Configure OAuth2 authentication
- Set up proper RBAC based on Keycloak roles
- Create security dashboard for cluster auditing

#### JupyterLab

- Configure OAuth2 authentication
- Set up shared storage if needed
- Configure resource limits

### 4. Security Dashboard Requirements

- Cluster security metrics and auditing
- User access logs
- Service health monitoring
- Certificate expiration tracking
- Resource usage by authenticated users

### 5. Orchestration Script Requirements

The script should:

- Validate all prerequisites
- Deploy/update all services in correct order
- Configure Keycloak realm and clients
- Set up OAuth2-Proxy integration
- Configure each service for SSO
- Run health checks for each component
- Provide clickable links upon completion
- Handle rollback on failures

### 6. IaC Integration

- Use Terraform where applicable for infrastructure
- Use Helm charts for Kubernetes deployments
- Use Ansible for configuration management
- Ensure all configurations are version controlled

## File Locations and Structure

```
/home/vector_weight/Documents/projects/homelab/homelab-infra/
├── kubernetes/
│   ├── base/
│   │   ├── keycloak-deployment.yaml
│   │   ├── oauth2-proxy.yaml
│   │   ├── gitlab-deployment.yaml
│   │   ├── ollama-webui-deployment.yaml
│   │   └── keycloak-realm-enhanced.yaml
│   └── overlays/
├── terraform/
│   └── modules/
├── ansible/
│   └── playbooks/
├── scripts/
│   └── orchestration/
└── config/
    └── services/
```

## Expected Outcome

After running the orchestration script:

1. Access <https://homelab.local> → Redirected to Keycloak login
2. After login → Landing page with all service links
3. Click any service → Seamlessly authenticated via SSO
4. Security dashboard accessible for cluster management
5. GitLab fully configured with runners
6. Ollama + Open-WebUI with RAG framework ready
7. All health checks passing

## Git Operations

- Use `git add` for all new and modified files
- Ensure proper .gitignore for sensitive data
- Stage all changes for commit after completion
