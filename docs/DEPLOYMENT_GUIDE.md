# Deployment Guide - Civilian Evacuation Simulation System

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Development Setup](#development-setup)
3. [Environment Configuration](#environment-configuration)
4. [Database & Storage Setup](#database--storage-setup)
5. [Service Dependencies](#service-dependencies)
6. [Local Development](#local-development)
7. [Production Deployment](#production-deployment)
8. [Docker Deployment](#docker-deployment)
9. [Monitoring & Logging](#monitoring--logging)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **CPU**: 4 cores, 2.5GHz
- **RAM**: 8GB (16GB recommended)
- **Storage**: 50GB free space
- **OS**: Ubuntu 20.04+, macOS 10.15+, Windows 10+
- **Python**: 3.9+
- **Node.js**: 16+
- **Internet**: Required for OSMnx data downloads

### Recommended Requirements
- **CPU**: 8 cores, 3.0GHz+
- **RAM**: 32GB
- **Storage**: 100GB SSD
- **GPU**: Optional, for ML acceleration
- **Network**: High-speed internet for real-time data

### External Dependencies
- **OpenStreetMap**: For geographic data via OSMnx
- **Folium**: For interactive map generation
- **FastAPI**: Backend web framework
- **React**: Frontend framework
- **Optional**: Twilio (WhatsApp alerts), OpenAI (AI features)

## Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/Civilian-Evacuation-Simulation-Manhattan-NYC.git
cd Civilian-Evacuation-Simulation-Manhattan-NYC
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional development tools
pip install pytest black flake8 mypy

# Verify installation
python -c "import osmnx; print('OSMnx installed successfully')"
python -c "import folium; print('Folium installed successfully')"
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify installation
npm run build
```

### 4. Verify Installation
```bash
# Test backend
cd backend
python -m pytest tests/ -v

# Test frontend
cd frontend
npm test
```

## Environment Configuration

### Backend Environment Variables

Create `backend/.env`:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
ENVIRONMENT=development

# Storage Configuration
LOCAL_STORAGE_PATH=./local_s3
CACHE_ENABLED=true
CACHE_TTL_HOURS=24

# External Services (Optional)
OPENAI_API_KEY=your_openai_api_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
MAX_WORKERS=4
SIMULATION_TIMEOUT_MINUTES=30
GRAPH_CACHE_SIZE=10
```

### Frontend Environment Variables

Create `frontend/.env`:
```bash
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development

# Feature Flags
REACT_APP_ENABLE_AGENTIC_FEATURES=true
REACT_APP_ENABLE_EMERGENCY_ALERTS=true
REACT_APP_ENABLE_REAL_TIME_CHAT=true

# Analytics (Optional)
REACT_APP_ANALYTICS_ID=your_analytics_id
```

### Production Environment Variables

Create `backend/.env.production`:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ENVIRONMENT=production

# Security
SECRET_KEY=your_secure_secret_key_here
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
CORS_ORIGINS=https://your-domain.com

# Database (if using external DB)
DATABASE_URL=postgresql://user:pass@localhost:5432/evacuation_db

# Storage
LOCAL_STORAGE_PATH=/var/lib/evacuation/storage
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=60

# Performance
MAX_WORKERS=8
SIMULATION_TIMEOUT_MINUTES=60
GRAPH_CACHE_SIZE=20
```

## Database & Storage Setup

### Local Storage Structure
```bash
# Create storage directories
mkdir -p local_s3/{runs,scenarios,images,logs,cache,results}

# Set permissions
chmod 755 local_s3
chmod 644 local_s3/*
```

### Storage Configuration
```python
# backend/core/config.py
class StorageConfig:
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./local_s3")
    
    # Directory structure
    RUNS_DIR = "runs"
    SCENARIOS_DIR = "scenarios" 
    IMAGES_DIR = "images"
    LOGS_DIR = "logs"
    CACHE_DIR = "cache"
    RESULTS_DIR = "results"
    
    # File retention
    CACHE_RETENTION_DAYS = 7
    RESULTS_RETENTION_DAYS = 30
    LOGS_RETENTION_DAYS = 90
```

### Database Migration (Optional)
If using external database:
```bash
# Install database dependencies
pip install psycopg2-binary alembic

# Initialize migrations
cd backend
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Service Dependencies

### Required Services
1. **Backend API Server** (FastAPI)
2. **Frontend Web Server** (React/Nginx)
3. **Storage Service** (Local filesystem or S3)

### Optional Services
1. **Database** (PostgreSQL for production)
2. **Redis** (Caching and session storage)
3. **Message Queue** (Celery for background tasks)
4. **Monitoring** (Prometheus + Grafana)

### Service Dependencies Diagram
```
Frontend (React) → Backend API (FastAPI) → Simulation Services
                                        → Storage Service
                                        → External APIs (OSMnx, OpenAI)
```

## Local Development

### Quick Start
```bash
# Terminal 1: Start backend
cd backend
source venv/bin/activate
python main.py

# Terminal 2: Start frontend  
cd frontend
npm start

# Access application
open http://localhost:3000
```

### Development Workflow
```bash
# 1. Make changes to code
# 2. Run tests
cd backend && python -m pytest
cd frontend && npm test

# 3. Check code quality
cd backend && black . && flake8 .
cd frontend && npm run lint

# 4. Test integration
curl http://localhost:8000/api/simulation/cities
```

### Hot Reload Configuration
Backend (FastAPI):
```python
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Enable hot reload
        reload_dirs=["./"]
    )
```

Frontend (React):
```json
// package.json
{
  "scripts": {
    "start": "react-scripts start",
    "dev": "FAST_REFRESH=true react-scripts start"
  }
}
```

## Production Deployment

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3 python3-pip nodejs npm nginx postgresql redis-server

# Install Python dependencies
sudo apt install -y python3-dev libpq-dev build-essential

# Create application user
sudo useradd -m -s /bin/bash evacuation
sudo usermod -aG sudo evacuation
```

### 2. Application Deployment
```bash
# Clone repository
sudo -u evacuation git clone https://github.com/your-org/repo.git /opt/evacuation
cd /opt/evacuation

# Backend setup
sudo -u evacuation python3 -m venv backend/venv
sudo -u evacuation backend/venv/bin/pip install -r backend/requirements.txt

# Frontend build
cd frontend
sudo -u evacuation npm install
sudo -u evacuation npm run build
```

### 3. Systemd Service Configuration

Create `/etc/systemd/system/evacuation-backend.service`:
```ini
[Unit]
Description=Evacuation Simulation Backend
After=network.target

[Service]
Type=simple
User=evacuation
WorkingDirectory=/opt/evacuation/backend
Environment=PATH=/opt/evacuation/backend/venv/bin
ExecStart=/opt/evacuation/backend/venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/evacuation`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Frontend
    location / {
        root /opt/evacuation/frontend/build;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support for SSE
    location /api/runs {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 5. SSL Configuration (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 6. Start Services
```bash
# Enable and start services
sudo systemctl enable evacuation-backend
sudo systemctl start evacuation-backend

sudo systemctl enable nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status evacuation-backend
sudo systemctl status nginx
```

## Docker Deployment

### 1. Backend Dockerfile
Create `backend/Dockerfile`:
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 evacuation && chown -R evacuation:evacuation /app
USER evacuation

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "main.py"]
```

### 2. Frontend Dockerfile
Create `frontend/Dockerfile`:
```dockerfile
# Build stage
FROM node:16-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 3. Docker Compose
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOCAL_STORAGE_PATH=/app/storage
    volumes:
      - ./local_s3:/app/storage
      - ./backend/.env.production:/app/.env
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: evacuation
      POSTGRES_USER: evacuation
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

### 4. Deploy with Docker
```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Scale services
docker-compose up -d --scale backend=3
```

## Monitoring & Logging

### 1. Application Logging
```python
# backend/core/logging.py
import logging
import structlog

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### 2. Health Check Endpoints
```python
# backend/api/health.py
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "storage": "available",
            "osmnx": "operational"
        }
    }

@router.get("/metrics")
async def metrics():
    return {
        "active_simulations": len(active_runs),
        "cache_hit_rate": 0.85,
        "avg_response_time": 250,
        "error_rate": 0.02
    }
```

### 3. Monitoring Setup (Prometheus)
Create `monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'evacuation-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    
  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']
```

### 4. Log Aggregation
```bash
# Install Filebeat for log shipping
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.15.0-linux-x86_64.tar.gz
tar xzvf filebeat-7.15.0-linux-x86_64.tar.gz

# Configure Filebeat
cat > filebeat.yml << EOF
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/evacuation/backend/logs/*.log
    - /var/log/nginx/access.log
  
output.elasticsearch:
  hosts: ["localhost:9200"]
EOF
```

## Troubleshooting

### Common Issues

#### 1. OSMnx Installation Issues
```bash
# Error: Failed to install OSMnx
# Solution: Install system dependencies
sudo apt install -y python3-dev libspatialindex-dev libgeos-dev

# macOS
brew install spatialindex geos

# Reinstall OSMnx
pip uninstall osmnx
pip install osmnx
```

#### 2. Memory Issues During Simulation
```bash
# Error: Out of memory during graph loading
# Solution: Increase system memory or reduce graph size

# Monitor memory usage
htop
free -h

# Reduce graph complexity in config
# backend/services/network/graph_service.py
CITY_CONFIGS = {
    "westminster": {
        "dist": 2000,  # Reduce from 3000
        "simplify": True,
        "retain_all": False
    }
}
```

#### 3. Frontend Build Issues
```bash
# Error: npm build fails
# Solution: Clear cache and reinstall

cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run build
```

#### 4. API Connection Issues
```bash
# Error: Frontend can't connect to backend
# Check backend is running
curl http://localhost:8000/api/health

# Check CORS configuration
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 5. Simulation Timeout Issues
```bash
# Error: Simulation times out
# Solution: Increase timeout or optimize simulation

# backend/.env
SIMULATION_TIMEOUT_MINUTES=60

# Or reduce simulation complexity
scenario_config = {
    "num_routes": 3,  # Reduce from 5
    "num_walks": 5,   # Reduce from 10
}
```

### Debug Mode Setup
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Run with verbose output
cd backend
python -m uvicorn main:app --reload --log-level debug

# Frontend debug mode
cd frontend
REACT_APP_DEBUG=true npm start
```

### Performance Optimization
```bash
# 1. Enable caching
export CACHE_ENABLED=true
export CACHE_TTL_HOURS=24

# 2. Increase worker processes
export MAX_WORKERS=8

# 3. Optimize graph loading
export GRAPH_CACHE_SIZE=20

# 4. Enable compression
# nginx.conf
gzip on;
gzip_types text/plain application/json application/javascript text/css;
```

### Backup and Recovery
```bash
# Backup storage data
tar -czf backup-$(date +%Y%m%d).tar.gz local_s3/

# Backup database (if using PostgreSQL)
pg_dump evacuation > backup-db-$(date +%Y%m%d).sql

# Restore from backup
tar -xzf backup-20251006.tar.gz
psql evacuation < backup-db-20251006.sql
```

---

This deployment guide provides comprehensive instructions for setting up, deploying, and maintaining the Civilian Evacuation Simulation System in both development and production environments.
