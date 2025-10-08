"""
async_stun_discovery.py

Discover your public IP address and port using the STUN protocol (RFC 8489) over UDP and TCP.

This module queries current publicly-available STUN servers (auto-updated lists, HTTP via aiohttp),
and parses their responses to reveal the NAT-mapped public address for your machine. All queries run concurrently using asyncio.

References:
    - RFC 8489: Session Traversal Utilities for NAT (STUN)
      https://datatracker.ietf.org/doc/html/rfc8489

Sample usage:
    python async_stun_discovery.py

-----------------------------------------------------------------------------

Relevant RFC 8489 Example:
  00 01 00 00 21 12 a4 42 <12 random bytes>
  - 00 01 : Binding Request
  - 00 00 : No attributes
  - 21 12 a4 42 : Magic cookie
  - <12 bytes>: Random Transaction ID

-----------------------------------------------------------------------------

STUN Server Response Overview:

The STUN server sends back a Binding Success Response message:
- Header: Message Type (e.g., 0x0101), Length, Magic Cookie (0x2112A442), matching Transaction ID.
- TLV attributes follow the header.
- The XOR-MAPPED-ADDRESS attribute (0x0020) contains your public IP and port, obfuscated using the magic cookie.

-----------------------------------------------------------------------------

struct format explanations:
- '!'   : network byte order (big-endian)
- 'H'   : unsigned short (2 bytes)
- 'I'   : unsigned int (4 bytes)
- 's'   : char[] bytes array
- '!HHI12s': STUN header; '!HH': attribute type/length.

Official doc: https://docs.python.org/3/library/struct.html#format-strings

-----------------------------------------------------------------------------
"""


import asyncio
import struct
import socket
import os
from typing import List, Tuple, Optional
import aiohttp
import configparser
from logs import logger as logger_wrapper

class STUNConfig:
    """
    Loads and holds STUN variables from dns.ini [STUNConfig] section.
    Provides sane defaults if not present.
    """
    def __init__(self, cfgfile="dns.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(cfgfile)
        section = self.config["STUNConfig"] if "STUNConfig" in self.config else {}

        self.udp_url = section.get("udp_host_list_url")
        self.tcp_url = section.get("tcp_host_list_url")
        self.BINDING_REQUEST = int(section.get("bind_request", 1))
        self.MAGIC_COOKIE = int(section.get("magic_cookie", 0x2112A442))
        self.XOR_MAPPED_ADDRESS = int(section.get("xor_mapped_address", 0x20))
        self.udp_limit = int(section.get("udp_limit", 3))
        self.tcp_limit = int(section.get("tcp_limit", 3))
        self.retry_attempts = int(section.get("retry_attempts", 3))
        self.retry_cooldown_seconds = int(section.get("retry_cooldown_seconds", 5))


class AsyncSTUNDiscovery:
    """
    Async STUN client using config from dns.ini [STUNConfig].
    Call .main() for demo/testing, or use individual async methods.
    """
    def __init__(self, cfgfile="dns.ini"):
        self.stun_conf = STUNConfig(cfgfile)
        self.logger = logger_wrapper()


    def build_stun_binding_request(self) -> bytes:
        """
    Construct a RFC 8489-compliant (Section 6) STUN binding request message.

        Returns:
            bytes: 20-byte binary header to be sent as Binding Request, ready for UDP/TCP transmission.

        RFC 8489 Section 6 describes the fixed header format:
        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |0 0|     STUN Message Type     |         Message Length        |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                         Magic Cookie                          |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                                                               |
        |                     Transaction ID (96 bits)                 |
        |                                                               |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

        - Message Type = 0x0001 for Binding Request
        - Message Length = 0x0000 (no attributes included in this minimal request)
        - Magic Cookie = 0x2112A442
        - Transaction ID = 12 bytes random value for message correlation and security


        Format: struct.pack('!HHI12s', ...):
        - '!'    : network byte order (big-endian)
        - 'H'    : unsigned short (Message Type)
        - 'H'    : unsigned short (Message Length)
        - 'I'    : unsigned int (Magic Cookie)
        - '12s'  : 12-byte string (Transaction ID)
        """
        transaction_id = os.urandom(12)
        return struct.pack(
            "!HHI12s",
            self.stun_conf.BINDING_REQUEST,
            0,
            self.stun_conf.MAGIC_COOKIE,
            transaction_id,
        )    

    def parse_xor_mapped_address(self, data: bytes) -> Tuple[Optional[str], Optional[int]]:
        """
        Parses the XOR-MAPPED-ADDRESS attribute from a STUN response.

        Args:
            data (bytes): Full response message.

        Returns:
            tuple: (public_ip (str), public_port (int)), or (None, None) if not found.

        Format: attribute header is struct.unpack('!HH', ...)
        - '!': network byte order
        - 'H': attribute type (2 bytes)
        - 'H': attribute length (2 bytes)
        """
        # offset = 20
        # while offset + 4 <= len(data):
        #     attr_type, attr_len = struct.unpack('!HH', data[offset:offset+4])
        #     attr = data[offset+4:offset+4+attr_len]
        #     if attr_type == self.stun_conf.XOR_MAPPED_ADDRESS and attr_len >= 8:
        #         family = attr[1]
        #         if family == 0x01:  # IPv4
        #             x_port = struct.unpack('!H', attr[2:4])[0] ^ (self.stun_conf.MAGIC_COOKIE >> 16)
        #             x_ip = struct.unpack('!I', attr[4:8])[0] ^ self.stun_conf.MAGIC_COOKIE
        #             ip_address = socket.inet_ntoa(struct.pack('!I', x_ip))
        #             return ip_address, x_port
        #     offset += 4 + attr_len
        # return None, None 
        
        # Start after 20-byte STUN header
        offset = 20  # skip the STUN header
        while offset + 4 <= len(data):
            try:
                attr_type, attr_len = struct.unpack('!HH', data[offset:offset+4])
            except Exception:
                break  # Not enough bytes left, corrupt packet, stop
            if offset + 4 + attr_len > len(data):
                break  # Not enough bytes for full TLV, stop
            attr = data[offset+4:offset+4+attr_len]
            if attr_type == 0x0020 and attr_len >= 8:
                family = attr[1]
                if family == 0x01:  # IPv4 only
                    x_port = struct.unpack('!H', attr[2:4])[0] ^ (self.stun_conf.MAGIC_COOKIE >> 16)
                    x_ip = struct.unpack('!I', attr[4:8])[0] ^ self.stun_conf.MAGIC_COOKIE
                    ip_address = socket.inet_ntoa(struct.pack('!I', x_ip))
                    return ip_address, x_port
            offset += 4 + attr_len
        return None, None
    async def query_stun_udp(self, host: str, port: int) -> Tuple[Optional[str], Optional[int]]:
        """
        Asynchronously send a STUN Binding Request over UDP and parse the response.

        Args:
            host (str): Target STUN server hostname/IP.
            port (int): UDP port.

        Returns:
            tuple: (public_ip (str), public_port (int)), or (None, None) if failed.

        Documentation:
            Uses asyncio loop's send/recv capabilities via a DatagramProtocol transport.
            If a response arrives, parses using parse_xor_mapped_address.
        """
        req_msg = self.build_stun_binding_request()
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: STUNDatagramClient(req_msg),
            remote_addr=(host, port)
        )
        try:
            response = await protocol.get_response(timeout=2)
            ip, external_port = self.parse_xor_mapped_address(response) if response else (None, None)
            if ip and external_port:
                self.logger.info(f"[UDP] {host}:{port} → Public IP: {ip}, Port: {external_port}")
            else:
                self.logger.warning(f"[UDP] {host}:{port} → XOR-MAPPED-ADDRESS attribute not found in response.")
            return ip, external_port
        
        finally:
            transport.close()        
        # try:
        #     # Await result for up to 2s
        #     response = await protocol.get_response(timeout=2)
        #     ip, external_port = parse_xor_mapped_address(response) if response else (None, None)
        #     if ip and external_port:
        #         logging.info(f"[UDP] {host}:{port} → Public IP: {ip}, Port: {external_port}")
        #         return ip, external_port
        #     else:
        #         logging.warning(f"[UDP] {host}:{port} → XOR-MAPPED-ADDRESS attribute not found in response.")
        #         return None, None
        # except asyncio.TimeoutError:
        #     logging.error(f"[UDP] {host}:{port} → Request timed out.")
        #     return None, None
        # except Exception as exc:
        #     logging.error(f"[UDP] {host}:{port} → Exception: {exc}")
        #     return None, None
        # finally:
        #     transport.close()

    # async def query_stun_tcp(host: str, port: int) -> Tuple[Optional[str], Optional[int]]:
    #     """
    #     Asynchronously send a STUN Binding Request over TCP and parse the response.

    #     Args:
    #         host (str): Target STUN server host.
    #         port (int): Target TCP port.

    #     Returns:
    #         tuple: (public_ip (str), public_port (int)), or (None, None).

    #     Documentation:
    #         Uses asyncio streams (open_connection) for TCP I/O.
    #         Request/response is sent and received in binary form.
    #     """
    #     req_msg = build_stun_binding_request()
    #     try:
    #         reader, writer = await asyncio.open_connection(host, port)
    #         writer.write(req_msg)
    #         await writer.drain()
    #         response = await asyncio.wait_for(reader.read(2048), timeout=3)
    #         writer.close()
    #         await writer.wait_closed()
    #         ip, external_port = parse_xor_mapped_address(response) if response else (None, None)
    #         if ip and external_port:
    #             logging.info(f"[TCP] {host}:{port} → Public IP: {ip}, Port: {external_port}")
    #             return ip, external_port
    #         else:
    #             logging.warning(f"[TCP] {host}:{port} → XOR-MAPPED-ADDRESS not found in response.")
    #             return None, None
    #     except (asyncio.TimeoutError, Exception) as exc:
    #         logging.error(f"[TCP] {host}:{port} → Exception: {exc}")
    #         return None, None
    async def query_stun_tcp(self, host, port):
        """
        Asynchronously send a STUN Binding Request over TCP and parse the response.

        Args:
            host (str): Target STUN server host.
            port (int): Target TCP port.

        Returns:
            tuple: (public_ip (str), public_port (int)), or (None, None).

        Documentation:
            Uses asyncio streams (open_connection) for TCP I/O.
            Request/response is sent and received in binary form.
        """
        req_msg = self.build_stun_binding_request()
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(req_msg)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(2048), timeout=3)
            writer.close()
            await writer.wait_closed()
            ip, external_port = self.parse_xor_mapped_address(response) if response else (None, None)
            if ip and external_port:
                self.logger.info(f"[TCP] {host}:{port} → Public IP: {ip}, Port: {external_port}")
            else:
                self.logger.warning(f"[TCP] {host}:{port} → XOR-MAPPED-ADDRESS not found in response.")
            return ip, external_port
        except Exception as exc:
            self.logger.error(f"[TCP] {host}:{port} → Exception: {exc}")
            return None, None

    async def load_host_list(self, url: str) -> List[Tuple[str, int]]:
        """
        Asynchronously download and parse list of STUN servers from URL.

        Args:
            url (str): Text file with "host:port" per line.

        Returns:
            List of (host, port) tuples.

        Documentation:
            Uses aiohttp for concurrent HTTP download.
        """
        hosts = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=8) as resp:
                    lines = (await resp.text()).splitlines()
                    for line in lines:
                        line = line.strip()
                        if not line or ':' not in line: 
                            continue
                        host, port_str = line.split(':', 1)
                        try:
                            hosts.append(
                                (host, int(port_str)))
                        except Exception:
                            self.logger.warning(f"Skipping malformed line: {line}")
            self.logger.info(f"Loaded {len(hosts)} hosts from {url}")
        except Exception as exc:
            self.logger.error(f"Failed to fetch host list from {url}: {exc}")
        return hosts

    async def main(self):
        """
        Asynchronous entry point. 
        - Downloads UDP and TCP host lists (configurable in dns.ini).
        - Dispatches concurrent STUN queries to configured servers.
        - Logs each query result.

        Usage:
            python async_stun_discovery.py
        References:
            RFC 8489 Section 6.2.1, 6.2.2
        """
        udp_hosts = await self.load_host_list(self.stun_conf.udp_url)
        tcp_hosts = await self.load_host_list(self.stun_conf.tcp_url)
        udp_hosts = udp_hosts[:self.stun_conf.udp_limit]
        tcp_hosts = tcp_hosts[:self.stun_conf.tcp_limit]
        udp_tasks = [self.query_stun_udp(h, p) for h, p in udp_hosts]
        tcp_tasks = [self.query_stun_tcp(h, p) for h, p in tcp_hosts]
        await asyncio.gather(*udp_tasks, *tcp_tasks)


class STUNDatagramClient(asyncio.DatagramProtocol):
    """
    Helper for asynchronous UDP STUN exchange; stores response for further parsing.
    """
    def __init__(self, request_data: bytes):
        self.request_data = request_data
        self._response_fut = asyncio.Future()
    def connection_made(self, transport):
        transport.sendto(self.request_data)
    def datagram_received(self, data, addr):
        if not self._response_fut.done():
            self._response_fut.set_result(data)
    def error_received(self, exc):
        if not self._response_fut.done():
            self._response_fut.set_exception(exc)
    def connection_lost(self, exc):
        if not self._response_fut.done():
            self._response_fut.set_exception(exc or EOFError())

    async def get_response(self, timeout: float = 2.0) -> Optional[bytes]:
        """
        Await the response (datagram) with a timeout.
        Returns: bytes or None
        """
        try:
            return await asyncio.wait_for(self._response_fut, timeout)
        except asyncio.TimeoutError:
            return None


if __name__ == "__main__":
    asyncio.run(AsyncSTUNDiscovery().main())

