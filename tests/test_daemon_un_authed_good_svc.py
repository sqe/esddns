import unittest
from configparser import ConfigParser
import json
import os
from utils.scribe_daemon import daemon_whisper as scribe
from urllib.parse import urlparse

class DaemonUnAuthenticated(unittest.TestCase):
    """TestCase class for Daemon not authenticated scenario
        - Supplies incorrect API Key
    """

    @classmethod
    def setUpClass(self):
        os.environ["API_KEY"] = ""  # Set incorrect key
        self.config = ConfigParser()
        self.config.read("dns.ini")
        self.scribe = scribe()
        self.ip_conf = dict(self.config["WANIPState"])
        self.ip_check_services = json.loads(self.ip_conf["ip_check_services"])["svc"]
        self.gandi_conf = dict(self.config["gandi"])
        self.api_url_base = self.gandi_conf["api_url_base"]
    @classmethod
    def tearDown(self):
        pass

    def test_whisper_19(self):
        daemon_conf = dict(self.config["ESDDNS"])
        interval = int(daemon_conf["daemon_thread_interval"])
        msg = """Scheduled Daemon Thread Interval: {} seconds""".format(interval)
        assert msg in str(self.scribe[19])

    def test_whisper_21(self):
        expected_msg = "ESDDNS Standalone scheduler started!"
        whisper = str(self.scribe[21])
        assert expected_msg in whisper
        
    def test_whisper_22(self):
        expected_msg = "Running scheduled daemon thread!"
        whisper = str(self.scribe[22])
        assert expected_msg in whisper

    def test_whisper_23(self):

        expected_msg = "Starting new HTTPS connection"
        whisper =str(self.scribe[23])
        assert expected_msg in whisper

    def test_whisper_24(self):

        expected_msg = "Starting new HTTPS connection"
        whisper =str(self.scribe)
        assert expected_msg in whisper

    def test_whisper_connect_check_services(self):
        expected_msg = "Starting new HTTPS connection (1): "
        whisper = str(self.scribe)
        for check_svc in self.ip_check_services:
            assert expected_msg + str(urlparse(check_svc).hostname) in whisper

    def test_whisper_connection_success(self):
        expected_msg = 'DEBUG {}:443 "GET'
        whisper = str(self.scribe)
        for check_svc in self.ip_check_services:
            look_for = urlparse(check_svc).scheme + "://" + urlparse(check_svc).hostname 
            assert expected_msg.format(look_for) in whisper

    def test_whisper_ips_match(self):
        expected_msg = "SUCCESS: IPv4 addresses from external services match!"
        whisper = str(self.scribe)
        assert expected_msg in whisper
    
    def test_whisper_gandi_unauthed(self):
        expected_msg = 'DEBUG {}'.format(self.api_url_base) + \
            ':443 "GET /v5/livedns/domains HTTP/1.1" 401'
        whisper = str(self.scribe)
        assert expected_msg in whisper

    def test_whisper_client_401_error(self):
        expected_msg = 'CRITICAL 401 Client Error: Unauthorized for url: {}'.format(
            self.api_url_base)
        whisper = str(self.scribe)
        assert expected_msg in whisper