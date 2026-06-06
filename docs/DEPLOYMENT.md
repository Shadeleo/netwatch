# NetWatch Deployment Guide

Comprehensive deployment instructions for various platforms.

## Table of Contents

1. [Local Deployment](#local-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Heroku Deployment](#heroku-deployment)
4. [AWS Deployment](#aws-deployment)
5. [Linux Server Deployment](#linux-server-deployment)
6. [Production Best Practices](#production-best-practices)

---

## Local Deployment

### Windows (Recommended for Development)

1. **Prerequisites**
   ```bash
   # Check Python version
   python --version  # Should be 3.9+
   
   # Check Node.js version
   node --version    # Should be 18+
   ```

2. **Setup**
   ```bash
   # Clone repository
   git clone https://github.com/YOUR_USERNAME/netwatch.git
   cd netwatch
   
   # Copy environment
   copy .env.example .env
   
   # Run startup script
   start.bat
   ```

3. **Access**
   - Dashboard: http://localhost:3000
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Linux/macOS

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/netwatch.git
cd netwatch

# Copy environment
cp .env.example .env

# Run startup script
chmod +x start.sh
./start.sh
```

---

## Docker Deployment

### Build Docker Images

#### Backend (Python/FastAPI)

**Dockerfile.backend**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/python/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/python /app

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "api_server.py"]
```

Build and run:
```bash
docker build -f Dockerfile.backend -t netwatch-backend:latest .
docker run -p 8000:8000 netwatch-backend:latest
```

#### Frontend (Node.js)

**Dockerfile.frontend**
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --prefer-offline

# Copy public files
COPY public ./public
COPY Server.js .

# Expose port
EXPOSE 3000

# Run server
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -f Dockerfile.frontend -t netwatch-frontend:latest .
docker run -p 3000:3000 -e BACKEND_URL=http://backend:8000 netwatch-frontend:latest
```

### Docker Compose

**docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      PORT: 8000
    volumes:
      - ./backend/python:/app
      - netwatch-db:/app/data
    networks:
      - netwatch
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      BACKEND_URL: http://backend:8000
      NODE_PORT: 3000
    depends_on:
      - backend
    networks:
      - netwatch
    restart: unless-stopped

networks:
  netwatch:
    driver: bridge

volumes:
  netwatch-db:
```

Run with Docker Compose:
```bash
docker-compose up -d
```

---

## Heroku Deployment

### Prerequisites
- Heroku CLI installed
- Git repository initialized
- Heroku account

### Steps

1. **Create Heroku Apps**
```bash
heroku login
heroku create netwatch-backend
heroku create netwatch-frontend
```

2. **Backend (Python)**
```bash
# Add Procfile
echo "web: cd backend/python && python api_server.py" > Procfile

# Deploy
git push heroku main:main

# View logs
heroku logs --app netwatch-backend
```

3. **Frontend (Node.js)**
```bash
# Set environment
heroku config:set BACKEND_URL=https://netwatch-backend.herokuapp.com --app netwatch-frontend

# Deploy
git push heroku main:main --app netwatch-frontend
```

4. **Access**
   - Dashboard: https://netwatch-frontend.herokuapp.com
   - Backend: https://netwatch-backend.herokuapp.com

---

## AWS Deployment

### Option 1: EC2 + RDS

1. **Launch EC2 Instance**
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.medium
   - Security Group: Allow ports 3000, 8000

2. **Connect and Setup**
```bash
ssh -i key.pem ubuntu@ec2-xxx.amazonaws.com

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip nodejs npm git

# Clone repository
git clone https://github.com/YOUR_USERNAME/netwatch.git
cd netwatch

# Setup
cp .env.example .env
npm install
cd backend/python && pip install -r requirements.txt
cd ../..
```

3. **Run with PM2 (Process Manager)**
```bash
sudo npm install -g pm2

pm2 start "npm start" --name "netwatch-frontend"
pm2 start "cd backend/python && python api_server.py" --name "netwatch-backend"
pm2 startup
pm2 save
```

4. **Setup Nginx Reverse Proxy**
```bash
sudo apt install -y nginx

# Configure /etc/nginx/sites-available/netwatch
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api {
        proxy_pass http://backend;
    }

    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/netwatch /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Option 2: ECS (Elastic Container Service)

1. Push Docker images to ECR
2. Create ECS task definitions
3. Deploy using Fargate or EC2 launch type

---

## Linux Server Deployment

### Production Setup (Ubuntu 22.04)

1. **Initial Setup**
```bash
# Create app user
sudo useradd -m -s /bin/bash netwatch
sudo su - netwatch

# Install Node and Python
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs python3.10 python3-pip

# Clone repository
git clone https://github.com/YOUR_USERNAME/netwatch.git
cd netwatch
```

2. **Install Dependencies**
```bash
npm install
cd backend/python
pip3 install -r requirements.txt
cd ../..
```

3. **Systemd Services**

**Backend Service**: `/etc/systemd/system/netwatch-backend.service`
```ini
[Unit]
Description=NetWatch Backend (FastAPI)
After=network.target

[Service]
User=netwatch
Type=simple
WorkingDirectory=/home/netwatch/netwatch/backend/python
ExecStart=/usr/bin/python3 api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Frontend Service**: `/etc/systemd/system/netwatch-frontend.service`
```ini
[Unit]
Description=NetWatch Frontend (Node.js)
After=network.target

[Service]
User=netwatch
Type=simple
WorkingDirectory=/home/netwatch/netwatch
ExecStart=/usr/bin/npm start
Environment="NODE_ENV=production"
Environment="PORT=3000"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. **Enable Services**
```bash
sudo systemctl daemon-reload
sudo systemctl enable netwatch-backend
sudo systemctl enable netwatch-frontend
sudo systemctl start netwatch-backend
sudo systemctl start netwatch-frontend
```

5. **SSL/TLS with Let's Encrypt**
```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot certonly --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Production Best Practices

### Security
- ✅ Use HTTPS/SSL certificates
- ✅ Run services with restricted user permissions
- ✅ Use environment variables for secrets
- ✅ Implement firewall rules
- ✅ Regular security updates

### Performance
- ✅ Use reverse proxy (Nginx/Apache)
- ✅ Enable gzip compression
- ✅ Implement caching headers
- ✅ Use CDN for static assets
- ✅ Monitor resource usage

### Monitoring & Logging
- ✅ Setup centralized logging
- ✅ Monitor CPU, memory, disk
- ✅ Alert on errors and anomalies
- ✅ Implement health checks
- ✅ Use APM tools

### Database
- ✅ Regular backups
- ✅ Implement retention policies
- ✅ Monitor database size
- ✅ Use database replication

### Maintenance
- ✅ Automated updates
- ✅ Rolling deployments
- ✅ Health checks
- ✅ Graceful shutdown handling

---

## Monitoring & Maintenance

### Health Check
```bash
curl http://localhost:8000/api/health
curl http://localhost:3000/
```

### View Logs (Systemd)
```bash
sudo journalctl -u netwatch-backend -f
sudo journalctl -u netwatch-frontend -f
```

### Update Application
```bash
cd /home/netwatch/netwatch
git pull origin main
npm install
cd backend/python && pip install -r requirements.txt
sudo systemctl restart netwatch-backend netwatch-frontend
```

---

For additional help, see README.md or open an issue on GitHub.
