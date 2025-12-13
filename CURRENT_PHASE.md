# Current Phase: Docker/Compose PoC/MVP

## Overview

This document clarifies the **current development phase** and distinguishes it from future enhancements documented elsewhere in the repository.

### ⚠️ Important Clarification

Much of the existing documentation references K3s/Kubernetes infrastructure. **These are future enhancements** planned after the current PoC/MVP phase is complete and validated.

## Current Phase: PoC/MVP (Active Development)

**Technology Stack:**
- Docker and Docker Compose for service orchestration
- Python for deployment automation and orchestration
- Shell/Bash scripts for setup and helper utilities
- YAML-based configuration management

**NOT currently using:**
- ❌ K3s or any Kubernetes distribution
- ❌ kubectl, Helm, or Kubernetes-specific tools
- ❌ MetalLB, Ingress controllers, or K8s networking
- ❌ Kubernetes manifests, namespaces, or pods

## Services to Deploy (Docker Compose)

### Core Services
1. **Keycloak** - Authentication and identity management
2. **OAuth2-Proxy** - Authentication proxy for services
3. **PostgreSQL** - Database for Keycloak and other services

### Monitoring Stack
4. **Prometheus** - Metrics collection and alerting
5. **Grafana** - Visualization and dashboards
6. **AlertManager** - Alert routing and management

### Development Tools
7. **GitLab** - Source control and CI/CD
8. **JupyterLab** - Interactive development environment
9. **Ollama + Open-WebUI** - Local AI/ML tools

### Infrastructure
10. **Landing Page/Portal** - Central dashboard for accessing services
11. **Nginx** - Reverse proxy for services (if needed)

## Current Task Priorities

### Phase 1: Foundation (Immediate)
- [ ] Create Docker Compose file structure for all services
- [ ] Set up environment variable management (.env files)
- [ ] Create Python orchestration scripts for deployment
- [ ] Implement service health checking
- [ ] Basic networking between services

### Phase 2: Authentication (High Priority)
- [ ] Deploy Keycloak with PostgreSQL backend
- [ ] Configure OAuth2-Proxy integration
- [ ] Set up Keycloak realm and clients for services
- [ ] Implement SSO flow for all services
- [ ] Test authentication end-to-end

### Phase 3: Monitoring (High Priority)
- [ ] Deploy Prometheus for metrics collection
- [ ] Deploy Grafana for visualization
- [ ] Configure service discovery for Docker containers
- [ ] Create basic dashboards
- [ ] Set up alerting rules

### Phase 4: Development Tools (Medium Priority)
- [ ] Deploy GitLab with runner support
- [ ] Deploy JupyterLab with persistent storage
- [ ] Deploy Ollama + Open-WebUI
- [ ] Configure inter-service authentication

### Phase 5: Integration & Testing (Medium Priority)
- [ ] Create comprehensive deployment script
- [ ] Implement rollback mechanisms
- [ ] Add health checks and validation
- [ ] Documentation for deployment process
- [ ] Testing framework for deployed services

## File Structure (To Be Created)

```
homelab-infra/
├── docker/
│   ├── docker-compose.yml           # Main compose file
│   ├── .env.example                 # Environment template
│   ├── services/
│   │   ├── keycloak/
│   │   │   ├── docker-compose.yml
│   │   │   └── config/
│   │   ├── oauth2-proxy/
│   │   ├── monitoring/
│   │   │   ├── prometheus/
│   │   │   ├── grafana/
│   │   │   └── alertmanager/
│   │   ├── gitlab/
│   │   ├── jupyter/
│   │   └── ollama/
│   └── networks.yml                  # Docker network definitions
├── scripts/
│   ├── deploy/
│   │   ├── deploy.py                # Main deployment orchestrator
│   │   ├── setup_environment.sh     # Environment setup
│   │   └── validate.py              # Deployment validation
│   ├── configure/
│   │   ├── keycloak_setup.py       # Keycloak realm/client setup
│   │   └── oauth2_config.py         # OAuth2 proxy configuration
│   └── utilities/
│       ├── health_check.py          # Service health monitoring
│       └── logs.py                  # Log aggregation utilities
└── config/
    ├── environments/
    │   ├── development.yml
    │   ├── staging.yml
    │   └── production.yml
    └── services/
        ├── keycloak.yml
        ├── oauth2-proxy.yml
        └── monitoring.yml
```

## Migration to K3s (Future Phase)

After the Docker Compose PoC/MVP is:
1. ✅ Fully operational with all services running
2. ✅ Authentication flow working end-to-end
3. ✅ Monitoring and observability established
4. ✅ Documentation complete and validated

Then we will:
1. Design K3s migration strategy
2. Create Kubernetes manifests/Helm charts
3. Set up K3s cluster
4. Migrate services incrementally
5. Implement K8s-specific features (MetalLB, Ingress, etc.)

## Documentation Reference

### Current Phase Documentation
- **This file**: Current phase overview and tasks
- **deployment-plan.yaml**: Phased approach (Phase 1 = current)
- **README.md**: Updated to reflect Docker/Compose focus

### Future Phase Documentation (Reference Only)
- **kubernetes/**: K8s manifests (future migration targets)
- **helm/**: Helm charts (future deployment method)
- **BOOTSTRAP_ISSUES_TRACKER.md**: K8s-specific issues (future phase)
- **homelab_orchestrator/**: Contains some K8s deployment code (future)

## Getting Started

Since Docker Compose files don't exist yet, the first task is to create them based on the service requirements documented in CLAUDE_TASK_CONTEXT.md.

### Immediate Next Steps:
1. Create basic docker-compose.yml structure
2. Add Keycloak + PostgreSQL service definitions
3. Add OAuth2-Proxy service definition
4. Create Python deployment orchestrator
5. Test basic service deployment and connectivity

## Questions or Clarifications

If you encounter references to K3s, Kubernetes, Helm, kubectl, or other K8s-specific tools in the documentation, remember these are **future enhancements**. Focus on Docker Compose and Python/Shell orchestration for the current phase.
