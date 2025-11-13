# ESDDNS Operator - Development ArgoCD Deployment

ArgoCD applications for deploying ESDDNS Operator to the development environment.

## Features

- Automatic sync enabled (deploys on every commit)
- Single replica for cost efficiency
- Development-specific values applied
- Supports both Helm and Kustomize deployments

## Quick Deploy

```bash
# Deploy all dev applications
kubectl apply -k argocd/dev/

# Or deploy specific applications
kubectl apply -f argocd/dev/applications/esddns-operator-helm.yaml
```

## Applications

### esddns-operator-helm-dev
- **Type**: Helm-based deployment
- **Namespace**: esddns-operator-dev
- **Sync**: Automatic (prune + selfHeal enabled)
- **Values**: values.yaml + values-development.yaml

### esddns-operator-kustomize-dev
- **Type**: Kustomize-based deployment
- **Namespace**: esddns-operator-dev
- **Sync**: Automatic (prune + selfHeal enabled)
- **Overlay**: k8s/overlays/development

## Monitoring

```bash
# Check application status
argocd app get esddns-operator-helm-dev
argocd app get esddns-operator-kustomize-dev

# View logs
argocd app logs esddns-operator-helm-dev

# Sync manually
argocd app sync esddns-operator-helm-dev
```

## Configuration

Edit the following files to customize:

- `applications/esddns-operator-helm.yaml` - Helm application definition
- `applications/esddns-operator-kustomize.yaml` - Kustomize application definition
- `appproject.yaml` - AppProject (permissions, source repos, destinations)

## Cleanup

```bash
kubectl delete -k argocd/dev/
```
