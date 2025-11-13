"""
ESDDNS Kopf Operator

A Kubernetes-native operator that manages dynamic DNS updates for nodes.
Watches node IP changes and automatically updates DNS records via Gandi.net API.

Architecture:
- Centralized IP detection: Single operator instance detects WAN IP and stores in ConfigMap
- DaemonSet nodes: Read cached IP from ConfigMap, update DNS if needed
- Eliminates redundant IP detection calls and prevents drift

Deployment: DaemonSet with hostNetwork enabled
Integration: Reuses existing esddns.py and api/dns_manager.py logic
"""

import kopf
import kubernetes
import logging
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.dns_manager import DomainManagement
from api.get_ip import WANIPState
from api.logs import logger as logger_wrapper


logger = logging.getLogger(__name__)
logger_wrapper_instance = logger_wrapper()

# Constants
CONFIG_MAP_NAME = 'esddns-wan-ip'
CONFIG_MAP_NAMESPACE = 'default'
CONFIG_MAP_KEY = 'current_ip'
IP_DETECTION_INTERVAL = 300  # 5 minutes


class CentralizedIPDetector:
    """Detects WAN IP once and stores in ConfigMap (runs on single leader)"""
    
    def __init__(self):
        """Initialize IP detector"""
        self.wan_ip_state = WANIPState()
        self.k8s_client = kubernetes.client.CoreV1Api()
        self.last_detected_ip = None
    
    def get_current_ip(self):
        """Retrieve current WAN IP using existing logic"""
        try:
            ip_state = self.wan_ip_state()
            ip = ip_state.get("wan_ip_state", {}).get("IP")
            if ip and ip_state.get("wan_ip_state", {}).get("usable"):
                return ip
            return None
        except Exception as e:
            logger_wrapper_instance.error(f"Failed to retrieve WAN IP: {e}")
            return None
    
    def update_configmap(self, ip, timestamp):
        """Store detected IP in ConfigMap"""
        try:
            config_data = {
                CONFIG_MAP_KEY: ip,
                'timestamp': timestamp,
                'detected_at': datetime.now().isoformat()
            }
            
            try:
                # Try to get existing ConfigMap
                cm = self.k8s_client.read_namespaced_config_map(
                    CONFIG_MAP_NAME,
                    CONFIG_MAP_NAMESPACE
                )
                # Update existing
                cm.data = config_data
                self.k8s_client.patch_namespaced_config_map(
                    CONFIG_MAP_NAME,
                    CONFIG_MAP_NAMESPACE,
                    cm
                )
                logger_wrapper_instance.info(
                    f"Updated ConfigMap {CONFIG_MAP_NAME} with IP: {ip}"
                )
            except kubernetes.client.rest.ApiException as e:
                if e.status == 404:
                    # Create new ConfigMap
                    cm = kubernetes.client.V1ConfigMap(
                        api_version='v1',
                        kind='ConfigMap',
                        metadata=kubernetes.client.V1ObjectMeta(
                            name=CONFIG_MAP_NAME,
                            namespace=CONFIG_MAP_NAMESPACE
                        ),
                        data=config_data
                    )
                    self.k8s_client.create_namespaced_config_map(
                        CONFIG_MAP_NAMESPACE,
                        cm
                    )
                    logger_wrapper_instance.info(
                        f"Created ConfigMap {CONFIG_MAP_NAME} with IP: {ip}"
                    )
                else:
                    raise e
            return True
        
        except Exception as e:
            logger_wrapper_instance.error(f"Failed to update ConfigMap: {e}")
            return False
    
    def detect_and_store(self):
        """Detect WAN IP and store in ConfigMap"""
        try:
            ip = self.get_current_ip()
            if not ip:
                logger_wrapper_instance.warning("Unable to retrieve current IP")
                return False
            
            if ip != self.last_detected_ip:
                self.last_detected_ip = ip
                return self.update_configmap(ip, datetime.now().isoformat())
            
            # IP unchanged, but update timestamp to show health
            return self.update_configmap(ip, datetime.now().isoformat())
        
        except Exception as e:
            logger_wrapper_instance.error(f"Error detecting and storing IP: {e}")
            return False


class NodeDNSUpdater:
    """Updates DNS using cached IP from ConfigMap (runs on all nodes)"""
    
    def __init__(self):
        """Initialize DNS updater"""
        self.config = ConfigParser()
        self.config.read('dns.ini')
        self.esddns_config = dict(self.config["ESDDNS"])
        self.dns_manager = DomainManagement()
        self.wan_ip_state = WANIPState()  # Fallback detection
        self.k8s_client = kubernetes.client.CoreV1Api()
        self.last_update = None
        self.last_ip = None
        self.last_cm_check = None
        self.metrics = {
            'updates': 0,
            'failures': 0,
            'configmap_reads': 0,
            'configmap_read_failures': 0,
            'fallback_detections': 0,
            'stale_ip_warnings': 0,
            'last_update_time': None,
            'current_ip': None
        }
    
    def get_cached_ip(self):
        """Read cached IP from ConfigMap with fallback to direct detection"""
        try:
            cm = self.k8s_client.read_namespaced_config_map(
                CONFIG_MAP_NAME,
                CONFIG_MAP_NAMESPACE
            )
            self.metrics['configmap_reads'] += 1
            ip = cm.data.get(CONFIG_MAP_KEY)
            timestamp = cm.data.get('detected_at', '')
            
            if ip:
                # Check if IP is fresh (within 2x the detection interval)
                if timestamp:
                    try:
                        detected_time = datetime.fromisoformat(timestamp)
                        age = (datetime.now() - detected_time).total_seconds()
                        if age > IP_DETECTION_INTERVAL * 2:
                            logger_wrapper_instance.warning(
                                f"Cached IP is stale ({age}s old, interval: {IP_DETECTION_INTERVAL}s)"
                            )
                            self.metrics['stale_ip_warnings'] += 1
                    except Exception:
                        pass
                
                self.metrics['current_ip'] = ip
                return ip
            
            # ConfigMap exists but no IP data
            logger_wrapper_instance.warning("ConfigMap exists but contains no IP data")
            return None
            
        except kubernetes.client.rest.ApiException as e:
            if e.status == 404:
                logger_wrapper_instance.warning("ConfigMap not yet created, will use fallback detection")
            else:
                logger_wrapper_instance.error(f"Failed to read ConfigMap: {e}")
            self.metrics['configmap_read_failures'] += 1
            return None
        except Exception as e:
            logger_wrapper_instance.error(f"Unexpected error reading ConfigMap: {e}")
            self.metrics['configmap_read_failures'] += 1
            return None
    
    def fallback_detect_ip(self):
        """Fallback: detect IP directly (for bootstrap or ConfigMap unavailable)"""
        try:
            logger_wrapper_instance.warning("Using fallback IP detection (ConfigMap unavailable or stale)")
            self.metrics['fallback_detections'] += 1
            
            ip_state = self.wan_ip_state()
            ip = ip_state.get("wan_ip_state", {}).get("IP")
            if ip and ip_state.get("wan_ip_state", {}).get("usable"):
                return ip
            return None
        except Exception as e:
            logger_wrapper_instance.error(f"Fallback IP detection failed: {e}")
            return None
    
    def update_dns(self, ip):
        """Update DNS record with cached IP"""
        try:
            if not ip or ip == self.last_ip:
                logger_wrapper_instance.debug(f"IP unchanged or invalid: {ip}")
                return True
            
            logger_wrapper_instance.info(f"Updating DNS record with cached IP: {ip}")
            update_record, status_code = self.dns_manager.update_a_record(ip)
            
            if status_code == 201:
                logger_wrapper_instance.info(
                    f"Successfully updated DNS record to {ip}"
                )
                self.last_ip = ip
                self.last_update = datetime.now()
                self.metrics['updates'] += 1
                self.metrics['last_update_time'] = self.last_update.isoformat()
                return True
            else:
                logger_wrapper_instance.error(
                    f"Failed to update DNS record: Status {status_code}"
                )
                self.metrics['failures'] += 1
                return False
        
        except Exception as e:
            logger_wrapper_instance.error(f"Error updating DNS: {e}")
            self.metrics['failures'] += 1
            return False
    
    def sync_dns_from_cache(self):
        """Synchronize DNS from cached IP in ConfigMap (with fallback)"""
        try:
            # Try to get IP from ConfigMap first
            ip = self.get_cached_ip()
            
            # Fallback to direct detection if ConfigMap unavailable
            if not ip:
                logger_wrapper_instance.warning("ConfigMap IP unavailable, attempting fallback detection")
                ip = self.fallback_detect_ip()
            
            if not ip:
                logger_wrapper_instance.error("Unable to retrieve IP from ConfigMap or fallback detection")
                self.metrics['failures'] += 1
                return False
            
            return self.update_dns(ip)
        
        except Exception as e:
            logger_wrapper_instance.error(f"Error syncing DNS from cache: {e}")
            self.metrics['failures'] += 1
            return False


# Global instances
ip_detector = CentralizedIPDetector()
dns_updater = NodeDNSUpdater()


# ============================================================================
# HANDLERS - Centralized IP Detection (runs on leader pod)
# ============================================================================

@kopf.timer(
    'v1',
    'ConfigMap',
    name=CONFIG_MAP_NAME,
    interval=IP_DETECTION_INTERVAL,
    labels={'app': 'esddns-operator'}
)
def detect_wan_ip(name, **kwargs):
    """
    Centralized WAN IP detection - runs once, stores in ConfigMap.
    Uses Kopf's lock mechanism to ensure only one operator instance runs this.
    """
    try:
        logger_wrapper_instance.info("Running centralized WAN IP detection")
        success = ip_detector.detect_and_store()
        
        if success:
            kopf.info(kwargs.get('event'), "WAN IP detection and storage completed")
        else:
            kopf.warning(kwargs.get('event'), "WAN IP detection failed")
    
    except Exception as e:
        logger_wrapper_instance.error(f"Error in WAN IP detection: {e}")


# ============================================================================
# HANDLERS - Distributed DNS Updates (runs on all DaemonSet pods)
# ============================================================================

@kopf.on.event('v1', 'Node', handler='handle_node_event')
def handle_node_event(event, name, **kwargs):
    """
    Event handler for Node resource changes.
    Reads IP from ConfigMap and updates DNS if needed.
    """
    try:
        logger_wrapper_instance.info(f"Node event detected for {name}")
        
        # Sync DNS using cached IP from ConfigMap
        success = dns_updater.sync_dns_from_cache()
        
        if success:
            kopf.info(event, f"DNS sync completed for node {name}")
        else:
            kopf.warning(event, f"DNS sync failed for node {name}")
    
    except Exception as e:
        logger_wrapper_instance.error(f"Error handling node event: {e}")
        kopf.exception(event, f"Failed to handle node event: {e}")


@kopf.timer('v1', 'Node', interval=int(os.environ.get('DNS_SYNC_INTERVAL', '300')))
def periodic_dns_sync(**kwargs):
    """
    Periodic timer to check ConfigMap and sync DNS if IP changed.
    Interval configurable via DNS_SYNC_INTERVAL env var.
    """
    try:
        logger_wrapper_instance.info("Running periodic DNS sync check")
        dns_updater.sync_dns_from_cache()
    
    except Exception as e:
        logger_wrapper_instance.error(f"Error in periodic sync: {e}")


@kopf.on.update('apps/v1', 'Deployment', labels={'app': 'esddns-service'})
def handle_deployment_update(spec, name, **kwargs):
    """
    Handler for esddns-service Deployment updates.
    Ensures service remains healthy and accessible.
    """
    try:
        logger_wrapper_instance.info(f"Deployment update detected: {name}")
        
        # Verify service health
        v1 = kubernetes.client.CoreV1Api()
        service = v1.read_namespaced_service('esddns-service', 'default')
        
        if service.spec.type == 'LoadBalancer':
            if service.status.load_balancer.ingress:
                ip = service.status.load_balancer.ingress[0].ip
                logger_wrapper_instance.info(f"LoadBalancer IP: {ip}")
            else:
                logger_wrapper_instance.warning("LoadBalancer IP not yet assigned")
    
    except Exception as e:
        logger_wrapper_instance.error(f"Error handling deployment update: {e}")


# ============================================================================
# METRICS ENDPOINTS
# ============================================================================

def get_operator_metrics():
    """Return current operator metrics"""
    return {
        'dns_updates_total': dns_updater.metrics['updates'],
        'dns_update_failures_total': dns_updater.metrics['failures'],
        'last_dns_update': dns_updater.metrics['last_update_time'],
        'current_wan_ip': dns_updater.metrics['current_ip'],
    }


if __name__ == '__main__':
    # For local testing
    logger_wrapper_instance.info("ESDDNS Kopf Operator initialized")
