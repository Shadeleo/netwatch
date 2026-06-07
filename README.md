# NetWatch — Real-Time Network Monitor

![NetWatch](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-green)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**NetWatch** is a professional network traffic monitoring dashboard for real-time analysis, anomaly detection, and security monitoring. Built with Python (FastAPI) backend and vanilla JavaScript frontend.

## 🎯 Features

✨ **Real-Time Monitoring**
- Live packet capture and analysis
- Bandwidth utilization tracking
- Protocol distribution visualization
- Network connection monitoring

🔍 **Local Device Discovery**
- Passive mDNS listener (port 5353) — detects Chromecast, smart TVs, speakers, etc.
- NetBIOS Name Service queries (port 137) — detects Windows machines
- MAC address resolution via system ARP table
- Manufacturer lookup via IEEE OUI database (~30,000 entries, auto-cached)
- Current machine automatically labeled as **"Ordinateur actuel"**

🚨 **Anomaly Detection**
- Port scan detection
- DDoS attack patterns
- Unusual protocol usage
- Traffic concentration alerts

📊 **Professional Dashboard**
- Real-time line charts (bandwidth/pps)
- Protocol distribution donut chart
- Top source IPs ranking with device names
- Live connection table with DNS/org resolution
- Alert stream with severity levels

⚡ **Performance**
- WebSocket real-time updates
- SQLite database for historical data
- Async Python backend
- Minimal frontend dependencies

## 📋 System Requirements

### Windows
- Windows 7+ (10/11 recommended)
- Python 3.9+
- Node.js 18+
- Administrator privileges (for packet capture)

### Linux/macOS
- Python 3.9+
- Node.js 18+
- Root/sudo privileges (for packet capture)

## 🚀 Quick Start

### 1️⃣ Clone & Setup

```bash
# Clone repository
git clone <your-repo-url> netwatch
cd netwatch

# Copy environment file
cp .env.example .env

# Install Python dependencies
cd backend/python
pip install -r requirements.txt
cd ../..

# Install Node.js dependencies
npm install
```

### 2️⃣ Start Services

**Windows (Batch Script):**
```bash
start.bat
```

**Linux/macOS (Bash Script):**
```bash
chmod +x start.sh
./start.sh
```

**Manual Start:**

Terminal 1 - Python Backend:
```bash
cd backend/python
python api_server.py
```

Terminal 2 - Node.js Frontend:
```bash
npm start
```

### 3️⃣ Access Dashboard

```
🌐 Dashboard:  http://localhost:3000
📡 Backend:    http://localhost:8000
📖 API Docs:   http://localhost:8000/docs
```

## 📁 Project Structure

```
netwatch/
├── backend/
│   ├── python/
│   │   ├── api_server.py          # FastAPI server with WebSockets
│   │   ├── network_sniffer.py     # Packet capture engine
│   │   ├── anomaly_detector.py    # Anomaly detection engine
│   │   ├── device_scanner.py      # Local device discovery (mDNS + NetBIOS)
│   │   ├── mac_resolver.py        # MAC address + manufacturer resolution
│   │   ├── resolver.py            # IP → hostname/org/country resolution
│   │   ├── requirements.txt       # Python dependencies
│   │   ├── oui_cache.json         # IEEE OUI cache (auto-generated)
│   │   └── netwatch.db            # SQLite database (auto-created)
│   └── nodejs/
│       └── (reserved for future)
│
├── public/
│   ├── index.html                 # Main dashboard HTML
│   ├── css/
│   │   └── style.css             # Dashboard styles (retro-terminal theme)
│   └── js/
│       ├── ws.js                 # WebSocket manager
│       ├── charts.js             # Chart.js visualizations
│       ├── alerts.js             # Alert management
│       └── app.js                # Main application logic
│
├── Server.js                      # Node.js frontend server (Express + proxy)
├── package.json                   # Node.js dependencies
├── .env                           # Environment configuration
├── .env.example                   # Example configuration
├── .gitignore                     # Git ignore rules
├── start.bat                      # Windows startup script
├── start.sh                       # Linux/macOS startup script
├── README.md                      # This file
└── LICENSE                        # MIT License
```

## 🔧 Configuration

Edit `.env` to customize:

```env
# Frontend
NODE_PORT=3000

# Backend
PYTHON_PORT=8000
BACKEND_API_URL=http://localhost:8000

# Thresholds
PORT_SCAN_THRESHOLD=20
DDOS_THRESHOLD=500
```

## 📡 API Endpoints

### REST API (Python Backend)

```
GET /api/health                  # Health check
GET /api/stats                   # Current statistics
GET /api/alerts                  # Recent alerts
GET /api/history?limit=100       # Connection history
GET /api/alerts/history?limit=50 # Alert history
GET /api/devices                 # Discovered local devices (mDNS/NetBIOS/ARP)
GET /api/resolve?ip=<ip>         # Resolve IP → hostname, org, country
GET /api/local-ip                # Get current machine's local IP
```

### WebSocket

```
WS /ws                           # Real-time updates
  ├── Message: { type: "stats_update", data: {...} }
  ├── Message: { type: "alerts", alerts: [...] }
  └── Keepalive: { type: "ping" }
```

## 🚨 Alert Types

| Type | Description | Severity |
|------|-------------|----------|
| `PORT_SCAN_DETECTED` | Suspicious port scanning | HIGH |
| `HIGH_PACKET_RATE` | Unusual packet per second rate | MEDIUM |
| `HIGH_BANDWIDTH` | Bandwidth usage spike | MEDIUM |
| `UNUSUAL_PROTOCOLS` | Non-standard protocols detected | MEDIUM |
| `TRAFFIC_CONCENTRATION` | Traffic from single source | LOW |

## 🖥️ Device Discovery

NetWatch passively discovers local devices using two protocols:

- **mDNS** — listens on `224.0.0.251:5353`, identifies Apple, Google, and IoT devices
- **NetBIOS** — queries port `137`, identifies Windows machines
- **ARP + IEEE OUI** — resolves MAC addresses to manufacturers (Sagemcom, Google, Harman, etc.)

Devices are cached in SQLite and refreshed every 5 minutes. The machine running NetWatch is always labeled **"Ordinateur actuel"** in the dashboard.

## 🛡️ Security Notes

⚠️ **Important**
- Requires administrator/root privileges for packet capture
- Only monitors traffic passing through the local machine's network interface
- Data is stored in local SQLite database
- No external data transmission (OUI database cached locally after first download)

## 🐛 Troubleshooting

### "Port already in use"
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:3000 | xargs kill -9
```

### "WebSocket connection failed"
- Ensure Python backend is running on port 8000
- Check firewall settings
- Verify `BACKEND_API_URL` in `.env`

### "No packets captured"
- Ensure running with administrator/root privileges
- Check network interface selection
- Try different interface in `network_sniffer.py`

### "No devices discovered"
- mDNS requires devices to be active on the network
- NetBIOS only works with Windows machines
- Run as administrator for mDNS multicast access

### "Permission denied on database"
- Delete `netwatch.db`
- Ensure write permissions in `backend/python/`

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -am 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

**Made with ❤️ for network engineers and Blue Team professionals**

Last Updated: 2026