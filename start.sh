#!/bin/bash
# NetWatch — Linux/macOS Startup Script
# Starts both Python backend and Node.js frontend

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            NetWatch — Network Monitor                    ║"
echo "║       Starting Python Backend + Node.js Frontend         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3.9+ from https://www.python.org"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi

# Load .env if exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found, using defaults"
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        cat > .env << EOF
BACKEND_API_URL=http://localhost:8000
NODE_PORT=3000
PYTHON_PORT=8000
DEBUG=false
EOF
    fi
fi

echo "▶️  Starting Python backend (Port 8000)..."
echo "   ⚠️  IMPORTANT: Requires root/sudo for packet capture!"
echo ""

# Start Python backend in background
cd backend/python
pip3 install -q -r requirements.txt
python3 api_server.py &
PYTHON_PID=$!
cd ../..

sleep 3

echo "▶️  Starting Node.js frontend (Port 3000)..."
echo ""

# Install npm deps
npm install -q 2>/dev/null || true

# Start Node.js frontend in background
npm start &
NODE_PID=$!

echo ""
echo "✅ Both services started!"
echo ""
echo "🌐 Dashboard:  http://localhost:3000"
echo "📡 Backend:    http://localhost:8000"
echo "📖 API Docs:   http://localhost:8000/docs"
echo ""
echo "Backend PID: $PYTHON_PID"
echo "Frontend PID: $NODE_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait

echo "Done!"
