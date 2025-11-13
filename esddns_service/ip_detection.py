"""
IP Detection Service for ESDDNS
Centralizes WAN IP detection with caching to avoid redundant API calls
Used by Flask service to detect IP once, shared via ConfigMap to all DaemonSet pods
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import threading
from api.get_ip import WANIPState
from api.logs import logger as logger_wrapper

logger = logging.getLogger(__name__)
logger_wrapper_instance = logger_wrapper()


class IPDetectionService:
    """
    Singleton service for detecting and caching WAN IP.
    Prevents redundant API calls from multiple nodes.
    
    Features:
    - Caches IP with configurable TTL
    - Thread-safe operations
    - Graceful error handling
    - Metrics tracking
    """
    
    def __init__(self, cache_ttl: int = 60):
        """
        Initialize IP detection service.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 60)
        """
        self.cache_ttl = cache_ttl
        self.wan_ip_state = WANIPState()
        self._lock = threading.Lock()
        self._cache: Dict = {
            "ip": None,
            "last_detected": None,
            "detection_status": "uninitialized",
            "error_message": None,
        }
        self.metrics = {
            "detection_calls_total": 0,
            "detection_success_total": 0,
            "detection_failures_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_detection_time": None,
        }
    
    def _is_cache_fresh(self) -> bool:
        """Check if cached IP is still fresh within TTL"""
        if not self._cache["last_detected"]:
            return False
        
        age = (datetime.utcnow() - self._cache["last_detected"]).total_seconds()
        return age < self.cache_ttl
    
    def _detect_wan_ip(self) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Detect WAN IP using existing WANIPState logic.
        
        Returns:
            Tuple of (ip, success, error_message)
        """
        try:
            self.metrics["detection_calls_total"] += 1
            ip_state = self.wan_ip_state()
            
            ip = ip_state.get("wan_ip_state", {}).get("IP")
            usable = ip_state.get("wan_ip_state", {}).get("usable", False)
            
            if ip and usable:
                logger_wrapper_instance.info(f"WAN IP detected: {ip}")
                self.metrics["detection_success_total"] += 1
                return ip, True, None
            else:
                error = "IP not usable or missing"
                logger_wrapper_instance.warning(f"IP detection failed: {error}")
                self.metrics["detection_failures_total"] += 1
                return None, False, error
        
        except Exception as e:
            error = str(e)
            logger_wrapper_instance.error(f"Error detecting WAN IP: {error}")
            self.metrics["detection_failures_total"] += 1
            return None, False, error
    
    def get_wan_ip(self, force_refresh: bool = False) -> Dict:
        """
        Get current WAN IP with caching.
        
        Args:
            force_refresh: Force fresh detection, ignore cache
        
        Returns:
            Dictionary with keys:
            - ip: Detected IP address or None
            - last_detected: ISO timestamp of detection
            - age_seconds: Age of cached IP
            - fresh: Whether IP is within TTL
            - status: "success", "failed", "cache", or "stale"
            - error: Error message if failed
        """
        with self._lock:
            # Check if we can use cache
            if not force_refresh and self._is_cache_fresh():
                self.metrics["cache_hits"] += 1
                age = (datetime.utcnow() - self._cache["last_detected"]).total_seconds()
                return {
                    "ip": self._cache["ip"],
                    "last_detected": self._cache["last_detected"].isoformat(),
                    "age_seconds": int(age),
                    "fresh": True,
                    "status": "cache",
                    "error": None,
                }
            
            # Cache miss or expired - detect new IP
            self.metrics["cache_misses"] += 1
            ip, success, error = self._detect_wan_ip()
            
            if success:
                self._cache["ip"] = ip
                self._cache["last_detected"] = datetime.utcnow()
                self._cache["detection_status"] = "success"
                self._cache["error_message"] = None
                self.metrics["last_detection_time"] = datetime.utcnow().isoformat()
                
                return {
                    "ip": ip,
                    "last_detected": self._cache["last_detected"].isoformat(),
                    "age_seconds": 0,
                    "fresh": True,
                    "status": "success",
                    "error": None,
                }
            else:
                # Detection failed - return cached if available (stale)
                if self._cache["ip"]:
                    age = (datetime.utcnow() - self._cache["last_detected"]).total_seconds()
                    logger_wrapper_instance.warning(
                        f"Detection failed, using stale cache (age: {age}s)"
                    )
                    return {
                        "ip": self._cache["ip"],
                        "last_detected": self._cache["last_detected"].isoformat(),
                        "age_seconds": int(age),
                        "fresh": False,
                        "status": "stale",
                        "error": error,
                    }
                else:
                    # No cache available
                    self._cache["detection_status"] = "failed"
                    self._cache["error_message"] = error
                    
                    return {
                        "ip": None,
                        "last_detected": None,
                        "age_seconds": None,
                        "fresh": False,
                        "status": "failed",
                        "error": error,
                    }
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        with self._lock:
            return {
                "wan_ip_detection_calls_total": self.metrics["detection_calls_total"],
                "wan_ip_detection_success_total": self.metrics["detection_success_total"],
                "wan_ip_detection_failures_total": self.metrics["detection_failures_total"],
                "wan_ip_cache_hits": self.metrics["cache_hits"],
                "wan_ip_cache_misses": self.metrics["cache_misses"],
                "wan_ip_last_detection_time": self.metrics["last_detection_time"],
            }
    
    def clear_cache(self):
        """Clear cache (useful for testing)"""
        with self._lock:
            self._cache = {
                "ip": None,
                "last_detected": None,
                "detection_status": "uninitialized",
                "error_message": None,
            }


class ConfigMapIPStore:
    """
    Manages storing detected IP in Kubernetes ConfigMap.
    Allows DaemonSet pods to read single source of truth without detecting IP.
    """
    
    def __init__(self, namespace: str = "esddns-system", name: str = "esddns-wan-ip-state"):
        """
        Initialize ConfigMap IP store.
        
        Args:
            namespace: Kubernetes namespace
            name: ConfigMap name
        """
        from kubernetes import client, config
        
        self.namespace = namespace
        self.name = name
        
        try:
            config.load_incluster_config()
        except Exception:
            # Fall back for local testing
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.metrics = {
            "updates_total": 0,
            "update_failures_total": 0,
            "reads_total": 0,
            "read_failures_total": 0,
        }
    
    def update_ip(self, ip: str, status: str = "success", error: str = None) -> bool:
        """
        Update ConfigMap with detected IP.
        
        Args:
            ip: IP address to store
            status: Detection status ("success" or "failed")
            error: Error message if detection failed
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from kubernetes.client.rest import ApiException
            
            # Prepare ConfigMap data
            data = {
                "current_ip": ip or "",
                "last_update": datetime.utcnow().isoformat() + "Z",
                "detection_status": status,
                "age_seconds": "0",
            }
            
            if error:
                data["error_message"] = error
            
            # Try to read existing ConfigMap
            try:
                configmap = self.v1.read_namespaced_config_map(self.name, self.namespace)
                configmap.data = data
                self.v1.patch_namespaced_config_map(self.name, self.namespace, configmap)
                logger_wrapper_instance.debug(f"Updated ConfigMap with IP: {ip}")
            except ApiException as e:
                if e.status == 404:
                    # ConfigMap doesn't exist - create it
                    from kubernetes.client import V1ConfigMap, V1ObjectMeta
                    configmap = V1ConfigMap(
                        metadata=V1ObjectMeta(name=self.name, namespace=self.namespace),
                        data=data,
                    )
                    self.v1.create_namespaced_config_map(self.namespace, configmap)
                    logger_wrapper_instance.info(f"Created ConfigMap with IP: {ip}")
                else:
                    raise
            
            self.metrics["updates_total"] += 1
            return True
        
        except Exception as e:
            logger_wrapper_instance.error(f"Failed to update ConfigMap: {e}")
            self.metrics["update_failures_total"] += 1
            return False
    
    def get_ip(self) -> Dict:
        """
        Read IP from ConfigMap.
        
        Returns:
            Dictionary with IP and metadata or None if not found
        """
        try:
            configmap = self.v1.read_namespaced_config_map(self.name, self.namespace)
            data = configmap.data or {}
            
            self.metrics["reads_total"] += 1
            
            return {
                "ip": data.get("current_ip"),
                "last_update": data.get("last_update"),
                "status": data.get("detection_status"),
                "error": data.get("error_message"),
            }
        
        except Exception as e:
            logger_wrapper_instance.error(f"Failed to read ConfigMap: {e}")
            self.metrics["read_failures_total"] += 1
            return None
    
    def get_metrics(self) -> Dict:
        """Get ConfigMap store metrics"""
        return {
            "configmap_updates_total": self.metrics["updates_total"],
            "configmap_update_failures_total": self.metrics["update_failures_total"],
            "configmap_reads_total": self.metrics["reads_total"],
            "configmap_read_failures_total": self.metrics["read_failures_total"],
        }


# Global instances
ip_detection_service = None
configmap_store = None


def init_services(cache_ttl: int = 60):
    """Initialize global IP detection service and ConfigMap store"""
    global ip_detection_service, configmap_store
    
    if ip_detection_service is None:
        ip_detection_service = IPDetectionService(cache_ttl=cache_ttl)
    
    if configmap_store is None:
        configmap_store = ConfigMapIPStore()
    
    logger_wrapper_instance.info("IP detection services initialized")


def get_ip_detection_service() -> IPDetectionService:
    """Get global IP detection service instance"""
    global ip_detection_service
    
    if ip_detection_service is None:
        init_services()
    
    return ip_detection_service


def get_configmap_store() -> ConfigMapIPStore:
    """Get global ConfigMap store instance"""
    global configmap_store
    
    if configmap_store is None:
        init_services()
    
    return configmap_store
