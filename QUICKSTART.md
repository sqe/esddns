# ESDDNS Kubernetes Operator - Quick Start Guide

## 60-Second Deploy

### Cloud Providers (AWS/GCP/Azure)
```bash
# 1. Set your Gandi API key
export GANDI_API_KEY="your-gandi-api-key"

# 2. Run deployment script
cd k8s
./deploy.sh production

# 3. Get external IP (wait 2-5 minutes for cloud provider assignment)
kubectl get svc -n esddns esddns-service

# 4. Access the service
EXTERNAL_IP=$(kubectl get svc -n esddns esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/
```

### On-Premises with MetalLB
```bash
# 1. Set your Gandi API key
export GANDI_API_KEY="your-gandi-api-key"

# 2. Run MetalLB deployment (installs MetalLB + ESDDNS)
cd k8s
./deploy-metallb.sh production 192.168.1.100-192.168.1.110

# 3. Get LoadBalancer IP (assigned by MetalLB within seconds)
kubectl get svc -n esddns-production esddns-service

# 4. Access the service
curl http://<METALLB-IP>/
```

Done! Your DNS is now syncing automatically.

## What Just Deployed

✅ **Operator DaemonSet** - Monitors every node for IP changes
✅ **Flask Web Service** - Exposes DNS state via REST API
✅ **LoadBalancer Service** - Stable external IP from cloud provider
✅ **Kubernetes Configuration** - RBAC, ConfigMaps, Secrets
✅ **Monitoring Setup** - Prometheus metrics and alerts ready

## Common Commands

### View Status
```bash
# All resources
kubectl get all -n esddns

# Just services
kubectl get svc -n esddns

# Just pods
kubectl get pods -n esddns -o wide
```

### View Logs
```bash
# Operator logs (following)
kubectl logs -n esddns -l app=esddns-operator -f

# Service logs
kubectl logs -n esddns -l app=esddns-service -f

# Last 20 lines
kubectl logs -n esddns -l app=esddns-operator --tail=20
```

### Check Configuration
```bash
# View domain configuration
kubectl get configmap esddns-config -n esddns -o jsonpath='{.data.target-domain}'

# View API key is set
kubectl get secret esddns-gandi-credentials -n esddns

# View full ConfigMap
kubectl get configmap esddns-config -n esddns -o yaml
```

### Update Configuration
```bash
# Edit domain or settings
kubectl edit configmap esddns-config -n esddns

# Then restart pods to pick up changes
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
kubectl rollout restart deployment/esddns-service -n esddns
```

### View Metrics
```bash
# Port-forward to metrics endpoint
kubectl port-forward -n esddns daemonset/esddns-operator-daemon 8080:8080

# In another terminal
curl http://localhost:8080/metrics | grep esddns
```

## Accessing the Web Service

```bash
# Get external IP
EXTERNAL_IP=$(kubectl get svc -n esddns esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# View HTML dashboard
curl http://$EXTERNAL_IP/

# Get raw JSON state
curl http://$EXTERNAL_IP/raw
```

## Troubleshooting

### Operator pod not running
```bash
# Check events
kubectl describe daemonset -n esddns esddns-operator-daemon

# Check pod status
kubectl describe pod -n esddns -l app=esddns-operator

# Check logs
kubectl logs -n esddns -l app=esddns-operator --previous
```

### LoadBalancer IP stuck "Pending"
```bash
# Check service status
kubectl describe svc -n esddns esddns-service

# This is normal - can take 2-5 minutes
# Check your cloud provider's load balancer quota
# AWS: aws elb describe-load-balancers
# GCP: gcloud compute forwarding-rules list
# Azure: az network lb list
```

### DNS not updating
```bash
# Check operator logs for API errors
kubectl logs -n esddns -l app=esddns-operator | grep -i "update\|error"

# Verify API key is correct
kubectl get secret esddns-gandi-credentials -n esddns -o jsonpath='{.data.api-key}' | base64 -d

# Check domain configuration
kubectl get configmap esddns-config -n esddns -o jsonpath='{.data.target-domain}'
```

### Service not responding
```bash
# Check service pod status
kubectl get pods -n esddns -l app=esddns-service

# Check service logs
kubectl logs -n esddns -l app=esddns-service -f

# Check if service is listening
kubectl port-forward -n esddns svc/esddns-service 8080:80
curl http://localhost:8080/
```

## Updating Configuration

### Change Target Domain
```bash
# Edit ConfigMap
kubectl patch configmap esddns-config -n esddns \
  -p '{"data":{"target-domain":"yourdomain.com"}}'

# Restart operator
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
```

### Change Update Interval
```bash
# Edit check interval (in seconds)
kubectl patch configmap esddns-config -n esddns \
  -p '{"data":{"daemon_thread_interval":"600"}}'

# Restart operator
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
```

### Update API Key
```bash
# Delete old secret
kubectl delete secret esddns-gandi-credentials -n esddns

# Create new secret
kubectl create secret generic esddns-gandi-credentials \
  --from-literal=api-key=$NEW_GANDI_API_KEY \
  -n esddns

# Restart pods
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns
kubectl rollout restart deployment/esddns-service -n esddns
```

## Monitoring

### With Prometheus
```bash
# Metrics are exposed on port 8080
# Configure Prometheus scrape config:
- job_name: 'esddns-operator'
  static_configs:
  - targets: ['esddns-operator-daemon:8080']

# Or use ServiceMonitor (already configured):
kubectl get servicemonitor -n esddns
```

### Key Metrics to Monitor
```
esddns_dns_updates_total             # Successful DNS updates
esddns_dns_update_failures_total     # Failed DNS updates
esddns_last_dns_update_timestamp     # Last update time
esddns_current_wan_ip_info           # Current WAN IP
esddns_state_in_sync                 # Sync status (1=yes, 0=no)
esddns_service_health                # Service health
```

### Alerts Configured
- DNS updates failing
- No recent updates (>20 minutes)
- Operator pod down
- Service pod down
- LoadBalancer IP not assigned

## Scaling & Advanced

### Deploy to Development
```bash
./k8s/deploy.sh development
# Uses: esddns-dev namespace, debug logging, lower resources
```

### Manually Build & Push Image
```bash
# Build
docker build -f k8s/Dockerfile -t youregistry/esddns:1.0.0 .

# Push
docker push youregistry/esddns:1.0.0

# Update deployment
kubectl set image daemonset/esddns-operator-daemon \
  esddns-operator=youregistry/esddns:1.0.0 \
  -n esddns
```

### Use NodePort Instead of LoadBalancer
```bash
# For on-premises or clusters without cloud provider
kubectl patch svc esddns-service -n esddns \
  -p '{"spec":{"type":"NodePort"}}'

# Get node port
kubectl get svc esddns-service -n esddns
# Access via: <node-ip>:<node-port>
```

### Check Resource Usage
```bash
# Pod resources
kubectl top pods -n esddns

# Node resources
kubectl top nodes

# Describe pod for limits
kubectl describe pod -n esddns -l app=esddns-operator
```

## Cleanup

```bash
# Remove entire deployment
kubectl delete namespace esddns

# Or just the release
kubectl delete -f esddns-prod.yaml

# Remove monitoring
kubectl delete -f k8s/monitoring/
```

## File References

- **DEPLOYMENT.md** - Complete deployment guide with all details
- **k8s/README.md** - Architecture and feature overview
- **OPERATOR_SUMMARY.md** - Implementation details
- **k8s/esddns_operator.py** - Kopf operator source code
- **esddns_service/metrics.py** - Prometheus metrics

## Getting Help

1. **Check logs**: `kubectl logs -n esddns -l app=esddns-operator -f`
2. **Check events**: `kubectl describe daemonset -n esddns esddns-operator-daemon`
3. **View metrics**: Port-forward to 8080 and check `/metrics`
4. **Read docs**: See DEPLOYMENT.md troubleshooting section
5. **Open issue**: https://github.com/sqe/esddns/issues

## Quick Reference

| Task | Command |
|------|---------|
| Deploy | `./k8s/deploy.sh production` |
| Check status | `kubectl get all -n esddns` |
| View logs | `kubectl logs -n esddns -l app=esddns-operator -f` |
| Get external IP | `kubectl get svc -n esddns esddns-service` |
| View metrics | `kubectl port-forward -n esddns daemonset/esddns-operator-daemon 8080:8080` |
| Update domain | `kubectl patch configmap esddns-config -n esddns -p '{"data":{"target-domain":"domain.com"}}'` |
| Update API key | See "Update Configuration" section |
| Restart pods | `kubectl rollout restart daemonset/esddns-operator-daemon -n esddns` |
| Cleanup | `kubectl delete namespace esddns` |

---

**Happy DNS syncing! 🚀**

Need more details? See [DEPLOYMENT.md](DEPLOYMENT.md)
