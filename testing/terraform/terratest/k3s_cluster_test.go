package terratest

import (
	"testing"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestK3sClusterModule(t *testing.T) {
	terraformOptions := &terraform.Options{
		TerraformDir: "../../../terraform/modules/k3s-cluster",
		Vars: map[string]interface{}{
			"cluster_name": "terratest-k3s",
			"node_count":   1,
			"environment":  "test",
		},
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	endpoint := terraform.Output(t, terraformOptions, "cluster_endpoint")
	assert.NotEmpty(t, endpoint)
}
