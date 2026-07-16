#!/usr/bin/env bash
# Verify Terratest prerequisites and print actionable install guidance.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
README="${SCRIPT_DIR}/README.md"

errors=()
warnings=()

require_cmd() {
  local name="$1"
  if ! command -v "$name" &>/dev/null; then
    errors+=("$name")
    return 1
  fi
  return 0
}

# Go is mandatory for all tests.
if ! require_cmd go; then
  :
fi

# Terratest shells out to a terraform-compatible CLI.
iac_binary=""
if command -v terraform &>/dev/null; then
  iac_binary="terraform ($(command -v terraform))"
elif command -v tofu &>/dev/null; then
  iac_binary="tofu ($(command -v tofu)) — use run-terratest.sh or a terraform shim on PATH"
  warnings+=("OpenTofu is installed as 'tofu' but Terratest expects 'terraform' on PATH unless you use ./run-terratest.sh")
else
  errors+=("opentofu or terraform")
fi

# kubectl is required for tests that apply and assert on cluster state.
if ! command -v kubectl &>/dev/null; then
  warnings+=("kubectl not found — plan-only tests work; apply tests (TestNetworkingModule, TestK3sClusterModule) need kubectl + KUBECONFIG")
fi

if [[ ${#errors[@]} -gt 0 ]]; then
  echo "ERROR: Terratest prerequisites missing: ${errors[*]}" >&2
  echo "" >&2
  echo "Install OpenTofu (recommended):" >&2
  echo "  https://opentofu.org/docs/intro/install/" >&2
  echo "" >&2
  echo "Or HashiCorp Terraform 1.6+:" >&2
  echo "  https://developer.hashicorp.com/terraform/install" >&2
  echo "" >&2
  echo "Then run from ${SCRIPT_DIR}:" >&2
  echo "  ./check-prereqs.sh" >&2
  echo "  ./run-terratest.sh" >&2
  echo "" >&2
  echo "Full documentation: ${README}" >&2
  exit 1
fi

echo "Terratest prerequisites OK."
echo "  Go:       $(go version)"
echo "  IaC CLI:  ${iac_binary}"

if [[ ${#warnings[@]} -gt 0 ]]; then
  echo ""
  echo "Warnings:"
  for w in "${warnings[@]}"; do
    echo "  - ${w}"
  done
fi