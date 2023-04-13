import unittest
import os
from configparser import ConfigParser
import json
from utils.scribe_daemon import daemon_whisper as scribe
from urllib.parse import urlparse

class DaemonAuthenticated(unittest.TestCase):
    """TestCase Class
    Contains test cases for Daemon Authenticated with DNS Registrar API 
    for synchranization.
        - Supplies correct API Key
    """
    @classmethod
    def setUpClass(self):
        self.config = ConfigParser()
        self.config.read("dns.ini")
        self.ip_conf = dict(self.config["WANIPState"])
        self.ip_check_services = json.loads(self.ip_conf["ip_check_services"])["svc"]
        self.gandi_conf = dict(self.config["gandi"])
        self.api_url_base = self.gandi_conf["api_url_base"]
        self.esddns_conf = dict(self.config["ESDDNS"])
        self.scribe = str(scribe())

    @classmethod
    def tearDown(self):
        pass

    def test_whisper_logo_footer(self):
        interval = int(self.esddns_conf["daemon_thread_interval"])
        msg = """Scheduled Daemon Thread Interval: {} seconds""".format(interval)
        assert msg in self.scribe

    def test_whisper_daemon_scheduled(self):
        assert self.esddns_conf["msg_daemon_scheduled"] in self.scribe
        
    def test_whisper_daemon_running(self):
        assert self.esddns_conf["msg_daemon_exec"] in self.scribe

    def test_whisper_connect_check_services(self):
        expected_msg = "Starting new HTTPS connection (1): "
        for check_svc in self.ip_check_services:
            assert expected_msg + str(urlparse(check_svc).hostname) in self.scribe

    def test_whisper_connection_success(self):
        expected_msg = 'DEBUG {}:443 "GET'
        for check_svc in self.ip_check_services:
            look_for = urlparse(check_svc).scheme + "://" + urlparse(check_svc).hostname 
            assert expected_msg.format(look_for) in self.scribe

    def test_whisper_ips_match(self):
        assert self.ip_conf["msg_success_from_all"][:-3] in self.scribe
    
    def test_whisper_gandi_authed(self):
        expected_msg = 'DEBUG {}'.format(self.api_url_base) + \
            ':443 "GET /v5/livedns/domains HTTP/1.1" 200'
        assert expected_msg in self.scribe
    
    def test_whisper_gandi_get_all_domains(self):
        assert self.gandi_conf["msg_dns_get_all_domains"] in self.scribe

    def test_whisper_gandi_search_target(self):
        assert self.gandi_conf["msg_dns_search_domain"] in self.scribe

    def test_whisper_gandi_target_domain_found(self):
        assert self.gandi_conf["msg_dns_domain_found"].format(
            os.environ.get("TARGET_DOMAIN_FQDN")) in self.scribe

    def test_whisper_states_are_in_sync(self):
        assert self.esddns_conf["msg_ip_dns_in_sync"][:-3] in self.scribe 