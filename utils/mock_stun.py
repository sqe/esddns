"""
Mock STUN utilities for testing purposes.

This module provides mocking capabilities to simulate STUN protocol responses
without requiring actual network connections or external services during testing.
"""

from unittest.mock import patch
from typing import List, Tuple, Optional


class MockSTUNProvider:
    """
    Mock STUN provider that simulates STUN protocol behavior for testing.
    
    This class can be used to mock actual STUN server queries, providing 
    predictable responses for testing without network dependencies.
    """
    
    def __init__(self):
        """Initialize the mock STUN provider."""
        self.responses = []
        self.call_count = 0
        
    def add_response(self, ip: str, service: str):
        """
        Add a mock response to be returned by the provider.
        
        Args:
            ip (str): The mock IP address to return
            service (str): The mock service identifier 
        """
        self.responses.append((ip, service))
        
    def get_wan_ip(self, svc: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Mock implementation of get_wan_ip that returns predefined responses.
        
        Args:
            svc: Optional specific service (ignored in mock implementation)
            
        Returns:
            Tuple of (IP, service) where service identifies the mock response.
            Returns (None, None) if no responses are available.
        """
        self.call_count += 1
        
        # Return first response if available, otherwise None
        if self.responses:
            return self.responses.pop(0)
        
        # Default mock response
        return "192.168.1.100", "mock:stun.example.com:3478:udp"


class MockAsyncSTUNDiscovery:
    """
    Mock AsyncSTUNDiscovery that simulates loading host lists and querying STUN servers.
    
    This class can be used to mock the AsyncSTUNDiscovery behavior for testing.
    """
    
    def __init__(self):
        """Initialize the mock AsyncSTUNDiscovery."""
        self.host_lists = {
            "https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts.txt": [
                ("stun1.example.com", 3478),
                ("stun2.example.com", 3478)
            ],
            "https://raw.githubusercontent.com/pradt2/always-online-stun/master/valid_hosts_tcp.txt": [
                ("stuntcp1.example.com", 3478),
                ("stuntcp2.example.com", 3478)
            ]
        }
        
    async def load_host_list(self, url: str) -> List[Tuple[str, int]]:
        """
        Mock loading of host lists.
        
        Args:
            url (str): URL to load hosts from
            
        Returns:
            List of (host, port) tuples
        """
        return self.host_lists.get(url, [])
        
    async def query_stun_udp(self, host: str, port: int) -> Tuple[Optional[str], Optional[int]]:
        """
        Mock UDP STUN query.
        
        Args:
            host (str): Host to query
            port (int): Port to query
            
        Returns:
            Tuple of (IP, port) or (None, None)
        """
        return "192.168.1.100", 3478
        
    async def query_stun_tcp(self, host: str, port: int) -> Tuple[Optional[str], Optional[int]]:
        """
        Mock TCP STUN query.
        
        Args:
            host (str): Host to query
            port (int): Port to query
            
        Returns:
            Tuple of (IP, port) or (None, None)
        """
        return "192.168.1.101", 3479


# Context manager for mocking STUN functionality in tests
class MockSTUNContext:
    """
    Context manager to mock STUN functionality during tests.
    
    Usage:
        with MockSTUNContext() as mock_stun:
            # Your test code here
            pass
    """
    
    def __init__(self):
        self.mock_provider = MockSTUNProvider()
        self.mock_discovery = MockAsyncSTUNDiscovery()
        
    def __enter__(self):
        return self.mock_provider, self.mock_discovery
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass


# Utility function to set up mock responses for testing
def setup_mock_stun_responses(
    ip_addresses: List[str], 
    services: List[str] = None
) -> MockSTUNProvider:
    """
    Set up mock STUN responses for testing.
    
    Args:
        ip_addresses (List[str]): List of IP addresses to mock
        services (List[str], optional): List of service identifiers
        
    Returns:
        MockSTUNProvider: Configured mock provider
    """
    if services is None:
        services = [f"mock:stun.example.com:{10000+i}:udp" for i in range(len(ip_addresses))]
    
    mock_provider = MockSTUNProvider()
    
    # Add each IP and service as a response
    for ip, svc in zip(ip_addresses, services):
        mock_provider.add_response(ip, svc)
        
    return mock_provider


# Utility function to patch STUN modules for testing
def patch_stun_modules():
    """
    Patch the actual STUN modules with mocks for testing.
    
    Returns:
        Context manager that patches the modules
    """
    # Create mock objects for patching
    mock_provider = MockSTUNProvider()
    mock_discovery = MockAsyncSTUNDiscovery()
    
    # Create a context manager that patches the modules
    patcher = patch('esddns.api.get_ip_stun.STUNProvider', return_value=mock_provider)
    patcher2 = patch('esddns.api.get_ip_stun.AsyncSTUNDiscovery', return_value=mock_discovery)
    
    return patcher, patcher2


# Example usage in tests:
"""
# In your test file:
from esddns.utils.mock_stun import MockSTUNProvider, setup_mock_stun_responses

def test_stun_mocking():
    # Setup mock responses
    mock_provider = setup_mock_stun_responses(["192.168.1.100", "192.168.1.101"])
    
    # Use the mock in your test
    ip, service = mock_provider.get_wan_ip()
    assert ip == "192.168.1.100"
    assert service == "mock:stun.example.com:10000:udp"
"""
