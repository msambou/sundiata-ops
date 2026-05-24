# Infra stuff
acr_login_server = "cloudnativeopsacr.azurecr.io"
aks_cluster_id = "/subscriptions/e11daff8-fb7e-4bbe-80f5-4aa5b9745326/resourceGroups/cloudnative-ops-rg/providers/Microsoft.ContainerService/managedClusters/cloudnative-ops-aks"
aks_cluster_name = "cloudnative-ops-aks"
get_credentials_command = "az aks get-credentials --resource-group cloudnative-ops-rg --name cloudnative-ops-aks"
resource_group_name = "cloudnative-ops-rg"

## Claude Code Best Practices

[https://code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)
## Claude AI Capabilities
* Can confidently give wrong answers. For example, I had to nudge Claude a few times before it was able to bootstrap FluxCD with the K8s cluster. At first, it told me it wasn't the clean approach to go.
* 

## Flux Reconcile
```bash
flux reconcile kustomization flux-system --with-source

kubectl get kustomizations -n flux-system --watch
kubectl get helmreleases -A --watch
```

## Build and Push Images
```bash
az acr login --name cloudnativeopsacr

# Incident Image
docker buildx build --no-cache --platform linux/amd64 \
  -t cloudnativeopsacr.azurecr.io/incident-api:latest \
  services/incident-api/ --push

# Triage Agent Image
docker buildx build --no-cache --platform linux/amd64 \
  -t cloudnativeopsacr.azurecr.io/triage-agent:latest \
  services/triage-agent/ --push
```

## View deployed microservices

Deployments are placed in the namespace, apps

```bash
kubectl get pods -n apps
```

AI Slop:
At first, I couldn't see the apps. It made me run a bunch of commands,
I copied and pasted the output to Claude and that's when it told me the namespace was in apps.

## Get Loadbalancer

```bash
kubectl get svc -n kong 

NAME                   TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)                      AGE
kong-kong-kong-admin   ClusterIP      10.0.147.78   <none>        8001/TCP,8444/TCP            27h
kong-kong-kong-proxy   LoadBalancer   10.0.13.219   20.51.70.6    80:31000/TCP,443:31115/TCP   27h
```

curl http://20.51.70.6/health

## In-Cluster Curl
```bash
kubectl run curlpod --image=curlimages/curl -it --rm --restart=Never -- \
  curl http://apps-incident-api.apps.svc.cluster.local:8000/health
```

**AI Slop**:
Claude had misconfigured Kong to use a different service name other than apps-incident-api, making the app
unreachable.

