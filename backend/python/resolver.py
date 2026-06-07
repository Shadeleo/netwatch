#!/usr/bin/env python3
"""
NetWatch — DNS & Org Resolver
Resolves IPs to hostnames (reverse DNS), hostnames to IPs (forward DNS),
fetches Whois/ASN info and geolocation, and caches all results in SQLite.
"""

import socket
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(UTC)

import requests
from ipwhois import IPWhois

# ── Configuration ─────────────────────────────────────────────────────────────

CACHE_TTL_HOURS  = 24
GEO_API_URL      = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon,org,as"
GEO_API_TIMEOUT  = 3      # seconds
DB_PATH          = Path(__file__).parent / "netwatch.db"

# IPs to skip (private ranges, loopback, link-local)
_SKIP_PREFIXES = (
    "0.",
    "10.",
    "127.",
    "169.254.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",
    "::1",
    "fe80:",
)


def _is_private(ip: str) -> bool:
    return any(ip.startswith(p) for p in _SKIP_PREFIXES)


# ── SQLite cache ───────────────────────────────────────────────────────────────

class ResolverCache:
    """Thread-safe SQLite cache for DNS and org data."""

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
                CREATE TABLE IF NOT EXISTS dns_cache (
                    ip          TEXT PRIMARY KEY,
                    hostname    TEXT,
                    org         TEXT,
                    asn         TEXT,
                    country     TEXT,
                    country_code TEXT,
                    city        TEXT,
                    lat         REAL,
                    lon         REAL,
                    resolved_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()

    def get(self, ip: str) -> Optional[dict]:
        """Return cached entry if still valid (within TTL), else None."""
        with self._lock:
            conn = self._connect()
            row  = conn.execute(
                "SELECT * FROM dns_cache WHERE ip = ?", (ip,)
            ).fetchone()
            conn.close()

        if row is None:
            return None

        resolved_at = datetime.fromisoformat(row["resolved_at"])
        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=UTC)
        if _utcnow() - resolved_at > timedelta(hours=CACHE_TTL_HOURS):
            return None          # expired — caller will refresh

        return dict(row)

    def set(self, ip: str, data: dict):
        """Insert or replace a cache entry."""
        with self._lock:
            conn = self._connect()
            conn.execute("""
                INSERT OR REPLACE INTO dns_cache
                    (ip, hostname, org, asn, country, country_code, city, lat, lon, resolved_at)
                VALUES
                    (:ip, :hostname, :org, :asn, :country, :country_code, :city, :lat, :lon, :resolved_at)
            """, {
                "ip":           ip,
                "hostname":     data.get("hostname"),
                "org":          data.get("org"),
                "asn":          data.get("asn"),
                "country":      data.get("country"),
                "country_code": data.get("country_code"),
                "city":         data.get("city"),
                "lat":          data.get("lat"),
                "lon":          data.get("lon"),
                "resolved_at":  _utcnow().isoformat(),
            })
            conn.commit()
            conn.close()


# ── Resolver ───────────────────────────────────────────────────────────────────

class DNSResolver:
    """
    Resolves an IP address to:
      - hostname  (reverse DNS)
      - org, ASN  (ipwhois)
      - country, city, lat, lon  (ip-api.com)
    Results are cached in SQLite for CACHE_TTL_HOURS hours.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.cache = ResolverCache(db_path)

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve_ip(self, ip: str) -> dict:
        """
        Resolve an IP address.
        Returns a dict with keys:
            ip, hostname, org, asn, country, country_code, city, lat, lon,
            cached (bool), resolved_at (ISO string)
        Private/loopback IPs return immediately with minimal data.
        """
        if _is_private(ip):
            return self._private_result(ip)

        cached = self.cache.get(ip)
        if cached:
            cached["cached"] = True
            return cached

        result = self._resolve_fresh(ip)
        self.cache.set(ip, result)
        result["cached"] = False
        return result

    def resolve_hostname(self, hostname: str) -> dict:
        """
        Forward DNS: resolve a hostname to its IP address.
        Returns { hostname, ip, error }.
        """
        try:
            ip = socket.gethostbyname(hostname)
            return {"hostname": hostname, "ip": ip, "error": None}
        except socket.gaierror as e:
            return {"hostname": hostname, "ip": None, "error": str(e)}

    # ── Internal resolution ───────────────────────────────────────────────────

    def _resolve_fresh(self, ip: str) -> dict:
        """Run all resolution steps and merge results."""
        result: dict = {
            "ip":           ip,
            "hostname":     None,
            "org":          None,
            "asn":          None,
            "country":      None,
            "country_code": None,
            "city":         None,
            "lat":          None,
            "lon":          None,
            "resolved_at":  _utcnow().isoformat(),
        }

        result["hostname"] = self._reverse_dns(ip)

        geo = self._geolocate(ip)
        if geo:
            result.update(geo)
        else:
            whois = self._whois(ip)
            if whois:
                result.update(whois)

        return result

    def _reverse_dns(self, ip: str) -> Optional[str]:
        """Reverse DNS lookup: IP → hostname."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return None

    def _geolocate(self, ip: str) -> Optional[dict]:
        """
        Call ip-api.com (free, no key needed, 45 req/min).
        Returns org, asn, country, city, lat, lon — or None on failure.
        """
        try:
            resp = requests.get(
                GEO_API_URL.format(ip=ip),
                timeout=GEO_API_TIMEOUT
            )
            data = resp.json()
            if data.get("status") != "success":
                return None

            return {
                "org":          data.get("org"),
                "asn":          data.get("as"),
                "country":      data.get("country"),
                "country_code": data.get("countryCode"),
                "city":         data.get("city"),
                "lat":          data.get("lat"),
                "lon":          data.get("lon"),
            }
        except Exception:
            return None

    def _whois(self, ip: str) -> Optional[dict]:
        """
        Fallback: use ipwhois for ASN / org data when ip-api fails.
        No geolocation, but gives reliable ASN info.
        """
        try:
            result = IPWhois(ip).lookup_rdap(depth=1)
            org = (
                result.get("network", {}).get("name")
                or result.get("asn_description")
            )
            asn = f"AS{result.get('asn')}" if result.get("asn") else None
            return {"org": org, "asn": asn}
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _private_result(ip: str) -> dict:
        return {
            "ip":           ip,
            "hostname":     None,
            "org":          "Private network",
            "asn":          None,
            "country":      None,
            "country_code": None,
            "city":         None,
            "lat":          None,
            "lon":          None,
            "cached":       True,
            "resolved_at":  _utcnow().isoformat(),
        }


# ── Module-level singleton ─────────────────────────────────────────────────────

_resolver: Optional[DNSResolver] = None
_resolver_lock = threading.Lock()


def get_resolver() -> DNSResolver:
    """Return the module-level DNSResolver singleton (lazy init)."""
    global _resolver
    if _resolver is None:
        with _resolver_lock:
            if _resolver is None:
                _resolver = DNSResolver()
    return _resolver


# ── Quick self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    resolver = DNSResolver(db_path=Path("/tmp/test_resolver.db"))

    test_ips = ["8.8.8.8", "1.1.1.1", "192.168.1.1", "142.251.41.1"]
    for ip in test_ips:
        t0     = time.time()
        result = resolver.resolve_ip(ip)
        elapsed = (time.time() - t0) * 1000
        print(
            f"[{'CACHE' if result['cached'] else 'FRESH':5s}] {ip:<18}"
            f"  hostname={result['hostname'] or '—':<35}"
            f"  org={result['org'] or '—':<30}"
            f"  {result['country_code'] or '—':<3}"
            f"  {elapsed:.0f}ms"
        )

    print("\n— Forward DNS —")
    for host in ["google.com", "cloudflare.com", "invalid.local"]:
        r = resolver.resolve_hostname(host)
        print(f"  {host:<25} → {r['ip'] or r['error']}")