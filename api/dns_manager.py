from configparser import ConfigParser
from functools import wraps
from logs import logger as logger_wrapper 
from requests.exceptions import HTTPError as HTTPError
from requests.exceptions import RequestException as RequestException
import json
import os
import requests
import sys

class DomainManagement:
    """A Class to manage DNS Domain and Records and it's state

    Methods

    __init__(self)
        Initialize variables and helpers to manage DNS domains and records

        Defaults
            `self.config` : Object instance
                ConfigParser instance
            `self.config.read('dns.ini')` : file 
                Configuration file
            `self.dns_config` : dict
                dictionary of variables of gandi section from configuration file
            `self.header_auth` : dict
                dictionary for authorization header, read key from config file
                {"Authorization": "Apikey " + self.dns_config["api_key"]}
            `self.header_content_type` : dict
                dictonary for content-type header
                {"content-type": "application/json"}
            `self.logger` : Method instance
                logger_wrapper() log wrapper instance
            `self.s` : Session instance
                requests.Session() instance
            `self.dns_record_state` : dict
                default dns record state 
                {"record_state": {"in_sync": False, "record_data": {}}}
    
    exception_handler(func)
        Exception handler decorator for HTTP requests, receives a function to run.
        Try/except wrapper function decorator handle and log exceptions.

    get_all_domains()
        Retrieves and returns all domains for your Account/Organization

    get_target_domain_url()
        Retrieves and returns target domain url from `get_all_domains()`,
        target_domain_fqdn supplied from config file
    
    get_target_domain_records()
        Retrieves and returns target domain's all records from `get_target_domain_url()`

    get_target_domain_a_records()
        Seek for target `record_type_a` and `record_name_root` supplied from 
        config file, environment variable `RECORD_NAME_ROOT` should be exported,
        return if such A record found else log 
        "Searching for the target A record" event and keep looking through 
        all records 
    
    manage_a_record(ip=None)
        Manages target DNS A record, if target A record not found from 
        `get_target_domain_a_records()` creates the target A record 
        from supplied argument`ip` and returns new A record data 

    a_record_state(ip=None)
        Manages DNS A record state. Using `manage_a_record(ip)` 
        Checks if target A record's IP is equal to the supplied argument `ip`,
        Returns updated dns_record_state setting `in_sync` to True 
        with filling record data
        If not A record's IP is not same as supplied argument `ip` returns 
        defaults `dns_record_state`

    create_record(rrset_name=None, rrset_type=None, ip=None, rrset_ttl=None)
        Creates record with supplied args
        Run with `@exception_handler` decorator

    create_a_record(ip=None)
        Creates A record via `create_record()` with supplying arguments 
        from configuration file and an IP address  
    
    overwrite_record(rrset_name=None, rrset_type=None, rrset_value=None, rrset_ttl=None)
        Since Gandi.net doesn't offer `update a record` route they have `overwrite`
        functionality to update a single recordset with supplied arguments

    update_a_record(ip=None)
        Updates single A record data with supplied IP address and argument from 
        config file  

    """
    def __init__(self):
        """Initializes DomainManagement class
        """
        self.config = ConfigParser()
        self.config.read('dns.ini')
        self.dns_config = dict(self.config["gandi"])
        self.header_auth = {"Authorization": "Apikey " + 
            os.environ[self.dns_config["api_key"]]}
        self.header_content_type = {"content-type": "application/json"}
        self.logger = logger_wrapper()
        self.s = requests.Session()
        self.dns_record_state = {"record_state": {"in_sync": False, "record_data": {}}}

    # Requests exception handler decorator
    def exception_handler(func):
        """Requests exception handling decorator

        Args
        ----
        func : function 
            Function with requests to decorate

        Returns
        -------
        Function passed throug exception handling
        If HTTP Exception caught:
            log and exit with HTTP exception
        If Base request exception caught:
            log and exit with base exception
        """
        @wraps(func)
        def wrapper(*args):
            self = args[0]
            try:
                return func(*args)
            except HTTPError as http_error:
                self.logger.critical(http_error)
                return sys.exit(http_error)
            except RequestException as base_exception:
                self.logger.critical(base_exception)
                return sys.exit(base_exception)     
        return wrapper
         
    @exception_handler
    def get_all_domains(self):
        """
        Retrieves and returns (does not display to user on purpose) 
        all domains for in Account/Organization. Constructs a request and 
        executes against https://api.gandi.net/docs/livedns/#get-v5-livedns-domains-fqdn

        Parameters
        ----------
            `url` : str 
                from config file `api_url_base` + `api_url_domains`  
            `self.header_auth` : dict
                dictionary for authorization header, read key from config file
            `HTTP Request` : type
                GET

        Returns
        -------
            dict: All domains in your Account / Organization
        """
        with self.s:
            header = self.header_auth
            url = self.dns_config["api_url_base"] + self.dns_config["api_url_domains"]
            domains_request = self.s.get(url, headers=header)
            domains_request.raise_for_status()
            domains_response = json.dumps(domains_request.json())
            self.logger.info(self.dns_config["msg_dns_get_all_domains"])
            return domains_response

    @exception_handler
    def get_target_domain_url(self):
        """Retrieves and returns target domain url from `get_all_domains()`,
        target_domain_fqdn supplied from config file
        
        Returns
        -------
            str: URL of target domain 
                - When target domain fqdn same as the one from config file

            exit: Quit ESDDNS with error message
                - When target domain fqdn is not same as the one from config file \
                Iterate over next domain, if not found from any consequential loops \
                log and exit `msg_dns_domain_not_found` from config file 

        """
        all_domains = json.loads(self.get_all_domains())
        self.logger.info(self.dns_config["msg_dns_search_domain"])
        for domain in all_domains:
            if domain["fqdn"] == os.environ[self.dns_config["target_domain_fqdn"]]:
                self.logger.info(self.dns_config["msg_dns_domain_found"].format(domain["fqdn"]))
                return domain["domain_records_href"]
            else:
                continue
        self.logger.critical(self.dns_config["msg_dns_domain_not_found"])
        return sys.exit(self.dns_config["msg_dns_domain_not_found"])

    @exception_handler
    def get_target_domain_records(self):
        """Retrieves and returns target domain's all records from \
            `get_target_domain_url()`
        Run with `@exception_handler` decorator

        Returns:
            dict: All records of the target domain
        """
        with self.s:
            header = self.header_auth
            target_domain_records_url = self.get_target_domain_url()
            records_request = self.s.get(target_domain_records_url, headers=header)
            records_response = json.dumps(records_request.json(), indent=2)
            self.logger.info(self.dns_config["msg_dns_domain_records_get"])
            return records_response
        
    @exception_handler
    def get_target_domain_a_records(self, fqdn=None):
        """Seek for target `record_type_a` and `record_name_root` supplied from 
        config file, return if such A record found else log 
        "Searching for the target A record" event and keep looking through 
        all records 

        Returns:
            dict : A record data
            - When A record's type and name match with supplied values from config
        """
        with self.s:
            all_records = json.loads(self.get_target_domain_records())
            for a_record in all_records: 
                if a_record["rrset_type"] == os.environ[self.dns_config["record_type_a"]] \
                    and a_record["rrset_name"] == os.environ[self.dns_config["record_name_root"]]:
                    self.logger.info(self.dns_config["msg_dns_domain_a_record_root_found"].format(a_record))
                    return a_record
                else:
                    self.logger.info(self.dns_config["msg_dns_domain_a_records_get"])
                    continue                    
            return

    def manage_a_record(self, ip=None):
        """Manages target DNS A record, if target A record not found from 
        `get_target_domain_a_records()` creates the target A record 
        from supplied argument `ip` and returns new A record data 

        Args:
            ip (str, optional): IP address to use to bind to A record. Defaults to None.

        Returns:
            dict: target A record data
        """
        a_records_root = self.get_target_domain_a_records()
        if a_records_root is None:
            self.logger.critical(self.dns_config["msg_dns_domain_a_record_not_found"])
            self.logger.info(self.dns_config["msg_dns_domain_a_record_root_create"])
            create_a_record, status_code, payload = self.create_a_record(ip)
            return json.loads(payload)
        else:
            return a_records_root

    def a_record_state(self, ip=None):
        """Manages DNS A record state. Using `manage_a_record(ip)` 
        Checks if target A record's IP is equal to the supplied argument `ip`,
        Returns updated dns_record_state setting `in_sync` to True 
        with filling record data
        If not A record's IP is not same as supplied argument `ip` returns 
        defaults `dns_record_state`

        Returns:
            ``{"record_state": {"in_sync": False/True, "record_data": { data/empty }}}``
            
            dict: A record state  
        """
        managed_a_record = self.manage_a_record(ip)
        a_record_ip = managed_a_record["rrset_values"][0] 
        self.logger.info(self.dns_config["msg_dns_a_record_validate"].format(
            a_record_ip, ip))
        if ip == a_record_ip:
            self.logger.info("A Record state has correct IP!")
            self.dns_record_state["record_state"]["in_sync"] = True
            self.dns_record_state["record_state"]["record_data"] = managed_a_record 
            return self.dns_record_state
        else:
            self.dns_record_state["record_state"]["record_data"] = managed_a_record 
            self.logger.warning(self.dns_config["msg_dns_a_record_state_ip_not_synced"].format(
                self.dns_record_state))
            return self.dns_record_state
        
    @exception_handler
    def create_record(self,
            fqdn=None,
            rrset_name=None,
            rrset_type=None,
            ip=None,
            rrset_ttl=None):
        """Creates record with supplied args by constructing a request against 
        https://api.gandi.net/docs/livedns/#post-v5-livedns-domains-fqdn-records
        Run with `@exception_handler` decorator

        Args:
            rrset_name (str, optional): Record name.
            rrset_type (str, optional): Record type.
            ip (str, optional): IP address.
            rrset_ttl (int, optional): TTL.
            headers (dict): Union of headers.
            POST Request (POST, default): HTTP Request type.

        Returns:
            tuple: create_request_response, create_request.status_code, payload.
                create_record request data
            exit: Quit ESDDNS with error message
                When create failed for some reason, log and exit response.
        """
        with self.s:
            header = dict(self.header_auth.items() | self.header_content_type.items())
            url = self.dns_config["api_url_base"] + \
                self.dns_config["api_url_domains"]  + \
                self.dns_config["api_url_domains_records"].format(os.environ[self.dns_config["target_domain_fqdn"]])
            payload = json.dumps({
                "rrset_name": rrset_name, 
                "rrset_type": rrset_type,
                "rrset_values": [ip],
                "rrset_ttl": int(rrset_ttl)})
            create_request = self.s.post(url, data=payload, headers=header)
            create_request_response = json.dumps(create_request.json())

            request_output = self.dns_config["msg_dns_domain_record_create"].format(
                    create_request_response, 
                    create_request.status_code, 
                    payload)
            if create_request.status_code == 201:
                self.logger.info(request_output)
                return create_request_response, create_request.status_code, payload
            else:
                self.logger.debug(request_output)
                sys.exit(request_output)

    def create_a_record(self, ip=None):
        """Creates A Record using create_record() function, supply 
        record type "A" as rrset_type.

        Args:
            ip (str, optional): IP address to use to bind to A record. Defaults to None.

        Returns:
            tuple: create_request_response, create_request.status_code, payload.
                create_record request data
            exit: Quit ESDDNS with error message
                When create failed for some reason, log and exit response.
        """
        create_a_record, status_code, payload  = self.create_record(
            os.environ[self.dns_config["target_domain_fqdn"]],
            os.environ[self.dns_config["record_name_root"]],
            os.environ[self.dns_config["record_type_a"]],
            ip,
            os.environ[self.dns_config["record_ttl"]])
        return create_a_record, status_code, payload
    
    @exception_handler
    def overwrite_record(self, 
            fqdn=None,
            rrset_name=None,  
            rrset_type=None,
            rrset_value=None,  
            rrset_ttl=None):
        """Overwrites record with supplied args by constructing a request against
        https://api.gandi.net/docs/livedns/#put-v5-livedns-domains-fqdn-records-rrset_name-rrset_type
        Run with `@exception_handler` decorator

        Args:
            fqdn (str, optional): fqdn.
            rrset_name (str, optional): Record name.
            rrset_type (str, optional): Record type.
            rrset_value (str, optional): IP address.
            rrset_ttl (int, optional): TTL.
            headers (dict): Union of headers.
            PUT Request (PUT, default): HTTP Request type.
        Returns:
            tuple: `overwrite_record_request` response and it's `status_code`
        """
        with self.s:
            header = dict(self.header_auth.items() | self.header_content_type.items())
            url = self.dns_config["api_url_base"] + \
                self.dns_config["api_url_domains"] + \
                self.dns_config["api_url_domains_records"].format(
                os.environ[self.dns_config["target_domain_fqdn"]]) + \
                "/" + rrset_name + \
                "/" + rrset_type
            payload = json.dumps({"rrset_values": [rrset_value], "rrset_ttl": rrset_ttl})
            overwrite_record_request = self.s.put(url, data=payload, headers=header)
            overwrite_record_request_response = json.dumps(overwrite_record_request.json())
            return overwrite_record_request_response, overwrite_record_request.status_code

    def update_a_record(self, ip=None):
        """Updates A record with `overwrite_record()` function, supply 
        `target_domain_fqdn`, `record_name_root`, `record_type_a`, `record_ttl` 
        from config file, and IP address from another Class to manage A record

        Args:
            ip (str, optional): IP address to use to bind to A record. Defaults to None.

        Returns:
            tuple: `update_a_record` response, and `status_code`
        """
        self.logger.info(self.dns_config["msg_dns_a_record_overwrite"])
        update_a_record, status_code = self.overwrite_record(
            os.environ[self.dns_config["target_domain_fqdn"]],
            os.environ[self.dns_config["record_name_root"]],
            os.environ[self.dns_config["record_type_a"]],
            ip,
            os.environ[self.dns_config["record_ttl"]])
        return update_a_record, status_code