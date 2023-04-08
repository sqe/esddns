from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from api.dns_manager import DomainManagement 
from api.get_ip import WANIPState 
from api.logs import logger as logger_wrapper
from time import sleep
import sys

class ESDDNS:
    """A Class to Synchronize WAN IP and DNS Record states

    - When ESDDNS is ran directly from shell by executing: ``python esddns.py``
    It runs in Standalone mode with Daemon Thread which's interval is set in 
    configurationfile
    
    - When imported as module, runs the Functor to return synchronized 
    dynamic union of managed WAN IP and DNS Record states
    Methods:
    
    __init__(self):
       Initiates configuration, DomainManagement class, WAN IP State class, logging
    
       Defaults
            `self.config` : Object instance
                ConfigParser instance
            `self.config.read('dns.ini')` : file 
                Configuration file
            `self.cur_conf` : dict
                dictionary of variables of ESDDNS section from configuration file
            `self.dns_manager`: Class instance
                Initializes DomainManagement class 
            `self.wan_ip_state`: Functor
                WAN IP State as dictionary
            `self.logger` : Method instance
                logger_wrapper() log wrapper instance        
    __call__(self):
        Functor to return dynamic union of managed WAN IP and DNS A Record States
        when ESDDNS() class is called

    """


    def __init__(self):
        """Initializes ESDDNS class
        """
        self.config = ConfigParser()
        self.config.read('dns.ini') 
        self.cur_conf = dict(self.config["ESDDNS"])
        self.dns_manager = DomainManagement()
        self.wan_ip_state = WANIPState()
        self.logger = logger_wrapper()

    def __call__(self):
        """Functor to return dynamic union of WAN IP and DNS A Record States

        Returns:
            functor: Returns object function ESDDNS().sync_states()
            which holds dynamic union of WAN IP and DNS A Record States 
        """
        return self.sync_states()

    def sync_states(self):
        """Manages both WAN IP and DNS A Records States for synchronization.
        Updates DNS A Record's IP address if it's out of sync.
        Logs each transaction.
        Gracefully exits if synchronization fails. 

        Returns:
        ``{'wan_ip_state': {'usable': True, 'IP': 'WAN_IP'}, 
        'record_state': {'in_sync': True, 'record_data': {data}}}``
            - dict: states union
                - When DNS Record state is in sync, 
                Union of WAN IP and DNS A Record states. 
                - When DNS A Record state is not in sync
                Updates DNS A Record IP with current WAN IP
            - exit: Quit ESDDNs with message
                If can't update DNS A record
        """
        wan_ip_state = self.wan_ip_state()
        wan_ip = wan_ip_state["wan_ip_state"]["IP"] 
        states_union = wan_ip_state | self.dns_manager.a_record_state(wan_ip)
        
        if states_union["record_state"]["in_sync"] is True:
            log_msg = self.cur_conf["msg_ip_dns_in_sync"].format(states_union)
            self.logger.info(log_msg)
            return states_union

        elif states_union["record_state"]["in_sync"] is False:
            log_msg = self.cur_conf["msg_dns_not_in_sync"].format(states_union)
            self.logger.warning(log_msg)
            self.logger.info(self.cur_conf["msg_dns_update"].format(wan_ip))
            update_rec, status_code = self.dns_manager.update_a_record(wan_ip)

            if status_code == 201:
                states_union["record_state"]["in_sync"] = True
                states_union["record_state"]["record_data"]["rrset_values"][0] = wan_ip
                log_msg = self.cur_conf["msg_dns_update_success"].format(states_union) 
                self.logger.info(log_msg)
            else:
                log_msg = self.cur_conf["msg_dns_update_fail"].format(
                    update_rec, 
                    status_code)                
                self.logger.debug(log_msg)
                sys.exit(log_msg)    
            return update_rec , states_union

if __name__ == '__main__':
    standalone_conf = ConfigParser()
    standalone_conf.read("dns.ini")
    daemon_conf = dict(standalone_conf["ESDDNS"])
    interval = int(daemon_conf["daemon_thread_interval"])
    welcome_msg = '''
    --------------|----|----------
    ,---.,---.,---|,---|,---.,---.
    |---'`---.|   ||   ||   |`---.
    `---'`---'`---'`---'`   '`---'
              For Emil and Stella!
    
    Welcome to ESDDNS Standalone mode!

    ESDDNS is an Open Source solution to automatically synchronize public 
    WAN IPv4 address with a target DNS A Record when there is a configuration drift 
    due to IPv4 address changes. 
    
    Creates and manages dynamic states for WAN IPv4 and DNS Record.  
    Utilizes dynamic public WAN IPv4 address discovered and retrieved from 
    external IPv4 check services, automatically synchronizes it with 
    managed DNS A record via REST APIs.

    ---------------------------------
    Scheduled Daemon Thread Interval: {} seconds
        '''
    logger_wrapper().info(welcome_msg.format(interval))

    logger_wrapper().info(daemon_conf["msg_daemon_scheduled"])
    while True :
        with ThreadPoolExecutor(max_workers=1) as executor:
            logger_wrapper().info(daemon_conf["msg_daemon_exec"])
            jobs = executor.submit(ESDDNS())
            result = jobs.result()
            logger_wrapper().info(daemon_conf["msg_daemon_next_exec"].format(interval))
            sleep(interval)            