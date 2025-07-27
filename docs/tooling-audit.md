# Developer Tooling Configuration Audit

## Overview

This document provides a comprehensive audit of all linting and formatting tools across the three configuration files in the homelab-infra project.

## 1. Tools in `.pre-commit-config.yaml`

### Pre-commit hooks (v4.6.0)

- trailing-whitespace
- end-of-file-fixer
- check-yaml (with --unsafe for custom tags)
- check-json
- check-toml
- check-xml
- check-merge-conflict
- check-case-conflict
- check-symlinks
- check-added-large-files (--maxkb=1024)
- detect-private-key
- check-executables-have-shebangs
- check-shebang-scripts-are-executable
- mixed-line-ending (--fix=lf)

### Python Tools

- **ruff** (v0.6.9) - Python linting and formatting
  - ruff-lint with --fix and --unsafe-fixes
  - ruff-format
- **mypy** (v1.11.2) - COMMENTED OUT
  - Configured with --strict, --ignore-missing-imports
- **bandit** (1.7.10) - Security scanning
  - Output to JSON format

### Shell Tools

- **shellcheck** (v0.10.0.1) - Shell script linting
  - Excludes: SC1091, SC2034, SC2086, SC2155
- **shfmt** (v3.9.0) - COMMENTED OUT
  - Shell script formatting

### YAML/JSON Tools

- **prettier** (v4.0.0-alpha.8) - YAML/JSON/Markdown formatting
  - Excludes helm, kubernetes, ansible files
- **yamllint** (v1.35.1) - Kubernetes/Helm YAML validation
  - Relaxed mode with 120 char line length

### Security Tools

- **gitleaks** (v8.21.2) - Secret scanning
- **detect-secrets** (v1.4.0) - Secret detection with baseline

### Documentation

- **markdownlint** (v0.42.0) - Markdown linting with --fix

### Git

- **conventional-pre-commit** (v3.4.0) - Commit message linting

### Ansible

- **ansible-lint** (v24.9.2) - COMMENTED OUT
  - Ansible playbook linting with --fix

### Custom Hooks

- homelab-config-validation
- homelab-security-check
- deployment-script-validation
- helm-template-validation
- uv-dependency-check

## 2. Tools in `.trunk/trunk.yaml`

### Linters Enabled

- **checkov** (3.2.454) - Infrastructure as code scanner
- **git-diff-check** - Git diff validation
- **markdownlint** (0.45.0) - Markdown linting
- **prettier** (3.6.2) - Code formatting
- **shellcheck** (0.10.0) - Shell script linting
- **shfmt** (3.6.0) - Shell script formatting
- **tflint** (0.58.1) - Terraform linting
- **trufflehog** (3.90.2) - Secret scanning
- **yamllint** (1.37.1) - YAML linting
- **black** (24.3.0) - Python formatting
- **isort** (5.13.2) - Python import sorting
- **ruff** (0.3.4) - Python linting
- **mypy** (1.9.0) - Python type checking
- **bandit** (1.7.8) - Python security linting
- **ansible-lint** (24.2.0) - Ansible linting

### Runtimes

- go@1.21.0
- node@22.16.0
- python@3.10.8

## 3. Tools in `pyproject.toml`

### Project Dependencies

- kubernetes>=28.0.0
- requests>=2.31.0
- pyyaml>=6.0.1
- jsonschema>=4.19.0

### Dev Dependencies

- pytest>=7.4.0
- pytest-cov>=4.1.0
- ruff>=0.6.0
- mypy>=1.5.0
- pre-commit>=3.3.0
- bandit[toml]>=1.7.5
- safety>=3.0.0
- yamllint>=1.35.0
- ansible-lint>=24.9.0

### Tool Configurations

- **ruff** - Comprehensive configuration with line-length=100, many rules selected
- **mypy** - Basic configuration with python_version=3.10
- **bandit** - Excludes tests and untracked_backup
- **black** - Line-length=100, target Python 3.10
- **isort** - Profile=black, line_length=100
- **pytest** - Configured with coverage reporting
- **yamllint** - Extends relaxed with 120 char lines

## Configuration Conflicts and Overlaps

### Version Conflicts

1. **ruff**:
   - pre-commit: v0.6.9
   - trunk: 0.3.4
   - pyproject.toml: >=0.6.0

2. **mypy**:
   - pre-commit: v1.11.2
   - trunk: 1.9.0
   - pyproject.toml: >=1.5.0

3. **bandit**:
   - pre-commit: 1.7.10
   - trunk: 1.7.8
   - pyproject.toml: >=1.7.5

4. **ansible-lint**:
   - pre-commit: v24.9.2
   - trunk: 24.2.0
   - pyproject.toml: >=24.9.0

5. **prettier**:
   - pre-commit: v4.0.0-alpha.8
   - trunk: 3.6.2

6. **markdownlint**:
   - pre-commit: v0.42.0
   - trunk: 0.45.0

7. **yamllint**:
   - pre-commit: v1.35.1
   - trunk: 1.37.1
   - pyproject.toml: >=1.35.0

### Configuration Conflicts

1. **Black** is configured in both trunk and pyproject.toml but not used in pre-commit (replaced by ruff)
2. **Isort** is configured in trunk and pyproject.toml but not used in pre-commit (replaced by ruff)
3. **Shellcheck** excludes differ between pre-commit and trunk
4. **Ruff** has different rule selections between trunk and pyproject.toml

### Unique Tools

1. **Pre-commit only**: gitleaks, detect-secrets, conventional-pre-commit, custom hooks
2. **Trunk only**: checkov, tflint, trufflehog, git-diff-check
3. **Pyproject.toml only**: safety, pytest-mock, pytest-asyncio

## Recommendations

1. Consolidate Python tool configurations in pyproject.toml
2. Remove trunk configuration entirely as it duplicates pre-commit
3. Standardize tool versions across all configurations
4. Use ruff to replace black and isort
5. Enable mypy and ansible-lint in pre-commit
6. Move security scanning tools (checkov, tflint) from trunk to pre-commit if needed
