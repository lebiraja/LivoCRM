#!/usr/bin/env bash
# Local PostgreSQL backup for non-AWS servers. Set BACKUP_DIR to a mounted disk when available.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/livocrm}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
compose=(docker compose -f "$APP_DIR/docker-compose.yml" -f "$APP_DIR/docker-compose.cloudflare.yml")

install -d -m 0700 "$BACKUP_DIR"
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$BACKUP_DIR/livocrm-postgres-$stamp.sql.gz.tmp"
final="$BACKUP_DIR/livocrm-postgres-$stamp.sql.gz"
trap 'rm -f "$tmp"' EXIT

"${compose[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip -9 > "$tmp"
test -s "$tmp"
mv "$tmp" "$final"
find "$BACKUP_DIR" -type f -name 'livocrm-postgres-*.sql.gz' -mtime "+$RETENTION_DAYS" -delete
echo "created $final"
