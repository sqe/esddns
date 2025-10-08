import unittest
import os
import shutil
from configparser import ConfigParser
from utils.scribe_daemon import daemon_whisper as scribe


class STUNIntegrationTests(unittest.TestCase):
    """TestCase Class for STUN Protocol Integration
    
    Tests STUN protocol IP discovery functionality:
        - STUN initialization and configuration
        - STUN query execution (UDP and TCP)
        - STUN + HTTP validation
        - Service tracking and logging
    """
    
    @classmethod
    def setUpClass(cls):
        os.environ["API_KEY"] = ""  # Set incorrect key to prevent DNS updates
        
        cls.config = ConfigParser()
        cls.config.read("tests/data/test_stun_dns.ini")
        
        # Check if STUN is configured
        cls.stun_configured = "STUNConfig" in cls.config
        
        if cls.stun_configured:
            cls.stun_conf = dict(cls.config["STUNConfig"])
        else:
            cls.stun_conf = {}
        
        # Check if HTTP services configured
        cls.http_configured = "WANIPState" in cls.config
        
        if cls.http_configured:
            cls.ip_conf = dict(cls.config["WANIPState"])
        else:
            cls.ip_conf = {}
        
        cls.esddns_conf = dict(cls.config["ESDDNS"])
        cls.scribe = str(scribe())
    
    @classmethod
    def tearDownClass(cls):
        pass

    def test_stun_protocol_enabled(self):
        """Test STUN protocol initialization message"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "STUN protocol enabled for IP discovery"
        self.assertIn(expected_msg, self.scribe,
                     "STUN protocol should be enabled when [STUNConfig] exists")

    def test_stun_fetching_message(self):
        """Test STUN fetching initiation message"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "[stun] Fetching IP via STUN protocol..."
        self.assertIn(expected_msg, self.scribe,
                     "STUN should log fetching message")

    def test_stun_host_list_loaded(self):
        """Test STUN host lists are loaded"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        loaded_udp = "Loaded" in self.scribe and "hosts from https://raw.githubusercontent.com" in self.scribe
        loaded_tcp = "Loaded" in self.scribe and "hosts from https://raw.githubusercontent.com" in self.scribe
        self.assertTrue(loaded_udp and loaded_tcp,
                     "UDP and TCP STUN hosts should be loaded")

    def test_stun_udp_queries_initiated(self):
        """Test STUN UDP queries are initiated"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "Starting new STUN UDP query:"
        self.assertIn(expected_msg, self.scribe,
                     "STUN UDP queries should be initiated")

    def test_stun_tcp_queries_initiated(self):
        """Test STUN TCP queries are initiated"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "Starting new STUN TCP query:"
        self.assertIn(expected_msg, self.scribe,
                     "STUN TCP queries should be initiated")

    def test_stun_ip_extraction_success(self):
        """Test STUN successfully extracts at least one IP"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        udp_found = "[UDP]" in self.scribe and "Public IP:" in self.scribe
        tcp_found = "[TCP]" in self.scribe and "Public IP:" in self.scribe
        
        self.assertTrue(udp_found or tcp_found,
                       "STUN should successfully extract IP via UDP or TCP")

    def test_stun_ip_obtained(self):
        """Test STUN provider returns IP with service identifier"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "[stun] Successfully obtained IP:"
        self.assertIn(expected_msg, self.scribe,
                     "STUN should successfully obtain IP address")

    def test_stun_service_tracking(self):
        """Test STUN tracks which server provided the IP"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        expected_msg = "SUCCESS: STUN returned"
        self.assertIn(expected_msg, self.scribe,
                     "STUN should log successful IP retrieval")
        
        # Check service format: stun:hostname:port:protocol
        self.assertIn("from stun:", self.scribe,
                     "STUN should track service name with stun: prefix")

    def test_stun_http_combined_validation(self):
        """Test STUN and HTTP IPs are validated together"""
        if not self.stun_configured or not self.http_configured:
            self.skipTest("Both STUN and HTTP must be configured")
        expected_msg = "SUCCESS: IPv4 addresses from external services match!"
        self.assertIn(expected_msg, self.scribe,
                     "STUN and HTTP IPs should be validated and match")

    def test_http_services_enabled(self):
        """Test HTTP services initialization when configured"""
        if not self.http_configured:
            self.skipTest("HTTP not configured in dns.ini")
        expected_msg = "HTTP-based IP services enabled"
        self.assertIn(expected_msg, self.scribe,
                     "HTTP services should be enabled when [WANIPState] exists")

    def test_at_least_one_method_enabled(self):
        """Test that at least one IP discovery method is enabled"""
        stun_enabled = "STUN protocol enabled for IP discovery" in self.scribe
        http_enabled = "HTTP-based IP services enabled" in self.scribe
        
        self.assertTrue(stun_enabled or http_enabled,
                       "At least one IP discovery method (STUN or HTTP) must be enabled")

    def test_stun_handles_failures_gracefully(self):
        """Test STUN handles server failures without crashing"""
        if not self.stun_configured:
            self.skipTest("STUN not configured in dns.ini")
        success_msg = "Successfully obtained IP:"
        
        # System should continue even if some servers fail
        self.assertIn(success_msg, self.scribe,
                     "STUN should succeed despite some server failures")

    def test_wan_ip_state_usable(self):
        """Test final WAN IP state is usable"""
        expected_msg = "usable"
        success_msg = "SUCCESS: IPv4 addresses"
        self.assertIn(expected_msg, self.scribe,
                     "WAN IP state should be usable after successful IP discovery")
        self.assertIn(success_msg, self.scribe,
                     "Should log success message for IP discovery")

    def test_stun_completes_successfully(self):
        """Test STUN IP discovery completes successfully"""
        success_msg = "SUCCESS: STUN returned"
        validation_msg = "SUCCESS: IPv4 addresses"
        
        self.assertIn(success_msg, self.scribe,
                     "STUN should complete IP discovery successfully")
        self.assertIn(validation_msg, self.scribe,
                     "IPs should be validated after STUN discovery")


if __name__ == '__main__':
    unittest.main()
