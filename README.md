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

🚨 **Anomaly Detection**
- Port scan detection
- DDoS attack patterns
- Unusual protocol usage
- Traffic concentration alerts

📊 **Professional Dashboard**
- Real-time line charts (bandwidth/pps)
- Protocol distribution donut chart
- Top source IPs ranking
- Live connection table
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
│   │   ├── requirements.txt        # Python dependencies
│   │   └── netwatch.db            # SQLite database (auto-created)
│   └── nodejs/
│       └── (reserved for future)
│
├── public/
│   ├── index.html                  # Main dashboard HTML
│   ├── css/
│   │   └── style.css              # Dashboard styles (retro-terminal theme)
│   └── js/
│       ├── ws.js                  # WebSocket manager
│       ├── charts.js              # Chart.js visualizations
│       ├── alerts.js              # Alert management
│       └── app.js                 # Main application logic
│
├── frontend/
│   └── assets/                    # (reserved for future)
│
├── docs/
│   └── (API documentation)
│
├── Server.js                       # Node.js frontend server (Express + proxy)
├── package.json                    # Node.js dependencies
├── .env                            # Environment configuration
├── .env.example                    # Example configuration
├── .gitignore                      # Git ignore rules
├── start.bat                       # Windows startup script
├── start.sh                        # Linux/macOS startup script
├── README.md                       # This file
└── LICENSE                         # MIT License

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

## 🛡️ Security Notes

⚠️ **Important**
- Requires administrator/root privileges for packet capture
- Only works on local network interfaces
- Data is stored in local SQLite database
- No external data transmission

## 🐳 Docker Deployment (Optional)

```dockerfile
# Dockerfile (for Python backend)
FROM python:3.9-slim
WORKDIR /app
COPY backend/python /app
RUN pip install -r requirements.txt
CMD ["python", "api_server.py"]
```

## 📚 Development

### Architecture

```
┌─────────────────────────────────────────────────┐
│           Browser Dashboard (Port 3000)          │
│  ├─ HTML/CSS/JS (Vanilla, Chart.js)            │
│  └─ WebSocket Connection                        │
└────────────────┬────────────────────────────────┘
                 │ WS + HTTP Proxy
┌────────────────▼────────────────────────────────┐
│       Node.js Server (Express, Port 3000)       │
│  ├─ Static Asset Serving                        │
│  ├─ Proxy to Backend API (/api/*)              │
│  └─ Proxy to WebSocket (/ws)                   │
└────────────────┬────────────────────────────────┘
                 │ HTTP/WS
┌────────────────▼────────────────────────────────┐
│      Python API Server (FastAPI, Port 8000)     │
│  ├─ Network Sniffer Thread                      │
│  ├─ Anomaly Detection Engine                    │
│  ├─ WebSocket Broadcaster                      │
│  └─ SQLite Database                            │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼──────────┐
        │ Raw Socket / WinPcap
        │ (Packet Capture)
        └───────────────────┘
```

### Adding New Features

1. **New Chart**: Add canvas to `public/index.html`, implement in `public/js/charts.js`
2. **New Alert**: Add detection logic to `backend/python/anomaly_detector.py`
3. **API Endpoint**: Add route to `backend/python/api_server.py`

## 🐛 Troubleshooting

### "Port already in use"
```bash
# Windows: Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/macOS: Kill process on port 3000
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

## 📞 Support

For issues and feature requests, visit:
- GitHub Issues: [Report Bug]
- Documentation: See `/docs` folder
- API Docs: http://localhost:8000/docs (when running)

---

**Made with ❤️ for network engineers and Blue Team professionals**

Last Updated: 2026
