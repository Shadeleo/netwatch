#!/usr/bin/env python3
"""
NetWatch — Anomaly Detection Engine
Detects network anomalies like port scans, DDoS, unusual traffic patterns.
"""

import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class AnomalyDetector:
    """Detects network anomalies from traffic patterns."""
    
    # Thresholds
    PORT_SCAN_THRESHOLD = 20  # connections to different ports in 10 seconds
    DDoS_THRESHOLD = 500  # packets/sec from single IP
    UNUSUAL_PROTOCOL_RATIO = 0.9  # 90% unusual protocols
    FAILED_CONNECTIONS_THRESHOLD = 50  # connection attempts in 10 seconds
    
    def __init__(self):
        self.alerts = []
        self.lock = threading.Lock()
        
        # Tracking windows
        self.port_scan_tracker = defaultdict(list)  # src_ip -> list of (dst_ip, port, timestamp)
        self.connection_attempts = defaultdict(list)  # src_ip -> list of timestamps
        self.protocol_distribution = defaultdict(lambda: defaultdict(int))  # src_ip -> protocol -> count
        self.ip_packet_rate = defaultdict(int)  # src_ip -> pps
        
        self.cleanup_interval = 30  # seconds
        self.last_cleanup = datetime.now()
    
    def analyze_packet(self, src_ip: str, dst_ip: str, dst_port: int, protocol: str, size: int):
        """Analyze a single packet for anomalies."""
        now = datetime.now()
        
        # Clean old data periodically
        if (now - self.last_cleanup).seconds > self.cleanup_interval:
            self._cleanup_old_data(now)
            self.last_cleanup = now
        
        # Check for port scans
        self._check_port_scan(src_ip, dst_ip, dst_port, now)
        
        # Track protocol distribution
        with self.lock:
            self.protocol_distribution[src_ip][protocol] += 1
        
        # Check for unusual patterns
        self._check_unusual_patterns(src_ip, protocol, now)
    
    def _check_port_scan(self, src_ip: str, dst_ip: str, dst_port: int, now: datetime):
        """Detect port scanning activity."""
        with self.lock:
            self.port_scan_tracker[src_ip].append((dst_ip, dst_port, now))
            
            # Keep only recent entries
            cutoff = now - timedelta(seconds=10)
            self.port_scan_tracker[src_ip] = [
                entry for entry in self.port_scan_tracker[src_ip]
                if entry[2] > cutoff
            ]
            
            # Check threshold
            unique_ports = len(set(entry[1] for entry in self.port_scan_tracker[src_ip]))
            
            if unique_ports >= self.PORT_SCAN_THRESHOLD:
                alert = {
                    "type": "PORT_SCAN_DETECTED",
                    "severity": "HIGH",
                    "source": src_ip,
                    "timestamp": now.isoformat(),
                    "details": f"Detected {unique_ports} unique ports scanned",
                    "description": "Possible port scanning activity"
                }
                self._add_alert(alert)
    
    def _check_unusual_patterns(self, src_ip: str, protocol: str, now: datetime):
        """Detect unusual traffic patterns."""
        with self.lock:
            total_packets = sum(self.protocol_distribution[src_ip].values())
            
            if total_packets > 100:
                unusual_count = 0
                total_unusual = 0
                
                for proto, count in self.protocol_distribution[src_ip].items():
                    if proto not in ["TCP", "UDP", "ICMP", "ARP"]:
                        total_unusual += count
                
                ratio = total_unusual / total_packets if total_packets > 0 else 0
                
                if ratio > self.UNUSUAL_PROTOCOL_RATIO:
                    alert = {
                        "type": "UNUSUAL_PROTOCOLS",
                        "severity": "MEDIUM",
                        "source": src_ip,
                        "timestamp": now.isoformat(),
                        "details": f"{ratio*100:.1f}% unusual protocols",
                        "description": "Unusual protocol distribution detected"
                    }
                    self._add_alert(alert)
    
    def _cleanup_old_data(self, now: datetime):
        """Remove old tracking data."""
        cutoff = now - timedelta(seconds=60)
        
        with self.lock:
            # Clean port scan tracker
            for src_ip in list(self.port_scan_tracker.keys()):
                self.port_scan_tracker[src_ip] = [
                    entry for entry in self.port_scan_tracker[src_ip]
                    if entry[2] > cutoff
                ]
                if not self.port_scan_tracker[src_ip]:
                    del self.port_scan_tracker[src_ip]
            
            # Keep only recent alerts
            cutoff_alerts = now - timedelta(minutes=5)
            self.alerts = [a for a in self.alerts if datetime.fromisoformat(a["timestamp"]) > cutoff_alerts]
    
    def _add_alert(self, alert: Dict):
        """Add a new alert, avoiding duplicates."""
        with self.lock:
            # Avoid duplicate alerts in the same timeframe
            for existing in self.alerts[-10:]:  # Check last 10 alerts
                if (existing["type"] == alert["type"] and
                    existing["source"] == alert["source"] and
                    (datetime.fromisoformat(alert["timestamp"]) - 
                     datetime.fromisoformat(existing["timestamp"])).seconds < 30):
                    return  # Skip duplicate
            
            self.alerts.append(alert)
            
            # Keep last 500 alerts
            if len(self.alerts) > 500:
                self.alerts = self.alerts[-500:]
    
    def get_alerts(self) -> List[Dict]:
        """Get all current alerts."""
        with self.lock:
            return self.alerts[-50:]  # Return last 50
    
    def get_alert_summary(self) -> Dict:
        """Get alert summary statistics."""
        with self.lock:
            by_type = defaultdict(int)
            by_severity = defaultdict(int)
            
            for alert in self.alerts:
                by_type[alert["type"]] += 1
                by_severity[alert["severity"]] += 1
            
            return {
                "total_alerts": len(self.alerts),
                "by_type": dict(by_type),
                "by_severity": dict(by_severity)
            }


class SimpleAnomalyChecker:
    """Simplified anomaly checker using traffic statistics."""
    
    def __init__(self, stats_obj):
        """Initialize with reference to PacketStats object."""
        self.stats = stats_obj
        self.alerts = []
        self.lock = threading.Lock()
    
    def analyze_stats(self) -> List[Dict]:
        """Analyze current statistics for anomalies."""
        snapshot = self.stats.get_snapshot()
        alerts = []
        
        # Check for high packet rate
        if snapshot.get("pps", 0) > 1000:
            alerts.append({
                "type": "HIGH_PACKET_RATE",
                "severity": "MEDIUM",
                "timestamp": datetime.now().isoformat(),
                "details": f"{snapshot['pps']} packets/sec",
                "description": "Unusually high packet rate detected"
            })
        
        # Check for high bandwidth
        if snapshot.get("bps", 0) > 100_000_000:  # 100 MB/s
            alerts.append({
                "type": "HIGH_BANDWIDTH",
                "severity": "MEDIUM",
                "timestamp": datetime.now().isoformat(),
                "details": f"{snapshot['bps'] / 1_000_000:.1f} MB/s",
                "description": "High bandwidth usage detected"
            })
        
        # Check for connection concentration
        top_src_list = snapshot.get("top_src_ips", [])
        if top_src_list and len(top_src_list) > 0:
            top_ip, top_data = top_src_list[0]
            top_bytes = top_data.get("bytes", 0)
            total_bytes = snapshot.get("total_bytes", 1)
            
            if total_bytes > 0 and (top_bytes / total_bytes) > 0.7:
                alerts.append({
                    "type": "TRAFFIC_CONCENTRATION",
                    "severity": "LOW",
                    "source": top_ip,
                    "timestamp": datetime.now().isoformat(),
                    "details": f"{(top_bytes/total_bytes)*100:.1f}% from single source",
                    "description": "Traffic heavily concentrated on one source"
                })
        
        with self.lock:
            self.alerts = alerts
        
        return alerts
