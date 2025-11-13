# ESDDNS Kubernetes Deployment Guide

## Overview

This guide walks through deploying ESDDNS as a Kubernetes operator with a LoadBalancer service for automatic DNS synchronization.

## Architecture

### Components

1. **Kopf Operator Daemon** (DaemonSet)
   - Runs on every node with hostNetwork
   - Watches node IP changes
   - Triggers DNS updates via Gandi.net API
   - Exposes Prometheus metrics on port 8080

2. **Web Service** (Deployment)
   - Single replica Flask service
   - Exposes DNS state via REST API on port 51339
   - Served via LoadBalancer service
   - Health checks: liveness and readiness probes

3. **LoadBalancer Service**
   - External IP from cloud provider (AWS, GCP, etc.)
   - Stable endpoint for API access
   - No port management needed
   - Built-in health checks and failover

### Kustomization Structure

```
k8s/
├── base/                          # Base configuration
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── serviceaccount.yaml
│   ├── clusterrole.yaml
│   ├── clusterrolebinding.yaml
│   ├── daemon-deployment.yaml     # Kopf operator DaemonSet
│   ├── service-deployment.yaml    # Flask web service
│   ├── service.yaml               # LoadBalancer service
│   ├── secrets.yaml
│   └── configmap.yaml
│
├── overlays/
│   ├── development/               # Dev environment overrides
│   │   ├── kustomization.yaml
│   │   ├── daemon-dev-patch.yaml
│   │   └── service-dev-patch.yaml
│   │
│   └── production/                # Prod environment overrides
│       ├── kustomization.yaml
│       ├── daemon-prod-patch.yaml
│       └── service-prod-patch.yaml
│
└── monitoring/                    # Prometheus monitoring
    ├── prometheus-servicemonitor.yaml
    └── prometheus-rules.yaml
```

## Prerequisites

- Kubernetes 1.19+ cluster
- `kubectl` configured with cluster access
- `kustomize` CLI (v5.0+)
- Gandi.net API key for DNS updates
- Container registry access (for pushing images)

## Installation

### Step 1: Prepare Configuration

Update the ConfigMap with your domain information:

```bash
# Edit configuration
kubectl kustomize k8s/overlays/production | \
  yq eval '.[] | select(.kind == "ConfigMap") | .data."target-domain" = "yourdomain.com"'
```

Or directly edit: `k8s/base/configmap.yaml`

### Step 2: Create Secret with API Key

```bash
# Create namespace
kubectl create namespace esddns

# Create secret with your Gandi API key
kubectl create secret generic esddns-gandi-credentials \
  --from-literal=api-key=$GANDI_API_KEY \
  -n esddns
```

For sealed-secrets (production recommended):
```bash
# Install sealed-secrets controller first
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Create and seal secret
kubectl create secret generic esddns-gandi-credentials \
  --from-literal=api-key=$GANDI_API_KEY \
  -n esddns \
  --dry-run=client \
  -o yaml | kubeseal -o yaml > sealed-secret.yaml

kubectl apply -f sealed-secret.yaml
```

### Step 3: Build and Push Container Image

```bash
# Build Docker image
docker build -f k8s/Dockerfile -t youregistry.azurecr.io/esddns:latest .

# Push to registry
docker push youregistry.azurecr.io/esddns:latest

# Update image references in kustomization
sed -i 's|esddns:latest|youregistry.azurecr.io/esddns:latest|g' \
  k8s/base/daemon-deployment.yaml \
  k8s/base/service-deployment.yaml
```

### Step 4: Deploy to Development

```bash
# Generate manifests
kubectl kustomize k8s/overlays/development > esddns-dev.yaml

# Review generated manifests
cat esddns-dev.yaml | less

# Deploy
kubectl apply -f esddns-dev.yaml

# Monitor deployment
kubectl get pods -n esddns-dev -w
kubectl logs -n esddns-dev -l app=esddns-operator -f
```

### Step 5: Deploy to Production

```bash
# Generate manifests
kubectl kustomize k8s/overlays/production > esddns-prod.yaml

# Review manifests
cat esddns-prod.yaml | less

# Deploy
kubectl apply -f esddns-prod.yaml

# Verify all components are running
kubectl get all -n esddns
```

## Verification

### Check Operator Status

```bash
# Get DaemonSet status
kubectl get daemonset -n esddns-system esddns-operator-daemon
kubectl describe daemonset -n esddns-system esddns-operator-daemon

# Check operator logs
kubectl logs -n esddns-system -l app=esddns-operator -f --all-containers=true
```

### Check Service Status

```bash
# Get Deployment status
kubectl get deployment -n esddns-system esddns-service
kubectl describe deployment -n esddns-system esddns-service

# Check service logs
kubectl logs -n esddns-system -l app=esddns-service -f
```

### Check LoadBalancer

```bash
# Get LoadBalancer external IP
kubectl get svc -n esddns-system esddns-service
kubectl describe svc -n esddns-system esddns-service

# Test service endpoint
EXTERNAL_IP=$(kubectl get svc -n esddns-system esddns-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/
curl http://$EXTERNAL_IP/raw
```

### Check Metrics

```bash
# Port-forward to Prometheus metrics
kubectl port-forward -n esddns-system daemonset/esddns-operator-daemon 8080:8080

# In another terminal
curl http://localhost:8080/metrics
```

## Configuration

### Environment Variables

Key environment variables from ConfigMap and Secrets:

```yaml
API_KEY                   # Gandi.net API key (from secret)
TARGET_DOMAIN_FQDN       # Domain to manage (from configmap)
RECORD_NAME_ROOT         # Root record name, typically "@" (from configmap)
RECORD_TYPE_A            # DNS record type, always "A" (hardcoded)
RECORD_TTL               # DNS TTL in seconds (from configmap)
KOPF_LOG_LEVEL           # Logging level: DEBUG, INFO, WARNING
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap esddns-config -n esddns

# Or patch it
kubectl patch configmap esddns-config -n esddns \
  --patch='{"data":{"target-domain":"newdomain.com"}}'

# Rolling restart pods to pick up changes
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
kubectl rollout restart deployment/esddns-service -n esddns
```

### Update API Key

```bash
# Delete old secret
kubectl delete secret esddns-gandi-credentials -n esddns

# Create new secret
kubectl create secret generic esddns-gandi-credentials \
  --from-literal=api-key=$NEW_API_KEY \
  -n esddns

# Restart pods
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
kubectl rollout restart deployment/esddns-service -n esddns
```

## Monitoring

### Prometheus Integration

ServiceMonitor resources are defined in `k8s/monitoring/prometheus-servicemonitor.yaml`

Install with:
```bash
kubectl apply -f k8s/monitoring/prometheus-servicemonitor.yaml
```

### PrometheusRules

Alert rules are defined in `k8s/monitoring/prometheus-rules.yaml`

Available alerts:
- `ESDDNSDNSUpdateFailures` - DNS updates failing
- `ESDDNSNoRecentUpdates` - No updates in 20+ minutes
- `ESDDNSOperatorDown` - Operator not responding
- `ESDDNSServiceDown` - Web service not responding
- `ESDDNSLoadBalancerPending` - LoadBalancer IP not assigned

Install with:
```bash
kubectl apply -f k8s/monitoring/prometheus-rules.yaml
```

### Key Metrics

```
esddns_dns_updates_total             # Successful DNS updates
esddns_dns_update_failures_total     # Failed DNS updates
esddns_dns_update_duration_seconds   # DNS update time
esddns_last_dns_update_timestamp     # Last update time
esddns_current_wan_ip_info           # Current WAN IP
esddns_wan_ip_changes_total          # IP change events
esddns_state_in_sync                 # Sync status (1=yes, 0=no)
esddns_service_health                # Service health (1=up, 0=down)
```

## Troubleshooting

### Operator Pod Not Starting

```bash
# Check pod events
kubectl describe pod -n esddns-system -l app=esddns-operator

# Check logs
kubectl logs -n esddns-system -l app=esddns-operator --previous

# Check resource availability
kubectl describe nodes
kubectl top nodes
```

### DNS Updates Not Happening

```bash
# Check operator logs for DNS errors
kubectl logs -n esddns-system -l app=esddns-operator | grep -i dns

# Verify API key is set
kubectl get secret esddns-gandi-credentials -n esddns -o jsonpath='{.data.api-key}' | base64 -d

# Verify domain configuration
kubectl get configmap esddns-config -n esddns -o jsonpath='{.data.target-domain}'

# Test Gandi API manually
POD=$(kubectl get pod -n esddns-system -l app=esddns-operator -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n esddns-system -- python -c "
from api.dns_manager import DomainManagement
dm = DomainManagement()
print(dm.get_all_domains())
"
```

### LoadBalancer IP Not Assigning

Check cloud provider status:
```bash
# AWS
kubectl get svc -n esddns-system esddns-service -o jsonpath='{.status.loadBalancer}'

# GCP
gcloud compute forwarding-rules list --filter="name:esddns*"

# Azure
az network lb list --resource-group YOUR_RG
```

### High Memory/CPU Usage

Review and adjust resource limits:
```bash
# Edit DaemonSet
kubectl edit daemonset esddns-operator-daemon -n esddns-system

# Edit Deployment
kubectl edit deployment esddns-service -n esddns-system
```

Typical production values:
- DaemonSet: 256Mi memory, 200m CPU (request), 512Mi/500m (limit)
- Deployment: 256Mi memory, 100m CPU (request), 512Mi/500m (limit)

## Scaling & Updates

### Rolling Updates

```bash
# Update image
kubectl set image daemonset/esddns-operator-daemon \
  esddns-operator=youregistry.azurecr.io/esddns:1.0.1 \
  -n esddns-system

# Monitor rollout
kubectl rollout status daemonset/esddns-operator-daemon -n esddns-system

# For deployments
kubectl set image deployment/esddns-service \
  esddns-web=youregistry.azurecr.io/esddns:1.0.1 \
  -n esddns-system

kubectl rollout status deployment/esddns-service -n esddns-system
```

### Rollback

```bash
# Rollback daemon
kubectl rollout undo daemonset/esddns-operator-daemon -n esddns-system

# Rollback service
kubectl rollout undo deployment/esddns-service -n esddns-system
```

## Security Best Practices

1. **Use Sealed Secrets** for API keys in production
2. **Enable RBAC** - ServiceAccounts have minimal required permissions
3. **Network Policies** - Restrict ingress/egress traffic
4. **Pod Security Policy** - Enforce security standards
5. **Image Scanning** - Scan container images for vulnerabilities
6. **Audit Logging** - Enable Kubernetes audit logs

## Cleanup

```bash
# Remove from production
kubectl delete -f esddns-prod.yaml

# Remove namespace and all resources
kubectl delete namespace esddns-system

# Remove monitoring components
kubectl delete -f k8s/monitoring/
```

## Support

For issues or questions:
1. Check operator logs: `kubectl logs -n esddns-system -l app=esddns-operator -f`
2. Review Prometheus metrics for trends
3. Check Gandi API documentation: https://doc.livedns.gandi.net/
4. Open GitHub issue: https://github.com/sqe/esddns/issues
