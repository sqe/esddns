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

class WANIPState:
    """A Class to retrieve Public WAN IP from multiple external sources 
    and return as a State

    Methods:

    __init__(self):
        Initiates Dynamic multi-threaded extraction of valid Public WAN IPs 
        from services and creates a updates the list `self.ipaddress_list` 
        upon IPv4 address discovery.

        Defaults:

            `self.config` : Object instance
                ConfigParser instance
            `self.config.read('dns.ini')`: file 
                Configuration file
            `self.ip_conf` : dict
                dictionary of variables of WANIPState section from configuration file
            `self.ip_check_services` : list 
                list from dictionary of external ip check services from self.ip_conf
            `self.retry_attempts`: int
                number of retry attempts 
            `self.retry_interval`: int
                cooldown interval, multiplied to retry attempt on each iteration
                list to store WAN IP addresses collected from supplied services
            `self.ipaddress_list`: list
                collected IPs, defaults to Empty
            `self.ips_extraction()`: method
               adds extracted IPs to discovered ipaddresses list ipaddress_list
            `self._wan_ip_state`: dict 
                defatult local mutable WAN IP State containing usable state of 
                `{"wan_ip_state" : {"usable" : False, "IP": {}}}`

    __call__(self):
        Functor to return WAN IP State when WANIPState() class is called

    retry_request(self, svc, func=None)
        Decorator for request retry function func on external service, 
        used if an external service is in flaky state but with retriable 
        http status code.
    
    get_wan_ip(sefl, svc=None)   
        Retrieves Public WAN IP from external service.
        Retries if HTTP STATUS CODE is in list:[408, 429, 449, 500, 502, 503, 504, 509]
        Gracefully exits in Request Exceptions

    ips_extraction(self)
        Dynamic multi-threaded extraction of valid Public WAN IPs from services 
        via get_wan_ip method.
        Adds extracted IPs to discovered ipaddresses list ipaddress_list
        Gracefully skips if IP is malformed, or if WAN IP is not Globally Reachable 
        https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml

    wan_ip_state(self)
        WAN IP State dictionary, contains "usable" state (True or False) and,
        Validated Globally Reachable WAN IP or empty value. Gracefully skips and exits 
        if Unable to collect any IPs or if Collected IP addresses do not match    
    """
    def __init__(self):
        """Initiates WANIPState class

        """
        # Initializing variables and class methods
        self.config = configparser.ConfigParser()
        self.config.read('dns.ini')
        self.ip_conf = dict(self.config["WANIPState"])
        self.ip_check_services = json.loads(self.ip_conf["ip_check_services"])["svc"]
        self.retry_interval = int(self.ip_conf["retry_cooldown_seconds"])
        self.retry_attempts = int(self.ip_conf["retry_attempts"])
        # Initializing logging
        self.logger = logger_wrapper()
        # Initialize HTTP Request session
        self.s = requests.Session()
        # WAN IP address list from supplied services
        self.ipaddress_list = []
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
        with ThreadPoolExecutor(max_workers=len(self.ip_check_services)) as executor:
            jobs = [executor.submit(self.get_wan_ip, svc) for svc in self.ip_check_services]
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