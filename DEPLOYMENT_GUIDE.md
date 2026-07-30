# MotherCare AI — Deployment Guide

**Version:** 1.0.0  
**Last Updated:** July 6, 2026  
**Status:** Production-Ready ✓

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Running the Application](#running-the-application)
7. [Health Checks & Monitoring](#health-checks--monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)
10. [Security Checklist](#security-checklist)

---

## Prerequisites

### System Requirements
```
OS: Linux, macOS, or Windows (with WSL2)
CPU: 2+ cores
RAM: 4GB minimum, 8GB recommended
Disk: 20GB for development, 50GB+ for production
```

### Required Software
```
Docker 20.10+
Docker Compose 2.0+
Git 2.30+
Python 3.11+ (for local development)
Node.js 18+ (for local frontend development)
```

### API Keys & Credentials
```
- GEMINI_API_KEY (Google's Generative AI)
- MC_SECRET_KEY (For JWT token signing)
```

---

## Local Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/mothercare-ai.git
cd mothercare-ai
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env.local
# Edit .env.local with API endpoint
```

### 4. Start Local Services

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Access Application:**
- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:8001
- API Documentation: http://127.0.0.1:8001/docs

---

## Docker Deployment

### Build Images Locally

```bash
# Build backend image
docker build -t mothercare-ai-backend:1.0.0 ./backend

# Build frontend image
docker build -t mothercare-ai-frontend:1.0.0 ./frontend

# Or use docker-compose to build both
docker-compose build
```

### Run with Docker Compose

```bash
# Create .env file for docker-compose
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
MC_SECRET_KEY=your_secret_key_here
EOF

# Generate self-signed SSL certificates for the Nginx proxy
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/generate_certs.ps1
# Linux/macOS:
bash scripts/generate_certs.sh

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

### Verify Deployment

```bash
# Check running containers
docker ps

# Check container logs
docker logs mothercare-ai-backend
docker logs mothercare-ai-frontend

# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000
```

---

## Environment Configuration

### Backend .env File

```bash
# API Keys
GEMINI_API_KEY=sk-...  # Get from Google AI Studio

# Security
MC_SECRET_KEY=your-secure-random-key-min-32-chars

# Database (SQLite by default)
DATABASE_URL=sqlite:///./data/mothercare.db

# Frontend Origins (CORS)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development  # or production
```

### Frontend .env.local File

```bash
# Backend API
VITE_API_URL=http://127.0.0.1:8001

# Environment
VITE_ENVIRONMENT=development  # or production
```

### Generate Secure Secret Key

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

---

## Database Setup

### SQLite (Default - Development)

SQLite is configured by default. Database file will be created at:
```
backend/data/mothercare.db
```

**Backup Database:**
```bash
cp backend/data/mothercare.db backend/data/mothercare.db.backup
```

**Reset Database:**
```bash
rm backend/data/mothercare.db
# Restart backend to reinitialize
```

### PostgreSQL (Production - Recommended)

PostgreSQL is supported out-of-the-box in the Docker Compose environment and replaces the development SQLite DB.

**Manual PostgreSQL Setup:**
1. Install PostgreSQL 16+ database server.
2. Create the database:
   ```sql
   CREATE DATABASE mothercare_db;
   ```
3. Install driver dependencies:
   ```bash
   pip install psycopg2-binary
   ```
4. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://mothercare:mothercare_secret@localhost:5432/mothercare_db
   ```

**Running Database Migrations:**
Alembic is used to manage database schema updates. To apply migrations to your database (PostgreSQL or SQLite):
```bash
# Apply migrations to the database
python -m alembic upgrade head
```

### Redis Cache & WebSocket Pub/Sub

Redis is used to provide distributed caching and push real-time notifications to connected WebSockets.

**Configuration:**
1. Configure `REDIS_URL` in `.env`:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```
   *If `REDIS_URL` is empty, the application will automatically fall back to local in-memory caching and standard HTTP polling mode.*
2. Set the client WebSocket variable for frontend:
   ```
   VITE_WS_URL=ws://127.0.0.1:8000
   ```
   *Connected tabs subscribe dynamically to `/ws/notifications?token=<JWT>`.*

---

## Running the Application

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Scale services (if using load balancer)
docker-compose up -d --scale backend=3

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Using Docker Individually

```bash
# Backend
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e MC_SECRET_KEY=$MC_SECRET_KEY \
  -v mothercare_data:/app/data \
  -v mothercare_uploads:/app/uploads \
  --name mothercare-backend \
  mothercare-ai-backend:1.0.0

# Frontend
docker run -d \
  -p 3000:3000 \
  -e VITE_API_URL=http://127.0.0.1:8000 \
  --name mothercare-frontend \
  mothercare-ai-frontend:1.0.0
```

### Using Local Virtual Environments

```bash
# Backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm run preview  # or npm run dev for development
```

---

## Health Checks & Monitoring

### Backend Health Endpoint

```bash
# Health check
curl http://127.0.0.1:8000/health

# Response (200 OK):
{
  "status": "success",
  "data": {
    "status": "healthy",
    "service": "MotherCare AI API",
    "uploads_directory": "/app/uploads"
  }
}
```

### Docker Health Checks

```bash
# Check container health status
docker ps --format "{{.Names}} {{.Status}}"

# Inspect health details
docker inspect --format='{{json .State.Health}}' mothercare-ai-backend
```

### View Logs

```bash
# Backend logs
docker logs mothercare-ai-backend --tail 50 -f

# Frontend logs
docker logs mothercare-ai-frontend --tail 50 -f

# Combined logs
docker-compose logs -f
```

### Performance Monitoring

**Request Metrics:**
- Check backend logs for request duration
- Rate limit headers: `X-RateLimit-Remaining`
- Response times visible in browser DevTools

**Container Resources:**
```bash
docker stats --no-stream
```

---

## Troubleshooting

### Backend Not Starting

**Error: Port 8000 already in use**
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>
# or
docker ps -q | xargs docker kill
```

**Error: GEMINI_API_KEY not set**
```bash
# Verify .env file exists and contains key
cat .env

# Add key to environment
export GEMINI_API_KEY=your_key_here
# or in .env file
GEMINI_API_KEY=your_key_here
```

**Error: ModuleNotFoundError**
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Or use Docker to skip dependencies issues
docker-compose up --build
```

### Frontend Not Loading

**Blank page or CORS errors**
```bash
# Check backend is running
curl http://127.0.0.1:8000/health

# Check CORS configuration in backend .env
ALLOWED_ORIGINS must include your frontend URL

# Clear browser cache and reload
# Or test in incognito window
```

**Build fails**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force

# Rebuild with verbose output
npm run build -- --verbose
```

### Database & Cache Issues

**"database is locked" error (SQLite)**
*   SQLite only allows one write transaction at a time. Stop all processes and restart:
    ```bash
    docker-compose down
    # Or kill local uvicorn tasks
    killall uvicorn
    ```

**PostgreSQL connection refused / dynamic credentials mismatch**
*   Verify the PostgreSQL container is running: `docker ps | grep postgres`
*   Verify that `DATABASE_URL` matches the credentials set in `POSTGRES_USER` and `POSTGRES_PASSWORD` variables in the `.env` file.
*   Check the docker-compose logs: `docker-compose logs postgres`

**Alembic Migration errors ("Relation does not exist" or "Out of date")**
*   Apply the baseline and subsequent migrations:
    ```bash
    python -m alembic upgrade head
    ```
*   If developing locally, make sure you have installed the client drivers: `pip install psycopg2-binary`

**Redis cache connection latency / fallback issues**
*   Verify Redis container is running: `docker ps | grep redis`
*   If Redis is offline, the backend Cache circuit breaker will automatically trip after 3 failed attempts, switching immediately to local in-memory cache for a 30s cool-off window. This prevents any latency bottlenecks.
*   To check cache status: `curl http://localhost:8000/readiness` (observing checks).

**WebSocket disconnect / connection drops**
*   Verify the client status indicator dot in the top-right of the dashboard:
    *   **Green:** Live WebSocket connection established.
    *   **Yellow/Red:** Connecting/Reconnecting state (WebSocket is attempting exponential backoff reconnects up to 5 times).
    *   **Gray:** Polling fallback active (WS is offline, app has cleanly downgraded to standard HTTP polling every 60 seconds).
*   Ensure that the WebSocket base URL (`VITE_WS_URL`) does not end with a trailing slash in your client configurations.

### Rate Limiting Too Strict

Edit rate limit config in `backend/app/core/rate_limiter.py`:
```python
# Example: Increase chat endpoint limit from 30 to 60 requests per 60 seconds
chat_limiter = PerUserRateLimiter(max_tokens=60, refill_rate=1.0)
```

### Circuit Breaker Open (Service Unavailable)

**Symptom:** 503 responses with fallback messages

```python
# Verify Gemini API key is valid
# Check Gemini API status: https://status.cloud.google.com/

# Adjust circuit breaker thresholds in backend/app/core/circuit_breaker.py:
gemini_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=120)  # More lenient
```

---

## Production Deployment

### Pre-Deployment Checklist

```
✓ All tests passing (pytest, npm test)
✓ Security audit completed (see Security Checklist)
✓ Environment variables configured securely
✓ Database backups created
✓ SSL/TLS certificates configured
✓ Rate limiting thresholds tuned
✓ Logging configured for production
✓ Monitoring/alerting setup
✓ Disaster recovery plan in place
✓ Documentation updated
```

### Deploy to Production

**Option 1: AWS ECS (Recommended)**
```bash
# Push images to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker tag mothercare-ai-backend:1.0.0 $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mothercare-backend:1.0.0
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mothercare-backend:1.0.0

# Deploy using CloudFormation or CDK
```

**Option 2: Kubernetes**
```bash
# Build and push to registry
docker build -t registry.example.com/mothercare-backend:1.0.0 ./backend
docker push registry.example.com/mothercare-backend:1.0.0

# Apply Kubernetes manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -l app=mothercare-ai
```

**Option 3: DigitalOcean App Platform**
```bash
# Connect GitHub repository
# Configure environment variables in UI
# Deploy from branch

# Or via CLI
doctl apps create --spec app.yaml
```

### Production Configuration

**backend/.env (production)**
```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
GEMINI_API_KEY=<production-key>
MC_SECRET_KEY=<production-secure-key>
DATABASE_URL=postgresql://user:password@db.example.com:5432/mothercare
ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
```

### Monitoring & Alerting

```bash
# Setup CloudWatch/DataDog/New Relic metrics
# Configure alerts for:
#   - Error rate > 5%
#   - Response time > 2s
#   - 429 (rate limit) rate > 1%
#   - Container restart count > 3/hour
#   - Disk usage > 80%
```

### Scaling

```bash
# Horizontal scaling (multiple instances)
docker-compose up -d --scale backend=3

# Or with Kubernetes
kubectl scale deployment mothercare-backend --replicas=5

# Load balancing (nginx)
# See SCALING_GUIDE.md for details
```

---

## Security Checklist

### Application Security

- [ ] JWT secret key is strong (min 32 characters)
- [ ] Passwords hash with bcrypt (or equivalent)
- [ ] HTTPS/SSL enabled in production
- [ ] CORS origins are restrictive (not *)
- [ ] API keys never logged or exposed in errors
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] XSS prevention (React auto-escaping + DOMPurify)
- [ ] CSRF tokens implemented
- [ ] Rate limiting active on all endpoints
- [ ] Input validation on all user inputs
- [ ] File upload validation (type, size, content)
- [ ] Error messages don't expose stack traces
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)

### Infrastructure Security

- [ ] Non-root user in Docker containers
- [ ] Secrets managed in secure vault (not in code)
- [ ] Database connections encrypted
- [ ] Regular backups scheduled and tested
- [ ] Firewall rules restrictive (only needed ports)
- [ ] Network segmentation (VPC/security groups)
- [ ] SSL/TLS certificates from trusted CA
- [ ] Authentication for database/admin tools
- [ ] Audit logging enabled
- [ ] Intrusion detection configured

### Operational Security

- [ ] Access control policy in place
- [ ] Audit logs retained for 90+ days
- [ ] Incident response plan documented
- [ ] Vulnerability scanning scheduled
- [ ] Dependencies kept up-to-date
- [ ] Secrets rotation policy established
- [ ] Disaster recovery tested quarterly
- [ ] Security training for team
- [ ] Privacy policy published
- [ ] GDPR compliance verified (if applicable)

---

## Rollback Procedures

### Docker Rollback

```bash
# Rollback to previous image version
docker-compose down
docker pull mothercare-ai-backend:0.9.0
docker-compose up -d

# Or keep multiple tagged versions running
docker-compose -f docker-compose.v1.yml up -d
```

### Database Rollback

```bash
# Restore from backup
cp backend/data/mothercare.db.backup backend/data/mothercare.db

# Or restore from PostgreSQL backup
psql mothercare_ai < backup.sql
```

### Code Rollback

```bash
# In Git
git revert <commit-hash>
git push production main

# Redeploy
docker-compose up -d --build
```

---

## Support & Escalation

### Common Issues & Solutions

See [Troubleshooting](#troubleshooting) section above.

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Review error messages and status codes
3. Consult documentation: `/docs` or `/docs/DEPLOYMENT_GUIDE.md`
4. Check GitHub Issues: `https://github.com/your-org/mothercare-ai/issues`
5. Contact team: `team@example.com` or `Slack #mothercare-ai`

### Emergency Contacts

- **On-Call Engineer:** `+1-XXX-XXX-XXXX`
- **Engineering Lead:** `engineering-lead@example.com`
- **Operations Team:** `ops@example.com`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-06 | Initial deployment guide for Phase 3 |
| 0.9.0 | 2026-06-15 | Phase 2 stability patterns |
| 0.8.0 | 2026-05-30 | Phase 1 core features |

---

**Generated by Kiro AI**  
**Last Updated:** July 6, 2026  
**Status:** Production-Ready ✓
