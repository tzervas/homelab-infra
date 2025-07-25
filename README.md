# Homelab Infrastructure

Infrastructure as Code (IaC) for managing homelab environment.

## Overview

This repository contains the infrastructure configuration for a homelab environment, using:

- Terraform for infrastructure provisioning
- Kubernetes for container orchestration
- Helm for application deployment

## Repository Structure

```
.
├── .gitignore         # Git ignore patterns
├── LICENSE           # MIT License
├── README.md         # This documentation
├── docs/            # Additional documentation
├── kubernetes/      # Kubernetes manifests
│   ├── base/       # Base configurations
│   └── overlays/   # Environment-specific overlays
├── terraform/       # Terraform configurations
│   ├── main.tf     # Main Terraform configuration
│   ├── variables.tf # Input variables
│   └── outputs.tf  # Output variables
└── helm/           # Helm charts
    └── charts/     # Custom Helm charts
```

## Getting Started

Documentation for setup and usage can be found in the [docs](./docs) directory.

## Contributing

1. Create a feature branch from `develop` using:
   ```bash
   git checkout -b feature/your-feature-name develop
   ```
2. Make your changes
3. Submit a pull request to `develop`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
