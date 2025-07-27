# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-07-27

### Breaking Changes

- Migrate from Ansible playbooks to Helm-based deployment
- Implement rootless deployment architecture
- Replace bastion host pattern with direct secure access
- Remove deprecated deployment components and simplify configuration

### Added

- Comprehensive testing framework with issue tracking and reporting
- Deployment orchestration with privilege management
- Security-hardened rootless deployment configuration
- Enhanced validation scripts and infrastructure testing
- Private configuration repository integration
- Monitoring stack with Prometheus and AlertManager
- Backup solutions guide and implementation
- Python project structure for testing framework
- SSH readiness check with intelligent backoff
- Comprehensive documentation structure

### Fixed

- Kubernetes manifest validation issues
- Duplicate PostgreSQL configuration in Keycloak
- Rootless deployment configuration issues
- Git-tracked sensitive files cleanup
- Various script syntax and configuration issues

### Changed

- Consolidate and enhance documentation
- Update gitignore patterns for better security
- Improve deployment validation process
- Enhance test framework with code review improvements

## [0.2.0] - 2025-07-15

### Breaking Changes

- Initial migration from Ansible to Helm
- Restructure deployment architecture
- Consolidate configuration management

### Added

- Initial Helm charts for core services
- Basic testing framework
- Documentation structure
- Architecture and network documentation

### Changed

- Move from individual playbooks to Helm releases
- Centralize configuration management
- Improve deployment workflow

## [0.1.0] - 2025-07-01

### Added

- Initial project structure
- Basic Ansible playbooks
- Configuration templates
- Basic documentation
- Branch management scripts
- Environment configuration templates

[Unreleased]: https://github.com/tzervas/homelab-infra/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/tzervas/homelab-infra/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tzervas/homelab-infra/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tzervas/homelab-infra/releases/tag/v0.1.0
