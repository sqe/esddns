"""
Prometheus metrics integration for ESDDNS service
Exposes metrics about DNS update operations and system health
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest
import time

# DNS Update Metrics
dns_updates_total = Counter(
    'esddns_dns_updates_total',
    'Total number of successful DNS updates',
    ['domain', 'record_type']
)

dns_update_failures_total = Counter(
    'esddns_dns_update_failures_total',
    'Total number of failed DNS update attempts',
    ['domain', 'record_type', 'error_type']
)

dns_update_duration = Histogram(
    'esddns_dns_update_duration_seconds',
    'Time taken to update DNS record',
    ['domain'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

last_dns_update_time = Gauge(
    'esddns_last_dns_update_timestamp',
    'Unix timestamp of last successful DNS update',
    ['domain']
)

# WAN IP Metrics
current_wan_ip = Gauge(
    'esddns_current_wan_ip_info',
    'Current WAN IP address (stored as label)',
    ['ip_address']
)

wan_ip_changes_total = Counter(
    'esddns_wan_ip_changes_total',
    'Total number of WAN IP address changes detected',
)

wan_ip_discovery_duration = Histogram(
    'esddns_wan_ip_discovery_duration_seconds',
    'Time taken to discover WAN IP from external services',
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0)
)

wan_ip_discovery_failures = Counter(
    'esddns_wan_ip_discovery_failures_total',
    'Total failed WAN IP discovery attempts',
    ['service']
)

# Service Health Metrics
service_health = Gauge(
    'esddns_service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['component']
)

cache_hits = Counter(
    'esddns_cache_hits_total',
    'Total number of endpoint cache hits'
)

cache_misses = Counter(
    'esddns_cache_misses_total',
    'Total number of endpoint cache misses'
)

state_poll_timestamp = Gauge(
    'esddns_state_poll_timestamp',
    'Unix timestamp of last state poll'
)

# Sync State Metrics
state_in_sync = Gauge(
    'esddns_state_in_sync',
    'Whether WAN IP and DNS record are in sync (1=yes, 0=no)',
    ['domain']
)

dns_record_ip_matches = Gauge(
    'esddns_dns_record_ip_matches',
    'Whether DNS record IP matches current WAN IP (1=yes, 0=no)',
    ['domain']
)

# Request metrics for Flask endpoints
request_duration = Histogram(
    'esddns_endpoint_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

endpoint_requests_total = Counter(
    'esddns_endpoint_requests_total',
    'Total HTTP requests to endpoints',
    ['method', 'endpoint', 'status']
)


def record_dns_update(domain, record_type, success, error_type=None, duration=None):
    """Record a DNS update attempt"""
    if success:
        dns_updates_total.labels(domain=domain, record_type=record_type).inc()
        last_dns_update_time.labels(domain=domain).set(time.time())
        state_poll_timestamp.set(time.time())
    else:
        dns_update_failures_total.labels(
            domain=domain,
            record_type=record_type,
            error_type=error_type or 'unknown'
        ).inc()
    
    if duration is not None:
        dns_update_duration.labels(domain=domain).observe(duration)


def record_wan_ip_discovery(ip, duration, success, failed_service=None):
    """Record WAN IP discovery attempt"""
    if success:
        current_wan_ip.labels(ip_address=ip).set(1)
    else:
        wan_ip_discovery_failures.labels(service=failed_service or 'unknown').inc()
    
    if duration is not None:
        wan_ip_discovery_duration.observe(duration)


def record_state_sync(domain, in_sync, ip_matches):
    """Record state sync status"""
    state_in_sync.labels(domain=domain).set(1 if in_sync else 0)
    dns_record_ip_matches.labels(domain=domain).set(1 if ip_matches else 0)
    state_poll_timestamp.set(time.time())


def set_service_health(component, healthy):
    """Set service health status"""
    service_health.labels(component=component).set(1 if healthy else 0)


def record_cache_access(hit=True):
    """Record cache hit/miss"""
    if hit:
        cache_hits.inc()
    else:
        cache_misses.inc()


def record_endpoint_request(method, endpoint, status, duration):
    """Record HTTP endpoint request"""
    endpoint_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def get_metrics():
    """Return all metrics in Prometheus format"""
    return generate_latest()
