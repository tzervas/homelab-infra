package terratest

import (
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/k8s"
	"github.com/gruntwork-io/terratest/modules/retry"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNetworkingModule(t *testing.T) {
	t.Parallel()

	terraformOptions := &terraform.Options{
		TerraformDir: "../../../terraform/modules/networking",
		Vars: map[string]interface{}{
			"cluster_name":     "terratest-networking",
			"environment":      "test",
			"metallb_ip_range": "192.168.100.200-192.168.100.250",
			"enable_ingress":   true,
		},
		NoColor: true,
	}

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndPlan(t, terraformOptions)
	terraform.Apply(t, terraformOptions)

	// Test MetalLB deployment
	testMetalLBDeployment(t, terraformOptions)

	// Test Ingress controller
	testIngressController(t, terraformOptions)

	// Test network policies
	testNetworkPolicies(t, terraformOptions)
}

func testMetalLBDeployment(t *testing.T, terraformOptions *terraform.Options) {
	kubectlOptions := k8s.NewKubectlOptions("", "", "metallb-system")

	// Wait for MetalLB controller to be available
	retry.DoWithRetry(t, "Wait for MetalLB controller", 30, 10*time.Second, func() (string, error) {
		return k8s.RunKubectlAndGetOutputE(t, kubectlOptions, "rollout", "status", "deployment/controller")
	})

	// Verify MetalLB speaker daemonset
	daemonSet := k8s.GetDaemonSet(t, kubectlOptions, "speaker")
	require.NotNil(t, daemonSet)
	assert.Equal(t, "speaker", daemonSet.Name)
}

func testIngressController(t *testing.T, terraformOptions *terraform.Options) {
	kubectlOptions := k8s.NewKubectlOptions("", "", "ingress-nginx")

	// Check if ingress is enabled
	ingressEnabled := terraform.Output(t, terraformOptions, "ingress_enabled")
	if ingressEnabled != "true" {
		t.Skip("Ingress controller not enabled")
	}

	// Wait for ingress controller to be available
	retry.DoWithRetry(t, "Wait for Ingress controller", 30, 10*time.Second, func() (string, error) {
		return k8s.RunKubectlAndGetOutputE(t, kubectlOptions, "rollout", "status", "deployment/ingress-nginx-controller")
	})

	// Verify ingress service has LoadBalancer IP
	service := k8s.GetService(t, kubectlOptions, "ingress-nginx-controller")
	require.NotNil(t, service)
	assert.NotEmpty(t, service.Status.LoadBalancer.Ingress)
}

func testNetworkPolicies(t *testing.T, terraformOptions *terraform.Options) {
	kubectlOptions := k8s.NewKubectlOptions("", "", "default")

	// Test network policy creation
	networkPolicyCount := terraform.Output(t, terraformOptions, "network_policy_count")
	assert.NotEmpty(t, networkPolicyCount)

	// Verify at least one network policy exists
	policies, err := k8s.RunKubectlAndGetOutputE(t, kubectlOptions, "get", "networkpolicies", "-o", "json")
	require.NoError(t, err)
	assert.Contains(t, policies, "NetworkPolicy")
}

func TestNetworkingModuleWithCustomConfig(t *testing.T) {
	t.Parallel()

	terraformOptions := &terraform.Options{
		TerraformDir: "../../../terraform/modules/networking",
		VarFiles:     []string{"../../../config/terraform/test.tfvars"},
		Vars: map[string]interface{}{
			"cluster_name": "terratest-custom-network",
			"environment":  "test",
		},
	}

	defer terraform.Destroy(t, terraformOptions)

	terraform.InitAndValidate(t, terraformOptions)
	planOutput := terraform.Plan(t, terraformOptions)

	// Verify plan includes expected resources
	assert.Contains(t, planOutput, "metallb")
	assert.Contains(t, planOutput, "ConfigMap")
}
