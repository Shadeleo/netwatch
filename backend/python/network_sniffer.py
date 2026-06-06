#!/usr/bin/env python3
"""
NetWatch — Network Traffic Sniffer
Captures and analyzes network packets on Windows using built-in APIs.
Optimized for Windows (no tcpdump/Wireshark needed).
"""

import socket
import struct
import sys
import textwrap
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

# Windows socket constants
IPPROTO_TCP = 6
IPPROTO_UDP = 17
IPPROTO_ICMP = 1


class PacketStats:
    """Statistics for network traffic."""
    
    def __init__(self):
        self.total_packets = 0
        self.total_bytes = 0
        self.protocol_counts = defaultdict(int)
        self.src_ips = defaultdict(lambda: {"bytes": 0, "packets": 0})
        self.dst_ips = defaultdict(lambda: {"bytes": 0, "packets": 0})
        self.connections = []
        self.lock = threading.Lock()
    
    def add_packet(self, src_ip: str, dst_ip: str, protocol: str, size: int, flags: str = ""):
        """Record a packet."""
        with self.lock:
            self.total_packets += 1
            self.total_bytes += size
            self.protocol_counts[protocol] += 1
            
            self.src_ips[src_ip]["bytes"] += size
            self.src_ips[src_ip]["packets"] += 1
            
            self.dst_ips[dst_ip]["bytes"] += size
            self.dst_ips[dst_ip]["packets"] += 1
            
            self.connections.append({
                "timestamp": datetime.now().isoformat(),
                "src": src_ip,
                "dst": dst_ip,
                "protocol": protocol,
                "size": size,
                "flags": flags
            })
            
            # Keep last 1000 connections
            if len(self.connections) > 1000:
                self.connections = self.connections[-1000:]
    
    def get_snapshot(self) -> Dict:
        """Get current statistics snapshot."""
        with self.lock:
            return {
                "total_packets": self.total_packets,
                "total_bytes": self.total_bytes,
                "protocols": dict(self.protocol_counts),
                "top_src_ips": sorted(
                    self.src_ips.items(),
                    key=lambda x: x[1]["bytes"],
                    reverse=True
                )[:10],
                "top_dst_ips": sorted(
                    self.dst_ips.items(),
                    key=lambda x: x[1]["bytes"],
                    reverse=True
                )[:10],
                "recent_connections": list(self.connections[-50:]),  # Ensure it's a list
                "unique_ips": len(set(list(self.src_ips.keys()) + list(self.dst_ips.keys())))
            }
    
    def reset_counters(self):
        """Reset rate counters for new interval."""
        with self.lock:
            self.total_packets = 0
            self.total_bytes = 0


class NetworkSniffer:
    """Captures network packets on Windows."""
    
    def __init__(self, interface: str = None):
        self.interface = interface or self._get_default_interface()
        self.stats = PacketStats()
        self.running = False
        
        # Rate tracking for anomaly detection
        self.last_pps = 0  # packets per second
        self.last_bps = 0  # bytes per second
        self.packet_threshold = 1000  # packets/sec threshold
        self.bytes_threshold = 100_000_000  # 100MB/s threshold
    
    def _get_default_interface(self) -> str:
        """Get default network interface on Windows."""
        try:
            # Get local hostname and IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception as e:
            print(f"Error getting default interface: {e}")
            return "0.0.0.0"
    
    def start_sniffing(self):
        """Start packet capture (Windows raw sockets)."""
        self.running = True
        
        if sys.platform == "win32":
            self._sniff_windows()
        else:
            print("Warning: Unsupported platform. Use Windows for full functionality.")
            self._mock_sniff()
    
    def _sniff_windows(self):
        """Capture packets on Windows using raw sockets."""
        # Create a raw socket on Windows
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        sock.bind((socket.gethostbyname(socket.gethostname()), 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        
        last_reset = time.time()
        
        try:
            while self.running:
                try:
                    raw_data = sock.recv(65535)
                    
                    # Parse IP header
                    src_ip, dst_ip, protocol, size = self._parse_ipv4_packet(raw_data)
                    
                    # Get flags for TCP
                    flags = ""
                    if protocol == "TCP":
                        flags = self._get_tcp_flags(raw_data)
                    
                    self.stats.add_packet(src_ip, dst_ip, protocol, size, flags)
                    
                    # Calculate rates every second
                    now = time.time()
                    if now - last_reset >= 1.0:
                        self.last_pps = self.stats.total_packets
                        self.last_bps = self.stats.total_bytes
                        self.stats.reset_counters()
                        last_reset = now
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error processing packet: {e}")
                    continue
        finally:
            sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
            sock.close()
    
    def _mock_sniff(self):
        """Mock sniffing for testing on non-Windows systems."""
        import random
        
        ips_local = [
            "192.168.1.100", "192.168.1.101", "192.168.1.102",
            "192.168.1.50", "192.168.1.200"
        ]
        ips_external = [
            "8.8.8.8", "1.1.1.1", "216.58.194.174", "142.251.41.1",
            "34.64.4.17", "44.218.184.125"
        ]
        tcp_ports = [80, 443, 3306, 5432, 22, 21, 25, 587, 8080, 8443]
        udp_ports = [53, 67, 68, 123, 5353, 5355, 5060]
        
        flags_tcp = ["SYN", "ACK", "SYN,ACK", "FIN", "RST", "FIN,ACK", "PSH,ACK"]
        
        while self.running:
            for _ in range(30):
                if not self.running:
                    break
                
                # Mix of internal and external
                if random.random() < 0.6:
                    src = random.choice(ips_local)
                    dst = random.choice(ips_external)
                else:
                    src = random.choice(ips_external)
                    dst = random.choice(ips_local)
                
                # Protocol distribution
                proto_rand = random.random()
                if proto_rand < 0.7:
                    proto = "TCP"
                    flags = random.choice(flags_tcp)
                elif proto_rand < 0.95:
                    proto = "UDP"
                    flags = ""
                else:
                    proto = "ICMP"
                    flags = ""
                
                size = random.randint(40, 1500)
                
                self.stats.add_packet(src, dst, proto, size, flags)
            
            time.sleep(1)
    
    @staticmethod
    def _parse_ipv4_packet(data: bytes) -> Tuple[str, str, str, int]:
        """Parse IPv4 packet and extract IP addresses and protocol."""
        try:
            if len(data) < 20:
                return "0.0.0.0", "0.0.0.0", "Unknown", len(data)

            version_ihl = data[0]
            version = version_ihl >> 4
            if version != 4:
                return "0.0.0.0", "0.0.0.0", f"IPv{version}", len(data)

            ttl, proto, src, dst = struct.unpack('! 8x B B 2x 4s 4s', data[:20])

            return (
                NetworkSniffer._format_ipv4(src),   # ← classe explicite, pas self
                NetworkSniffer._format_ipv4(dst),
                NetworkSniffer._format_protocol(proto),
                len(data)
            )
        except Exception as e:
            print(f"[parse_ipv4] {e}")
            return "0.0.0.0", "0.0.0.0", "Unknown", len(data)
        
    @staticmethod
    def _format_ipv4(bytes_addr: bytes) -> str:
        """Format IPv4 address from bytes."""
        return ".".join(map(str, bytes_addr))
    
    @staticmethod
    def _format_protocol(proto: int) -> str:
        """Convert protocol number to string."""
        if proto == IPPROTO_TCP:
            return "TCP"
        elif proto == IPPROTO_UDP:
            return "UDP"
        elif proto == IPPROTO_ICMP:
            return "ICMP"
        else:
            return f"Other({proto})"
    
    @staticmethod
    def _get_tcp_flags(data: bytes) -> str:
        """Extract TCP flags from packet."""
        try:
            ip_header_length = (data[0] & 15) * 4
            flags_byte = data[ip_header_length + 13]
            
            flags = []
            if flags_byte & 0x01:  # FIN
                flags.append("FIN")
            if flags_byte & 0x02:  # SYN
                flags.append("SYN")
            if flags_byte & 0x04:  # RST
                flags.append("RST")
            if flags_byte & 0x08:  # PSH
                flags.append("PSH")
            if flags_byte & 0x10:  # ACK
                flags.append("ACK")
            if flags_byte & 0x20:  # URG
                flags.append("URG")
            
            return ",".join(flags) if flags else "None"
        except Exception:
            return "Unknown"
    
    def stop_sniffing(self):
        """Stop packet capture."""
        self.running = False
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        snapshot = self.stats.get_snapshot()
        snapshot["pps"] = self.last_pps  # packets per second
        snapshot["bps"] = self.last_bps  # bytes per second
        return snapshot


if __name__ == "__main__":
    sniffer = NetworkSniffer()
    
    print("Starting NetWatch Network Sniffer...")
    print("(Run with administrator privileges on Windows)")
    
    try:
        sniffer.start_sniffing()
    except KeyboardInterrupt:
        print("\nStopping sniffer...")
        sniffer.stop_sniffing()
