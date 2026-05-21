# Infra stuff
acr_login_server = "cloudnativeopsacr.azurecr.io"
aks_cluster_id = "/subscriptions/e11daff8-fb7e-4bbe-80f5-4aa5b9745326/resourceGroups/cloudnative-ops-rg/providers/Microsoft.ContainerService/managedClusters/cloudnative-ops-aks"
aks_cluster_name = "cloudnative-ops-aks"
get_credentials_command = "az aks get-credentials --resource-group cloudnative-ops-rg --name cloudnative-ops-aks"
resource_group_name = "cloudnative-ops-rg"

## Claude AI Capabilities
* Can confidently give wrong answers. For example, I had to nudge Claude a few times before it was able to bootstrap FluxCD with the K8s cluster. At first, it told me it wasn't the clean approach to go.
* 