#!/usr/bin/env python3
"""
NetWatch — Local Device Scanner
Discovers local devices via mDNS (port 5353) and NetBIOS (port 137).
Purely passive + targeted unicast — no aggressive ping sweep.
Results are cached in SQLite (table: local_devices).
"""

import socket
import struct
import threading
import time
import sqlite3
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from mac_resolver import get_mac_info

# ── Constants ─────────────────────────────────────────────────────────────────

MDNS_ADDR    = "224.0.0.251"
MDNS_PORT    = 5353
NETBIOS_PORT = 137
SCAN_INTERVAL_SEC = 300   # 5 minutes
DB_PATH      = Path(__file__).parent / "netwatch.db"
UTC          = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── SQLite device store ───────────────────────────────────────────────────────

class DeviceStore:
    """Thread-safe SQLite store for discovered local devices."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self._lock   = threading.Lock()
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        with self._lock:
            conn = self._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_devices (
                    ip           TEXT PRIMARY KEY,
                    name         TEXT,
                    type         TEXT,
                    method       TEXT,
                    mac          TEXT,        -- NOUVEAU
                    manufacturer TEXT,        -- NOUVEAU
                    last_seen    TEXT NOT NULL
                )
            """)
            # Migration si la table existait déjà sans ces colonnes
            for col in [("mac", "TEXT"), ("manufacturer", "TEXT")]:
                try:
                    conn.execute(f"ALTER TABLE local_devices ADD COLUMN {col[0]} {col[1]}")
                except sqlite3.OperationalError:
                    pass  # colonne déjà présente
            conn.commit()
            conn.close()

    def upsert(self, ip: str, name: str, device_type: str, method: str):
            """Insert or update a device entry."""
            with self._lock:
                conn = self._connect()
                conn.execute("""
                    INSERT INTO local_devices (ip, name, type, method, last_seen)
                    VALUES (:ip, :name, :type, :method, :last_seen)
                    ON CONFLICT(ip) DO UPDATE SET
                        name      = excluded.name,
                        type      = excluded.type,
                        method    = excluded.method,
                        last_seen = excluded.last_seen
                """, {
                    "ip":        ip,
                    "name":      name,
                    "type":      device_type,
                    "method":    method,
                    "last_seen": _utcnow().isoformat(),
                })
                conn.commit()
                conn.close()    

    def set_mac(self, ip: str, mac: str, manufacturer: str):
            """Stocke (ou met à jour) le MAC et le fabricant pour un IP."""
            with self._lock:
                conn = self._connect()
                # Crée la ligne si elle n'existe pas encore
                conn.execute("""
                    INSERT OR IGNORE INTO local_devices (ip, name, type, method, last_seen)
                    VALUES (?, NULL, 'unknown', 'arp', ?)
                """, (ip, _utcnow().isoformat()))
                # Met à jour mac + manufacturer
                conn.execute("""
                    UPDATE local_devices
                    SET mac=?, manufacturer=?, last_seen=?
                    WHERE ip=?
                """, (mac, manufacturer, _utcnow().isoformat(), ip))
                conn.commit()
                conn.close()    

    def get_all(self) -> list[dict]:
        """Return all known devices."""
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM local_devices ORDER BY ip"
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]

    def get(self, ip: str) -> Optional[dict]:
        """Return a single device by IP, or None."""
        with self._lock:
            conn = self._connect()
            row  = conn.execute(
                "SELECT * FROM local_devices WHERE ip = ?", (ip,)
            ).fetchone()
            conn.close()
        return dict(row) if row else None


# ── mDNS scanner ──────────────────────────────────────────────────────────────

class MDNSScanner:
    """
    Listens passively on the mDNS multicast group (224.0.0.251:5353)
    and also sends PTR queries for devices seen by the sniffer.
    Extracts hostnames from mDNS responses.
    """

    # DNS response flags mask
    _QR_FLAG = 0x8000

    def __init__(self, store: DeviceStore):
        self.store   = store
        self._sock   = None
        self._running = False

    def start(self):
        """Start passive mDNS listener in a daemon thread."""
        self._running = True
        t = threading.Thread(target=self._listen, daemon=True, name="mdns-listener")
        t.start()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def query(self, ip: str):
        """Send a targeted PTR query for a single IP (non-blocking)."""
        threading.Thread(
            target=self._ptr_query,
            args=(ip,),
            daemon=True,
            name=f"mdns-query-{ip}"
        ).start()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _listen(self):
        """Passive multicast listener."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass  # SO_REUSEPORT not available on Windows

            sock.bind(("", MDNS_PORT))

            # Join multicast group
            mreq = struct.pack("4sL",
                socket.inet_aton(MDNS_ADDR),
                socket.INADDR_ANY
            )
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(2.0)
            self._sock = sock

            while self._running:
                try:
                    data, addr = sock.recvfrom(4096)
                    src_ip = addr[0]
                    self._parse_mdns(data, src_ip)
                except socket.timeout:
                    continue
                except OSError:
                    break

        except PermissionError:
            print("[mDNS] Permission denied — run as administrator for mDNS capture")
        except Exception as e:
            print(f"[mDNS] Listener error: {e}")

    def _ptr_query(self, ip: str):
        """Send a unicast PTR query to a specific IP."""
        try:
            # Build reverse DNS name: 1.2.3.192 → 192.3.2.1.in-addr.arpa
            reversed_ip = ".".join(reversed(ip.split(".")))
            name        = f"{reversed_ip}.in-addr.arpa"

            query = self._build_ptr_query(name)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(query, (ip, MDNS_PORT))

            try:
                data, _ = sock.recvfrom(4096)
                self._parse_mdns(data, ip)
            except socket.timeout:
                pass
            finally:
                sock.close()

        except Exception:
            pass  # Silently ignore unreachable hosts

    def _build_ptr_query(self, name: str) -> bytes:
        """Build a minimal DNS PTR query packet."""
        # Header: ID=0, flags=0 (query), 1 question, 0 answers
        header = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0)

        # Encode the query name
        encoded = b""
        for label in name.split("."):
            encoded += bytes([len(label)]) + label.encode()
        encoded += b"\x00"

        # Type PTR (12), Class IN (1)
        question = encoded + struct.pack("!HH", 12, 1)
        return header + question

    def _parse_mdns(self, data: bytes, src_ip: str):
        """Parse a DNS/mDNS packet and extract PTR/A record hostnames."""
        try:
            if len(data) < 12:
                return

            flags      = struct.unpack("!H", data[2:4])[0]
            is_response = bool(flags & self._QR_FLAG)
            if not is_response:
                return   # ignore queries

            an_count = struct.unpack("!H", data[6:8])[0]
            if an_count == 0:
                return

            # Skip the question section
            offset = 12
            qd_count = struct.unpack("!H", data[4:6])[0]
            for _ in range(qd_count):
                _, offset = self._read_name(data, offset)
                offset += 4  # type + class

            # Parse answer records
            for _ in range(an_count):
                _, offset = self._read_name(data, offset)
                if offset + 10 > len(data):
                    break

                rtype, _, _, rdlen = struct.unpack("!HHIH", data[offset:offset + 10])
                offset += 10

                if rtype == 12:  # PTR
                    name, _ = self._read_name(data, offset)
                    hostname = name.split(".")[0]  # strip .local / .in-addr.arpa
                    if hostname and src_ip:
                        self.store.upsert(src_ip, hostname, "unknown", "mDNS")

                elif rtype == 1 and rdlen == 4:  # A record
                    ip_bytes = data[offset:offset + 4]
                    ip       = socket.inet_ntoa(ip_bytes)
                    if self._is_local(ip):
                        # The name was parsed before this record
                        pass  # IP → hostname mapping done via PTR

                offset += rdlen

        except Exception:
            pass  # Malformed packet — ignore silently

    @staticmethod
    def _read_name(data: bytes, offset: int) -> tuple[str, int]:
        """Read a DNS name (with pointer compression support)."""
        labels  = []
        visited = set()

        while offset < len(data):
            length = data[offset]

            if length == 0:
                offset += 1
                break

            if (length & 0xC0) == 0xC0:
                # Pointer
                if offset + 1 >= len(data):
                    break
                ptr = ((length & 0x3F) << 8) | data[offset + 1]
                if ptr in visited:
                    break
                visited.add(ptr)
                name, _ = MDNSScanner._read_name(data, ptr)
                labels.append(name)
                offset += 2
                break

            offset += 1
            labels.append(data[offset:offset + length].decode("utf-8", errors="replace"))
            offset += length

        return ".".join(labels), offset

    @staticmethod
    def _is_local(ip: str) -> bool:
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False


# ── NetBIOS scanner ───────────────────────────────────────────────────────────

class NetBIOSScanner:
    """
    Sends NetBIOS Name Service queries (UDP 137) to individual IPs.
    Unicast only — no broadcast — to stay non-intrusive.
    """

    # NetBIOS node status request
    _NS_HEADER = struct.pack("!HHHHHH",
        0xABCD,  # transaction ID
        0x0000,  # flags: query
        1, 0, 0, 0
    )
    _NS_QUERY  = (
        b"\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00"  # encoded "*" (wildcard)
        + struct.pack("!HH", 0x0021, 0x0001)          # type=NBSTAT, class=IN
    )

    def __init__(self, store: DeviceStore):
        self.store = store

    def query(self, ip: str):
        """Send a NetBIOS node status query to ip (non-blocking)."""
        threading.Thread(
            target=self._nb_query,
            args=(ip,),
            daemon=True,
            name=f"netbios-{ip}"
        ).start()

    def _nb_query(self, ip: str):
        """Unicast NetBIOS Name Service node status request."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(self._NS_HEADER + self._NS_QUERY, (ip, NETBIOS_PORT))

            try:
                data, _ = sock.recvfrom(1024)
                name     = self._parse_nb_response(data)
                if name:
                    self.store.upsert(ip, name, "windows", "NetBIOS")
            except socket.timeout:
                pass
            finally:
                sock.close()

        except Exception:
            pass

    @staticmethod
    def _parse_nb_response(data: bytes) -> Optional[str]:
        """
        Parse NetBIOS NBSTAT response.
        Name entries start at byte 57; each is 18 bytes (15 chars + type + flags).
        We return the first workstation/server name (type 0x00 or 0x20).
        """
        try:
            if len(data) < 57:
                return None

            num_names = data[56]
            offset    = 57

            for _ in range(num_names):
                if offset + 18 > len(data):
                    break

                raw_name  = data[offset:offset + 15]
                name_type = data[offset + 15]

                # 0x00 = workstation, 0x20 = file server
                if name_type in (0x00, 0x20):
                    name = raw_name.decode("ascii", errors="ignore").rstrip()
                    if name and not name.startswith("\x00"):
                        return name

                offset += 18

        except Exception:
            pass
        return None


# ── Device Scanner (orchestrator) ─────────────────────────────────────────────

class DeviceScanner:
    """
    Orchestrates mDNS + NetBIOS scanning.
    - Starts a passive mDNS listener on init
    - Exposes scan_ip(ip) to probe a single IP on demand
      (called by the sniffer when it sees a new local IP)
    - Runs a full subnet refresh every SCAN_INTERVAL_SEC seconds
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.store   = DeviceStore(db_path)
        self.mdns    = MDNSScanner(self.store)
        self.netbios = NetBIOSScanner(self.store)
        self._seen   : set[str] = set()
        self._lock   = threading.Lock()

    def start(self):
        """Start passive listener + periodic refresh thread."""
        self.mdns.start()

        t = threading.Thread(
            target=self._periodic_refresh,
            daemon=True,
            name="device-scanner-refresh"
        )
        t.start()
        print("✅ Device scanner started (mDNS + NetBIOS)")

    def stop(self):
        self.mdns.stop()

    def scan_ip(self, ip: str):
        if not self._is_local(ip):
            return
        with self._lock:
            if ip in self._seen:
                return
            self._seen.add(ip)

        # NOUVEAU : lookup MAC depuis la table ARP
        mac_info = get_mac_info(ip)
        if mac_info["mac"]:
            self.store.set_mac(ip, mac_info["mac"], mac_info["manufacturer"])

        self.mdns.query(ip)
        self.netbios.query(ip)

    def get_devices(self) -> list[dict]:
        """Return all known local devices."""
        return self.store.get_all()

    def get_name(self, ip: str) -> Optional[str]:
        """Return the device name for an IP, or None."""
        device = self.store.get(ip)
        return device["name"] if device else None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _periodic_refresh(self):
        """Every SCAN_INTERVAL_SEC, re-probe all previously seen IPs."""
        while True:
            time.sleep(SCAN_INTERVAL_SEC)
            with self._lock:
                ips = list(self._seen)

            for ip in ips:
                self.mdns.query(ip)
                self.netbios.query(ip)
                time.sleep(0.05)  # small delay to avoid burst

    @staticmethod
    def _is_local(ip: str) -> bool:
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False


# ── Module-level singleton ────────────────────────────────────────────────────

_scanner: Optional[DeviceScanner] = None
_scanner_lock = threading.Lock()


def get_scanner() -> DeviceScanner:
    """Return the module-level DeviceScanner singleton (lazy init)."""
    global _scanner
    if _scanner is None:
        with _scanner_lock:
            if _scanner is None:
                _scanner = DeviceScanner()
    return _scanner


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    print("Starting device scanner self-test...")
    scanner = DeviceScanner(db_path=Path("/tmp/test_devices.db"))
    scanner.start()

    # Probe a few common local IPs
    test_ips = ["192.168.1.1", "192.168.1.100", "192.168.1.255"]
    for ip in test_ips:
        print(f"  Probing {ip}...")
        scanner.scan_ip(ip)

    time.sleep(5)

    devices = scanner.get_devices()
    if devices:
        print(f"\nDiscovered {len(devices)} device(s):")
        for d in devices:
            print(f"  {d['ip']:<18} {d['name']:<30} [{d['method']}]")
    else:
        print("\nNo devices found (normal if no mDNS/NetBIOS devices responded)")