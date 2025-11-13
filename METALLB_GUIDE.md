# MetalLB Deployment Guide for ESDDNS

## Overview

This guide explains how to deploy ESDDNS on **bare-metal (on-premises)** Kubernetes clusters using **MetalLB** for LoadBalancer support.

## Why MetalLB?

MetalLB provides LoadBalancer service type capability for Kubernetes clusters that don't run on cloud providers (AWS, GCP, Azure). This is essential for on-premises deployments.

### MetalLB Benefits for ESDDNS

✅ **LoadBalancer Service Type** - Enables cloud-like LoadBalancer on bare-metal  
✅ **Layer 2 Mode** - Simple ARP-based IP advertisement (same-subnet only)  
✅ **BGP Mode** - Enterprise-grade routing with multi-subnet support  
✅ **STUN Integration** - Works perfectly with ESDDNS's STUN-based WAN IP detection  
✅ **No Vendor Lock-in** - Open-source, works on any Kubernetes cluster  

## How It Works with ESDDNS

```
On-Premises Network
┌────────────────────────────────────────────────────────┐
│ Kubernetes Cluster                                     │
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │ ESDDNS Operator (DaemonSet)                  │      │
│  │ • Detects WAN IP via STUN protocol           │      │
│  │ • Updates Gandi DNS with public IP           │      │
│  └──────────────────────────────────────────────┘      │
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │ ESDDNS Service (LoadBalancer)                │      │
│  │ • Type: LoadBalancer                         │      │
│  │ • MetalLB assigns IP: 192.168.1.100          │      │
│  └──────────────────────────────────────────────┘      │
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │ MetalLB Speaker (DaemonSet)                  │      │
│  │ • Advertises 192.168.1.100 on local network  │      │
│  │ • Layer 2: ARP responses                     │      │
│  │ • BGP: Routes to upstream routers            │      │
│  └──────────────────────────────────────────────┘      │
│                                                        │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
         Local Network Router
         (receives ARP/BGP)
                 │
                 ▼
            NAT Gateway
                 │
                 ▼
            Internet
         (public WAN IP)
                 │
      ┌──────────┴──────────┐
      │                     │
   STUN Servers      Gandi.net API
(detect WAN IP)   (update DNS records)
```

**Key Points:**
- **MetalLB**: Provides LoadBalancer capability on-prem (assigns local IP)
- **STUN**: Detects actual public WAN IP behind NAT
- **ESDDNS**: Updates DNS with the public IP, not the LoadBalancer IP

## Quick Start (Automated)

### One-Command Deployment

```bash
export GANDI_API_KEY="your-gandi-api-key"
cd k8s
./deploy-metallb.sh production 192.168.1.100-192.168.1.110
```

This script:
1. ✅ Checks prerequisites (kubectl, helm)
2. ✅ Installs MetalLB (via Helm or kubectl)
3. ✅ Creates IP address pool with your IP range
4. ✅ Configures Layer 2 advertisement
5. ✅ Deploys ESDDNS operator with LoadBalancer service
6. ✅ Verifies deployment and shows status

### Script Arguments

```bash
./deploy-metallb.sh [environment] [ip-range]

# Examples:
./deploy-metallb.sh production 192.168.1.100/32              # Single IP
./deploy-metallb.sh production 192.168.1.100-192.168.1.110   # IP range
./deploy-metallb.sh development 10.0.0.100/28                # CIDR notation
```

### Supported IP Range Formats

| Format | Example | Description |
|--------|---------|-------------|
| Single IP | `192.168.1.100/32` | Only one IP address |
| Range | `192.168.1.100-192.168.1.110` | Range of IPs (11 addresses) |
| CIDR | `192.168.1.0/28` | CIDR notation (16 addresses) |

**Important**: Choose IPs that are:
- On your local network subnet
- NOT assigned by DHCP
- NOT already in use by other devices

## Manual Deployment

If you prefer manual control or need to customize the configuration:

### Step 1: Install MetalLB

#### Option A: Using Helm (Recommended)

```bash
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb \
  --namespace metallb-system \
  --create-namespace
```

#### Option B: Using kubectl

```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.5/config/manifests/metallb-native.yaml
```

### Step 2: Wait for MetalLB to be Ready

```bash
kubectl wait --namespace metallb-system \
  --for=condition=ready pod \
  --selector=app=metallb \
  --timeout=90s
```

### Step 3: Create IP Address Pool

```bash
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: esddns-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.110  # Your IP range
  autoAssign: true
EOF
```

### Step 4: Configure Layer 2 Advertisement

```bash
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: esddns-l2-advertisement
  namespace: metallb-system
spec:
  ipAddressPools:
  - esddns-pool
EOF
```

### Step 5: Deploy ESDDNS

```bash
export GANDI_API_KEY="your-gandi-api-key"
cd k8s
./deploy.sh production
```

### Step 6: Verify LoadBalancer IP

```bash
kubectl get svc -n esddns-production esddns-service

# Should show something like:
# NAME             TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)
# esddns-service   LoadBalancer   10.96.123.45    192.168.1.100    80:30123/TCP
```

## Layer 2 vs BGP Mode

MetalLB supports two modes for IP advertisement:

### Layer 2 Mode (Default - Simpler)

**How it works:**
- MetalLB responds to ARP requests for the LoadBalancer IP
- Traffic is sent directly to the node running the MetalLB speaker
- Works on same subnet only

**Use when:**
- Simple network setup
- All nodes on same subnet
- No BGP infrastructure
- Small to medium deployments

**Configuration:**
```yaml
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: esddns-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - esddns-pool
```

### BGP Mode (Advanced - Enterprise)

**How it works:**
- MetalLB announces routes via BGP to your network routers
- Traffic is routed by your network infrastructure
- Supports multiple subnets and advanced routing

**Use when:**
- Enterprise network with BGP routers
- Multi-subnet deployments
- Need advanced routing features
- Large-scale deployments

**Configuration:**
```yaml
# 1. Create BGP peer
apiVersion: metallb.io/v1beta2
kind: BGPPeer
metadata:
  name: router-peer
  namespace: metallb-system
spec:
  myASN: 64500          # Your ASN
  peerASN: 64501        # Router's ASN
  peerAddress: 192.168.1.1  # Router IP

---
# 2. Create BGP advertisement
apiVersion: metallb.io/v1beta1
kind: BGPAdvertisement
metadata:
  name: esddns-bgp
  namespace: metallb-system
spec:
  ipAddressPools:
  - esddns-pool
```

## Verification & Testing

### Check MetalLB Status

```bash
# All MetalLB resources
kubectl get all -n metallb-system

# IP address pools
kubectl get ipaddresspool -n metallb-system

# L2 advertisements
kubectl get l2advertisement -n metallb-system

# MetalLB speaker logs
kubectl logs -n metallb-system -l component=speaker -f
```

### Check ESDDNS LoadBalancer

```bash
# Get service status
kubectl get svc -n esddns-production esddns-service

# Get LoadBalancer IP
EXTERNAL_IP=$(kubectl get svc -n esddns-production esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "LoadBalancer IP: $EXTERNAL_IP"

# Test endpoint
curl http://$EXTERNAL_IP/
```

### Check WAN IP Detection

```bash
# View operator logs (should show STUN detection)
kubectl logs -n esddns-production -l app=esddns-operator -f

# Look for:
# INFO STUN protocol enabled for IP discovery
# INFO [stun] Successfully obtained IP: X.X.X.X
```

## Troubleshooting

### LoadBalancer IP Stuck in "Pending"

**Symptoms:**
```bash
kubectl get svc -n esddns-production esddns-service
# EXTERNAL-IP shows <pending>
```

**Solutions:**
1. Check MetalLB is running:
   ```bash
   kubectl get pods -n metallb-system
   ```

2. Check IP address pool exists:
   ```bash
   kubectl get ipaddresspool -n metallb-system esddns-pool
   ```

3. Check speaker logs:
   ```bash
   kubectl logs -n metallb-system -l component=speaker
   ```

4. Verify IP range is available on network

### MetalLB Not Installing

**Symptoms:**
- Helm install fails
- Pods crash or don't start

**Solutions:**
1. Check Kubernetes version (1.19+ required)
2. Verify RBAC is enabled
3. Check cluster has sufficient resources
4. Review installation logs:
   ```bash
   kubectl describe pod -n metallb-system
   ```

### No Traffic Reaching Service

**Symptoms:**
- LoadBalancer IP assigned
- But curl timeout or connection refused

**Solutions:**
1. Check ESDDNS pods are running:
   ```bash
   kubectl get pods -n esddns-production
   ```

2. Port-forward to test pod directly:
   ```bash
   kubectl port-forward -n esddns-production svc/esddns-service 8080:80
   curl http://localhost:8080/
   ```

3. Check firewall rules on nodes
4. Verify service port configuration

### ARP Issues (Layer 2 Mode)

**Symptoms:**
- LoadBalancer IP assigned
- Only works from some network locations

**Solutions:**
1. Check all nodes on same subnet
2. Verify no network policies blocking ARP
3. Check switch/router ARP settings
4. Try pinging LoadBalancer IP from different hosts

### BGP Not Peering

**Symptoms:**
- BGP peer shows "not established"

**Solutions:**
1. Verify router BGP configuration
2. Check ASN numbers match
3. Verify peer IP addresses
4. Check firewall allows BGP (TCP 179)
5. Review speaker logs:
   ```bash
   kubectl logs -n metallb-system -l component=speaker | grep BGP
   ```

## WAN IP Detection with STUN

### Why STUN is Perfect for On-Prem

ESDDNS uses **STUN (Session Traversal Utilities for NAT)** protocol to detect your public WAN IP address. This is ideal for on-premises deployments because:

✅ **NAT Traversal** - Designed specifically for discovering public IPs behind NAT  
✅ **Fast** - Typically ~2x faster than HTTP-based detection  
✅ **Reliable** - RFC 8489 standard, widely supported  
✅ **Free Public Servers** - Google, Cloudflare, Twilio provide STUN infrastructure  

### How It Works

```
On-Prem Network         NAT Gateway         Internet
┌──────────────┐       ┌──────────┐       ┌─────────────────┐
│ ESDDNS Pod   │──────▶│  NAT     │──────▶│ STUN Server     │
│ Private IP:  │       │  Maps:   │       │ stun.google.com │
│ 10.0.0.5     │       │  10.0.0.5│       │                 │
│              │       │  ──▶     │       │ Response:       │
│              │       │  X.X.X.X │       │ "Your IP is     │
│              │◀──────│          │◀──────│  X.X.X.X"       │
└──────────────┘       └──────────┘       └─────────────────┘
```

1. ESDDNS pod sends STUN request to public STUN server
2. Request passes through your NAT gateway
3. STUN server sees the public source IP (your WAN IP)
4. STUN server responds with the detected public IP
5. ESDDNS updates DNS with this public IP

### STUN Configuration

STUN is enabled by default in ESDDNS. Configuration is in the ConfigMap:

```yaml
[STUNConfig]
udp_host_list_url = https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt
tcp_host_list_url = https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts_tcp.txt
bind_request = 1
magic_cookie = 554869826
xor_mapped_address = 32
udp_limit = 10
tcp_limit = 10
retry_attempts = 3
retry_cooldown_seconds = 5
```

### Fallback Chain

ESDDNS uses multiple methods with automatic fallback:

1. **STUN Protocol** (primary) - Fast, designed for NAT traversal
2. **HTTP Services** (fallback) - api.ipify.org, checkip.amazonaws.com
3. **Direct Detection** (last resort) - If external services fail

## Advanced Configuration

### Custom IP Pool Naming

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: my-custom-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.110
  autoAssign: true
  avoidBuggyIPs: true  # Skip .0 and .255
```

### Multiple IP Pools

```yaml
# Production pool
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: production-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.110

---
# Development pool
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: development-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.200-192.168.1.210
```

### Service-Specific IP Assignment

```yaml
apiVersion: v1
kind: Service
metadata:
  name: esddns-service
  annotations:
    metallb.universe.tf/address-pool: production-pool  # Specific pool
    metallb.universe.tf/loadBalancerIPs: 192.168.1.100  # Specific IP
spec:
  type: LoadBalancer
  # ... rest of service spec
```

## Production Checklist

- [ ] MetalLB installed and healthy
- [ ] IP address pool created with available IPs
- [ ] L2Advertisement or BGPAdvertisement configured
- [ ] Network team notified of IP usage
- [ ] Firewall rules allow traffic to LoadBalancer IP
- [ ] ESDDNS deployed with correct Gandi API key
- [ ] LoadBalancer IP assigned successfully
- [ ] Service responding on LoadBalancer IP
- [ ] STUN-based WAN IP detection working
- [ ] DNS updates successful in Gandi
- [ ] Prometheus metrics enabled and scraped
- [ ] Alerts configured for failures

## Useful Commands Reference

```bash
# MetalLB
kubectl get all -n metallb-system
kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system
kubectl logs -n metallb-system -l component=speaker -f

# ESDDNS
kubectl get all -n esddns-production
kubectl get svc -n esddns-production esddns-service
kubectl logs -n esddns-production -l app=esddns-operator -f
kubectl logs -n esddns-production -l app=esddns-service -f

# Get LoadBalancer IP
EXTERNAL_IP=$(kubectl get svc -n esddns-production esddns-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/

# Restart ESDDNS
kubectl rollout restart daemonset/esddns-operator-daemon -n esddns-production
kubectl rollout restart deployment/esddns-service -n esddns-production
```

## Resources

- **MetalLB Documentation**: https://metallb.universe.tf
- **ESDDNS Documentation**: [README.md](README.md)
- **STUN RFC**: https://datatracker.ietf.org/doc/html/rfc8489
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Kubernetes Operator**: [k8s/README.md](k8s/README.md)

## Support

For issues or questions:

1. Check [QUICKSTART.md troubleshooting](QUICKSTART.md#troubleshooting)
2. Review MetalLB speaker logs: `kubectl logs -n metallb-system -l component=speaker`
3. Review ESDDNS operator logs: `kubectl logs -n esddns-production -l app=esddns-operator`
4. Open GitHub issue: https://github.com/sqe/esddns/issues
