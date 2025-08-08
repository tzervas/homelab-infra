# Test Environment Setup

This document describes how to set up your test environment for running the homelab-infra test suite.

## Environment Variables

The test suite requires certain environment variables to be set for security testing. These variables contain test values that should never be used in production.

1. Copy the template file to create your test environment file:

   ```bash
   cp .env.test.template .env.test
   ```

2. (Optional) Modify the test values in `.env.test` if you want to use different test secrets.

3. Load the environment variables before running tests:

   ```bash
   source .env.test
   ```

## Test Environment with devcontainers

If you're using VS Code with devcontainers:

1. The test environment will be automatically configured when the container starts
2. Environment variables from `.env.test` are loaded into the container environment
3. Python dependencies are managed through `uv`, our chosen package manager

## Running Tests

To run the test suite:

```bash
# Make sure you're in a Python virtual environment (if not using devcontainer)
python -m venv .venv
source .venv/bin/activate

# Install dependencies using uv
uv pip install -r requirements-dev.txt

# Run the tests
python test_mvp_deployment.py
```

## Important Notes

- The test environment variables contain dummy secrets for testing purposes only
- Never use these test values in production environments
- The `.env.test` file is git-ignored to prevent accidental commits of test secrets
- When adding new tests that require secrets, always use environment variables instead of hardcoding values
