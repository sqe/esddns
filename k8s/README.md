# ESDDNS Kubernetes Operator

Production-ready Kubernetes operator for automatic DNS synchronization with Gandi.net using Kopf framework.

## Quick Start

```bash
# Generate deployment manifests
./k8s/deploy.sh development

# Or for production
./k8s/deploy.sh production
```

## What's Included

### Core Components

- **esddns_operator.py** - Kopf-based operator for node IP monitoring and DNS updates
- **Dockerfile** - Container image with Kopf and all dependencies
- **RBAC Configuration** - ServiceAccounts, ClusterRoles, and bindings
- **LoadBalancer Service** - External IP for web service access

### Kubernetes Manifests

**Base Configuration** (`k8s/base/`)
- Namespace, ServiceAccounts, and RBAC
- DaemonSet for operator (hostNetwork enabled)
- Deployment for web service (Flask)
- LoadBalancer Service
- ConfigMap with dns.ini settings
- Secrets for API credentials

**Environment Overlays** (`k8s/overlays/`)
- **development/** - Debug logging, lower resources, dev domain
- **production/** - INFO logging, higher resources, production domain

### Monitoring

- **Prometheus ServiceMonitor** - Automatic scrape configuration
- **PrometheusRules** - Alert definitions for critical events
- **Metrics** - DNS updates, WAN IP changes, service health

## Architecture

### Centralized IP Detection + Distributed DNS Updates

```
┌──────────────────────────────────────────────────────┐
│     Kubernetes Cluster (Any Cloud)                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  CENTRALIZED IP DETECTION (Leader)                   │
│  ┌────────────────────────────────────────────────┐  │
│  │   esddns-operator (Single Instance)            │  │
│  │   CentralizedIPDetector (detect_wan_ip)        │  │
│  │   - Runs once every 5 minutes                  │  │
│  │   - Detects WAN IP from external services     │  │
│  │   - Stores in ConfigMap: esddns-wan-ip        │  │
│  └─────────────────────┬──────────────────────────┘  │
│                        │                              │
│                        ▼                              │
│            ┌───────────────────────┐                 │
│            │ ConfigMap             │                 │
│            │ esddns-wan-ip         │                 │
│            │ - current_ip: X.X.X.X │                 │
│            │ - timestamp: ...      │                 │
│            └───────────────────────┘                 │
│                        ▲                              │
│                        │ (Read cached IP)             │
│                        │                              │
│  DISTRIBUTED DNS UPDATES (All Nodes)                 │
│  Node 1              Node 2        Node N            │
│  ┌──────────┐       ┌──────────┐                     │
│  │ Operator │       │ Operator │ ...  DaemonSet     │
│  │ Pod      │       │ Pod      │      (hostNetwork)  │
│  │ NodeDNS  │       │ NodeDNS  │      Distributed   │
│  │ Updater  │       │ Updater  │                     │
│  └────┬─────┘       └────┬─────┘                     │
│       │                  │                            │
│       │ (Update if IP changed)                       │
│       │                  │                            │
│       └──────────────────┴────────┐                  │
│                                   │                  │
│  ┌────────────────────────────────▼──┐               │
│  │ esddns-service (Deployment)       │               │
│  │ Flask Web Service (Single Replica) │               │
│  └────────────────────────────────────┘               │
│             │                                         │
│  ┌──────────▼──────────────────┐                     │
│  │ LoadBalancer Service        │                     │
│  │ (cloud provider ELB/LB)     │                     │
│  └──────────┬──────────────────┘                     │
│             │                                        │
└─────────────┼────────────────────────────────────────┘
              │ External IP                             
              │                                        
        ┌─────▼──────────┐                            
        │ Gandi.net API  │ ◄──────────────────────────┘
        │ (DNS Updates)  │
        └────────────────┘
```

### How It Works

1. **Single IP Detection**: Operator leader detects WAN IP once and stores in ConfigMap
2. **No Redundant Calls**: Eliminates N API calls (one per node) → reduces to 1
3. **Distributed Updates**: All DaemonSet pods read from ConfigMap and update DNS if needed
4. **No Drift**: All nodes use the same detected IP, preventing conflicting updates
5. **Network Isolation Safe**: Works even if nodes can't reach external services directly

## Key Features

### Centralized IP Detection
- **Component**: CentralizedIPDetector class in operator
- **Execution**: Single Kopf timer handler (leader election via lock)
- **Frequency**: Every 5 minutes (configurable)
- **Method**: External IP detection services + STUN protocol
- **Storage**: Kubernetes ConfigMap `esddns-wan-ip`
- **Benefit**: Only 1 external API call instead of N (per node)

### Distributed DNS Updates  
- **Component**: NodeDNSUpdater class in operator
- **Execution**: DaemonSet with hostNetwork=true
- **Source**: Reads cached IP from ConfigMap (no detection overhead)
- **Trigger**: Node events + periodic check (every 5 minutes)
- **Benefit**: All nodes synchronized, no drift, network isolation safe

### Web Service
- **Framework**: Flask
- **Type**: LoadBalancer (stable external IP)
- **Traffic**: Medium traffic support
- **Scaling**: Single replica (no horizontal scaling needed)
- **Health**: Liveness and readiness probes

### DNS Synchronization
- **Detection**: Centralized in operator leader only
- **Updates**: Distributed across all nodes (from ConfigMap cache)
- **Provider**: Gandi.net (via REST API)
- **Records**: A records (IPv4)
- **Retry**: Built-in retry logic with backoff
- **Validation**: Confirms DNS record matches current IP

### Monitoring & Observability
- **Metrics**: Prometheus-compatible (port 8080 for operator, /metrics endpoint)
- **Alerts**: PrometheusRules for critical events
- **Logging**: Structured logs with configurable levels
- **Probes**: Liveness and readiness health checks

### Configuration Management
- **ConfigMap**: dns.ini bundled in cluster
- **Secrets**: Gandi API key stored securely
- **Environment**: Per-environment overrides (dev/prod)
- **Updates**: Rolling updates without service disruption

## Deployment Scenarios

### Scenario 1: AWS EKS
```bash
# SetupAWS credentials
export AWS_PROFILE=my-profile

# Deploy
./k8s/deploy.sh production

# Get LoadBalancer IP
kubectl get svc -n esddns esddns-service
# AWS Classic LB or NLB automatically assigned
```

### Scenario 2: Google GKE
```bash
# Setup GCP credentials
gcloud auth application-default login

# Deploy
./k8s/deploy.sh production

# Get LoadBalancer IP
kubectl get svc -n esddns esddns-service
# GCP Network LB automatically assigned
```

### Scenario 3: Azure AKS
```bash
# Setup Azure credentials
az login

# Deploy
./k8s/deploy.sh production

# Get LoadBalancer IP
kubectl get svc -n esddns esddns-service
# Azure LB automatically assigned
```

### Scenario 4: On-Premises with MetalLB (Recommended)
For bare-metal Kubernetes clusters, use MetalLB for LoadBalancer support:
```bash
# Automated deployment (installs MetalLB + ESDDNS)
./k8s/deploy-metallb.sh production 192.168.1.100-192.168.1.110

# Or manual deployment
# 1. Install MetalLB
helm install metallb metallb/metallb -n metallb-system --create-namespace

# 2. Create IP address pool
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: esddns-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.110
EOF

# 3. Create L2 advertisement
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: esddns-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - esddns-pool
EOF

# 4. Deploy ESDDNS
./k8s/deploy.sh production
```

### Scenario 5: Self-Hosted without MetalLB
For clusters without cloud provider or MetalLB, use NodePort:
```bash
# Edit service.yaml - change type from LoadBalancer to NodePort
kubectl patch svc esddns-service -n esddns \
  -p '{"spec":{"type":"NodePort"}}'

# Access via: <node-ip>:<node-port>
kubectl get svc -n esddns esddns-service
```

## File Structure

```
k8s/
├── esddns_operator.py              # Main Kopf operator implementation
├── Dockerfile                       # Container image definition
├── deploy.sh                        # Cloud deployment automation script
├── deploy-metallb.sh                # On-premises MetalLB + ESDDNS deployment
├── DEPLOYMENT.md                    # Detailed deployment guide
├── README.md                        # This file
│
├── base/                            # Base Kubernetes manifests
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── serviceaccount.yaml
│   ├── clusterrole.yaml
│   ├── clusterrolebinding.yaml
│   ├── daemon-deployment.yaml       # Kopf operator DaemonSet
│   ├── service-deployment.yaml      # Flask service Deployment
│   ├── service.yaml                 # LoadBalancer Service
│   ├── configmap.yaml               # Configuration and dns.ini
│   └── secrets.yaml                 # API credentials placeholder
│
├── overlays/
│   ├── development/                 # Development environment
│   │   ├── kustomization.yaml
│   │   ├── daemon-dev-patch.yaml
│   │   └── service-dev-patch.yaml
│   │
│   └── production/                  # Production environment
│       ├── kustomization.yaml
│       ├── daemon-prod-patch.yaml
│       └── service-prod-patch.yaml
│
└── monitoring/                      # Prometheus monitoring
    ├── prometheus-servicemonitor.yaml
    └── prometheus-rules.yaml
```

## Requirements

### Cluster Requirements
- Kubernetes 1.19+
- RBAC enabled
- Storage for logs (optional)

### Tool Requirements
- kubectl 1.19+
- kustomize 5.0+
- Docker (for building images)

### Gandi Requirements
- Active Gandi.net account
- Domain under Gandi management
- LiveDNS API access enabled
- API key with appropriate permissions

## Installation Steps

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step installation.

Quick summary:
```bash
# 1. Prepare domain and API key
export GANDI_API_KEY="your-api-key"

# 2. Generate and deploy
./k8s/deploy.sh production

# 3. Verify
kubectl get all -n esddns
kubectl get svc -n esddns esddns-service
```

## Operation

### View Logs
```bash
# Operator logs
kubectl logs -n esddns -l app=esddns-operator -f

# Service logs
kubectl logs -n esddns -l app=esddns-service -f

# All logs with timestamps
kubectl logs -n esddns --all-containers=true -f --prefix
```

### Check ConfigMap (Cached IP)
```bash
# View cached WAN IP
kubectl get configmap -n esddns esddns-wan-ip -o yaml

# Example output:
# data:
#   current_ip: 203.0.113.42
#   detected_at: 2025-11-13T15:30:45.123456
#   timestamp: 2025-11-13T15:30:45.123456
```

### Check Metrics
```bash
# Port-forward to metrics
kubectl port-forward -n esddns daemonset/esddns-operator-daemon 8080:8080

# View metrics
curl http://localhost:8080/metrics
```

### Access Web Service
```bash
# Get external IP
EXTERNAL_IP=$(kubectl get svc -n esddns esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# View current state
curl http://$EXTERNAL_IP/

# Get raw JSON
curl http://$EXTERNAL_IP/raw
```

### Update Configuration
```bash
# Edit ConfigMap
kubectl edit configmap esddns-config -n esddns

# Restart pods to pick up changes
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

## Troubleshooting

### Operator not starting
```bash
# Check events
kubectl describe daemonset -n esddns esddns-operator-daemon

# Check pod logs
kubectl logs -n esddns -l app=esddns-operator --previous
```

### DNS not updating
```bash
# Check operator logs
kubectl logs -n esddns -l app=esddns-operator | grep -i dns

# Verify API key
kubectl get secret -n esddns esddns-gandi-credentials -o jsonpath='{.data.api-key}' | base64 -d

# Check domain configuration
kubectl get configmap -n esddns esddns-config -o jsonpath='{.data.target-domain}'
```

### LoadBalancer IP not assigned
Check your cloud provider's load balancer quota and status.

See [DEPLOYMENT.md](DEPLOYMENT.md) for more troubleshooting steps.

## Integration with Monitoring

### Prometheus
ServiceMonitor resources automatically configured. Add to Prometheus config:
```yaml
serviceMonitorSelector:
  matchLabels:
    app: esddns
```

### Grafana
Available metrics for dashboards:
- `esddns_dns_updates_total`
- `esddns_dns_update_failures_total`
- `esddns_last_dns_update_timestamp`
- `esddns_current_wan_ip_info`
- `esddns_state_in_sync`
- `esddns_service_health`

### Alerts
PrometheusRules include:
- DNS update failures
- No recent updates
- Operator pod down
- Service pod down
- LoadBalancer IP pending

## Network & Security

### RBAC
Minimal permissions assigned:
- Node read-only access (for IP monitoring)
- Service read/write (for LoadBalancer management)
- ConfigMap/Secret read (for configuration)
- Event creation (for audit trail)

### Network Policies
Optional NetworkPolicy resources can restrict:
- Operator outbound to only Gandi API
- Service inbound to LoadBalancer only
- Pod-to-pod communication

### Image Security
- Multi-stage Dockerfile to reduce image size
- Non-root user (uid: 1000) for web service
- Root required for operator (hostNetwork access)
- No unnecessary dependencies

## Performance Tuning

### Resource Limits
Adjust in overlays based on your needs:
- **Development**: 256Mi memory, 200m CPU
- **Production**: 512Mi memory, 500m CPU

### IP Detection Interval
Configure via `DNS_SYNC_INTERVAL` environment variable (seconds).
Default: 300 seconds (5 minutes)

This controls how often:
- The operator detects WAN IP and updates ConfigMap
- All nodes check if DNS needs updating

### Reduce External API Calls
- **Before**: N nodes × detection calls = high API usage
- **After**: 1 centralized detection = minimal API calls
- **Savings**: 90-95% reduction in API calls for multi-node clusters

### Probe Timeouts
Adjust in deployment manifests for slow networks.
Default: 5 seconds

## Cleanup

```bash
# Remove everything
kubectl delete namespace esddns

# Or just the deployment
kubectl delete -f esddns-prod.yaml

# Remove monitoring
kubectl delete -f k8s/monitoring/
```

## Support

For issues:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
2. Review operator logs
3. Check Prometheus metrics
4. Open GitHub issue with logs and configuration

## License

Same as ESDDNS project (MIT)
