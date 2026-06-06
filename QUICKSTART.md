# 🚀 NetWatch Quick Start Guide

## ⚡ 5-Minute Setup

### Windows Users

1. **Download & Install**
   - [Python 3.10+](https://www.python.org/downloads/)
   - [Node.js 18+](https://nodejs.org/)
   - [Git](https://git-scm.com/)

2. **Clone & Run**
   ```bash
   git clone https://github.com/YOUR_USERNAME/netwatch.git
   cd netwatch
   start.bat
   ```

3. **Done!** 
   - Open http://localhost:3000 in your browser

### Linux/macOS Users

1. **Install Dependencies**
   ```bash
   # macOS (using Homebrew)
   brew install python@3.10 node git
   
   # Ubuntu/Debian
   sudo apt install python3.10 python3-pip nodejs git
   ```

2. **Clone & Run**
   ```bash
   git clone https://github.com/YOUR_USERNAME/netwatch.git
   cd netwatch
   chmod +x start.sh
   ./start.sh
   ```

3. **Done!** 
   - Open http://localhost:3000 in your browser

---

## 🎯 What You Get

| Feature | Description |
|---------|-------------|
| 📊 **Real-Time Dashboard** | Live bandwidth, protocols, top IPs |
| 🚨 **Anomaly Detection** | Port scans, DDoS patterns, unusual traffic |
| 📡 **WebSocket Updates** | Live updates pushed to browser |
| 📋 **Connection Tracking** | All network connections table |
| 💾 **SQLite Database** | Historical data logging |

---

## 🔧 Manual Setup (Advanced)

If the scripts don't work, try manually:

### Terminal 1 - Backend
```bash
cd backend/python
pip install -r requirements.txt
python api_server.py
```

### Terminal 2 - Frontend
```bash
npm install
npm start
```

### Then Open
```
http://localhost:3000
```

---

## ⚠️ Important Notes

- **Admin privileges**: Packet capture requires administrator/root rights
- **Windows only**: Some features optimized for Windows networking APIs
- **Firewall**: May need to allow ports 3000 and 8000

---

## 🐛 Troubleshooting

**Q: "Port 3000 already in use"**
```bash
# Windows
netstat -ano | findstr :3000

# macOS/Linux
lsof -ti:3000 | xargs kill -9
```

**Q: "Python not found"**
```bash
# Make sure Python is in PATH
python --version
```

**Q: "No packets captured"**
- Run with administrator privileges
- Check network interface
- Disable firewall temporarily

**Q: "Backend unreachable"**
- Ensure Python backend is running on port 8000
- Check firewall rules
- Try `curl http://localhost:8000/api/health`

---

## 📚 Next Steps

1. **Read** [README.md](../README.md) for full documentation
2. **Explore** [Dashboard](http://localhost:3000)
3. **Check** [API Docs](http://localhost:8000/docs)
4. **Deploy** using [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 🎓 Learning Path

### Beginner
1. Run the dashboard
2. Explore UI and charts
3. Check some network traffic
4. Review README

### Intermediate
1. Read source code in `backend/python/`
2. Understand WebSocket flow in `public/js/`
3. Try modifying thresholds in `.env`
4. Add custom alerts

### Advanced
1. Implement new detection algorithms
2. Add database persistence
3. Deploy to cloud
4. Integrate with SIEM tools

---

## 🤝 Need Help?

- 📖 **Docs**: See `/docs` folder
- 🐛 **Bugs**: Open GitHub issue
- 💬 **Questions**: Start GitHub discussion
- 🔐 **Security**: Email security@example.com

---

**Happy monitoring! 🎉**
