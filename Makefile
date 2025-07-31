# Homelab Infrastructure Makefile
# Provides common tasks for managing the homelab infrastructure

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: generate-domains
generate-domains: ## Generate domains.yaml from environment configuration
	@echo "Generating domain configuration..."
	@python3 scripts/generate-domains-config.py

.PHONY: check-env
check-env: ## Check if required environment variables are set
	@echo "Checking environment configuration..."
	@if [ ! -f helm/environments/.env ]; then \
		echo "❌ Missing helm/environments/.env file"; \
		echo "   Copy helm/environments/.env.template to helm/environments/.env and update values"; \
		exit 1; \
	fi
	@echo "✅ Environment configuration found"

.PHONY: setup
setup: check-env generate-domains ## Initial setup for the project
	@echo "Setting up homelab infrastructure..."
	@echo "✅ Setup complete"

.PHONY: validate
validate: ## Validate all configurations
	@echo "Validating configurations..."
	@python3 scripts/testing/config_validator.py helm/environments/values-*.yaml
	@echo "✅ Validation complete"

.PHONY: clean
clean: ## Clean generated files
	@echo "Cleaning generated files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@echo "✅ Clean complete"

.PHONY: pre-deploy
pre-deploy: setup validate ## Run pre-deployment checks
	@echo "Running pre-deployment checks..."
	@echo "✅ Pre-deployment checks complete"

.PHONY: deploy-dev
deploy-dev: pre-deploy ## Deploy to development environment
	@echo "Deploying to development environment..."
	@./deploy-complete-homelab.sh development

.PHONY: deploy-staging
deploy-staging: pre-deploy ## Deploy to staging environment
	@echo "Deploying to staging environment..."
	@./deploy-complete-homelab.sh staging

.PHONY: deploy-prod
deploy-prod: pre-deploy ## Deploy to production environment
	@echo "⚠️  Deploying to PRODUCTION environment"
	@echo "Are you sure? [y/N]"
	@read -r response && [ "$$response" = "y" ] || (echo "Aborted"; exit 1)
	@./deploy-complete-homelab.sh production

.PHONY: test
test: ## Run all tests
	@echo "Running tests..."
	@python3 -m pytest testing/

.PHONY: lint
lint: ## Run linters
	@echo "Running linters..."
	@pre-commit run --all-files

.PHONY: format
format: ## Format code
	@echo "Formatting code..."
	@black .
	@isort .

.PHONY: update-secrets
update-secrets: ## Update secrets baseline
	@echo "Updating secrets baseline..."
	@detect-secrets scan --baseline .secrets.baseline

.PHONY: scan-secrets
scan-secrets: ## Scan for secrets
	@echo "Scanning for secrets..."
	@gitleaks detect --source=. --verbose
