# ESDDNS Helm Chart - Command Reference

Quick reference for common Helm chart operations.

## Validation & Testing

### Lint Chart
```bash
helm lint helm/esddns-operator/
```

### Template Rendering
```bash
# Render all templates with defaults
helm template esddns-operator helm/esddns-operator/

# Render with custom values
helm template esddns-operator helm/esddns-operator/ \
  --set gandi.apiKey=test-key \
  --set global.domain=example.com

# Save rendered templates to file
helm template esddns-operator helm/esddns-operator/ > rendered.yaml

# Validate rendered YAML
helm template esddns-operator helm/esddns-operator/ | \
  kubectl apply --dry-run=client -f -
```

### Debug Templating
```bash
# Show what values are being used
helm template esddns-operator helm/esddns-operator/ \
  --debug --values helm/esddns-operator/values.yaml

# Show specific values
helm template esddns-operator helm/esddns-operator/ \
  --show-values
```

## Installation

### Basic Install
```bash
helm install esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --create-namespace \
  --set gandi.apiKey=YOUR_API_KEY \
  --set global.domain=yourdomain.com
```

### Install with Production Values
```bash
helm install esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --create-namespace \
  -f helm/esddns-operator/values-production.yaml \
  --set gandi.apiKey=YOUR_API_KEY \
  --set global.domain=yourdomain.com
```

### Install with Development Values
```bash
helm install esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --create-namespace \
  -f helm/esddns-operator/values-development.yaml \
  --set gandi.apiKey=YOUR_API_KEY \
  --set global.domain=example.dev
```

### Dry-run Install (no changes)
```bash
helm install esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --create-namespace \
  --dry-run \
  --debug \
  --set gandi.apiKey=test-key
```

### Interactive Install
```bash
./helm/quick-install.sh
```

## Upgrade & Updates

### Upgrade Chart
```bash
helm upgrade esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --set gandi.apiKey=NEW_KEY \
  --set global.domain=newdomain.com
```

### Upgrade with New Values File
```bash
helm upgrade esddns-operator helm/esddns-operator/ \
  -f helm/esddns-operator/values-production.yaml \
  --set gandi.apiKey=NEW_KEY
```

### Upgrade (Dry-run)
```bash
helm upgrade esddns-operator helm/esddns-operator/ \
  --dry-run --debug \
  --set gandi.apiKey=test-key
```

### Rollback to Previous Release
```bash
helm rollback esddns-operator -n esddns-system
```

### Rollback to Specific Revision
```bash
helm rollback esddns-operator 1 -n esddns-system
```

## Release Management

### List Releases
```bash
helm list -n esddns-system
helm list --all-namespaces
```

### Get Release Values
```bash
helm get values esddns-operator -n esddns-system
```

### Get Release Manifest
```bash
helm get manifest esddns-operator -n esddns-system
```

### Get Release History
```bash
helm history esddns-operator -n esddns-system
```

### Get Release Notes
```bash
helm get notes esddns-operator -n esddns-system
```

### Uninstall Release
```bash
helm uninstall esddns-operator -n esddns-system
```

### Delete Namespace
```bash
kubectl delete namespace esddns-system
```

## Repository Management

### Add Repository
```bash
helm repo add esddns https://sqe.github.io/esddns/helm-repo
helm repo update
```

### List Repositories
```bash
helm repo list
```

### Search Repository
```bash
helm search repo esddns
helm search repo esddns/esddns-operator
```

### Update Repository
```bash
helm repo update esddns
```

### Remove Repository
```bash
helm repo remove esddns
```

## Packaging & Publishing

### Lint Chart
```bash
helm lint helm/esddns-operator/
```

### Package Chart
```bash
helm package helm/esddns-operator/ -d helm-repo
```

### Generate Repository Index
```bash
helm repo index helm-repo \
  --url https://sqe.github.io/esddns/helm-repo
```

### Auto Publish (Recommended)
```bash
cd helm/
./publish.sh
```

## Troubleshooting

### Check Chart Syntax
```bash
helm lint helm/esddns-operator/ --debug
```

### Check Rendered Output
```bash
helm template esddns-operator helm/esddns-operator/ \
  --debug --values helm/esddns-operator/values.yaml
```

### Compare Values
```bash
# Default values
helm template esddns-operator helm/esddns-operator/ \
  -f helm/esddns-operator/values.yaml

# Production values
helm template esddns-operator helm/esddns-operator/ \
  -f helm/esddns-operator/values-production.yaml
```

### Verify Chart Structure
```bash
helm lint helm/esddns-operator/
helm template esddns-operator helm/esddns-operator/ | head -20
```

### Check Release Status
```bash
kubectl get all -n esddns-system
kubectl describe pod -n esddns-system -l app=esddns-operator
kubectl logs -n esddns-system -l app=esddns-operator
```

## Helm Values Syntax

### Set Single Value
```bash
--set gandi.apiKey=value
```

### Set Multiple Values
```bash
--set gandi.apiKey=value,global.domain=example.com
```

### Override Entire File
```bash
--values custom-values.yaml
```

### Merge Multiple Value Files
```bash
--values values1.yaml --values values2.yaml
```

### Set Nested Values
```bash
--set daemon.resources.limits.memory=1Gi
```

### Set Array Values
```bash
--set affinity.tolerations[0].effect=NoSchedule
```

### Set JSON Values
```bash
--set-json 'affinity={"nodeAffinity":{}}'
```

## Useful Aliases

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Helm chart shortcuts
alias helm-lint='helm lint helm/esddns-operator/'
alias helm-template='helm template esddns-operator helm/esddns-operator/'
alias helm-install='helm install esddns-operator helm/esddns-operator/ --namespace esddns-system --create-namespace'
alias helm-status='helm status esddns-operator -n esddns-system'
alias helm-logs='kubectl logs -n esddns-system -l app=esddns-operator -f'
alias helm-pods='kubectl get pods -n esddns-system'

# Combine install with values
function helm-install-prod() {
  helm install esddns-operator helm/esddns-operator/ \
    -f helm/esddns-operator/values-production.yaml \
    --namespace esddns-system \
    --create-namespace \
    "$@"
}

function helm-install-dev() {
  helm install esddns-operator helm/esddns-operator/ \
    -f helm/esddns-operator/values-development.yaml \
    --namespace esddns-system \
    --create-namespace \
    "$@"
}
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy ESDDNS Operator

on:
  push:
    branches: [main]
    paths:
      - 'helm/esddns-operator/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Lint Helm Chart
        run: helm lint helm/esddns-operator/
      
      - name: Template Chart
        run: helm template esddns-operator helm/esddns-operator/ --debug
      
      - name: Install Chart
        run: |
          helm install esddns-operator helm/esddns-operator/ \
            --namespace esddns-system \
            --create-namespace \
            --set gandi.apiKey=${{ secrets.GANDI_API_KEY }}
```

## Performance Tips

### Large Deployments
```bash
# Increase timeout for large clusters
helm install esddns-operator helm/esddns-operator/ \
  --namespace esddns-system \
  --timeout 10m
```

### Parallel Operations
```bash
# Install multiple releases in parallel
helm install rel1 ./chart1 &
helm install rel2 ./chart2 &
wait
```

### Resource Optimization
```bash
# Install with minimal resources (dev)
helm install esddns-operator helm/esddns-operator/ \
  -f helm/esddns-operator/values-development.yaml
```

## Security

### Store Secrets Securely
```bash
# Using sealed-secrets
helm install esddns-operator helm/esddns-operator/ \
  -f sealed-secrets.yaml

# Using sops
helm install esddns-operator helm/esddns-operator/ \
  -f <(sops -d secrets.yaml)
```

### Validate Security
```bash
# Check RBAC
helm template esddns-operator helm/esddns-operator/ | \
  grep -A10 "kind: ClusterRole"

# Check security contexts
helm template esddns-operator helm/esddns-operator/ | \
  grep -A5 "securityContext"
```

## Additional Resources

- Helm Documentation: https://helm.sh/docs/
- Chart Best Practices: https://helm.sh/docs/chart_best_practices/
- Artifact Hub: https://artifacthub.io
- Kubernetes Docs: https://kubernetes.io/docs/

---

For more information, see:
- `helm/README.md` - Helm repository guide
- `HELM_CHART_SUMMARY.md` - Complete chart overview
- `ARTIFACT_HUB_GUIDE.md` - Publishing guide
- `helm/esddns-operator/README.md` - Chart documentation
