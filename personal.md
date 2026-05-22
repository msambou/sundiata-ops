# Infra stuff
acr_login_server = "cloudnativeopsacr.azurecr.io"
aks_cluster_id = "/subscriptions/e11daff8-fb7e-4bbe-80f5-4aa5b9745326/resourceGroups/cloudnative-ops-rg/providers/Microsoft.ContainerService/managedClusters/cloudnative-ops-aks"
aks_cluster_name = "cloudnative-ops-aks"
get_credentials_command = "az aks get-credentials --resource-group cloudnative-ops-rg --name cloudnative-ops-aks"
resource_group_name = "cloudnative-ops-rg"

## Claude AI Capabilities
* Can confidently give wrong answers. For example, I had to nudge Claude a few times before it was able to bootstrap FluxCD with the K8s cluster. At first, it told me it wasn't the clean approach to go.
* 

## Flux Reconcile
```bash
flux reconcile kustomization flux-system --with-source

kubectl get kustomizations -n flux-system --watch
kubectl get helmreleases -A --watch
```

## Build and Push Image
```bash
az acr login --name cloudnativeopsacr

docker buildx build --no-cache --platform linux/amd64 \
  -t cloudnativeopsacr.azurecr.io/incident-api:latest \
  services/incident-api/ --push
```

## View deployed microservices

Deployments are placed in the namespace, apps

```bash
kubectl get pods -n apps
```

AI Slop:
At first, I couldn't see the apps. It made me run a bunch of commands,
I copied and pasted the output to Claude and that's when it told me the namespace was in apps.