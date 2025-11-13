# ArgoCD Directory Structure

Organized separation of development and production ArgoCD configurations.

## Tree

```
argocd/
├── bootstrap/
│   └── argocd-setup.sh              # Bootstrap script for automated setup
├── dev/                              # Development environment
│   ├── appproject.yaml               # Dev AppProject with dev-specific permissions
│   ├── applications/                 # Dev applications
│   │   ├── kustomization.yaml
│   │   ├── esddns-operator-helm.yaml
│   │   └── esddns-operator-kustomize.yaml
│   ├── kustomization.yaml            # Dev root kustomization
│   └── README.md                     # Dev-specific documentation
├── prod/                             # Production environment
│   ├── appproject.yaml               # Prod AppProject with prod-specific permissions
│   ├── applications/                 # Prod applications
│   │   ├── kustomization.yaml
│   │   ├── esddns-operator-helm.yaml
│   │   └── esddns-operator-kustomize.yaml
│   ├── kustomization.yaml            # Prod root kustomization
│   └── README.md                     # Prod-specific documentation
├── README.md                         # Main documentation
├── DEPLOYMENT.md                     # Comprehensive deployment guide
└── STRUCTURE.md                      # This file
```

## File Details

### `/bootstrap/argocd-setup.sh`
Automated bootstrap script for deploying ESDDNS to ArgoCD.

**Usage:**
```bash
./argocd-setup.sh [dev|prod|both]
```

**Features:**
- Checks prerequisites (kubectl, cluster connectivity)
- Creates ArgoCD namespace
- Verifies ArgoCD installation
- Deploys specified environment(s)
- Displays applications and next steps

### `/dev/` - Development Environment

#### `appproject.yaml`
ArgoCD AppProject for development with:
- Project name: `esddns-dev`
- Allows source repos: ESDDNS repository
- Destination namespaces: `esddns-operator-dev`, `esddns-*-dev`
- Liberal RBAC for easier development

#### `applications/`
Development applications directory:

**`esddns-operator-helm.yaml`**
- Application: `esddns-operator-helm-dev`
- Deployment: Helm-based
- Replicas: 1
- Auto sync: Enabled (prune + selfHeal)
- Values: `values.yaml` + `values-development.yaml`
- Namespace: `esddns-operator-dev`

**`esddns-operator-kustomize.yaml`**
- Application: `esddns-operator-kustomize-dev`
- Deployment: Kustomize-based
- Replicas: 1
- Auto sync: Enabled (prune + selfHeal)
- Overlay: `k8s/overlays/development`
- Namespace: `esddns-operator-dev`

#### `kustomization.yaml`
Root kustomization for dev that includes:
- `appproject.yaml`
- `applications/`

Deploy with:
```bash
kubectl apply -k argocd/dev/
```

### `/prod/` - Production Environment

#### `appproject.yaml`
ArgoCD AppProject for production with:
- Project name: `esddns-prod`
- Allows source repos: ESDDNS repository (main branch only)
- Destination namespaces: `esddns-operator`, `esddns-*`
- Strict RBAC for security

#### `applications/`
Production applications directory:

**`esddns-operator-helm.yaml`**
- Application: `esddns-operator-helm-prod`
- Deployment: Helm-based
- Replicas: 3
- Auto sync: Disabled (manual only)
- Values: `values.yaml` + `values-production.yaml`
- Namespace: `esddns-operator`

**`esddns-operator-kustomize.yaml`**
- Application: `esddns-operator-kustomize-prod`
- Deployment: Kustomize-based
- Replicas: 3
- Auto sync: Disabled (manual only)
- Overlay: `k8s/overlays/production`
- Namespace: `esddns-operator`

#### `kustomization.yaml`
Root kustomization for prod that includes:
- `appproject.yaml`
- `applications/`

Deploy with:
```bash
kubectl apply -k argocd/prod/
```

## Configuration Isolation

### Dev vs Prod Differences

| Aspect | Dev | Prod |
|--------|-----|------|
| **Sync** | Automatic | Manual |
| **Prune** | Enabled | Disabled |
| **SelfHeal** | Enabled | Disabled |
| **Replicas** | 1 | 3 |
| **Values** | values-development.yaml | values-production.yaml |
| **AppProject** | esddns-dev | esddns-prod |
| **Namespace** | esddns-operator-dev | esddns-operator |
| **Permissions** | Liberal | Strict |

### Why Separate Environments?

1. **Isolation**: Changes in dev don't affect prod
2. **Different Sync Policies**: Dev auto-syncs, prod requires approval
3. **Different Scaling**: Dev runs on 1 replica, prod runs on 3
4. **Different Permissions**: Prod has stricter RBAC
5. **Clear Ownership**: Each environment has its own AppProject
6. **Easy Cleanup**: Remove entire environment with single command

## Deployment Workflows

### Deploy to Dev Only
```bash
kubectl apply -k argocd/dev/
```

### Deploy to Prod Only
```bash
kubectl apply -k argocd/prod/
```

### Deploy to Both (using bootstrap script)
```bash
cd argocd/bootstrap
./argocd-setup.sh both
```

### Manage Individual Applications
```bash
# Dev - Helm
kubectl apply -f argocd/dev/applications/esddns-operator-helm.yaml

# Dev - Kustomize
kubectl apply -f argocd/dev/applications/esddns-operator-kustomize.yaml

# Prod - Helm
kubectl apply -f argocd/prod/applications/esddns-operator-helm.yaml

# Prod - Kustomize
kubectl apply -f argocd/prod/applications/esddns-operator-kustomize.yaml
```

## Shared Resources

Both dev and prod reference the same Git repository:
- **Helm Charts**: `helm/esddns-operator/`
  - Base values: `values.yaml`
  - Dev overrides: `values-development.yaml`
  - Prod overrides: `values-production.yaml`

- **Kustomize Bases**: `k8s/base/`
  - Dev overlay: `k8s/overlays/development/`
  - Prod overlay: `k8s/overlays/production/`

## Cleanup

Remove specific environment:
```bash
# Remove dev
kubectl delete -k argocd/dev/

# Remove prod
kubectl delete -k argocd/prod/
```

Remove everything:
```bash
kubectl delete -k argocd/dev/
kubectl delete -k argocd/prod/
```

This will:
1. Delete all Applications in the environment(s)
2. Delete the AppProject(s)
3. Optionally delete deployed resources (depends on finalizer configuration)
