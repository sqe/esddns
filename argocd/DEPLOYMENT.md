# ArgoCD Deployment Guide for ESDDNS Operator

This guide provides comprehensive instructions for deploying the ESDDNS Operator using ArgoCD with both Helm and Kustomize options.

## Architecture Overview

```
ArgoCD (in argocd namespace)
├── AppProject: esddns
├── Application: esddns-operator-helm       → Helm deployment
├── Application: esddns-operator-kustomize  → Kustomize deployment
├── Application: esddns-operator-helm-dev   → Development environment
└── Application: esddns-operator-helm-prod  → Production environment
```

## Quick Start

### 1. Prerequisites

- Kubernetes cluster (1.20+)
- `kubectl` configured
- `helm` (optional, for manual Helm operations)
- ArgoCD v2.4+ installed

### 2. Install ArgoCD (if not already installed)

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm install argocd argo/argo-cd -n argocd \
  --set configs.params."application.instanceLabelKey"="argocd.argoproj.io/instance"
```

### 3. Deploy ESDDNS Applications

**Option A: Deploy with Bootstrap Script**

```bash
cd argocd/bootstrap
./argocd-setup.sh
```

**Option B: Manual Deployment**

```bash
# Deploy AppProject and all applications
kubectl apply -k argocd/

# Or deploy specific applications
kubectl apply -f argocd/argocd-appproject.yaml
kubectl apply -f argocd/applications/esddns-operator-helm.yaml
```

**Option C: Deploy with Environment Overlay**

```bash
# For development
kubectl apply -k argocd/overlays/dev/

# For production
kubectl apply -k argocd/overlays/prod/
```

## Deployment Strategies

### Strategy 1: Helm-Only Deployment

Use this if you prefer Helm for all deployments.

```bash
kubectl apply -f argocd/applications/esddns-operator-helm.yaml

# Monitor the application
argocd app get esddns-operator-helm
argocd app wait esddns-operator-helm --sync
```

**Pros:**
- Simpler, single approach
- Direct values override capability
- Environment-specific values files

**Cons:**
- Less flexibility for complex overlays
- Limited patch capability

### Strategy 2: Kustomize-Only Deployment

Use this if you have complex overlays and patches.

```bash
kubectl apply -f argocd/applications/esddns-operator-kustomize.yaml

# Monitor the application
argocd app get esddns-operator-kustomize
argocd app wait esddns-operator-kustomize --sync
```

**Pros:**
- Powerful patching and overlays
- Strong community support
- Excellent for multi-environment setups

**Cons:**
- Learning curve for complex setups
- More files to manage

### Strategy 3: Dual Deployment (Dev + Prod)

Deploy different versions to different environments.

```bash
# Production with Helm
kubectl apply -f argocd/applications/esddns-operator-helm-prod.yaml

# Development with Kustomize
kubectl apply -f argocd/applications/esddns-operator-kustomize.yaml

# Monitor both
argocd app get esddns-operator-helm-prod
argocd app get esddns-operator-kustomize
```

## Configuration Management

### Helm Configuration

Update values in `helm/esddns-operator/values.yaml`:

```yaml
replicaCount: 2
image:
  repository: sqe/esddns
  tag: latest
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

For environment-specific values, use:
- `values-development.yaml` - Development overrides
- `values-production.yaml` - Production overrides

### Kustomize Configuration

Update `k8s/overlays/production/kustomization.yaml`:

```yaml
resources:
  - ../../base

images:
  - name: esddns-operator
    newTag: v1.0.0

replicas:
  - name: esddns-operator-service
    count: 3

commonLabels:
  environment: production
```

## Sync Policies

### Manual Sync (Default - Safe for Production)

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
  automated: null
  retry:
    limit: 5
```

Manual sync keeps you in control:

```bash
# Sync the application
argocd app sync esddns-operator-helm

# Sync with prune (delete removed resources)
argocd app sync esddns-operator-helm --prune

# Force sync
argocd app sync esddns-operator-helm --force
```

### Automatic Sync (Development Only)

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Once enabled, every Git commit automatically deploys to the cluster.

### Selective Sync

Sync only specific resources:

```bash
argocd app sync esddns-operator-helm --resource apps:Deployment:esddns-operator-service
```

## Monitoring and Troubleshooting

### Check Application Status

```bash
# Get application status
kubectl get application -n argocd
kubectl get application esddns-operator-helm -n argocd -o yaml

# Using ArgoCD CLI
argocd app list
argocd app get esddns-operator-helm
argocd app logs esddns-operator-helm
```

### View Deployment Status

```bash
# Check deployed resources
kubectl get all -n esddns-operator
kubectl describe deployment esddns-operator-service -n esddns-operator

# Check for errors
kubectl logs -n esddns-operator -l app=esddns-operator-service
```

### Common Issues

**Application stuck in "Progressing"**

```bash
# Sync manually
argocd app sync esddns-operator-helm --force

# Check resource conditions
kubectl describe pod -n esddns-operator
```

**Resources not being created**

```bash
# Check AppProject permissions
kubectl get appproject esddns -n argocd -o yaml

# Check application source is valid
argocd app get esddns-operator-helm --refresh
```

**Sync failure**

```bash
# Get detailed error information
argocd app get esddns-operator-helm --hard-refresh
kubectl describe application esddns-operator-helm -n argocd

# Check Git repository access
argocd repo list
```

## Access ArgoCD UI

### Port Forward

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open: https://localhost:8080
```

### Get Admin Password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

### Using Ingress (Optional)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
spec:
  ingressClassName: nginx
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

## Advanced Usage

### GitOps Workflow

1. Make changes to Git repository
2. Create pull request with updates
3. ArgoCD detects changes
4. Review in ArgoCD UI
5. Merge PR
6. ArgoCD automatically syncs (if auto-sync enabled)

### Multiple Environments

Deploy to different clusters:

```yaml
# For cluster 1 (dev)
kubectl apply -k argocd/overlays/dev/ --context dev-cluster

# For cluster 2 (prod)
kubectl apply -k argocd/overlays/prod/ --context prod-cluster
```

### Automated Upgrades

Enable automatic image tag updates with ArgoCD Image Updater:

```bash
helm install argocd-image-updater argo/argocd-image-updater -n argocd
```

Update Application with annotation:

```yaml
metadata:
  annotations:
    argocd-image-updater.argoproj.io/image-list: esddns=sqe/esddns
    argocd-image-updater.argoproj.io/esddns.update-strategy: semver~1.0
    argocd-image-updater.argoproj.io/esddns.pull-secret: github
```

### Notifications

Setup Slack/Teams notifications for sync events:

```bash
# Install ArgoCD Notifications
helm install argocd-notifications argo/argocd-notifications -n argocd
```

## Cleanup

### Remove Specific Application

```bash
kubectl delete application esddns-operator-helm -n argocd
```

### Remove All ESDDNS Applications

```bash
kubectl delete -k argocd/
```

### Full Cleanup (including ArgoCD)

```bash
kubectl delete namespace argocd
kubectl delete namespace esddns-operator
```

## Best Practices

1. **Use Kustomize for Complex Overlays** - Easier to manage multiple environments
2. **Keep Git as Source of Truth** - All changes through Git
3. **Enable Automatic Sync for Non-Prod** - Manual sync for production
4. **Use AppProject for Multi-Team** - Control access and permissions
5. **Monitor Application Health** - Set up notifications and alerts
6. **Version Control All Manifests** - Track changes in Git
7. **Use Semantic Versioning** - Tag releases consistently
8. **Test in Dev First** - Validate changes before production

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kustomize Documentation](https://kubectl.sigs.k8s.io/docs/kubectl/kustomization/)
- [ESDDNS Repository](https://github.com/sqe/esddns)
