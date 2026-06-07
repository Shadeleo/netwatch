#!/usr/bin/env python3
"""
NetWatch — MAC Resolver
Résout IP → MAC (table ARP système) → Fabricant (base IEEE OUI, ~30 000 entrées).
La base IEEE est téléchargée une fois et mise en cache localement.

Utilisation dans device_scanner.py :
    from mac_resolver import get_mac_info
    info = get_mac_info("192.168.1.254")
    # → {"mac": "d0:5a:00:a9:a8:fd", "manufacturer": "Sagemcom"}
"""

import json
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────────────

IEEE_OUI_URL  = "https://standards-oui.ieee.org/oui/oui.txt"
CACHE_PATH    = Path(__file__).parent / "oui_cache.json"
CACHE_MAX_AGE = 30 * 86400   # 30 jours avant re-téléchargement
ARP_REFRESH   = 60           # secondes entre deux lectures de la table ARP


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_oui(mac: str) -> str:
    """Normalise une adresse MAC vers le format OUI.
    'D0-5A-00-A9-A8-FD'  →  'd0:5a:00'
    'd0:5a:00:a9:a8:fd'  →  'd0:5a:00'
    """
    clean = re.sub(r'[.\-]', ':', mac.strip()).lower()
    parts = clean.split(':')
    return ':'.join(parts[:3]) if len(parts) >= 3 else ''


# ── Base OUI IEEE ─────────────────────────────────────────────────────────────

class OUIDatabase:
    """
    Télécharge oui.txt depuis standards-oui.ieee.org (~7 Mo),
    le parse et le stocke en cache JSON local.
    Le chargement est asynchrone (thread daemon) pour ne pas bloquer
    le démarrage du serveur FastAPI.
    """

    def __init__(self):
        self._db: dict[str, str] = {}
        self._lock = threading.Lock()
        self.ready = threading.Event()   # levé quand la DB est disponible
        threading.Thread(target=self._load, daemon=True, name='oui-loader').start()

    def lookup(self, mac: str) -> str:
        """Retourne le fabricant pour une adresse MAC, ou '' si inconnu."""
        oui = _to_oui(mac)
        if not oui:
            return ''
        with self._lock:
            return self._db.get(oui, '')

    def size(self) -> int:
        with self._lock:
            return len(self._db)

    # ── Chargement (cache → IEEE) ─────────────────────────────────────────

    def _load(self):
        # 1. Cache local présent et frais ?
        if CACHE_PATH.exists():
            age = time.time() - CACHE_PATH.stat().st_mtime
            if age < CACHE_MAX_AGE:
                try:
                    data = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
                    with self._lock:
                        self._db = data
                    print(f'[OUI] Cache chargé : {len(data):,} entrées')
                    self.ready.set()
                    return
                except Exception as e:
                    print(f'[OUI] Cache corrompu ({e}), re-téléchargement…')

        # 2. Téléchargement depuis IEEE
        print('[OUI] Téléchargement base IEEE OUI (première fois ~7 Mo)…')
        try:
            req = urllib.request.Request(
                IEEE_OUI_URL,
                headers={'User-Agent': 'NetWatch/1.0'},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode('latin-1')

            db = self._parse(raw)
            CACHE_PATH.write_text(json.dumps(db, ensure_ascii=False), encoding='utf-8')

            with self._lock:
                self._db = db
            print(f'[OUI] Base IEEE mise à jour : {len(db):,} entrées')

        except Exception as e:
            print(f'[OUI] Erreur téléchargement : {e}')
            # Utiliser le cache périmé plutôt que rien
            if CACHE_PATH.exists():
                try:
                    data = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
                    with self._lock:
                        self._db = data
                    print(f'[OUI] Cache périmé utilisé : {len(data):,} entrées')
                except Exception:
                    pass
        finally:
            self.ready.set()

    @staticmethod
    def _parse(text: str) -> dict[str, str]:
        """Parse le fichier oui.txt IEEE → {oui: fabricant}
        Lignes cibles : '00-00-00   (hex)    XEROX CORPORATION'
        """
        db: dict[str, str] = {}
        pattern = re.compile(
            r'^([0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2})\s+\(hex\)\s+(.+)$'
        )
        for line in text.splitlines():
            m = pattern.match(line.strip())
            if m:
                oui = m.group(1).replace('-', ':').lower()
                db[oui] = m.group(2).strip()
        return db


# ── Table ARP ─────────────────────────────────────────────────────────────────

class ARPTable:
    """
    Lit la table ARP du système (arp -a) et résout chaque MAC
    vers son fabricant via OUIDatabase.
    Se rafraîchit automatiquement en arrière-plan.

    Windows  : D0-5A-00-A9-A8-FD  dynamique
    Linux    : d0:5a:00:a9:a8:fd  ether
    """

    def __init__(self, oui: OUIDatabase):
        self._table: dict[str, dict] = {}
        self._lock  = threading.Lock()
        self._oui   = oui
        self._load()
        threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name='arp-refresh',
        ).start()

    def get(self, ip: str) -> Optional[dict]:
        """Retourne {'mac': str, 'manufacturer': str} pour une IP, ou None."""
        with self._lock:
            return self._table.get(ip)

    def all(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._table)

    # ── Lecture ARP ───────────────────────────────────────────────────────

    def _load(self):
        try:
            result = subprocess.run(
                ['arp', '-a'],
                capture_output=True, text=True, timeout=5,
            )
            table: dict[str, dict] = {}
            pat = re.compile(
                r'(\d{1,3}(?:\.\d{1,3}){3})\s+'              # IP
                r'([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:]'     # MAC
                r'[0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:]'
                r'[0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})'
            )
            for line in result.stdout.splitlines():
                m = pat.search(line)
                if m:
                    ip  = m.group(1)
                    mac = m.group(2).replace('-', ':').lower()
                    table[ip] = {
                        'mac':          mac,
                        'manufacturer': self._oui.lookup(mac),
                    }
            with self._lock:
                self._table = table

        except Exception as e:
            print(f'[ARP] Erreur lecture table : {e}')

    def _refresh_loop(self):
        while True:
            time.sleep(ARP_REFRESH)
            self._load()


# ── Singleton module-level ─────────────────────────────────────────────────────

_oui_db: Optional[OUIDatabase] = None
_arp_table: Optional[ARPTable] = None
_init_lock = threading.Lock()


def _init():
    global _oui_db, _arp_table
    if _arp_table is None:
        with _init_lock:
            if _arp_table is None:
                _oui_db    = OUIDatabase()
                _arp_table = ARPTable(_oui_db)


# ── API publique ──────────────────────────────────────────────────────────────

def get_mac_info(ip: str) -> dict:
    """
    Retourne les infos MAC pour une IP locale.
    Toujours un dict — strings vides si l'IP n'est pas dans la table ARP.

    Exemple :
        get_mac_info("192.168.1.254")
        → {"mac": "d0:5a:00:a9:a8:fd", "manufacturer": "Sagemcom"}

        get_mac_info("8.8.8.8")
        → {"mac": "", "manufacturer": ""}
    """
    _init()
    entry = _arp_table.get(ip)
    return entry if entry else {'mac': '', 'manufacturer': ''}


def get_manufacturer(mac: str) -> str:
    """
    Lookup OUI direct sur une adresse MAC (sans ARP).
    Utile si tu as déjà la MAC et veux juste le fabricant.
    """
    _init()
    return _oui_db.lookup(mac)


# ── Self-test ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Initialisation MAC resolver…')
    _init()

    print('Attente base OUI (max 25s)…')
    _oui_db.ready.wait(timeout=25)
    print(f'Base OUI : {_oui_db.size():,} entrées\n')

    entries = _arp_table.all()
    if entries:
        print(f'Table ARP — {len(entries)} appareil(s) :\n')
        for ip, info in sorted(entries.items()):
            mfr = info['manufacturer'] or '—'
            print(f'  {ip:<20} {info["mac"]:<20} {mfr}')
    else:
        print('Table ARP vide (normal si aucun appareil actif sur le réseau)')