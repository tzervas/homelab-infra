# Homelab Infrastructure Documentation

Welcome to the comprehensive documentation for the refactored Homelab Infrastructure project. This documentation provides everything you need to understand, deploy, customize, and maintain your modern homelab environment with unified testing, enhanced deployment interfaces, and standardized processes.

## 📚 Documentation Overview

### 🎯 New Enhanced Documentation

- **[Comprehensive User Guide](comprehensive-user-guide.md)** - ⭐ **Complete guide to refactored homelab infrastructure**
- **[Interfaces and Process Guide](interfaces-and-processes.md)** - ⭐ **Detailed documentation of refactored interfaces and new processes**
- **[Testing Guide](testing-guide.md)** - ⭐ **Complete guide to unified testing framework and procedures**

### 🚀 Getting Started

- **[Quick Start Guide](setup/quick-start.md)** - Get your homelab running in 30 minutes
- **[Prerequisites](setup/prerequisites.md)** - System requirements and preparation
- **[Architecture Overview](setup/architecture.md)** - Understanding the system design

### ⚙️ Setup & Installation

- **[Initial Setup](setup/initial-setup.md)** - First-time installation process
- **[Network Configuration](setup/network-configuration.md)** - Network planning and setup
- **[SSH Key Setup](setup/ssh-keys.md)** - Secure authentication configuration
- **[DNS Configuration](setup/dns-setup.md)** - Domain and DNS requirements

### 🔧 Configuration Management (Unified)

- **[Unified Configuration Structure](../config/README.md)** - Consolidated configuration directory organization
- **[Consolidated Configs](../config/consolidated/README.md)** - Single source of truth for all configuration
- **[Environment Variables](configuration/environment-variables.md)** - Complete .env configuration guide
- **[Private Configuration](configuration/private-configuration.md)** - Managing secrets and private settings
- **[Helm Values](configuration/helm-values.md)** - Customizing application deployments
- **[Service Configuration](configuration/services.md)** - Individual service settings

### 🏗️ Deployment

- **[Deployment Structure](../deployments/README.md)** - Deployment directory organization and strategy
- **[Deployment Process](deployment/README.md)** - Deployment procedures and phases
- **[Scripts Documentation](../scripts/README.md)** - Automation and utility scripts
- **[VM Testing](deployment/vm-testing.md)** - Testing with virtual machines
- **[Bare Metal Deployment](deployment/bare-metal.md)** - Production deployment
- **[CI/CD Integration](deployment/cicd.md)** - Automated deployment pipelines

### 🔐 Security

- **[Bastion Host Security](security/bastion-host.md)** - Secure access patterns
- **[GPG Signing](security/gpg-signing.md)** - Commit signing and verification
- **[TLS/SSL Configuration](security/tls-ssl.md)** - Certificate management
- **[Security Best Practices](security/best-practices.md)** - Comprehensive security guide

### 🛠️ Operations

- **[Monitoring & Alerting](operations/monitoring.md)** - Prometheus and Grafana setup
- **[Backup & Recovery](operations/backup-recovery.md)** - Data protection strategies
- **[Maintenance](operations/maintenance.md)** - Regular maintenance tasks
- **[Scaling](operations/scaling.md)** - Growing your homelab

### 🔍 Troubleshooting

- **[Common Issues](troubleshooting/common-issues.md)** - Frequently encountered problems
- **[Debugging Guide](troubleshooting/debugging.md)** - Systematic troubleshooting
- **[Recovery Procedures](troubleshooting/recovery.md)** - Disaster recovery
- **[FAQ](troubleshooting/faq.md)** - Frequently asked questions

## 🎯 Quick Navigation

### New to Homelabs?

1. Read the [Architecture Overview](setup/architecture.md)
2. Check [Prerequisites](setup/prerequisites.md)
3. Follow the [Quick Start Guide](setup/quick-start.md)

### Ready to Deploy?

1. Review [Configuration Structure](../config/README.md)
2. Complete [Initial Setup](setup/initial-setup.md)
3. Configure [Environment Variables](configuration/environment-variables.md)
4. Start with [VM Testing](deployment/vm-testing.md)
5. Move to [Bare Metal Deployment](deployment/bare-metal.md)

### Need to Customize?

1. Understand [Configuration Management](../config/README.md)
2. Review [Private Configuration](configuration/private-configuration.md)
3. Modify [Helm Values](configuration/helm-values.md)
4. Adjust [Service Configuration](configuration/services.md)

### Production Operations?

1. Set up [Monitoring & Alerting](operations/monitoring.md)
2. Configure [Backup & Recovery](operations/backup-recovery.md)
3. Review [Security Best Practices](security/best-practices.md)

## 🏷️ Project Components

This homelab infrastructure includes:

- **🦊 GitLab**: Complete DevOps platform with CI/CD
- **🔐 Keycloak**: Identity and access management
- **📊 Monitoring**: Prometheus, Grafana, AlertManager
- **🌐 Ingress**: NGINX Ingress Controller with TLS
- **💾 Storage**: Longhorn distributed storage
- **🔒 Security**: cert-manager, network policies
- **⚖️ Load Balancing**: MetalLB for bare metal

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to this project.

## 📝 License

This project is licensed under multiple licenses. See [LICENSE](../LICENSE) for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/tzervas/homelab-infra/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tzervas/homelab-infra/discussions)
- **Documentation**: This comprehensive guide

## 📚 Additional Resources

### Project Structure Documentation

- **[Scripts Directory](../scripts/README.md)** - Automation and utility scripts
- **[Testing Framework](../testing/k3s-validation/README.md)** - Comprehensive testing suite
- **[Configuration Directory](../config/README.md)** - Configuration management structure
- **[Deployment Directory](../deployments/README.md)** - Deployment organization
- **[Tools Directory](../tools/README.md)** - Development and operational tools

### Project Organization

- **[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)** - Complete project structure overview
- **[Main README](../README.md)** - Project overview and quick start

---

**💡 Tip**: Use the search function in your editor or browser to quickly find specific topics in this documentation.
