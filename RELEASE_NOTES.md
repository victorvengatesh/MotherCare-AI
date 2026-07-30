# Release Notes — MotherCare AI v1.0.0 (Production Release)

We are proud to announce the **v1.0.0** release of **MotherCare AI**, transforming the clinical decision support platform into a production-grade, highly secure, and enterprise-ready application.

---

## 🚀 Key Features

### 🛡️ Production Security & Reverse Proxy
- **HTTPS Enforcement**: Automatic redirection from port `80` to `443` with hardened TLS cipher suites.
- **Access Restrictions**: Container networks are isolated; the backend (8000) and frontend (3000) are private and accessible *only* via the Nginx proxy gateway.
- **Security Hardening**: Standardized HSTS, Content Security Policy, X-Frame-Options, and X-Content-Type-Options headers.
- **CORS Policies & Rate Limiting**: Built-in protection against brute-force/DDoS attacks (10 req/s rate limits with burst buffers).

### 📈 Enterprise Architecture & Performance
- **Static Serving Optimization**: Replaced Node-based file serving with Nginx in the frontend container.
- **Code-Splitting**: Split client route bundles via React Suspense and `React.lazy()`.
- **Database Query Indexing**: Added query-level SQLAlchemy index settings for rapid joins on primary keys.
- **Structured JSON Logging**: Switchable logger to route logs in clean JSON strings.

### 🧪 DevOps & Automation
- **CI/CD Integration**: Automatic GitHub workflow verifying builds, lints, and test suites.
- **Cross-Platform Certs**: A local python script `generate_certs.py` to create dev SSL certificates without admin access.
- **Backup & Recovery**: Scripts to dump, compress, and restore PostgreSQL databases.

---

## 📋 Deployment Checklist

1. **Clone & Setup**:
   ```bash
   git clone <repo-url> MotherCare-AI
   cd MotherCare-AI
   cp production.env.example .env
   ```
2. **Generate SSL Certificates**:
   - On Windows: Run `powershell -File scripts/generate_certs.ps1`
   - On Linux/macOS: Run `bash scripts/generate_certs.sh`
3. **Environment Keys**: Edit `.env` and fill in `GEMINI_API_KEY` and a secure `MC_SECRET_KEY`.
4. **Deploy Containers**:
   ```bash
   docker-compose up -d --build
   ```

---

## 🚦 Go-Live Verification Steps

- [ ] Verify HTTPS redirect: `curl -I http://localhost` should return `301 Moved Permanently` pointing to `https://localhost`.
- [ ] Verify secure connection: Open browser at `https://localhost` and check for the lock icon.
- [ ] Verify API endpoints: Query `https://localhost/health` (should return JSON status 200).
- [ ] Verify WebSockets: Notification feeds should connect securely to `wss://localhost/ws/notifications`.
- [ ] Verify DB Backups: Execute `bash scripts/backup.sh` and confirm files generate under `backups/`.
