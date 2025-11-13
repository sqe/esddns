# ESDDNS Operator - Production ArgoCD Deployment

ArgoCD applications for deploying ESDDNS Operator to the production environment.

## Features

- Manual sync only (no automatic sync for safety)
- 3 replicas for high availability
- Production-specific values applied
- Supports both Helm and Kustomize deployments
- Strict RBAC and resource controls

## Quick Deploy

```bash
# Deploy all prod applications
kubectl apply -k argocd/prod/

# Or deploy specific applications
kubectl apply -f argocd/prod/applications/esddns-operator-helm.yaml
```

## Applications

### esddns-operator-helm-prod
- **Type**: Helm-based deployment
- **Namespace**: esddns-operator
- **Sync**: Manual only (no prune, no selfHeal)
- **Values**: values.yaml + values-production.yaml
- **Replicas**: 3

### esddns-operator-kustomize-prod
- **Type**: Kustomize-based deployment
- **Namespace**: esddns-operator
- **Sync**: Manual only (no prune, no selfHeal)
- **Overlay**: k8s/overlays/production
- **Replicas**: 3

## Monitoring

```bash
# Check application status
argocd app get esddns-operator-helm-prod
argocd app get esddns-operator-kustomize-prod

# View logs
argocd app logs esddns-operator-helm-prod

# Sync manually (requires approval)
argocd app sync esddns-operator-helm-prod
```

## Configuration

Edit the following files to customize:

- `applications/esddns-operator-helm.yaml` - Helm application definition
- `applications/esddns-operator-kustomize.yaml` - Kustomize application definition
- `appproject.yaml` - AppProject (permissions, source repos, destinations)

## Safety Practices

⚠️ **Production Deployment Guidelines**:

1. **Manual Sync Only** - Require human approval for changes
2. **Test in Dev First** - Always validate changes in development environment
3. **Review Changes** - Review Git changes before syncing
4. **Tag Releases** - Use semantic versioning for releases
5. **Monitor Health** - Check application and resource health before syncing
6. **Plan Upgrades** - Schedule major upgrades during maintenance windows

## Change Process

1. Create feature branch with changes
2. Test in development environment
3. Create pull request for review
4. Merge to main after approval
5. Review in ArgoCD UI
6. Execute manual sync with proper authorization

## Cleanup

```bash
kubectl delete -k argocd/prod/
```
