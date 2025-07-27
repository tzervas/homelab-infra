# Open Source Software Attributions

This project leverages several open source projects and tools. We gratefully acknowledge the contributions of these projects and their maintainers.

## License Compatibility Summary

This project is licensed under the MIT License and incorporates the following open source components:

- **9 Apache 2.0 licensed projects** - Fully compatible with MIT
- **1 MIT licensed project** - Fully compatible
- **3 AGPLv3 licensed projects** - Used as unmodified deployments

## Core Kubernetes Infrastructure

### k3s

- **License**: Apache License 2.0
- **Repository**: <https://github.com/k3s-io/k3s>
- **Copyright**: © Rancher Labs, Inc.
- **Usage**: Lightweight Kubernetes distribution for homelab deployment
- **CNCF Status**: Sandbox Project

### Helm

- **License**: Apache License 2.0
- **Repository**: <https://github.com/helm/helm>
- **Copyright**: © The Helm Authors
- **Usage**: Kubernetes package manager for application deployment
- **CNCF Status**: Graduated Project

### Helmfile

- **License**: MIT License
- **Repository**: <https://github.com/helmfile/helmfile>
- **Copyright**: © 2017 Robison Jacka
- **Usage**: Declarative Helm release management

## Networking and Load Balancing

### MetalLB

- **License**: Apache License 2.0
- **Repository**: <https://github.com/metallb/metallb>
- **Copyright**: © MetalLB contributors
- **Usage**: Load balancer implementation for bare metal Kubernetes clusters

### ingress-nginx

- **License**: Apache License 2.0
- **Repository**: <https://github.com/kubernetes/ingress-nginx>
- **Copyright**: © The Kubernetes Authors
- **Usage**: NGINX-based Kubernetes Ingress controller

## Certificate Management

### cert-manager

- **License**: Apache License 2.0
- **Repository**: <https://github.com/cert-manager/cert-manager>
- **Copyright**: © The cert-manager Authors
- **Usage**: Automated TLS certificate management for Kubernetes
- **CNCF Status**: Incubating Project

## Storage

### Longhorn

- **License**: Apache License 2.0
- **Repository**: <https://github.com/longhorn/longhorn>
- **Copyright**: © Rancher Labs, Inc.
- **Usage**: Distributed block storage system for Kubernetes
- **CNCF Status**: Incubating Project

## Security

### sealed-secrets (Bitnami)

- **License**: Apache License 2.0
- **Repository**: <https://github.com/bitnami-labs/sealed-secrets>
- **Copyright**: © Bitnami
- **Usage**: Encrypted Kubernetes Secret management

## Monitoring and Observability

### Prometheus

- **License**: Apache License 2.0
- **Repository**: <https://github.com/prometheus/prometheus>
- **Copyright**: © The Prometheus Authors
- **Usage**: Monitoring system and time series database
- **CNCF Status**: Graduated Project

### Grafana ⚠️

- **License**: GNU Affero General Public License v3.0 (AGPLv3)
- **Repository**: <https://github.com/grafana/grafana>
- **Copyright**: © Grafana Labs
- **Usage**: Visualization and dashboards platform
- **Note**: Used as unmodified deployment. AGPLv3 components remain separate from MIT-licensed infrastructure code.

### Loki ⚠️

- **License**: GNU Affero General Public License v3.0 (AGPLv3)
- **Repository**: <https://github.com/grafana/loki>
- **Copyright**: © Grafana Labs
- **Usage**: Log aggregation system
- **Note**: Used as unmodified deployment. AGPLv3 components remain separate from MIT-licensed infrastructure code.

### Promtail ⚠️

- **License**: GNU Affero General Public License v3.0 (AGPLv3)
- **Repository**: <https://github.com/grafana/loki> (Promtail is part of Loki)
- **Copyright**: © Grafana Labs
- **Usage**: Log collection agent
- **Note**: Used as unmodified deployment. AGPLv3 components remain separate from MIT-licensed infrastructure code.

## Helm Chart Sources

This project uses official Helm charts from the following repositories:

- **prometheus-community**: <https://github.com/prometheus-community/helm-charts>
- **grafana**: <https://github.com/grafana/helm-charts>
- **ingress-nginx**: <https://github.com/kubernetes/ingress-nginx/tree/main/charts/ingress-nginx>
- **jetstack**: <https://github.com/cert-manager/cert-manager/tree/master/deploy/charts/cert-manager>
- **metallb**: <https://github.com/metallb/metallb/tree/main/charts/metallb>
- **longhorn**: <https://github.com/longhorn/charts/tree/master/charts/longhorn>
- **sealed-secrets**: <https://github.com/bitnami-labs/sealed-secrets/tree/main/helm/sealed-secrets>

## License Compliance

### Apache 2.0 Licensed Components

For all Apache 2.0 licensed components, we include:

- Copyright notices as provided by the original authors
- Copy of the Apache 2.0 license (see `LICENSES/Apache-2.0.txt`)
- Preservation of any existing NOTICE files
- Attribution of modifications (none made to upstream components)

### MIT Licensed Components

For MIT licensed components, we include:

- Copyright notices as provided by the original authors
- Copy of the MIT license (see `LICENSES/MIT.txt`)

### AGPLv3 Licensed Components

For AGPLv3 licensed components (Grafana, Loki, Promtail):

- Used as unmodified deployments via official Helm charts
- No source code modifications made
- AGPLv3 license preserved (see `LICENSES/AGPL-3.0-REFERENCE.md`)
- These components remain separate from our MIT-licensed infrastructure code

## Cloud Native Computing Foundation (CNCF)

Several projects used in this infrastructure are part of the Cloud Native Computing Foundation:

- **Graduated Projects**: Helm, Prometheus
- **Incubating Projects**: cert-manager, Longhorn
- **Sandbox Projects**: k3s

Learn more about CNCF at: <https://www.cncf.io/>

## Additional Resources

- **License Texts**: See the `LICENSES/` directory for full license texts
- **Project Documentation**: Links to official documentation provided in individual project READMEs
- **Security Policies**: Refer to individual project repositories for security reporting procedures

## Acknowledgments

We extend our gratitude to all maintainers, contributors, and organizations behind these projects. The open source community's collaborative efforts make projects like this possible.

For questions about licensing or attributions, please open an issue in this repository.

---

*Last Updated: July 2025*
*License Verification Date: July 26, 2025*
