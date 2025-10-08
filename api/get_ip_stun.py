"""
stun_ip_results.py

STUN-based IP provider compatible with esddns get_ip.py interface.
Provides a Provider class that fetches public IP using STUN protocol.
"""

import asyncio
import ipaddress
from time import sleep
from typing import List, Tuple, Optional
from .async_stun_discovery import AsyncSTUNDiscovery
from logs import logger as logger_wrapper


class STUNProvider:
    """
    STUN-based IP provider compatible with esddns get_ip.py Provider interface.
    
    Usage:
        provider = STUNProvider(name="stun-udp", cfgfile="dns.ini")
        ip, service = provider.get_wan_ip()
    """
    
    def __init__(self, name: str = "stun", cfgfile: str = "dns.ini") -> None:
        self.name = name
        self.cfgfile = cfgfile
        self.last_service = None
        self.discovery = AsyncSTUNDiscovery(self.cfgfile)
        self.conf = self.discovery.stun_conf
        self.retry_interval = self.conf.retry_cooldown_seconds
        self.retry_attempts = self.conf.retry_attempts
        self.logger = logger_wrapper()
    
    def retry_request(self, func):
        """
        Retry wrapper for STUN query function.
        Similar to HTTP retry_request decorator pattern.
        
        Parameters:
        -----------
        func : function
            function to retry (should return (ip, service) tuple)
        
        Returns:
        --------
        result : tuple
            (IP, service) from successful attempt, or (None, None) if all fail
        """
        for retry in range(1, self.retry_attempts + 1):
            if retry > 1:
                retry_interval = retry * self.retry_interval
                self.logger.warning(f"[{self.name}] RETRY: Attempt #{retry}; Cooldown {retry_interval} seconds")
                sleep(retry_interval)
            
            try:
                result = func()
                if result[0] is not None:  # Success - got an IP
                    return result
                else:
                    if retry < self.retry_attempts:
                        self.logger.warning(f"[{self.name}] Failed to get IP from STUN servers, will retry...")
            except Exception as e:
                if retry < self.retry_attempts:
                    self.logger.warning(f"[{self.name}] Error on attempt #{retry}: {e}, will retry...")
                else:
                    self.logger.error(f"[{self.name}] Error after {self.retry_attempts} attempts: {e}")
        
        self.logger.warning(f"[{self.name}] Failed to get IP address from STUN servers after {self.retry_attempts} attempts.")
        return None, None    
    def get_wan_ip(self, svc: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetches the public IP address using STUN protocol with retry logic.
        Compatible with esddns WANIPState.get_wan_ip() interface.
        
        Args:
            svc: Optional specific STUN server (format: "stun:host:port:udp" or "stun:host:port:tcp")
        
        Returns:
            Tuple of (IP, service) where service identifies the STUN server:port that provided the IP.
            Returns (None, service) if no IP could be obtained.
        """
        self.logger.info(f"[{self.name}] Fetching IP via STUN protocol...")
        
        def _stun_query() -> Tuple[Optional[str], Optional[str]]:
            """Inner query function to be wrapped by retry_request"""
            async def _query_stun() -> Tuple[Optional[str], Optional[str]]:
                udp_hosts = await self.discovery.load_host_list(self.conf.udp_url)
                tcp_hosts = await self.discovery.load_host_list(self.conf.tcp_url)
                
                udp_hosts = udp_hosts[:self.conf.udp_limit]
                tcp_hosts = tcp_hosts[:self.conf.tcp_limit]
                
                # Build list of (task, service_name) tuples
                queries = []
                for h, p in udp_hosts:
                    service_name = f"stun:{h}:{p}:udp"
                    self.logger.debug(f"Starting new STUN UDP query: {h}:{p}")
                    queries.append((self.discovery.query_stun_udp(h, p), service_name))
                for h, p in tcp_hosts:
                    service_name = f"stun:{h}:{p}:tcp"
                    self.logger.debug(f"Starting new STUN TCP query: {h}:{p}")
                    queries.append((self.discovery.query_stun_tcp(h, p), service_name))
                
                # Execute all queries
                results = await asyncio.gather(*[q[0] for q in queries])
                
                # Find first successful result
                for idx, (ip, port) in enumerate(results):
                    service_name = queries[idx][1]
                    if ip:
                        try:
                            ipaddress.IPv4Address(ip)
                            self.logger.info(f"[{self.name}] Successfully obtained IP: {ip} from {service_name}")
                            return ip, service_name
                        except Exception:
                            self.logger.warning(f"[{self.name}] Non-IPv4 response from {service_name}: {ip}")
                            continue
                
                return None, None
            
            return asyncio.run(_query_stun())
        
        # Using retry_request decorator pattern
        ip, service = self.retry_request(_stun_query)
        
        if ip:
            self.last_service = service
        
        return ip, service


def get_stun_ip_results(cfgfile: str = "dns.ini") -> List[Tuple[Optional[str], str]]:
    """
    Legacy function for backward compatibility.
    Returns a list of (ip, service_name) tuples from STUN queries.
    
    Args:
        cfgfile: Path to DNS/STUN config file (default 'dns.ini')
    
    Returns:
        List of tuples: (IPv4 or None, service string)
    """
    log = logger_wrapper()
    log.info("Running STUN IP queries...")
    discovery = AsyncSTUNDiscovery(cfgfile)
    conf = discovery.stun_conf
    
    async def _get_results() -> List[Tuple[Optional[str], str]]:
        udp_hosts = await discovery.load_host_list(conf.udp_url)
        tcp_hosts = await discovery.load_host_list(conf.tcp_url)
        
        log.info(f"Loaded {len(udp_hosts)} UDP hosts, {len(tcp_hosts)} TCP hosts")
        
        udp_hosts = udp_hosts[:conf.udp_limit]
        tcp_hosts = tcp_hosts[:conf.tcp_limit]
        
        async def run_query(task, svc):
            try:
                ip, _ = await task
                if ip:
                    try:
                        ipaddress.IPv4Address(ip)
                        log.info(f"Valid IPv4: {ip} from {svc}")
                        return (ip, svc)
                    except Exception:
                        log.warning(f"Non-IPv4 response from {svc}: {ip}")
                return (None, svc)
            except Exception as exc:
                log.error(f"Exception during STUN query {svc}: {exc}")
                return (None, svc)
        
        coros = []
        for h, p in udp_hosts:
            coros.append(run_query(discovery.query_stun_udp(h, p), f"stun:{h}:{p}[UDP]"))
        for h, p in tcp_hosts:
            coros.append(run_query(discovery.query_stun_tcp(h, p), f"stun:{h}:{p}[TCP]"))
        
        log.info("Starting all STUN queries...")
        results = await asyncio.gather(*coros)
        log.info("Completed all STUN queries.")
        
        return results
    
    try:
        return asyncio.run(_get_results())
    except Exception as exc:
        log.error(f"Fatal error running STUN IP queries: {exc}")
        return []


if __name__ == '__main__':
    from logs import logger as logger_wrapper
    log = logger_wrapper()
    
    log.info("Testing STUNProvider.get_wan_ip() method...")
    provider = STUNProvider(name="stun-test")
    ip, service = provider.get_wan_ip()
    
    if ip:
        log.info(f"✓ Got IP: {ip} from {service}")
    else:
        log.error("✗ Failed to get IP")
    
    log.info("\nTesting get_stun_ip_results() function...")
    results = get_stun_ip_results()
    
    successful = [r for r in results if r[0]]
    log.info(f"\n==== STUN Results ({len(successful)}/{len(results)} successful) ====")
    for ip, svc in results:
        if ip:
            log.info(f"✓ {ip:15s} <- {svc}")
    log.info("=" * 60)
