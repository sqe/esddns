# ArgoCD ESDDNS Quick Start

Get ESDDNS Operator running with ArgoCD in minutes.

## Prerequisites

- Kubernetes cluster (1.20+)
- `kubectl` configured
- ArgoCD installed (v2.4+)

## Install ArgoCD (if needed)

```bash
# Add Helm repo
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install ArgoCD
kubectl create namespace argocd
helm install argocd argo/argo-cd -n argocd
```

## Deploy to Development

```bash
cd argocd
kubectl apply -k dev/
```

This deploys:
- 1 replica
- Auto-sync enabled
- Development configuration

## Deploy to Production

```bash
cd argocd
kubectl apply -k prod/
```

This deploys:
- 3 replicas
- Manual sync only (requires approval)
- Production configuration

## Deploy Both (using bootstrap script)

```bash
cd argocd/bootstrap
./argocd-setup.sh both
```

## Check Status

```bash
# List applications
kubectl get applications -n argocd

# Get specific app status
argocd app get esddns-operator-helm-dev
argocd app get esddns-operator-helm-prod

# Watch sync progress
argocd app wait esddns-operator-helm-dev --sync
```

## Access ArgoCD UI

```bash
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

Open: https://localhost:8080

## Verify Deployment

```bash
# Check pods
kubectl get pods -n esddns-operator
kubectl get pods -n esddns-operator-dev

# Check services
kubectl get svc -n esddns-operator
kubectl get svc -n esddns-operator-dev

# View logs
kubectl logs -n esddns-operator -l app=esddns-operator-service
```

## Manual Sync (Production)

```bash
# Sync production manually
argocd app sync esddns-operator-helm-prod

# With prune (delete removed resources)
argocd app sync esddns-operator-helm-prod --prune

# Force sync
argocd app sync esddns-operator-helm-prod --force
```

## Update Configuration

### Helm Values

Edit `helm/esddns-operator/values-development.yaml` or `values-production.yaml`

Commit and push to Git. Dev will auto-sync; prod requires manual sync.

### Kustomize Overlays

Edit `k8s/overlays/development/` or `k8s/overlays/production/`

Commit and push to Git. Dev will auto-sync; prod requires manual sync.

## Cleanup

```bash
# Remove dev only
kubectl delete -k argocd/dev/

# Remove prod only
kubectl delete -k argocd/prod/

# Remove both
kubectl delete -k argocd/dev/
kubectl delete -k argocd/prod/
```

## Troubleshooting

### Application stuck in "Progressing"

```bash
argocd app sync esddns-operator-helm-dev --force
```

### Check what's different

```bash
argocd app diff esddns-operator-helm-dev
```

### See detailed error

```bash
argocd app get esddns-operator-helm-dev
kubectl describe application esddns-operator-helm-dev -n argocd
```

### View logs

```bash
argocd app logs esddns-operator-helm-dev
kubectl logs -n argocd deployment/argocd-controller-manager
```

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for advanced configuration
- Read [STRUCTURE.md](STRUCTURE.md) for architecture details
- See environment READMEs: [dev/README.md](dev/README.md), [prod/README.md](prod/README.md)
