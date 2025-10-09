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
    **ESDDNS** (esddns) is an Open Source Dynamic DNS solution to automatically synchronize public
WAN IPv4 address with a target DNS A Record when there is a configuration drift
due to IPv4 address changes.

Creates and manages dynamic states for WAN IPv4 and DNS Record.
Utilizes dynamic public WAN IPv4 address discovered and retrieved from
external IPv4 check services and STUN protocol, automatically synchronizes it with
managed DNS A record via REST APIs.

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

