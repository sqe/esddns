# ArgoCD Applications for ESDDNS Operator

Environment-separated ArgoCD deployment configurations for the ESDDNS Operator.

## Directory Structure

```
argocd/
├── dev/                          # Development environment
│   ├── appproject.yaml
│   ├── applications/
│   │   ├── esddns-operator-helm.yaml
│   │   ├── esddns-operator-kustomize.yaml
│   │   └── kustomization.yaml
│   ├── kustomization.yaml
│   └── README.md
├── prod/                         # Production environment
│   ├── appproject.yaml
│   ├── applications/
│   │   ├── esddns-operator-helm.yaml
│   │   ├── esddns-operator-kustomize.yaml
│   │   └── kustomization.yaml
│   ├── kustomization.yaml
│   └── README.md
├── bootstrap/
│   └── argocd-setup.sh
├── README.md                     # This file
└── DEPLOYMENT.md                 # Comprehensive deployment guide
```

## Installation

### Prerequisites

- ArgoCD installed in your cluster (in `argocd` namespace)
- Git repository access to https://github.com/sqe/esddns

### Quick Start: Development

```bash
# Deploy development applications
kubectl apply -k argocd/dev/
```

### Quick Start: Production

```bash
# Deploy production applications
kubectl apply -k argocd/prod/
```

### Bootstrap All (includes setup script)

```bash
cd argocd/bootstrap
./argocd-setup.sh
```

## Environment Configurations

### Development (`argocd/dev/`)

- **Auto Sync**: Enabled (automatic prune + selfHeal)
- **Replicas**: 1
- **AppProject**: `esddns-dev`
- **Namespace**: `esddns-operator-dev`
- **Applications**:
  - `esddns-operator-helm-dev` (Helm-based)
  - `esddns-operator-kustomize-dev` (Kustomize-based)

Deploy with:
```bash
kubectl apply -k argocd/dev/
```

### Production (`argocd/prod/`)

- **Auto Sync**: Disabled (manual sync only)
- **Replicas**: 3
- **AppProject**: `esddns-prod`
- **Namespace**: `esddns-operator`
- **Applications**:
  - `esddns-operator-helm-prod` (Helm-based)
  - `esddns-operator-kustomize-prod` (Kustomize-based)

Deploy with:
```bash
kubectl apply -k argocd/prod/
```

## Syncing Applications

### Development (Auto Sync)

Changes are automatically deployed when committed to Git.

### Production (Manual Sync)

Require human approval:

```bash
# Review changes in ArgoCD UI or CLI
argocd app get esddns-operator-helm-prod

# Approve and sync manually
argocd app sync esddns-operator-helm-prod
```

## Configuration

### Helm Values

- **Dev**: Uses `values.yaml` + `values-development.yaml`
- **Prod**: Uses `values.yaml` + `values-production.yaml`

Edit in: `helm/esddns-operator/values*.yaml`

### Kustomize Overlays

- **Dev**: Uses `k8s/overlays/development`
- **Prod**: Uses `k8s/overlays/production`

Edit in: `k8s/overlays/{dev|prod}/kustomization.yaml`

## Monitoring

Check application status in ArgoCD UI:

1. Navigate to `https://your-argocd-instance`
2. Select desired application
3. View sync status and resource health

Or use CLI:

```bash
# Development
argocd app get esddns-operator-helm-dev
argocd app get esddns-operator-kustomize-dev

# Production
argocd app get esddns-operator-helm-prod
argocd app get esddns-operator-kustomize-prod
```

## Cleanup

```bash
# Remove development applications
kubectl delete -k argocd/dev/

# Remove production applications
kubectl delete -k argocd/prod/

# Remove both
kubectl delete -k argocd/dev/
kubectl delete -k argocd/prod/
```

## Next Steps

1. Commit ArgoCD files to Git repository
2. Deploy to ArgoCD: `kubectl apply -k argocd/dev/` (or prod)
3. Monitor in ArgoCD UI or CLI
4. See [DEPLOYMENT.md](DEPLOYMENT.md) for advanced usage
