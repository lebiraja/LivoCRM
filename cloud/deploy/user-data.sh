#!/usr/bin/env bash
# First-boot setup for the LivoCRM app host (Amazon Linux 2023, instance profile = AppInstanceRole).
# Paste into the EC2 launch wizard under "User data" after replacing every <PLACEHOLDER>.
# No secret is stored in this script. The app .env and the repo deploy key are SecureString
# parameters in SSM Parameter Store; this script only reads them on the instance.
set -euo pipefail

readonly REGION="<REGION>"
readonly REPO_SSH="git@github.com:<OWNER>/<REPO>.git"
readonly APP_DIR=/opt/livocrm
readonly COMPOSE_VERSION="v2.29.7"
readonly BUCKET="<BUCKET>"

dnf install -y docker git cronie
systemctl enable --now docker crond

# Compose v2 plugin, pinned. Verify the sha256 against the release page before first use.
install -d -m 0755 /usr/libexec/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/libexec/docker/cli-plugins/docker-compose
chmod 0755 /usr/libexec/docker/cli-plugins/docker-compose

# Read-only GitHub deploy key (SecureString /livocrm/prod/github_deploy_key) for the repo clone.
install -d -m 0700 /root/.ssh
aws ssm get-parameter --region "$REGION" --name /livocrm/prod/github_deploy_key \
  --with-decryption --query Parameter.Value --output text > /root/.ssh/id_ed25519
chmod 0600 /root/.ssh/id_ed25519
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts

git clone --quiet "$REPO_SSH" "$APP_DIR"

# The whole app .env is one SecureString (/livocrm/prod/dotenv). Keep it root-only.
aws ssm get-parameter --region "$REGION" --name /livocrm/prod/dotenv \
  --with-decryption --query Parameter.Value --output text > "$APP_DIR/.env"
chmod 0600 "$APP_DIR/.env"

# Nightly pg_dump to S3 at 20:30 UTC (02:00 IST).
cat > /etc/cron.d/livocrm-backup <<EOF
BACKUP_BUCKET=${BUCKET}
30 20 * * * root ${APP_DIR}/cloud/deploy/backup-pg.sh >> /var/log/livocrm-backup.log 2>&1
EOF
chmod 0644 /etc/cron.d/livocrm-backup
