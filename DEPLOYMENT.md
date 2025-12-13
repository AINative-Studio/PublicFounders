# PublicFounders Deployment Guide

This guide covers deploying PublicFounders to production with ZeroDB as the unified data platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [ZeroDB Configuration](#zerodb-configuration)
4. [Application Deployment](#application-deployment)
5. [Health Checks](#health-checks)
6. [Monitoring](#monitoring)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services

- **ZeroDB Account**: Sign up at https://zerodb.ai
- **OpenAI API Key**: For embedding generation
- **LinkedIn OAuth App**: For authentication (optional for MVP)
- **Container Platform**: Docker/Railway/Render/Fly.io

### Required Tools

- Docker (if using containers)
- Git
- Python 3.9+

---

## Environment Setup

### 1. Create ZeroDB Project

```bash
# Visit https://zerodb.ai/dashboard
# Click "New Project"
# Name: PublicFounders Production
# Copy your Project ID and API Key
```

### 2. Configure Environment Variables

Create a `.env` file or set environment variables in your deployment platform:

```bash
# ZeroDB Configuration
ZERODB_API_KEY=your_production_api_key_here
ZERODB_PROJECT_ID=your_production_project_id_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# JWT Configuration (CHANGE THESE IN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=https://yourdomain.com/api/v1/auth/linkedin/callback

# Application Settings
ENVIRONMENT=production
API_V1_PREFIX=/api/v1
PROJECT_NAME=PublicFounders
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional: Logging
LOG_LEVEL=INFO
```

### 3. Security Checklist

- [ ] JWT_SECRET_KEY is random and at least 32 characters
- [ ] API keys are never committed to git
- [ ] CORS origins are restricted to your domain
- [ ] HTTPS is enforced in production
- [ ] Environment variables are stored securely (secrets manager)

---

## ZeroDB Configuration

### Tables Setup

The following 8 NoSQL tables should already exist in your ZeroDB project. If not, they will be created automatically on first use:

1. **users** - User authentication and profiles
2. **founder_profiles** - Founder-specific data
3. **goals** - Founder goals and objectives
4. **asks** - Help requests
5. **posts** - Build-in-public content
6. **companies** - Company information
7. **company_roles** - User-company relationships
8. **introductions** - AI-facilitated connections

### Verify Tables

```python
# Quick verification script
import asyncio
from app.services.zerodb_client import zerodb_client

async def verify_tables():
    tables = ["users", "founder_profiles", "goals", "asks",
              "posts", "companies", "company_roles", "introductions"]

    for table in tables:
        try:
            result = await zerodb_client.query_rows(table, limit=1)
            print(f"✓ {table}: OK")
        except Exception as e:
            print(f"✗ {table}: {e}")

asyncio.run(verify_tables())
```

---

## Application Deployment

### Option 1: Docker Deployment

**1. Build Docker Image**

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Build and Run**

```bash
# Build image
docker build -t publicfounders:latest .

# Run container
docker run -d \
  --name publicfounders \
  -p 8000:8000 \
  --env-file .env \
  publicfounders:latest
```

**3. Docker Compose (Optional)**

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ZERODB_API_KEY=${ZERODB_API_KEY}
      - ZERODB_PROJECT_ID=${ZERODB_PROJECT_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENVIRONMENT=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### Option 2: Railway Deployment

**1. Install Railway CLI**

```bash
npm install -g @railway/cli
railway login
```

**2. Initialize Project**

```bash
railway init
railway link
```

**3. Set Environment Variables**

```bash
railway variables set ZERODB_API_KEY=your_key
railway variables set ZERODB_PROJECT_ID=your_project_id
railway variables set OPENAI_API_KEY=your_key
railway variables set JWT_SECRET_KEY=your_secret
railway variables set ENVIRONMENT=production
```

**4. Deploy**

```bash
railway up
```

---

### Option 3: Render Deployment

**1. Create `render.yaml`**

```yaml
services:
  - type: web
    name: publicfounders-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
      - key: ZERODB_API_KEY
        sync: false
      - key: ZERODB_PROJECT_ID
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: ENVIRONMENT
        value: production
```

**2. Connect Repository**

- Go to https://dashboard.render.com
- Click "New" → "Blueprint"
- Connect your GitHub repository
- Render will auto-deploy on push

---

### Option 4: Manual Server Deployment

**1. Server Setup (Ubuntu/Debian)**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.9 python3.9-venv python3-pip nginx -y

# Create application user
sudo useradd -m -s /bin/bash publicfounders
```

**2. Deploy Application**

```bash
# Clone repository
sudo -u publicfounders git clone https://github.com/your-org/PublicFounders.git /home/publicfounders/app
cd /home/publicfounders/app

# Create virtual environment
sudo -u publicfounders python3.9 -m venv venv
sudo -u publicfounders ./venv/bin/pip install -r requirements.txt

# Set up environment variables
sudo -u publicfounders nano /home/publicfounders/.env
# (Paste your environment variables)
```

**3. Create systemd Service**

```ini
# /etc/systemd/system/publicfounders.service
[Unit]
Description=PublicFounders API
After=network.target

[Service]
Type=simple
User=publicfounders
WorkingDirectory=/home/publicfounders/app
EnvironmentFile=/home/publicfounders/.env
ExecStart=/home/publicfounders/app/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**4. Start Service**

```bash
sudo systemctl daemon-reload
sudo systemctl enable publicfounders
sudo systemctl start publicfounders
sudo systemctl status publicfounders
```

**5. Configure Nginx**

```nginx
# /etc/nginx/sites-available/publicfounders
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/publicfounders /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**6. Set up SSL with Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Health Checks

### Application Health Endpoint

```bash
# Check application health
curl https://yourdomain.com/health

# Expected response:
{
  "status": "healthy",
  "service": "PublicFounders API",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2025-12-13T10:00:00Z"
}
```

### ZeroDB Connection Test

```bash
# Test ZeroDB connectivity
curl https://yourdomain.com/api/v1/health/database

# Expected response:
{
  "database": "connected",
  "tables": 8,
  "project_id": "f536cbc9-1305-4196-9e80-de62d6556317"
}
```

### Monitoring Endpoints

Set up monitoring for these endpoints:

- **Health Check**: `GET /health` (every 30s)
- **API Docs**: `GET /api/docs` (accessibility test)
- **Auth Status**: `POST /api/v1/auth/verify` (with test token)

---

## Monitoring

### Recommended Monitoring Tools

1. **Uptime Monitoring**: UptimeRobot, Pingdom, or StatusCake
2. **Application Monitoring**: Sentry for error tracking
3. **Performance Monitoring**: New Relic or DataDog
4. **Log Aggregation**: LogTail, Papertrail, or CloudWatch

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| API Response Time | p95 > 500ms | Investigate slow queries |
| Error Rate | > 1% | Check logs, alert team |
| CPU Usage | > 80% | Scale horizontally |
| Memory Usage | > 85% | Check for memory leaks |
| ZeroDB API Latency | > 200ms | Check ZeroDB status |

### Logging Configuration

```python
# backend/app/core/config.py
import logging

logging.basicConfig(
    level=logging.INFO if ENVIRONMENT == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/publicfounders/app.log')
    ]
)
```

---

## Rollback Procedures

### Quick Rollback (Docker)

```bash
# List recent images
docker images publicfounders

# Stop current container
docker stop publicfounders
docker rm publicfounders

# Run previous version
docker run -d \
  --name publicfounders \
  -p 8000:8000 \
  --env-file .env \
  publicfounders:v1.0.0  # Previous version tag
```

### Git-based Rollback

```bash
# Identify last working commit
git log --oneline

# Revert to previous version
git checkout <commit-hash>

# Redeploy
./deploy.sh  # Or your deployment command
```

### ZeroDB Data Rollback

**Important**: ZeroDB data is not versioned. Best practices:

1. **Backup before major changes**:
```python
# Export all data
from app.services.zerodb_client import zerodb_client

async def backup_all_data():
    tables = ["users", "founder_profiles", "goals", "asks", "posts"]
    backup = {}

    for table in tables:
        backup[table] = await zerodb_client.query_rows(table, limit=10000)

    import json
    with open(f'backup_{datetime.now().isoformat()}.json', 'w') as f:
        json.dump(backup, f)
```

2. **Test changes in development first**
3. **Use feature flags for risky changes**

---

## Troubleshooting

### Issue: Application won't start

**Symptoms**: Server starts but immediately crashes

**Solutions**:
1. Check environment variables are set:
   ```bash
   env | grep ZERODB
   env | grep OPENAI
   ```
2. Check logs:
   ```bash
   docker logs publicfounders  # Docker
   journalctl -u publicfounders -n 50  # systemd
   ```
3. Verify Python version:
   ```bash
   python --version  # Must be 3.9+
   ```

### Issue: 401 Unauthorized from ZeroDB

**Symptoms**: API returns "Authentication failed"

**Solutions**:
1. Verify API key is valid (not expired)
2. Check project ID matches your ZeroDB project
3. Test credentials manually:
   ```bash
   curl -H "X-API-Key: $ZERODB_API_KEY" \
        -H "X-Project-ID: $ZERODB_PROJECT_ID" \
        https://api.zerodb.ai/v1/tables
   ```

### Issue: Embedding generation failing

**Symptoms**: 500 errors when creating goals/posts

**Solutions**:
1. Check OpenAI API key and credits:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
2. Verify rate limits not exceeded
3. Check embedding service logs

### Issue: LinkedIn OAuth not working

**Symptoms**: OAuth callback returns 400/500 errors

**Solutions**:
1. Verify redirect URI matches exactly in LinkedIn app settings
2. Check CLIENT_ID and CLIENT_SECRET
3. Ensure HTTPS in production (LinkedIn requires it)
4. Test with LinkedIn's OAuth debugger

### Issue: High memory usage

**Symptoms**: Application consuming > 1GB RAM

**Solutions**:
1. Check for connection leaks (should use httpx, not persistent connections)
2. Monitor ZeroDB client connections
3. Restart application to clear cache
4. Consider scaling horizontally instead of vertically

---

## Production Checklist

Before going live:

- [ ] All environment variables set correctly
- [ ] JWT_SECRET_KEY is strong and unique
- [ ] CORS origins restricted to production domains
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Health checks configured and passing
- [ ] Monitoring and alerting set up
- [ ] Error tracking (Sentry) configured
- [ ] Backup procedures documented
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Rate limiting configured
- [ ] DDoS protection in place (Cloudflare/AWS Shield)

---

## Scaling Considerations

### Horizontal Scaling

ZeroDB architecture supports horizontal scaling easily:

```bash
# Multiple instances behind load balancer
# No database connection pooling needed
# Each instance makes independent HTTP API calls

# Example with Docker Swarm
docker service create \
  --name publicfounders \
  --replicas 3 \
  --env-file .env \
  -p 8000:8000 \
  publicfounders:latest
```

### Performance Optimization

1. **Enable ZeroDB caching** (built-in, no config needed)
2. **Use CDN** for static assets
3. **Implement request caching** for expensive operations
4. **Optimize embedding generation** (batch when possible)

---

## Support

For deployment issues:

- **GitHub Issues**: https://github.com/AINative-Studio/PublicFounders/issues
- **Email Support**: support@ainative.studio
- **ZeroDB Support**: https://zerodb.ai/support
- **Documentation**: See README.md, ARCHITECTURE.md

---

**Last Updated**: December 2025
**Version**: 1.0 (ZeroDB Migration Complete)
