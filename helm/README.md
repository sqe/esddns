# ESDDNS Helm Charts

This directory contains Helm charts for deploying ESDDNS components to Kubernetes clusters.

## Charts

### esddns-operator

A complete Kubernetes operator for automated dynamic DNS updates with optimized resource usage.

**Features:**
- **Centralized IP Detection**: Single operator leader detects WAN IP once (eliminates N redundant calls)
- **Distributed DNS Updates**: All DaemonSet pods update DNS from cached ConfigMap (no network isolation issues)
- **STUN + HTTP Methods**: Dual IP detection methods with automatic fallback
- **Flask web service**: REST API for DNS queries and state inspection
- **Gandi.net API integration**: Reliable DNS record updates
- **Prometheus metrics and alerts**: Full observability
- **Cloud provider support**: AWS EKS, Google GKE, Azure AKS
- **On-premises ready**: Works with network isolation
- **Leader election**: Kopf-based distributed coordination

See [esddns-operator/README.md](esddns-operator/README.md) for detailed documentation.

## Quick Start

### 1. Install the Chart

```bash
helm install esddns-operator ./esddns-operator \
  --namespace esddns-system \
  --create-namespace \
  --set gandi.apiKey=YOUR_GANDI_API_KEY \
  --set global.domain=yourdomain.com
```

### 2. Verify Installation

```bash
kubectl get all -n esddns-system
kubectl logs -n esddns-system -l app=esddns-operator
```

### 3. Get LoadBalancer IP

```bash
kubectl get svc -n esddns-system esddns-service
```

## Development

### Lint Charts

```bash
helm lint ./esddns-operator
```

### Template Rendering

```bash
helm template esddns-operator ./esddns-operator
helm template esddns-operator ./esddns-operator -f esddns-operator/values-production.yaml
```

### Local Testing

```bash
# Install from local directory
helm install esddns-operator ./esddns-operator \
  --set gandi.apiKey=test-key

# Upgrade after changes
helm upgrade esddns-operator ./esddns-operator \
  --set gandi.apiKey=test-key

# Test with development values
helm install esddns-operator ./esddns-operator \
  -f esddns-operator/values-development.yaml \
  --set gandi.apiKey=test-key
```

## Publishing to Artifact Hub

### Prerequisites

1. GitHub account with repository access
2. Artifact Hub account (sign in with GitHub)

### Steps

1. **Ensure Chart is Valid**
   ```bash
   helm lint ./esddns-operator
   helm template ./esddns-operator --debug
   ```

2. **Package the Chart**
   ```bash
   helm package ./esddns-operator
   # Creates esddns-operator-1.0.0.tgz
   ```

3. **Create Chart Repository**
   ```bash
   mkdir helm-repo
   helm package ./esddns-operator -d helm-repo
   helm repo index helm-repo
   ```

4. **Push to GitHub**
   ```bash
   git add helm-repo/
   git commit -m "Release esddns-operator Helm chart v1.0.0"
   git push origin main
   ```

5. **Enable GitHub Pages**
   - Go to repository Settings → Pages
   - Set source to `gh-pages` branch or specific folder

6. **Register on Artifact Hub**
   - Visit https://artifacthub.io
   - Sign in with GitHub
   - Register your repository
   - Chart URL: `https://<username>.github.io/esddns/helm-repo` or similar
   - Sync your repository

### Alternative: ChartMuseum

```bash
# Run ChartMuseum locally
helm repo add chartmuseum http://localhost:8080
helm push ./esddns-operator chartmuseum

# Or use remote ChartMuseum instance
```

## Configuration

### Production Deployment

```bash
helm install esddns-operator ./esddns-operator \
  -f esddns-operator/values-production.yaml \
  --set gandi.apiKey=YOUR_KEY \
  --set global.domain=yourdomain.com
```

### Development Deployment

```bash
helm install esddns-operator ./esddns-operator \
  -f esddns-operator/values-development.yaml \
  --set gandi.apiKey=YOUR_KEY \
  --set global.domain=example.dev
```

### Custom Values

```bash
helm install esddns-operator ./esddns-operator \
  --values custom-values.yaml \
  --set gandi.apiKey=$GANDI_API_KEY
```

## Troubleshooting

### Chart Validation

```bash
# Lint chart
helm lint ./esddns-operator

# Template and validate
helm template esddns-operator ./esddns-operator | kubectl apply --dry-run=client -f -

# Detailed debug
helm install esddns-operator ./esddns-operator --debug --dry-run
```

### Common Issues

**API key not set:**
```bash
# Error: gandi.apiKey is required
# Solution:
helm upgrade esddns-operator ./esddns-operator \
  --set gandi.apiKey=YOUR_KEY
```

**Domain not found:**
```bash
# Check ConfigMap
kubectl get configmap -n esddns-system esddns-config -o yaml

# Update domain
helm upgrade esddns-operator ./esddns-operator \
  --set global.domain=newdomain.com
```

**Resources not deploying:**
```bash
# Check templates
helm template esddns-operator ./esddns-operator | kubectl apply --dry-run=client -f -

# Check RBAC
kubectl get clusterrole esddns-operator
kubectl get clusterrolebinding esddns-operator
```

## Support

- GitHub Issues: https://github.com/sqe/esddns/issues
- Documentation: https://github.com/sqe/esddns/blob/main/helm/esddns-operator/README.md

## License

MIT - See main repository LICENSE file
