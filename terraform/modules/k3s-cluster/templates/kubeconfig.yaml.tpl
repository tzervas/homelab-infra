apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t... # Will be populated from actual cert
    server: https://127.0.0.1:6443
  name: ${cluster_name}
contexts:
- context:
    cluster: ${cluster_name}
    user: ${cluster_name}-admin
  name: ${cluster_name}
current-context: ${cluster_name}
users:
- name: ${cluster_name}-admin
  user:
    client-certificate-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t... # Will be populated from actual cert
    client-key-data: LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0t... # Will be populated from actual key
