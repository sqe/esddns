# ESDDNS Helm Chart - Summary

## Overview

A production-ready Helm chart for deploying the ESDDNS Kubernetes operator to any Kubernetes cluster.

**Chart Location**: `/helm/esddns-operator/`

## What's Included

### Core Components

✅ **DaemonSet** (`daemon-deployment.yaml`)
- Runs ESDDNS operator on every node
- Monitors node IPs and updates DNS
- Exports Prometheus metrics on port 8080

✅ **Deployment** (`service-deployment.yaml`)
- Flask web service for DNS queries
- HTTP endpoints: `/` and `/raw`
- Prometheus metrics on port 51339

✅ **Service** (`service.yaml`)
- LoadBalancer type (configurable)
- Exposes port 80 → 51339
- Cloud provider integration

✅ **ConfigMap** (`configmap.yaml`)
- Complete `dns.ini` configuration
- Domain and DNS settings
- Environment variables

✅ **Secret** (`secret.yaml`)
- Gandi.net API key storage
- Referenced by pods for authentication

✅ **RBAC**
- ServiceAccount for operator
- ClusterRole with minimal permissions
- ClusterRoleBinding

✅ **Monitoring**
- ServiceMonitor for Prometheus
- PrometheusRules with 5 alerts
- Metrics endpoints configured

✅ **Pod Disruption Budget**
- High availability support
- Graceful eviction handling

## File Structure

```
helm/
├── README.md                           # Helm repository guide
├── publish.sh                          # Publishing script
└── esddns-operator/
    ├── Chart.yaml                      # Chart metadata (v1.0.0)
    ├── values.yaml                     # Default configuration
    ├── values-production.yaml           # Production overrides
    ├── values-development.yaml          # Development overrides
    ├── README.md                        # Chart documentation
    ├── CHANGELOG.md                     # Version history
    ├── artifacthub-repo.yml            # Artifact Hub metadata
    ├── templates/
    │   ├── NOTES.txt                   # Post-install messages
    │   ├── _helpers.tpl                # Template helpers
    │   ├── namespace.yaml              # Namespace creation
    │   ├── serviceaccount.yaml         # Service accounts
    │   ├── clusterrole.yaml            # RBAC roles
    │   ├── configmap.yaml              # Configuration
    │   ├── secret.yaml                 # Credentials
    │   ├── daemon-deployment.yaml      # Operator DaemonSet
    │   ├── service-deployment.yaml     # Web service Deployment
    │   ├── service.yaml                # Kubernetes Service
    │   ├── pdb.yaml                    # Pod disruption budget
    │   ├── servicemonitor.yaml         # Prometheus integration
    │   └── prometheusrule.yaml         # Alert rules
    └── (all files listed above)
```

## Quick Start

### 1. Validate Chart Locally

```bash
cd helm/

# Lint the chart
helm lint esddns-operator/

# Template rendering test
helm template esddns-operator esddns-operator/ \
  --set gandi.apiKey=test-key \
  --set global.domain=example.com
```

### 2. Install to Cluster

```bash
helm install esddns-operator esddns-operator/ \
  --namespace esddns-system \
  --create-namespace \
  --set gandi.apiKey=YOUR_GANDI_API_KEY \
  --set global.domain=yourdomain.com
```

### 3. Verify Installation

```bash
kubectl get all -n esddns-system
kubectl logs -n esddns-system -l app=esddns-operator -f
```

## Configuration Options

### Required Settings

| Option | Default | Description |
|--------|---------|-------------|
| `gandi.apiKey` | (empty) | **Required**: Gandi.net API key |
| `global.domain` | example.com | Target domain for DNS updates |

### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `global.recordName` | @ | DNS record name (@ for root) |
| `global.recordTTL` | 300 | TTL in seconds |
| `service.type` | LoadBalancer | Service type (LoadBalancer/NodePort/ClusterIP) |
| `environment` | production | Environment (production/development) |
| `monitoring.enabled` | true | Enable Prometheus monitoring |

### Advanced Options

See `values.yaml` for 30+ configuration options including:
- Resource limits and requests
- Health check parameters
- Affinity and tolerations
- Security contexts
- Pod disruption budgets
- Node selectors

## Deployment Scenarios

### AWS EKS (LoadBalancer)

```bash
helm install esddns-operator esddns-operator/ \
  --set gandi.apiKey=$GANDI_KEY \
  --set global.domain=yourdomain.com \
  --set service.type=LoadBalancer
```

Creates AWS Network Load Balancer automatically.

### Google GKE (LoadBalancer)

```bash
helm install esddns-operator esddns-operator/ \
  --set gandi.apiKey=$GANDI_KEY \
  --set global.domain=yourdomain.com \
  --set service.type=LoadBalancer
```

Creates Google Cloud Load Balancer automatically.

### Azure AKS (LoadBalancer)

```bash
helm install esddns-operator esddns-operator/ \
  --set gandi.apiKey=$GANDI_KEY \
  --set global.domain=yourdomain.com \
  --set service.type=LoadBalancer
```

Creates Azure Load Balancer automatically.

### On-Premises (NodePort)

```bash
helm install esddns-operator esddns-operator/ \
  --set gandi.apiKey=$GANDI_KEY \
  --set global.domain=yourdomain.com \
  --set service.type=NodePort
```

Accessible via `<node-ip>:<node-port>`.

### Development Environment

```bash
helm install esddns-operator esddns-operator/ \
  -f esddns-operator/values-development.yaml \
  --set gandi.apiKey=$GANDI_KEY \
  --set global.domain=example.dev
```

Lower resource limits, debug logging, ClusterIP service.

## Monitoring

### Enable Prometheus Monitoring

```bash
helm install esddns-operator esddns-operator/ \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true \
  --set monitoring.prometheusRules.enabled=true \
  --set gandi.apiKey=$KEY
```

### Available Metrics

```
dns_updates_total                    # Successful DNS updates
dns_update_failures_total            # Failed DNS updates
dns_update_duration_seconds          # Time to update DNS
last_dns_update_timestamp            # Last update time
current_wan_ip_info                  # Current WAN IP
wan_ip_changes_total                 # IP change events
wan_ip_discovery_duration            # Time to discover IP
wan_ip_discovery_failures            # Failed discovery attempts
state_in_sync                        # Sync status
dns_record_ip_matches                # IP match status
service_health                       # Service health (1=up, 0=down)
cache_hits / cache_misses            # Endpoint cache stats
request_duration_seconds             # HTTP request latency
endpoint_requests_total              # Total HTTP requests
```

### Alert Rules

Pre-configured alerts for:
- DNS update failures
- No updates in 20+ minutes
- Operator pod down
- Service pod down
- LoadBalancer external IP not assigned

## Publishing to Artifact Hub

### Automatic (Recommended)

```bash
cd helm/
./publish.sh
```

This will:
1. Validate the chart
2. Package it
3. Generate repository index
4. Display next steps

### Manual Steps

1. Package chart:
   ```bash
   helm package esddns-operator -d helm-repo
   ```

2. Generate index:
   ```bash
   helm repo index helm-repo
   ```

3. Push to GitHub:
   ```bash
   git add helm-repo/
   git commit -m "Release esddns-operator Helm chart v1.0.0"
   git push origin main
   ```

4. Enable GitHub Pages (Settings → Pages)

5. Register on Artifact Hub:
   - Visit https://artifacthub.io
   - Sign in with GitHub
   - Register your repository
   - Chart URL: `https://sqe.github.io/esddns/helm-repo`

6. Verify publication:
   - Wait 5-10 minutes for sync
   - Search for `esddns-operator` on Artifact Hub

See `ARTIFACT_HUB_GUIDE.md` for detailed instructions.

## Updating the Chart

### For New Releases

1. Update version in `Chart.yaml`:
   ```yaml
   version: 1.1.0
   appVersion: "1.1.0"
   ```

2. Update `CHANGELOG.md`:
   ```markdown
   ## [1.1.0] - 2025-11-15
   ### Added
   - New feature description
   ### Fixed
   - Bug fix description
   ```

3. Package and publish:
   ```bash
   helm package esddns-operator -d helm-repo
   helm repo index helm-repo
   git add helm-repo/
   git commit -m "Release esddns-operator Helm chart v1.1.0"
   git push origin main
   ```

4. Artifact Hub will auto-sync within 15 minutes

## Troubleshooting

### Chart Validation

```bash
# Lint chart
helm lint esddns-operator/

# Template test
helm template esddns-operator esddns-operator/ --debug

# Dry-run install
helm install esddns-operator esddns-operator/ \
  --dry-run --debug \
  --set gandi.apiKey=test
```

### Installation Issues

**API key not set:**
```bash
helm upgrade esddns-operator esddns-operator/ \
  --set gandi.apiKey=YOUR_KEY
```

**Domain not found:**
```bash
kubectl get configmap -n esddns-system esddns-config -o yaml
helm upgrade esddns-operator esddns-operator/ \
  --set global.domain=newdomain.com
```

**Pods not starting:**
```bash
kubectl describe pod -n esddns-system -l app=esddns-operator
kubectl logs -n esddns-system -l app=esddns-operator --previous
```

## Best Practices

### Security

- Store API keys in sealed-secrets or sops
- Never commit credentials to version control
- Use RBAC to restrict access
- Apply network policies for additional isolation
- Keep chart versions up to date

### Operations

- Regularly update to new chart versions
- Monitor Prometheus metrics
- Review alert rules
- Test upgrades in development first
- Keep backups of configurations

### Chart Maintenance

- Update README when changing features
- Document breaking changes
- Follow semantic versioning
- Include clear upgrade instructions
- Provide examples for common scenarios

## Statistics

- **Total Resources**: 13 manifest templates
- **Lines of YAML**: 708 (rendered)
- **Configuration Options**: 30+
- **Helm Functions**: 6 helper templates
- **Alert Rules**: 5 pre-configured
- **Supported Kubernetes**: 1.21+

## Support & Documentation

- **GitHub Repository**: https://github.com/sqe/esddns
- **Chart Documentation**: `helm/esddns-operator/README.md`
- **Values Reference**: `helm/esddns-operator/values.yaml`
- **Artifact Hub Guide**: `ARTIFACT_HUB_GUIDE.md`
- **Installation Guide**: See README.md in repository root

## License

MIT - Same as ESDDNS project

---

**Ready to Deploy?**

1. Run: `helm lint helm/esddns-operator/` ✓
2. Run: `./helm/publish.sh` to prepare for Artifact Hub
3. See `ARTIFACT_HUB_GUIDE.md` for publishing steps
