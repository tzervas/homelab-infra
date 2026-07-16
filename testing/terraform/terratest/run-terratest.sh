#!/usr/bin/env bash
# Run Terratest with prerequisite checks and OpenTofu/terraform shim support.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

"${SCRIPT_DIR}/check-prereqs.sh"

# Terratest invokes "terraform" by default. Shim tofu when terraform is absent.
SHIM_DIR=""
cleanup() {
  if [[ -n "${SHIM_DIR}" && -d "${SHIM_DIR}" ]]; then
    rm -rf "${SHIM_DIR}"
  fi
}
trap cleanup EXIT

if ! command -v terraform &>/dev/null && command -v tofu &>/dev/null; then
  SHIM_DIR="$(mktemp -d)"
  ln -sf "$(command -v tofu)" "${SHIM_DIR}/terraform"
  export PATH="${SHIM_DIR}:${PATH}"
  echo "Using OpenTofu via terraform shim: ${SHIM_DIR}/terraform -> $(command -v tofu)"
fi

echo "Downloading Go modules..."
go mod download

echo "Running Terratest..."
go test -timeout 60m "$@" ./...