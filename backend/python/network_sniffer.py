#!/usr/bin/env python3
"""
NetWatch — Network Traffic Sniffer
Captures and analyzes network packets on Windows using built-in APIs.
Optimized for Windows (no tcpdump/Wireshark needed).
"""

import socket
import struct
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

# Protocol constants
IPPROTO_TCP  = 6
IPPROTO_UDP  = 17
IPPROTO_ICMP = 1

# Well-known port → service name
PORT_NAMES = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 67: "DHCP", 68: "DHCP",
    80: "HTTP", 110: "POP3", 123: "NTP", 143: "IMAP",
    194: "IRC", 443: "HTTPS", 445: "SMB", 465: "SMTPS",
    514: "Syslog", 587: "SMTP", 636: "LDAPS", 993: "IMAPS",
    995: "POP3S", 1080: "SOCKS", 1194: "OpenVPN",
    1433: "MSSQL", 1723: "PPTP", 3306: "MySQL",
    3389: "RDP", 4444: "Metasploit", 5353: "mDNS",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
    6881: "BitTorrent", 8080: "HTTP-alt", 8443: "HTTPS-alt",
    8888: "HTTP-alt", 9200: "Elasticsearch", 27017: "MongoDB",
}


def get_service(port: int) -> str:
    """Return service name for a port, or empty string."""
    return PORT_NAMES.get(port, "")


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

    def add_packet(self, src_ip: str, dst_ip: str, protocol: str,
                   size: int, flags: str = "",
                   src_port: int = 0, dst_port: int = 0):
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
                "src":       src_ip,
                "dst":       dst_ip,
                "src_port":  src_port,
                "dst_port":  dst_port,
                "service":   get_service(dst_port) or get_service(src_port),
                "protocol":  protocol,
                "size":      size,
                "flags":     flags,
            })

            # Keep last 1000 connections
            if len(self.connections) > 1000:
                self.connections = self.connections[-1000:]

    def get_snapshot(self) -> Dict:
        """Get current statistics snapshot."""
        with self.lock:
            return {
                "total_packets": self.total_packets,
                "total_bytes":   self.total_bytes,
                "protocols":     dict(self.protocol_counts),
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
                "recent_connections": list(self.connections[-50:]),
                "unique_ips": len(set(list(self.src_ips.keys()) +
                                      list(self.dst_ips.keys())))
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

        self.last_pps = 0
        self.last_bps = 0
        self.packet_threshold  = 1000
        self.bytes_threshold   = 100_000_000

    def _get_default_interface(self) -> str:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception as e:
            print(f"Error getting default interface: {e}")
            return "0.0.0.0"

    def start_sniffing(self):
        self.running = True
        if sys.platform == "win32":
            self._sniff_windows()
        else:
            print("Warning: Non-Windows platform detected — using mock sniffer.")
            self._mock_sniff()

    # ── Windows raw socket capture ────────────────────────────────────────
    def _sniff_windows(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        sock.bind((socket.gethostbyname(socket.gethostname()), 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

        last_reset = time.time()

        try:
            while self.running:
                try:
                    raw_data = sock.recv(65535)
                    src_ip, dst_ip, protocol, size, src_port, dst_port = \
                        self._parse_ipv4_packet(raw_data)

                    flags = ""
                    if protocol == "TCP":
                        flags = self._get_tcp_flags(raw_data)

                    self.stats.add_packet(
                        src_ip, dst_ip, protocol, size, flags,
                        src_port, dst_port
                    )

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

    # ── Mock sniffer (non-Windows / testing) ─────────────────────────────
    def _mock_sniff(self):
        import random

        ips_local    = ["192.168.1.100", "192.168.1.101", "192.168.1.102",
                        "192.168.1.50",  "192.168.1.200"]
        ips_external = ["8.8.8.8", "1.1.1.1", "216.58.194.174",
                        "142.251.41.1", "34.64.4.17", "44.218.184.125",
                        "140.82.113.21", "20.189.172.32"]
        tcp_ports    = [80, 443, 22, 3306, 5432, 8080, 8443, 587, 25, 3389]
        udp_ports    = [53, 67, 123, 5353, 5355]
        flags_tcp    = ["SYN", "ACK", "SYN,ACK", "FIN", "RST",
                        "FIN,ACK", "PSH,ACK"]

        while self.running:
            for _ in range(30):
                if not self.running:
                    break

                if random.random() < 0.6:
                    src = random.choice(ips_local)
                    dst = random.choice(ips_external)
                else:
                    src = random.choice(ips_external)
                    dst = random.choice(ips_local)

                proto_rand = random.random()
                if proto_rand < 0.70:
                    proto    = "TCP"
                    flags    = random.choice(flags_tcp)
                    src_port = random.randint(49152, 65535)
                    dst_port = random.choice(tcp_ports)
                elif proto_rand < 0.95:
                    proto    = "UDP"
                    flags    = ""
                    src_port = random.randint(49152, 65535)
                    dst_port = random.choice(udp_ports)
                else:
                    proto    = "ICMP"
                    flags    = ""
                    src_port = 0
                    dst_port = 0

                size = random.randint(40, 1500)
                self.stats.add_packet(src, dst, proto, size, flags,
                                      src_port, dst_port)

            time.sleep(1)

    # ── Packet parsers ────────────────────────────────────────────────────
    @staticmethod
    def _parse_ipv4_packet(data: bytes) -> Tuple[str, str, str, int, int, int]:
        """Parse IPv4 packet → (src_ip, dst_ip, protocol, size, src_port, dst_port)."""
        try:
            if len(data) < 20:
                return "0.0.0.0", "0.0.0.0", "Unknown", len(data), 0, 0

            version_ihl = data[0]
            version = version_ihl >> 4
            if version != 4:
                return "0.0.0.0", "0.0.0.0", f"IPv{version}", len(data), 0, 0

            ttl, proto, src, dst = struct.unpack('! 8x B B 2x 4s 4s', data[:20])
            ihl = (version_ihl & 0x0F) * 4

            src_ip   = NetworkSniffer._format_ipv4(src)
            dst_ip   = NetworkSniffer._format_ipv4(dst)
            protocol = NetworkSniffer._format_protocol(proto)

            src_port = 0
            dst_port = 0

            if proto in (IPPROTO_TCP, IPPROTO_UDP) and len(data) >= ihl + 4:
                src_port, dst_port = struct.unpack('!HH', data[ihl:ihl + 4])

            return src_ip, dst_ip, protocol, len(data), src_port, dst_port

        except Exception as e:
            print(f"[parse_ipv4] {e}")
            return "0.0.0.0", "0.0.0.0", "Unknown", len(data), 0, 0

    @staticmethod
    def _format_ipv4(bytes_addr: bytes) -> str:
        return ".".join(map(str, bytes_addr))

    @staticmethod
    def _format_protocol(proto: int) -> str:
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
        try:
            ip_header_length = (data[0] & 0x0F) * 4
            flags_byte = data[ip_header_length + 13]

            flags = []
            if flags_byte & 0x01: flags.append("FIN")
            if flags_byte & 0x02: flags.append("SYN")
            if flags_byte & 0x04: flags.append("RST")
            if flags_byte & 0x08: flags.append("PSH")
            if flags_byte & 0x10: flags.append("ACK")
            if flags_byte & 0x20: flags.append("URG")

            return ",".join(flags) if flags else "None"
        except Exception:
            return "Unknown"

    def stop_sniffing(self):
        self.running = False

    def get_stats(self) -> Dict:
        snapshot = self.stats.get_snapshot()
        snapshot["pps"] = self.last_pps
        snapshot["bps"] = self.last_bps
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