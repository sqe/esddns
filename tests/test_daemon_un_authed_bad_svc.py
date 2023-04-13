import unittest
import os
from configparser import ConfigParser
import json
from utils.scribe_daemon import daemon_whisper as scribe
from urllib.parse import urlparse

class DaemonUnAuthedBadService(unittest.TestCase):
    """TestCase class for Daemon not authenticated with DNS Registrar API.
        - Mocks incorrect IP check service scenario
        - Supplies correct API key
    """
    @classmethod
    def setUpClass(self):
        self.config = ConfigParser()
        self.config.read("dns.ini")
        self.ip_conf = dict(self.config["WANIPState"])
        self.esddns_conf = dict(self.config["ESDDNS"])
        self.ip_check_services = {"svc": ["https://aapi.ipify.org/?format=text"]}
        self.config.set("WANIPState","ip_check_services", json.dumps(self.ip_check_services))
        with open("dns.ini", "w") as ini:
            self.config.write(ini)

        self.scribe = scribe()

    @classmethod
    def tearDown(self):
        orig_services = {"svc": [
        "https://api.ipify.org/?format=text", 
        "https://checkip.amazonaws.com/", 
        "https://ifconfig.me/ip"]}
        with open("dns.ini", "w") as un_ini:
            self.config.set("WANIPState","ip_check_services", json.dumps(orig_services))
            self.config.write(un_ini)
        pass

    def test_whisper_logo_footer(self):
        interval = int(self.esddns_conf["daemon_thread_interval"])
        msg = """Scheduled Daemon Thread Interval: {} seconds""".format(interval)
        whisper = str(self.scribe)
        assert msg in whisper

    def test_whisper_daemon_scheduled(self):
        whisper = str(self.scribe)
        assert self.esddns_conf["msg_daemon_scheduled"] in whisper
        
    def test_whisper_daemon_running(self):
        assert self.esddns_conf["msg_daemon_exec"] in str(self.scribe)

    def test_whisper_connect_check_services(self):
        expected_msg = "Starting new HTTPS connection (1): "
        for check_svc in self.ip_check_services["svc"]:
            assert expected_msg + str(urlparse(check_svc).hostname) in str(self.scribe)

    def test_whisper_ip_svc_connection_error(self):
        whisper = str(self.scribe[24])
        assert self.ip_conf["msg_connection_error"][:-13] in whisper 

    def test_whisper_wan_ip_state_usable_false(self):
        expected_msg = """{'wan_ip_state': {'usable': False, 'IP': {}}}"""     
        whisper = str(self.scribe[25])
        assert expected_msg in whisper