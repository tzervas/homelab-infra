# Dependency Relationships

## Core Infrastructure Dependencies

### Base Configuration (feat/config-base)

- Parent: main
- Dependencies: None
- Child Branches:
  - feat/config-core-loading
  - feat/config-environments
  - feat/config-domains-env

### Infrastructure Base (feat/infra-base)

- Parent: main
- Dependencies: feat/config-base
- Child Branches:
  - feat/kubernetes-base
  - feat/infra-security
  - feat/infra-apps

### Orchestration Core (feat/orch-core)

- Parent: main
- Dependencies:
  - feat/infra-base
  - feat/config-base
- Child Branches:
  - feat/orch-core-config
  - feat/orch-core-health
  - feat/orch-core-state
  - feat/orch-core-gpu

## Feature Dependencies

### GPU Infrastructure

- Primary Branch: feature/ai-ml-gpu-infrastructure
- Dependencies:
  - feat/orch-core-gpu
  - feat/infra-base

### Authentication & SSO

- Primary Branch: feature/authentication-sso
- Dependencies:
  - feat/infra-security
  - feat/config-environments

### Configuration Management

- Primary Branch: feature/configuration-management
- Dependencies:
  - feat/config-base
  - feat/config-environments
  - feat/config-services

### Core Orchestrator

- Primary Branch: feature/core-orchestrator-foundation
- Dependencies:
  - feat/orch-core
  - feat/orch-deployment
  - feat/orch-security

### Portal Interface

- Primary Branch: feature/portal-web-interface
- Dependencies:
  - feat/orch-portal
  - feat/orch-portal-manager
  - feat/config-services
