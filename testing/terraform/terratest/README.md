# Terratest — Terraform module tests

Go integration tests for Terraform modules under `terraform/modules/`. Tests use [Terratest](https://terratest.gruntwork.io/) to run `init`, `plan`, and (where applicable) `apply`/`destroy` against real infrastructure.

## Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| **Go** | Yes | Match `go` version in `go.mod` (currently 1.25+) |
| **OpenTofu** or **Terraform** | Yes | OpenTofu is recommended; Terratest invokes a `terraform` binary on `PATH` (see below) |
| **kubectl** | For apply tests | Needed when tests call `terraform apply` and assert on cluster state |
| **KUBECONFIG** | For apply tests | Point at a disposable test cluster; never run apply tests against production |

Install OpenTofu:

```bash
# Linux (example) — see https://opentofu.org/docs/intro/install/
curl -fsSL https://get.opentofu.org/install-opentofu.sh | bash -s -- --install-method deb
```

Or install [HashiCorp Terraform](https://developer.hashicorp.com/terraform/install) 1.6+ if you prefer.

### OpenTofu vs Terraform binary name

Terratest defaults to the `terraform` command. If you only have OpenTofu (`tofu`), use the provided runner script (it symlinks `terraform` → `tofu` for the test run):

```bash
./run-terratest.sh
```

Alternatively, add a `terraform` shim on your `PATH`:

```bash
ln -sf "$(command -v tofu)" ~/bin/terraform
export PATH="$HOME/bin:$PATH"
```

## Quick start

From this directory:

```bash
# 1. Verify prerequisites (actionable errors if something is missing)
./check-prereqs.sh

# 2. Run all tests (plan-only tests work without a cluster)
./run-terratest.sh

# 3. Run a single test
./run-terratest.sh -run TestNetworkingModuleWithCustomConfig -v
```

Manual invocation:

```bash
go mod download
go test -v -timeout 60m ./...
```

## Test suites

| Test | Type | Cluster required |
|------|------|------------------|
| `TestNetworkingModuleWithCustomConfig` | `init` + `validate` + `plan` | No |
| `TestNetworkingModule` | `apply` + k8s assertions | Yes |
| `TestK3sClusterModule` | `apply` + output checks | Yes |

Skip cluster-dependent tests locally:

```bash
go test -v -timeout 60m -run TestNetworkingModuleWithCustomConfig ./...
```

## CI (manual dispatch only)

Terratest is **not** run by default in GitHub Actions. To run it from the **Infrastructure Testing & Validation** workflow:

1. Actions → **Infrastructure Testing & Validation** → **Run workflow**
2. Enable **Run Terratest** (`run_terratest: true`)
3. Ensure the runner has cluster credentials (`KUBECONFIG` secret) for apply tests

The workflow installs OpenTofu and runs `check-prereqs.sh` before `go test` so missing IaC tooling fails with a clear message instead of an opaque Terratest error.

## Troubleshooting

**`exec: "terraform": executable file not found in $PATH`**

Install OpenTofu/Terraform or run `./run-terratest.sh`, which handles the `tofu` → `terraform` shim.

**Tests hang or fail on `apply`**

Confirm `KUBECONFIG` targets a test cluster and that `kubectl get nodes` succeeds.

**`go mod tidy` / module errors**

```bash
go mod tidy
go mod download
```

See also: [testing/README.md](../../README.md) and [terraform/README.md](../../../terraform/README.md).