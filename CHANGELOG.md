# Changelog

All notable changes to the **MotherCare AI** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-29

### Added
- **Nginx Reverse Proxy Gateway**: Configured TLS v1.2/v1.3 HTTPS support, HTTP-to-HTTPS redirect, security headers (HSTS, CSP, X-Frame), rate limiting, and WebSocket proxying.
- **CI/CD Pipeline**: Designed GitHub Actions workflows to lint frontend and backend code, run unit test suites, and verify Docker Compose build syntax.
- **Production Shell Scripts**: Created `generate_certs.py` (and .sh/.ps1 wrappers) for cross-platform local SSL certificate generation, and automated backup/restore scripts (`backup.sh` and `restore.sh`) for Postgres.
- **Structured JSON Logging**: Implemented a JSON logger in backend `logger.py` to route uvicorn, database, and business logic logs for easy search and indexing.
- **Database Optimizations**: Added foreign key indexes to primary search columns (history logs, appointments, reminders, assignments, notifications) in SQLAlchemy `models.py`.
- **Frontend Code Splitting**: Utilized React lazy-loading and dynamic Route Suspense inside `App.jsx` to reduce chunk size loading times.

---

## [0.5.0] - 2026-07-29

### Added
- **Admin Panel UI**: Implemented `AdminDashboard.jsx` featuring system overview stats, active user directories, doctor-patient assignment mapper, RAG ingestion/indexing control console, and system audit logs.
- **Interactive Visualizations**: Embedded responsive SVG charts inside `RiskDashboard.jsx` showing patient symptom urgency trends and alert status distribution ratios.
- **Consultation Log Sidebar**: Added log history listings inside `ChatPage.jsx` to browse past symptom analyses and indexed PDF report summaries.
- **Unit Testing Setup**: Installed Vitest and `@testing-library/react` and wrote test specs in `Dashboard.test.jsx`.

---

## [0.4.0] - 2026-07-28

### Added
- **Multi-Agent Orchestrator (CMO)**: Integrated specialized OB-GYN, Nutrition, Mental Health, and Emergency AI Agents.
- **RAG System**: Enabled uploading and vector-indexing guideline PDFs (via ChromaDB and Google Gemini embeddings).
- **Digital Twin State Machine**: Enabled live tracking of maternal biomarkers and risk scores.
- **Notification WebSocket Channels**: Set up real-time in-app triggers.
