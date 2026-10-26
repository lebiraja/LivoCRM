#!/usr/bin/env bash
# Daily logical backup of the app database to the data bucket (backups/ prefix, 30-day expiry).
# Cron entry: cloud/deploy/README.md section "Backups". BACKUP_BUCKET is set in /etc/cron.d.
set -euo pipefail

readonly APP_DIR=/opt/livocrm
readonly BUCKET="${BACKUP_BUCKET:?set BACKUP_BUCKET (see cloud/deploy/README.md)}"
STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
readonly STAMP
readonly KEY="backups/postgres/livocrm-${STAMP}.sql.gz"

cd "$APP_DIR"
# POSTGRES_USER and POSTGRES_DB are read inside the db container, so no app secrets are needed here.
docker compose -f docker-compose.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
  | gzip -9 \
  | aws s3 cp - "s3://${BUCKET}/${KEY}" --sse AES256

echo "backup written to s3://${BUCKET}/${KEY}"
