# MotherCare AI — Backup and Data Safety Guide

> [!CAUTION]
> Never commit or email backups containing real patient records.
> All backups must be encrypted at rest.
> Access restricted to authorised clinical/technical personnel only.

---

## 1. Data assets to back up

| Asset | Location | Contains |
|---|---|---|
| SQLite database | `backend/mothercare.db` | User records, history, digital twins, alerts, appointments, reminders, notifications |
| Approved RAG guidelines metadata | `backend/app/chroma_db/` | Vector embeddings of approved clinical documents |
| Uploaded documents | `backend/uploads/` | Patient-uploaded health reports (PDF/images) |
| Environment config | `backend/.env` | Secrets — never backup to unencrypted storage |

---

## 2. SQLite backup procedure

```powershell
# One-time backup (safe, non-destructive)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$src = "V:\MotherCare-AI\backend\mothercare.db"
$dest = "D:\Backups\mothercare_$timestamp.db"

# Use SQLite .backup command (hot backup — no downtime required)
.venv\Scripts\python.exe -c "
import sqlite3, shutil
src = r'$src'
dst = r'$dest'
con = sqlite3.connect(src)
backup_con = sqlite3.connect(dst)
con.backup(backup_con)
backup_con.close()
con.close()
print('Backup complete:', dst)
"
```

### Automating daily backups (Windows Task Scheduler)
```xml
<!-- backup_task.xml — import via Task Scheduler -->
<Task>
  <Triggers><CalendarTrigger><StartBoundary>2026-01-01T02:00:00</StartBoundary><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Actions><Exec><Command>powershell.exe</Command><Arguments>-File V:\MotherCare-AI\scripts\backup.ps1</Arguments></Exec></Actions>
</Task>
```

---

## 3. Restoration procedure (synthetic data only for testing)

```powershell
# STOP the server first
# Then replace the database file:
$backup = "D:\Backups\mothercare_20260728_020000.db"
$live   = "V:\MotherCare-AI\backend\mothercare.db"
Copy-Item $backup $live -Force

# Verify integrity
.venv\Scripts\python.exe -c "
import sqlite3
con = sqlite3.connect(r'V:\MotherCare-AI\backend\mothercare.db')
result = con.execute('PRAGMA integrity_check').fetchone()
print('Integrity:', result)
con.close()
"
# Restart the server
```

> [!IMPORTANT]
> Always test restoration on a synthetic data copy first. Never test on production data.

---

## 4. Chroma vector DB backup

```powershell
$ts = Get-Date -Format "yyyyMMdd"
Compress-Archive `
  -Path "V:\MotherCare-AI\backend\app\chroma_db\" `
  -DestinationPath "D:\Backups\chroma_$ts.zip"
```

Restoration: extract the zip to `backend/app/chroma_db/` and restart the server.

---

## 5. Encryption at rest

For production deployments:
- Use OS-level disk encryption (BitLocker, LUKS) for backup storage volumes.
- Alternatively, use `gpg --symmetric backup.db` before storing.
- Never store encryption keys alongside backups.

---

## 6. What to NEVER back up to version control

- `backend/mothercare.db` — contains patient PII and clinical data.
- `backend/.env` — contains secrets.
- `backend/uploads/` — contains patient documents.
- `backend/app/chroma_db/` — may contain patient text fragments.

These are all covered by `.gitignore`. **Verify before every `git push`.**

---

## 7. Retention policy recommendation

| Backup type | Retention |
|---|---|
| Daily full backup | 30 days |
| Weekly snapshot | 12 weeks |
| Monthly archive | 12 months |

Specific retention must follow applicable health data regulations (e.g., India DPDPA, Tamil Nadu state health data rules).

---

## 8. Access control

- Backup files must be accessible only to the clinical operations team.
- Restrict filesystem permissions: `icacls D:\Backups /inheritance:r /grant "SYSTEM:F" "ClinicalAdmin:F"`
- Log all backup access events.

---

> [!NOTE]
> This guide documents the safe approach using synthetic data for testing.
> Production deployment must be reviewed by a qualified data protection officer.
