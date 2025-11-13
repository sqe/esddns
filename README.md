# [![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://stand-with-ukraine.pp.ua)

[![ESDDNS AutoTest Framework](https://github.com/sqe/esddns/actions/workflows/autotests.yaml/badge.svg)](https://github.com/sqe/esddns/actions/workflows/autotests.yaml)
[![Static Application Security Testing - CodeQL](https://github.com/sqe/esddns/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/sqe/esddns/actions/workflows/github-code-scanning/codeql)

ESDDNS
======

    --------------|----|----------
    ,---.,---.,---|,---|,---.,---.
    |---'`---.|   ||   ||   |`---.
    `---'`---'`---'`---'`   '`---'
              For Emil and Stella!

**ESDDNS** (esddns) is an Open Source Dynamic DNS solution to automatically synchronize public WAN IPv4 address with a target DNS A Record when there is a configuration drift due to IPv4 address changes.

Creates and manages dynamic states for WAN IPv4 and DNS Record.
Utilizes dynamic public WAN IPv4 address discovered and retrieved from
external IPv4 check services and STUN protocol, automatically synchronizes it with
managed DNS A record via REST APIs.

## Milestone: Kubernetes Operator with Cloud & On-Prem Support

ESDDNS now includes a production-ready **Kubernetes operator** with optimized architecture and multi-cloud support:

### Key Achievements
- **Centralized IP Detection**: Single leader detects WAN IP once → 90-95% fewer API calls
- **Distributed DNS Updates**: All nodes update DNS from cached ConfigMap → network isolation safe
- **Zero Configuration Drift**: All nodes use same detected IP source → consistent state
- **Cloud Provider Support**: AWS EKS, Google GKE, Azure AKS (automatic LoadBalancer integration)
- **On-Premises Ready**: MetalLB + STUN protocol for bare-metal Kubernetes clusters
- **High Availability**: Automatic fallback to direct detection if central detection fails
- **Full Observability**: Prometheus metrics, ServiceMonitor, and alert rules included

### Supported Deployment Scenarios

| Cloud Provider | Service Type | Load Balancer | Status |
|---|---|---|---|
| **AWS EKS** | LoadBalancer | AWS Network/Classic LB | ✅ Production-ready |
| **Google GKE** | LoadBalancer | Google Cloud LB | ✅ Production-ready |
| **Azure AKS** | LoadBalancer | Azure LB | ✅ Production-ready |
| **On-Prem (MetalLB)** | LoadBalancer | MetalLB Layer 2/BGP | ✅ Production-ready |
| **Self-Hosted** | NodePort | Manual exposure | ✅ Supported |

### MetalLB Integration for On-Premises

For bare-metal Kubernetes clusters without cloud provider support, ESDDNS works seamlessly with **MetalLB**:

```yaml
# MetalLB provides LoadBalancer service type on-prem
# Layer 2 Mode: Uses ARP for IP advertisement (simple, same-subnet only)
# BGP Mode: Full BGP advertisement (enterprise, multi-subnet support)

# Example MetalLB AddressPool
apiVersion: metallb.io/v1beta1
kind: AddressPool
metadata:
  name: esddns-pool
spec:
  addresses:
  - 192.168.1.100-192.168.1.110  # Your on-prem IP range
  autoAssign: true
```

**Why MetalLB helps for on-prem:**
- Enables LoadBalancer service type (normally cloud-only)
- BGP mode advertises service IP to your network
- Works with STUN protocol for WAN IP detection
- No proprietary vendor lock-in

📘 **See [METALLB_GUIDE.md](METALLB_GUIDE.md) for complete on-premises deployment guide**

**WAN IP Detection on On-Prem:**
- **STUN Protocol**: Best option for NAT traversal (RFC 8489 compliant)
- **HTTP Services**: If external internet access available
- **Direct Detection**: If node has public interface directly assigned
- **Fallback Chain**: Tries STUN first, falls back to HTTP, then direct detection

### Quick Deployment

```bash
# Cloud providers (AWS EKS, Google GKE, Azure AKS)
export GANDI_API_KEY="your-api-key"
cd k8s
./deploy.sh production

# On-premises with MetalLB (automated - recommended!)
export GANDI_API_KEY="your-api-key"
cd k8s
./deploy-metallb.sh production 192.168.1.100-192.168.1.110
# This script installs MetalLB + ESDDNS in one command

# Or manually:
# 1. Install MetalLB first
helm install metallb metallb/metallb -n metallb-system
# 2. Create AddressPool (see example above)
# 3. Deploy ESDDNS
./deploy.sh production
```

### Architecture Highlights

**Centralized IP Detection (Leader)**
- Kopf timer handler runs once every 5 minutes
- Uses Kopf's lock mechanism for leader election
- Stores IP in ConfigMap for all nodes to read
- Result: 1 external API call instead of N

**Distributed DNS Updates (All Nodes)**
- DaemonSet reads cached IP from ConfigMap
- Updates DNS only if IP changed
- Automatic fallback if ConfigMap unavailable/stale
- Result: No network isolation issues, consistent state

See [k8s/README.md](k8s/README.md) for detailed architecture, [OPERATOR_SUMMARY.md](OPERATOR_SUMMARY.md) for implementation details, and [README_OPERATOR.md](README_OPERATOR.md) for comprehensive documentation.

### Helm Chart Support

ESDDNS also provides **Helm charts** for simplified deployment:

```bash
# Install via Helm
helm install esddns-operator ./helm/esddns-operator \
  --namespace esddns-system \
  --create-namespace \
  --set gandi.apiKey=YOUR_GANDI_API_KEY \
  --set global.domain=yourdomain.com

# Verify
kubectl get all -n esddns-system
```

**Helm Features:**
- One-command deployment and upgrades
- Production and development value presets
- Automatic RBAC and secret management
- Published to Artifact Hub for easy discovery
- Full configuration customization via values.yaml

See [helm/README.md](helm/README.md) and [helm/esddns-operator/README.md](helm/esddns-operator/README.md) for complete Helm documentation.

### ArgoCD GitOps Support

ESDDNS integrates seamlessly with **ArgoCD** for GitOps-based deployments with environment separation:

```bash
# Deploy to development (auto-sync enabled)
kubectl apply -k argocd/dev/

# Deploy to production (manual sync only)
kubectl apply -k argocd/prod/

# Or use automated bootstrap
cd argocd/bootstrap
./argocd-setup.sh both
```

**ArgoCD Features:**
- **Environment-separated**: Dedicated dev and prod configurations
- **Helm and Kustomize support**: Choose your deployment method
- **Auto-sync for dev**: Automatic deployment on Git commits
- **Manual sync for prod**: Requires human approval for safety
- **Unified control**: Single source of truth in Git
- **Complete observability**: ArgoCD UI dashboard and CLI

See [argocd/README.md](argocd/README.md), [argocd/QUICKSTART.md](argocd/QUICKSTART.md), and [argocd/DEPLOYMENT.md](argocd/DEPLOYMENT.md) for complete ArgoCD deployment documentation.

### Complete Documentation Index

Choose your deployment path:

| Documentation | Purpose | Time Required |
|---|---|---|
| [QUICKSTART.md](QUICKSTART.md) | 60-second deploy guide | 5 minutes |
| [argocd/QUICKSTART.md](argocd/QUICKSTART.md) | **GitOps ArgoCD deployment** | **5 minutes** |
| [METALLB_GUIDE.md](METALLB_GUIDE.md) | **On-premises MetalLB deployment** | **15 minutes** |
| [k8s/DEPLOYMENT.md](k8s/DEPLOYMENT.md) | Complete installation walkthrough | 30 minutes |
| [k8s/README.md](k8s/README.md) | Architecture & features overview | 15 minutes |
| [OPERATOR_SUMMARY.md](OPERATOR_SUMMARY.md) | Implementation details | 20 minutes |
| [README_OPERATOR.md](README_OPERATOR.md) | Master index for operator | 5 minutes |
| [helm/README.md](helm/README.md) | Helm chart deployment | 10 minutes |
| [argocd/DEPLOYMENT.md](argocd/DEPLOYMENT.md) | ArgoCD comprehensive guide | 20 minutes |
| [argocd/STRUCTURE.md](argocd/STRUCTURE.md) | ArgoCD architecture details | 10 minutes |

[Documentation](https://sqe.github.io/esddns/)


## Milestone: STUN Support Added

The integration of STUN protocol in ESDDNS was made possible by a community feature request, marking a major milestone: it is the **first time STUN-based public IP detection** is available in this project.

STUN support was requested in [issue \#71](https://github.com/sqe/esddns/issues/71) by [willglynn](https://github.com/willglynn). This enhancement fulfills the need for a robust, modern method for NAT traversal and public IPv4 discovery—an essential capability for reliable dynamic DNS updates.

[Session Traversal Utilities for NAT (STUN)](https://datatracker.ietf.org/doc/html/rfc8489) is a standardized protocol for discovering the public IP address and port assigned to a device through NAT. Historically used in VoIP (e.g., SIP), STUN is now common in WebRTC, so many large tech providers operate public STUN infrastructure.

Recommended public STUN servers:

- `stun.l.google.com:19302` (Google)
- `stun.cloudflare.com:3478` (Cloudflare)
- `global.stun.twilio.com:3478` (Twilio)
- See this [public STUN server list](https://github.com/pradt2/always-online-stun/tree/master) for additional choices.

This milestone reflects ESDDNS's commitment to open development, modern standards, and responsiveness to user feedback. Special thanks to [willglynn](https://github.com/willglynn) for this important feature request.

## STUN Protocol Integration

ESDDNS now supports **STUN (Session Traversal Utilities for NAT)** protocol as a first-priority WAN IP discovery method, with automatic fallback to HTTP services.

### Features

- ✅ **RFC 8489 compliant** STUN implementation
- ✅ **Async/concurrent** queries using asyncio
- ✅ **UDP and TCP** query support with parallel execution
- ✅ **Retry logic** with exponential backoff (matching HTTP behavior)
- ✅ **Three configuration modes**: STUN-only, HTTP-only, or both
- ✅ **Faster discovery** - STUN typically ~2x faster than HTTP
- ✅ **NAT-aware** - Designed specifically for NAT traversal
- ✅ **Zero breaking changes** - Fully backward compatible


### Configuration

#### STUN + HTTP (Recommended)

Add `[STUNConfig]` section to `dns.ini`:

```ini
[STUNConfig]
udp_host_list_url = [https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt](https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt)
tcp_host_list_url = [https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts_tcp.txt](https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts_tcp.txt)
bind_request = 1
magic_cookie = 554869826
xor_mapped_address = 32
udp_limit = 10
tcp_limit = 10
retry_attempts = 3
retry_cooldown_seconds = 5
```


#### Configuration Modes

| [WANIPState] | [STUNConfig] | Behavior |
| :-- | :-- | :-- |
| ✅ Present | ✅ Present | STUN first, HTTP verification |
| ❌ Missing | ✅ Present | STUN only |
| ✅ Present | ❌ Missing | HTTP only (original) |

### Files Added

- `api/async_stun_discovery.py` - Core STUN protocol implementation
- `api/get_ip_stun.py` - STUN provider wrapper


### Expected Output

```log
2025-10-08 02:21:01,371 INFO HTTP-based IP services enabled
2025-10-08 02:21:01,371 INFO STUN protocol enabled for IP discovery
2025-10-08 02:21:01,372 INFO [stun] Fetching IP via STUN protocol...
2025-10-08 02:21:01,566 INFO Loaded 85 hosts from [https://raw.githubusercontent.com/.../valid_hosts.txt](https://raw.githubusercontent.com/.../valid_hosts.txt)
2025-10-08 02:21:01,726 INFO Loaded 85 hosts from [https://raw.githubusercontent.com/.../valid_hosts_tcp.txt](https://raw.githubusercontent.com/.../valid_hosts_tcp.txt)
2025-10-08 02:21:01,727 DEBUG Starting new STUN UDP query: stun.stochastix.de:3478
2025-10-08 02:21:01,727 DEBUG Starting new STUN UDP query: stun.healthtap.com:3478
2025-10-08 02:21:01,728 DEBUG Starting new STUN TCP query: stun.hot-chilli.net:3478
2025-10-08 02:21:01,728 DEBUG Starting new STUN TCP query: stun.3wayint.com:3478
2025-10-08 02:21:01,850 INFO [UDP] stun.healthtap.com:3478 → Public IP: 174.247.177.50, Port: 1570
2025-10-08 02:21:01,851 INFO [UDP] stun.frozenmountain.com:3478 → Public IP: 174.247.177.50, Port: 1595
2025-10-08 02:21:01,935 INFO [UDP] stun.stochastix.de:3478 → Public IP: 174.247.177.50, Port: 1592
2025-10-08 02:21:02,153 INFO [TCP] stun.thinkrosystem.com:3478 → Public IP: 174.247.177.50, Port: 3558
2025-10-08 02:21:02,196 WARNING [TCP] stun.verbo.be:3478 → XOR-MAPPED-ADDRESS not found in response.
2025-10-08 02:21:03,741 INFO [stun] Successfully obtained IP: 174.247.177.50 from stun:stun.stochastix.de:3478:udp
2025-10-08 02:21:03,744 INFO SUCCESS: STUN returned 174.247.177.50 from stun:stun.stochastix.de:3478:udp
2025-10-08 02:21:03,755 DEBUG Starting new HTTPS connection (1): checkip.amazonaws.com:443
2025-10-08 02:21:03,755 DEBUG Starting new HTTPS connection (1): ifconfig.me:443
2025-10-08 02:21:03,756 DEBUG Starting new HTTPS connection (1): api.ipify.org:443
2025-10-08 02:21:03,972 INFO "SUCCESS: [https://api.ipify.org/?format=text](https://api.ipify.org/?format=text) Returned: 174.247.177.50 as your WAN IPv4"
2025-10-08 02:21:04,191 INFO "SUCCESS: [https://checkip.amazonaws.com/](https://checkip.amazonaws.com/) Returned: 174.247.177.50 as your WAN IPv4"
2025-10-08 02:21:04,199 INFO "SUCCESS: IPv4 addresses from external services match! {'wan_ip_state': {'usable': True, 'IP': '174.247.177.50'}}"
```

Note: Failed STUN servers (like `stun.verbo.be` with `XOR-MAPPED-ADDRESS not found`) return `None` and are skipped - they don't affect validation.

### IP Validation

All IPs (from STUN and HTTP) are validated together in `wan_ip_state()`:

**Scenario 1: All Match** (1 STUN + 2 HTTP)

```python
ipaddress_list = ["174.247.177.50", "174.247.177.50", "174.247.177.50"]
→ Log: "SUCCESS: IPv4 addresses from external services match!"
```

**Scenario 2: Single Source, all others fail** (STUN only)

```python
ipaddress_list = ["174.247.177.50"]
→ Log: "SUCCESS: At least one IPv4 was collected!"
```

**Scenario 3: Mismatch** (Different IPs)

```python
ipaddress_list = ["174.247.177.50", "73.96.163.207"]
→ Log: "CRITICAL: Mismatch in IPv4 addresses" [EXITS]
```

Failed queries returning `None` are filtered out and don't affect validation.

### Performance

| Scenario | HTTP Only | STUN Only | STUN + HTTP |
| :-- | :-- | :-- | :-- |
| Success | ~2s | ~1.5s | ~3s |
| With retry | ~7s | ~6.5s | ~8s |

### Troubleshooting

**No STUN output?**

- Check for: `INFO STUN protocol enabled for IP discovery`
- If missing: Verify `[STUNConfig]` section exists in `dns.ini`

**STUN fails?**

- Check firewall allows UDP/TCP port 3478
- View retry logs: `WARNING [stun] RETRY: Attempt #2...`
- System falls back to HTTP automatically



<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: https://stand-with-ukraine.pp.ua

