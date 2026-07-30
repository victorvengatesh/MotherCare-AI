#!/usr/bin/env bash
# restore.sh — Production database recovery script for MotherCare AI (PostgreSQL)

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>" >&2
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

echo "Starting database recovery..."
echo "WARNING: This will overwrite existing data. Proceeding in 3 seconds..."
sleep 3

# Check if PostgreSQL container is running
if ! docker ps --format '{{.Names}}' | grep -q 'mothercare-postgres'; then
    echo "❌ Error: mothercare-postgres container is not running!" >&2
    exit 1
fi

# Decompress and stream SQL dumps into psql inside the container
gunzip -c "$BACKUP_FILE" | docker exec -i mothercare-postgres psql -U mothercare -d mothercare_db

echo "✓ Database recovery completed successfully!"
