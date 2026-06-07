#!/usr/bin/env python3
"""
NetWatch — API Server
FastAPI server with WebSocket support for real-time dashboard updates.
Runs on localhost:8000 by default.
"""

import asyncio
import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, List
from resolver import get_resolver

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from network_sniffer import NetworkSniffer
from anomaly_detector import SimpleAnomalyChecker

# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="NetWatch API",
    description="Real-time network monitoring API",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────────────────────────────────────

sniffer = None
anomaly_checker = None
active_connections: List[WebSocket] = []
db_path = os.path.join(os.path.dirname(__file__), "netwatch.db")


def init_database():
    """Initialize SQLite database for logs."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            src_ip TEXT,
            dst_ip TEXT,
            protocol TEXT,
            size INTEGER,
            flags TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            alert_type TEXT,
            severity TEXT,
            source TEXT,
            details TEXT,
            description TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def save_connection_to_db(conn: Dict):
    """Save connection record to database."""
    try:
        conn_db = sqlite3.connect(db_path)
        cursor = conn_db.cursor()
        
        cursor.execute("""
            INSERT INTO connections (timestamp, src_ip, dst_ip, protocol, size, flags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            conn.get("timestamp"),
            conn.get("src"),
            conn.get("dst"),
            conn.get("protocol"),
            conn.get("size"),
            conn.get("flags")
        ))
        
        conn_db.commit()
        conn_db.close()
    except Exception as e:
        print(f"Error saving connection: {e}")


def save_alert_to_db(alert: Dict):
    """Save alert record to database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts (timestamp, alert_type, severity, source, details, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert.get("timestamp"),
            alert.get("type"),
            alert.get("severity"),
            alert.get("source", ""),
            alert.get("details", ""),
            alert.get("description", "")
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving alert: {e}")


def broadcaster():
    """Broadcast stats and alerts to all connected WebSocket clients."""
    while True:
        if sniffer and sniffer.running and active_connections:
            try:
                stats = sniffer.get_stats()
                
                # Analyze for anomalies
                alerts = anomaly_checker.analyze_stats() if anomaly_checker else []
                
                # Save alerts to database
                for alert in alerts:
                    save_alert_to_db(alert)
                
                # Save recent connections
                for conn in stats.get("recent_connections", [])[-5:]:
                    save_connection_to_db(conn)
                
                message = {
                    "type": "stats_update",
                    "data": stats,
                    "alerts": alerts,
                    "timestamp": datetime.now().isoformat()
                }
                
                asyncio.run(broadcast_message(message))
            
            except Exception as e:
                print(f"Broadcaster error: {e}")
        
        time.sleep(1)


async def broadcast_message(message: Dict):
    """Broadcast message to all connected clients."""
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global sniffer, anomaly_checker
    
    print("🚀 Starting NetWatch API...")
    
    # Initialize database
    init_database()
    
    # Start network sniffer in background
    sniffer = NetworkSniffer()
    anomaly_checker = SimpleAnomalyChecker(sniffer.stats)
    
    # Run sniffer in thread
    sniffer_thread = threading.Thread(target=sniffer.start_sniffing, daemon=True)
    sniffer_thread.start()
    
    # Start broadcaster in thread
    broadcaster_thread = threading.Thread(target=broadcaster, daemon=True)
    broadcaster_thread.start()
    
    print("✅ Sniffer and broadcaster started")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "sniffer_running": sniffer.running if sniffer else False,
        "active_connections": len(active_connections),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/stats")
async def get_stats():
    """Get current network statistics."""
    if not sniffer:
        return {"error": "Sniffer not initialized"}
    
    return sniffer.get_stats()


@app.get("/api/alerts")
async def get_alerts():
    """Get recent alerts."""
    if not anomaly_checker:
        return {"alerts": []}
    
    return {
        "alerts": anomaly_checker.alerts,
        "summary": {}
    }


@app.get("/api/history")
async def get_history(limit: int = 100):
    """Get connection history from database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM connections
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "connections": [dict(row) for row in rows]
        }
    except Exception as e:
        return {"error": str(e), "connections": []}


@app.get("/api/alerts/history")
async def get_alerts_history(limit: int = 50):
    """Get alert history from database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "alerts": [dict(row) for row in rows]
        }
    except Exception as e:
        return {"error": str(e), "alerts": []}

@app.get("/api/resolve")
async def resolve_ip(ip: str):
    """Resolve an IP address to hostname, org, country, city."""
    return get_resolver().resolve_ip(ip)
# ──────────────────────────────────────────────────────────────────────────────
# WebSocket Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    print(f"📡 Client connected. Total: {len(active_connections)}")
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to NetWatch API",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            # Receive and echo (for keep-alive)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        print(f"🔌 Client disconnected. Total: {len(active_connections) - 1}")
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if sniffer:
        sniffer.stop_sniffing()
    print("🛑 NetWatch API shutdown")


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("""
    ╔════════════════════════════════════════════╗
    ║  NetWatch API Server                       ║
    ║  http://localhost:8000                     ║
    ║                                            ║
    ║  Docs: http://localhost:8000/docs         ║
    ║  Health: http://localhost:8000/api/health ║
    ╚════════════════════════════════════════════╝
    """)
    
    # Note: On Windows, requires admin privileges
    print("⚠️  This requires administrator/root privileges to capture packets!\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
