#!/usr/bin/env bash
# backup.sh — Production database backup script for MotherCare AI (PostgreSQL)

set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/mothercare_db_$TIMESTAMP.sql.gz"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Starting database backup for MotherCare AI..."

# Check if PostgreSQL container is running
if ! docker ps --format '{{.Names}}' | grep -q 'mothercare-postgres'; then
    echo "❌ Error: mothercare-postgres container is not running!" >&2
    exit 1
fi

# Run pg_dump inside postgres container and compress
# Uses environment variables defined in docker-compose
docker exec -t mothercare-postgres pg_dumpall -U mothercare | gzip > "$BACKUP_FILE"

echo "✓ Database backup successfully saved to: $BACKUP_FILE"

# Apply retention policy: delete backups older than retention days
echo "Applying retention policy (deleting backups older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -type f -name "mothercare_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "✓ Backup maintenance complete!"
