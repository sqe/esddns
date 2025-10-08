from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from logs import logger as logger_wrapper
from requests.exceptions import HTTPError as HTTPError
from requests.exceptions import RequestException as RequestException
from time import sleep
import configparser
import ipaddress
import json
import requests
import sys

# Optional STUN support
try:
    from .get_ip_stun import STUNProvider
    STUN_AVAILABLE = True
except ImportError as e:
    STUN_AVAILABLE = False
    import logging
    logging.getLogger(__name__).debug(f"STUN not available: {e}") 

class WANIPState:
    """A Class to retrieve Public WAN IP from multiple external sources 
    (STUN protocol and/or HTTP services) and return as a State

    IP Discovery Methods (Configurable):
    
        STUN Protocol (Optional):
            Enabled when [STUNConfig] section exists in dns.ini
            Uses RFC 8489 compliant STUN protocol over UDP and TCP
            Async/concurrent queries to multiple STUN servers
            Retry logic with exponential backoff
            Typically ~2x faster than HTTP services
            
        HTTP Services (Optional):
            Enabled when [WANIPState] section exists in dns.ini
            Multi-threaded concurrent HTTP requests to external IP check services
            Retry logic for transient failures (HTTP status codes: 408, 429, 449, 500, 502, 503, 504, 509)
            
        Note: At least one method ([STUNConfig] or [WANIPState]) must be configured.
              Both can be enabled for redundancy - STUN runs first, HTTP verifies.

    Methods:

    __init__(self):
        Initiates WANIPState class and performs IP discovery.

        Configuration Loading:
            `self.config` : ConfigParser instance
            `self.config.read('dns.ini')` : Loads configuration file
            
        HTTP Services (if [WANIPState] exists):
            `self.http_enabled` : bool - True if HTTP services configured
            `self.ip_conf` : dict - WANIPState section variables
            `self.ip_check_services` : list - External HTTP IP check service URLs
            `self.retry_attempts` : int - Number of retry attempts (default: 3)
            `self.retry_interval` : int - Cooldown interval in seconds (default: 5)
            `self.s` : requests.Session - HTTP session for requests
            
        STUN Protocol (if [STUNConfig] exists and module available):
            `self.stun_enabled` : bool - True if STUN protocol configured
            `self.stun_provider` : STUNProvider - STUN query handler
            Queries multiple STUN servers concurrently (UDP and TCP)
            Retry logic with exponential backoff
            
        Common:
            `self.ipaddress_list` : list - Collected valid IPs from all sources
            `self._wan_ip_state` : dict - `{"wan_ip_state": {"usable": False, "IP": {}}}`
            `self.ips_extraction()` : Executes IP discovery from configured sources

    __call__(self):
        Functor to return WAN IP State when WANIPState() class is called
        Returns: self.wan_ip_state()

    retry_request(self, svc, func=None)
        HTTP retry decorator for request function on external service.
        Used when HTTP service returns retriable status codes.
        
        Parameters:
            svc (str): External service URL
            func (function): Function to retry
    
    get_wan_ip(self, svc=None)   
        Retrieves Public WAN IP from external HTTP service.
        Retries if HTTP STATUS CODE is in list: [408, 429, 449, 500, 502, 503, 504, 509]
        Gracefully handles Request Exceptions
        
        Returns:
            tuple: (IP, service) - IPv4 string and service URL, or (None, service) on failure

    ips_extraction(self)
        Executes IP discovery from configured sources with priority order.
        
        Priority Order:
            1. STUN Protocol (if enabled) - Queries STUN servers with retry logic
            2. HTTP Services (if enabled) - Multi-threaded HTTP queries with retry logic
            
        Validation:
            - Validates IPv4 format using ipaddress.IPv4Address
            - Checks global reachability (filters private/reserved IPs)
            - See: https://www.iana.org/assignments/iana-ipv4-special-registry/
            
        Behavior:
            - Failed queries returning None are filtered out
            - Adds all valid IPs to self.ipaddress_list
            - Skips gracefully on malformed or non-global IPs

    wan_ip_state(self)
        Returns WAN IP State dictionary with validation of all collected IPs.
        
        Validation Logic:
            - Compares all IPs in ipaddress_list (from STUN and/or HTTP)
            - All IPs must match or only one IP collected
            
        Returns:
            dict: `{"wan_ip_state": {"usable": True/False, "IP": "x.x.x.x" or {}}}`
            
        Cases:
            Multiple IPs Match: usable=True (e.g., STUN + 2 HTTP all return same IP)
            Single IP Collected: usable=True (e.g., only STUN succeeded)
            IP Mismatch: usable=False, exits (e.g., STUN=1.2.3.4, HTTP=5.6.7.8)
            No IPs Collected: usable=False, exits
    """
    def __init__(self):
        """Initiates WANIPState class

        """
        # Initializing variables and class methods
        self.config = configparser.ConfigParser()
        self.config.read('dns.ini')
        
        # Initializing logging
        self.logger = logger_wrapper()
        
        # Check if WANIPState section exists (HTTP services)
        self.http_enabled = False
        if "WANIPState" in self.config:
            self.ip_conf = dict(self.config["WANIPState"])
            self.ip_check_services = json.loads(self.ip_conf["ip_check_services"])["svc"]
            self.retry_interval = int(self.ip_conf["retry_cooldown_seconds"])
            self.retry_attempts = int(self.ip_conf["retry_attempts"])
            self.http_enabled = True
            self.logger.info("HTTP-based IP services enabled")
        else:
            # Set defaults for when HTTP is disabled
            self.ip_conf = {
                "msg_ip_invalid": "SKIPPING: Invalid IPv4 address: {}",
                "msg_ip_non_global": "SKIPPING: IPv4 is not Globally Reachable {}",
                "msg_missmatch": "CRITICAL: {} Mismatch in IPv4 addresses {}",
                "msg_success_from_all": "SUCCESS: IPv4 addresses match! {}",
                "msg_success_from_one": "SUCCESS: IP collected! {}",
                "msg_ip_not_collected": "CRITICAL: Unable to collect IPv4 address"
            }
            self.ip_check_services = []
            self.retry_interval = 5
            self.retry_attempts = 3
            self.logger.info("HTTP-based IP services disabled (no [WANIPState] section)")
        
        # Initialize HTTP Request session (even if HTTP disabled, for potential future use)
        self.s = requests.Session()
        
        # WAN IP address list from supplied services
        self.ipaddress_list = []
        
        # Check if STUN is configured and available
        self.stun_enabled = False
        self.stun_provider = None
        if STUN_AVAILABLE and "STUNConfig" in self.config:
            try:
                self.stun_provider = STUNProvider(name="stun", cfgfile="dns.ini")
                self.stun_enabled = True
                self.logger.info("STUN protocol enabled for IP discovery")
            except Exception as e:
                self.logger.warning(f"STUN provider initialization failed: {e}, falling back to HTTP services")
        
        # Validate at least one method is enabled
        if not self.stun_enabled and not self.http_enabled:
            error_msg = "CRITICAL: Neither STUN nor HTTP IP discovery methods are configured!"
            self.logger.critical(error_msg)
            sys.exit(error_msg)
        
        self.ips_extraction()
        self._wan_ip_state = {"wan_ip_state" : {"usable" : False, "IP": {}}}

    def __call__(self):
        """Functor to return WAN IP State

        Returns:
            functor: Returns object function WANIPState.wan_ip_state()
            which holds WAN IP State dictionary when WANIPState() class is called
        """
        return self.wan_ip_state()
    def retry_request(self, svc, func=None):
        """Decorator for request retry function func on external service svc, 
        Used if an external service is in flaky state but with retriable 
        http status code.
        
        Parameters:
        -----------
        svc : str
            External service url
        func : function
            function to retry

        Defaults:
        ---------
        self.retry_attempts : int
            number of retry attempts
        self.retry_interval : int
            cooldown interval, multiplied to retry attempt on each iteration
        """
        for retry in range(1, self.retry_attempts + 1):
            self.retry_interval = retry * self.retry_interval
            self.logger.warning(self.ip_conf["msg_retry_request"].format(
                retry, self.retry_interval, svc))
            sleep(self.retry_interval)
            func

    def get_wan_ip(self, svc=None):
        """Retrieves Public WAN IP from external service.
        Retries if HTTP STATUS CODE is in list:[408, 429, 449, 500, 502, 503, 504, 509]
        Gracefully exits on Request Exceptions, skips if IP address not IPv4 compliant 

        Args
        ----
            svc: str

        Raises
        ------
            raise_for_status()
            HTTP Error Exceptions
            Request Exceptions

        Returns
        -------
            (IP, service): tuple
            if IPv4 found:  
                `('xxx.xxx.xxx.xxx', 'service')`
            if IPv4 not found or during exception handling:
                `(None, 'service')`

        Doctest
        -------
            >>> WANIPState().get_wan_ip("https://bcheckip.amazonaws.com/")
            (None, 'https://bcheckip.amazonaws.com/')

        """
        with self.s:
            try:    
                ip_check_request = self.s.get(svc)
                ip_check_request.raise_for_status()
                normalized_response = ip_check_request.text.strip("\n")
                if len(normalized_response) > 15:
                    self.logger.critical(self.ip_conf["msg_ip_non_ipv4"].format(
                        svc, normalized_response))
                    return None, svc
                self.logger.info(self.ip_conf["msg_ip_found"].format(
                    svc, normalized_response))
                return (normalized_response, svc)
            except HTTPError as http_error:
                # Retry request on following HTTP Statuses
                if http_error.response.status_code in [
                    408, 429, 449, 500, 502, 503, 504, 509]:
                    self.retry_request(svc, ip_check_request)
                log_msg = self.ip_conf["msg_http_error"].format(
                    svc, http_error.response.status_code, http_error.response.text)
                self.logger.critical(log_msg)
                return (None, svc)
            except RequestException as base_exception:
                log_msg = self.ip_conf["msg_connection_error"].format(
                    svc, base_exception)
                self.logger.critical(log_msg)
                return (None, svc)
       
    def ips_extraction(self):
        """Dynamic multi-threaded extraction of valid Public WAN IPs from services 
        via get_wan_ip method.

        Creates a concurrent worker threads for each external service in the config file
        to extract IPs addresses.
        Gracefully skips if IP is malformed, or if WAN IP is not Globally Reachable 
        https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml  

        Adds extracted IPs to discovered ipaddresses list ipaddress_list

        Defaults
        --------
        self.ip_check_services : list
            list of external IP check services from the config file
        max_workers : int
            value : length of self.ip_check_services list
            maximum amount of concurrent worker threads to utilize.
        """
        # Try STUN first if enabled
        if self.stun_enabled and self.stun_provider:
            try:
                stun_ip, stun_service = self.stun_provider.get_wan_ip()
                if stun_ip:
                    ip_address = ipaddress.IPv4Address(stun_ip)
                    if ip_address.is_global:
                        self.logger.info(f"SUCCESS: STUN returned {stun_ip} from {stun_service}")
                        self.ipaddress_list.append(stun_ip)
                    else:
                        self.logger.warning(f"STUN IP {stun_ip} is not globally reachable, trying HTTP services")
            except Exception as e:
                self.logger.warning(f"STUN query failed: {e}, falling back to HTTP services")
        
        # Proceed with HTTP services (as fallback or additional verification)
        if self.http_enabled and self.ip_check_services:
            with ThreadPoolExecutor(max_workers=len(self.ip_check_services)) as executor:
                jobs = [executor.submit(
                    self.get_wan_ip, svc) for svc in self.ip_check_services]
                for job in as_completed(jobs):
                    if job.result()[0] is None:
                        continue
                    job_result_ip, job_result_svc = job.result()
                    ip_address = ipaddress.IPv4Address(job_result_ip)
                    ip_format_check = str(ip_address)
                    if job_result_ip != ip_format_check:
                        self.logger.critical(self.ip_conf["msg_ip_invalid"].format(
                            job_result_ip))
                        continue
                    if not ip_address.is_global:
                        self.logger.critical(self.ip_conf["msg_ip_non_global"].format(
                            ip_address))
                        continue
                    self.ipaddress_list.append(job_result_ip)

    def wan_ip_state(self):
        """Returns WAN IP State dictionary, contains  usable state (True or False) and,
        Validated Globally Reachable WAN IP or empty value.

        Gracefully skips and exits if Unable to collect any IPs or if Collected IP
        addresses do not match  

        Examples:
        ---------
        WAN IP is usable: ``{'wan_ip_state': {'usable': True, 'IP': 'xxx.xxx.xxx.xxx'}``

        Else: ``{'wan_ip_state': {'usable': False, 'IP': {}}}``

        Defaults
        --------
        self.ipaddress_list : list
            list of extracted WAN IP addresses
        self._wan_ip_state: dict 
            dictionary containing usable state of collected IPs, defaults to False

        Returns
        -------
        ``{'wan_ip_state': {'usable': False / True, 'IP': {WAN IP address}}}``

            WAN IP State dictionary, contains "usable" state (True or False) and,
            Validated Globally Reachable WAN IP from collected self.ipaddress_list.

        Case A:
            Collected IP addresses don't match
            Lengh and cardinality of ip_list_uniques is not 0 or 1, simply > 1, 
            0 when no IP collected, 1 when IPs collected 
            and deduplication yields one value 
            Logs mismatch event and exits, without modifying self._wan_ip_state
            
            ``{'wan_ip_state': {'usable': False, 'IP': {}}}``
        
        Case B:
            IPs from all services match
            Cardinality of set over self.ipaddress_list is 1
            and length of the self.ipaddress_list is greater than one
            Updates self._wan_ip_state to True, for quick access return the first
            IP address from the list since the values will be same
            
            ``{'wan_ip_state': {'usable': True, 'IP': 'xxx.xxx.xxx.xxx'}}``

        Case C: 
            At least one valid IP was collected
            Length and cardinality of self.ipaddress_list and set over it yields 1
            Updates self._wan_ip_state to True, for quick access return the first
            IP address from the list since the values will be same

            ``{'wan_ip_state': {'usable': True, 'IP': 'xxx.xxx.xxx.xxx'}}``

        Case D: 
            Unable to collect IP from any services
            Length of self.ipaddress_list is 0
            Logs IP not collected event and exits, doesn't modify self._wan_ip_state

            ``{'wan_ip_state': {'usable': False, 'IP': {}}}``
        """
        ip_list_length = len(self.ipaddress_list)
        ip_list_uniques = len(set(self.ipaddress_list))
        #Critical: Collected IP addresses don't match
        if ip_list_uniques > 1:
            log_msg = self.ip_conf["msg_missmatch"].format(
                self._wan_ip_state, self.ipaddress_list)
            self.logger.warning(log_msg)
            sys.exit(log_msg)
        # Success: IPs from all services match
        elif ip_list_uniques == 1 and ip_list_length > 1:
            self._wan_ip_state["wan_ip_state"]["usable"] = True
            self._wan_ip_state["wan_ip_state"]["IP"] = self.ipaddress_list[0]
            self.logger.info(self.ip_conf["msg_success_from_all"].format(
                self._wan_ip_state))
            return self._wan_ip_state
        # Success: At least one valid IP was collected
        elif ip_list_uniques and ip_list_length == 1:
            self._wan_ip_state["wan_ip_state"]["usable"] = True
            self._wan_ip_state["wan_ip_state"]["IP"] = self.ipaddress_list[0]
            self.logger.info(self.ip_conf["msg_success_from_one"].format(
                self._wan_ip_state))
            return self._wan_ip_state
        # Critical: Unable to collect IP from any services
        elif ip_list_length == 0:
            log_msg = self._wan_ip_state, self.ip_conf["msg_ip_not_collected"].format(
                self.ip_check_services)
            self.logger.critical(log_msg)
            sys.exit(log_msg)
        return self._wan_ip_state
