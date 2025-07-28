package test

import (
	"fmt"
	"path/filepath"
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/k8s"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// TestK3sClusterModule tests the K3s cluster Terraform module
func TestK3sClusterModule(t *testing.T) {
	t.Parallel()

	// Path to the terraform module to test
	terraformDir := filepath.Join("..", "..", "..", "terraform", "modules", "k3s-cluster")

	// Set up terraform options
	terraformOptions := &terraform.Options{
		TerraformDir: terraformDir,
		Vars: map[string]interface{}{
			"cluster_name":   "test-k3s-cluster",
			"node_count":     3,
			"server_memory":  "2048",
			"agent_memory":   "1024",
			"k3s_version":    "v1.28.5+k3s1",
			"environment":    "test",
		},
		BackendConfig: map[string]interface{}{
			"path": fmt.Sprintf("terraform-test-%d.tfstate", time.Now().Unix()),
		},
		NoColor: true,
	}

	// Clean up resources with "terraform destroy" at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run "terraform init" and "terraform apply"
	terraform.InitAndApply(t, terraformOptions)

	// Test the cluster is properly configured
	testK3sClusterConfiguration(t, terraformOptions)
	testK3sClusterConnectivity(t, terraformOptions)
	testK3sClusterSecurity(t, terraformOptions)
	testK3sClusterResources(t, terraformOptions)
}

// testK3sClusterConfiguration validates basic cluster configuration
func testK3sClusterConfiguration(t *testing.T, terraformOptions *terraform.Options) {
	// Get outputs from terraform
	clusterName := terraform.Output(t, terraformOptions, "cluster_name")
	kubeconfig := terraform.Output(t, terraformOptions, "kubeconfig_content")

	assert.NotEmpty(t, clusterName, "Cluster name should not be empty")
	assert.NotEmpty(t, kubeconfig, "Kubeconfig should not be empty")

	// Test cluster name matches expected value
	expectedClusterName := terraformOptions.Vars["cluster_name"].(string)
	assert.Equal(t, expectedClusterName, clusterName, "Cluster name should match input variable")
}

// testK3sClusterConnectivity tests cluster connectivity and API server
func testK3sClusterConnectivity(t *testing.T, terraformOptions *terraform.Options) {
	kubeconfigPath := terraform.Output(t, terraformOptions, "kubeconfig_path")
	require.NotEmpty(t, kubeconfigPath, "Kubeconfig path should not be empty")

	// Create kubernetes options
	options := k8s.NewKubectlOptions("", kubeconfigPath, "default")

	// Test cluster connectivity by getting cluster info
	nodes := k8s.GetNodes(t, options)
	require.NotEmpty(t, nodes, "Should have at least one node")

	// Verify expected number of nodes
	expectedNodeCount := terraformOptions.Vars["node_count"].(int)
	assert.GreaterOrEqual(t, len(nodes), expectedNodeCount, "Should have expected number of nodes")

	// Test all nodes are ready
	for _, node := range nodes {
		k8s.WaitUntilNodeReady(t, options, node.Name, 60, 10*time.Second)
	}
}

// testK3sClusterSecurity validates security configuration
func testK3sClusterSecurity(t *testing.T, terraformOptions *terraform.Options) {
	kubeconfigPath := terraform.Output(t, terraformOptions, "kubeconfig_path")
	options := k8s.NewKubectlOptions("", kubeconfigPath, "default")

	// Test RBAC is enabled
	_, err := k8s.RunKubectlAndGetOutputE(t, options, "auth", "can-i", "get", "pods")
	require.NoError(t, err, "RBAC should be properly configured")

	// Test network policies are supported
	testNetworkPolicy := &k8s.NetworkPolicy{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-network-policy",
			Namespace: "default",
		},
		Spec: k8s.NetworkPolicySpec{
			PodSelector: metav1.LabelSelector{},
			PolicyTypes: []k8s.PolicyType{k8s.PolicyTypeIngress},
		},
	}

	k8s.KubectlApplyFromString(t, options, k8s.MarshalResource(t, testNetworkPolicy))
	defer k8s.KubectlDeleteFromString(t, options, k8s.MarshalResource(t, testNetworkPolicy))

	// Verify network policy was created
	k8s.WaitUntilNetworkPolicyAvailable(t, options, "test-network-policy", "default", 30, 5*time.Second)
}

// testK3sClusterResources validates cluster resources and system pods
func testK3sClusterResources(t *testing.T, terraformOptions *terraform.Options) {
	kubeconfigPath := terraform.Output(t, terraformOptions, "kubeconfig_path")
	options := k8s.NewKubectlOptions("", kubeconfigPath, "kube-system")

	// Test essential system pods are running
	essentialPods := []string{
		"coredns",
		"local-path-provisioner",
		"metrics-server",
	}

	for _, podPrefix := range essentialPods {
		pods := k8s.ListPods(t, options, metav1.ListOptions{
			LabelSelector: fmt.Sprintf("app=%s", podPrefix),
		})

		assert.NotEmpty(t, pods, fmt.Sprintf("Should have %s pods running", podPrefix))

		for _, pod := range pods {
			k8s.WaitUntilPodAvailable(t, options, pod.Name, 30, 5*time.Second)
		}
	}

	// Test service accounts are properly configured
	serviceAccounts := k8s.ListServiceAccounts(t, options, metav1.ListOptions{})
	assert.NotEmpty(t, serviceAccounts, "Should have service accounts in kube-system namespace")

	// Test persistent volume support
	storageClasses := k8s.ListStorageClasses(t, options, metav1.ListOptions{})
	assert.NotEmpty(t, storageClasses, "Should have at least one storage class available")
}

// TestK3sClusterHelmIntegration tests Helm integration with the cluster
func TestK3sClusterHelmIntegration(t *testing.T) {
	t.Parallel()

	terraformDir := filepath.Join("..", "..", "..", "terraform", "modules", "k3s-cluster")

	terraformOptions := &terraform.Options{
		TerraformDir: terraformDir,
		Vars: map[string]interface{}{
			"cluster_name":   "test-k3s-helm-cluster",
			"node_count":     2,
			"server_memory":  "2048",
			"agent_memory":   "1024",
			"k3s_version":    "v1.28.5+k3s1",
			"environment":    "test",
		},
		BackendConfig: map[string]interface{}{
			"path": fmt.Sprintf("terraform-helm-test-%d.tfstate", time.Now().Unix()),
		},
		NoColor: true,
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	kubeconfigPath := terraform.Output(t, terraformOptions, "kubeconfig_path")
	options := k8s.NewKubectlOptions("", kubeconfigPath, "default")

	// Test Helm Tiller is not installed (Helm 3)
	_, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "deployment", "tiller-deploy", "-n", "kube-system")
	assert.Error(t, err, "Tiller should not be installed in Helm 3 environment")

	// Test that Helm can be used to install charts
	// This would typically involve using helm commands directly
	// For now, we validate the cluster is ready for Helm installations
	nodes := k8s.GetNodes(t, options)
	for _, node := range nodes {
		k8s.WaitUntilNodeReady(t, options, node.Name, 60, 10*time.Second)
	}
}

// TestK3sClusterUpgrade tests cluster upgrade scenarios
func TestK3sClusterUpgrade(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping upgrade test in short mode")
	}

	t.Parallel()

	terraformDir := filepath.Join("..", "..", "..", "terraform", "modules", "k3s-cluster")

	// Initial cluster with older version
	terraformOptions := &terraform.Options{
		TerraformDir: terraformDir,
		Vars: map[string]interface{}{
			"cluster_name":   "test-k3s-upgrade-cluster",
			"node_count":     2,
			"server_memory":  "2048",
			"agent_memory":   "1024",
			"k3s_version":    "v1.27.8+k3s1", // Older version
			"environment":    "test",
		},
		BackendConfig: map[string]interface{}{
			"path": fmt.Sprintf("terraform-upgrade-test-%d.tfstate", time.Now().Unix()),
		},
		NoColor: true,
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	kubeconfigPath := terraform.Output(t, terraformOptions, "kubeconfig_path")
	options := k8s.NewKubectlOptions("", kubeconfigPath, "default")

	// Verify initial version
	serverVersion := k8s.GetKubernetesClusterVersion(t, options)
	assert.Contains(t, serverVersion, "v1.27", "Initial version should be v1.27")

	// Update to newer version
	terraformOptions.Vars["k3s_version"] = "v1.28.5+k3s1"
	terraform.Apply(t, terraformOptions)

	// Wait for upgrade to complete
	time.Sleep(2 * time.Minute)

	// Verify upgrade
	newServerVersion := k8s.GetKubernetesClusterVersion(t, options)
	assert.Contains(t, newServerVersion, "v1.28", "Version should be upgraded to v1.28")

	// Verify cluster is still functional
	nodes := k8s.GetNodes(t, options)
	for _, node := range nodes {
		k8s.WaitUntilNodeReady(t, options, node.Name, 120, 10*time.Second)
	}
}
