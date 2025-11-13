# ESDDNS Operator Helm Chart

A Kubernetes Helm chart for deploying the ESDDNS operator - an automated dynamic DNS updater for Kubernetes clusters using the Gandi.net API.

## Overview

ESDDNS Operator is a Kopf-based Kubernetes operator that:
- Monitors node IP changes in your cluster
- Automatically updates DNS records at Gandi.net
- Exposes Prometheus metrics for monitoring
- Supports cloud providers (AWS EKS, Google GKE, Azure AKS) and on-premises clusters
- Includes a Flask web service for querying DNS status

## Prerequisites

- Kubernetes 1.21+
- Helm 3.0+
- A Gandi.net account with API access
- Gandi.net API key (with LiveDNS permissions)

## Installation

### 1. Add Helm Repository (once Artifact Hub is configured)

```bash
helm repo add esddns https://your-helm-repo-url
helm repo update
```

### 2. Install the Chart

```bash
helm install esddns-operator esddns/esddns-operator \
  --namespace esddns-system \
  --create-namespace \
  --set gandi.apiKey=<your-gandi-api-key> \
  --set global.domain=yourdomain.com
```

### 3. Verify Installation

```bash
kubectl get all -n esddns-system
kubectl logs -n esddns-system -l app=esddns-operator
```

## Configuration

### Required Values

- `gandi.apiKey` - Your Gandi.net API key (required for DNS updates)
- `global.domain` - Target domain for DNS updates (e.g., `yourdomain.com`)

### Common Options

```yaml
# Change domain and DNS settings
global:
  domain: yourdomain.com
  recordName: "@"          # @ for root domain
  recordTTL: 300           # TTL in seconds

# Use ClusterIP service instead of LoadBalancer
service:
  type: ClusterIP

# Development mode with debug logging
environment: development

# Disable monitoring
monitoring:
  enabled: false

# Disable web service, operator only
service:
  enabled: false
```

### Advanced Configuration

See `values.yaml` for all available options including:
- Resource limits and requests
- Health check parameters
- Node affinity and tolerations
- Pod disruption budgets
- Security context settings

## Usage

### Get LoadBalancer External IP

```bash
kubectl get svc -n esddns-system esddns-service
```

Wait for the `EXTERNAL-IP` to be assigned (may take a few minutes on cloud providers).

### Query DNS Status

```bash
EXTERNAL_IP=$(kubectl get svc -n esddns-system esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/
```

### View Operator Logs

```bash
kubectl logs -n esddns-system -l app=esddns-operator -f
```

### Access Prometheus Metrics

```bash
kubectl port-forward -n esddns-system daemonset/esddns-operator-daemon 8080:8080
curl http://localhost:8080/metrics
```

## Environment Configurations

### Production (Default)

```bash
helm install esddns-operator esddns/esddns-operator \
  --set environment=production \
  --set gandi.apiKey=<key>
```

- INFO logging level
- Higher resource limits
- Pod disruption budgets enabled
- Affinity rules enabled

### Development

```bash
helm install esddns-operator esddns/esddns-operator \
  --set environment=development \
  --set gandi.apiKey=<key>
```

- DEBUG logging level
- Lower resource limits
- Optimized for testing

## Monitoring

### Enable Prometheus Monitoring

The chart includes ServiceMonitor and PrometheusRules for Prometheus Operator:

```bash
helm install esddns-operator esddns/esddns-operator \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true \
  --set monitoring.prometheusRules.enabled=true \
  --set gandi.apiKey=<key>
```

### Available Metrics

- `dns_updates_total` - Successful DNS updates
- `dns_update_failures_total` - Failed DNS updates
- `dns_update_duration_seconds` - Time to update DNS
- `last_dns_update_timestamp` - Last update time
- `current_wan_ip_info` - Current WAN IP
- `wan_ip_changes_total` - IP change events

### Alert Rules

The chart includes pre-configured alerts for:
- DNS update failures
- No updates in 20+ minutes
- Operator pod down
- Service pod down
- LoadBalancer external IP not assigned

## Upgrade

```bash
helm upgrade esddns-operator esddns/esddns-operator \
  --set gandi.apiKey=<new-key> \
  -n esddns-system
```

## Uninstall

```bash
helm uninstall esddns-operator -n esddns-system
kubectl delete namespace esddns-system
```

## Troubleshooting

### No External IP Assigned

```bash
# Check service status
kubectl describe svc -n esddns-system esddns-service

# Check events
kubectl get events -n esddns-system --sort-by='.lastTimestamp'
```

### DNS Not Updating

```bash
# Check operator logs
kubectl logs -n esddns-system -l app=esddns-operator -f

# Verify API key is set
kubectl get secret -n esddns-system esddns-gandi-credentials

# Check metrics
kubectl port-forward -n esddns-system daemonset/esddns-operator-daemon 8080:8080
curl http://localhost:8080/metrics
```

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n esddns-system -l app=esddns-operator

# Check logs
kubectl logs -n esddns-system -l app=esddns-operator --previous
```

## Deployment Scenarios

### AWS EKS

```bash
helm install esddns-operator esddns/esddns-operator \
  --set service.type=LoadBalancer \
  --set gandi.apiKey=<key>
# Creates AWS Network Load Balancer
```

### Google GKE

```bash
helm install esddns-operator esddns/esddns-operator \
  --set service.type=LoadBalancer \
  --set gandi.apiKey=<key>
# Creates Google Cloud Load Balancer
```

### Azure AKS

```bash
helm install esddns-operator esddns/esddns-operator \
  --set service.type=LoadBalancer \
  --set gandi.apiKey=<key>
# Creates Azure Load Balancer
```

### On-Premises

```bash
helm install esddns-operator esddns/esddns-operator \
  --set service.type=NodePort \
  --set gandi.apiKey=<key>
# Exposes service on node port (default: 80)
```

## Security

### API Key Management

**For Production:**
1. Use Kubernetes Secrets sealed by `sealed-secrets` or `sops`
2. Never commit API keys to version control
3. Rotate API keys regularly
4. Use RBAC to restrict access

```bash
# Using sealed-secrets
helm install esddns-operator esddns/esddns-operator \
  --set gandi.apiKey= \
  -f sealed-secret-values.yaml
```

### RBAC

The chart includes minimal RBAC permissions:
- Read nodes, pods, services, deployments
- Read configmaps and secrets
- Create events for logging

### Network Policies

For additional security, apply network policies:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: esddns-operator
  namespace: esddns-system
spec:
  podSelector:
    matchLabels:
      app: esddns-operator
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
```

## Support

- GitHub: https://github.com/sqe/esddns
- Issues: https://github.com/sqe/esddns/issues
- Documentation: https://github.com/sqe/esddns#readme

## License

MIT - See LICENSE file for details

## Contributing

Contributions are welcome! Please see GitHub repository for contribution guidelines.
