# Deploy LivoCRM to a server with Cloudflare Tunnel

This is the direct server deployment path. The application images build on the server; Docker
pulls the pinned Cloudflare Tunnel image and the base images. Cloudflare terminates public HTTPS,
then routes to Nginx over the private Docker network. Only cloudflared can reach that ingress
network, and no app, database, Redis, or Nginx port is published on the host.

## 1. Prepare the server and domain

Use an Ubuntu 24.04 server with at least 2 vCPU and 4 GiB RAM, Docker Engine, Docker Compose v2.24.4
or newer, Git, and OpenSSL. Enable Docker at boot. The firewall can leave all inbound ports closed;
allow outbound DNS and HTTPS, including Cloudflare Tunnel connections on TCP/UDP 7844.

On a fresh Ubuntu 24.04 host, install the packaged Docker engine and Compose plugin:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git openssl
sudo systemctl enable --now docker
docker compose version
```

In Cloudflare:

1. Make sure `lebiraja.in` is active in your Cloudflare account.
2. Go to **Networking → Tunnels**, create a remotely managed tunnel, and copy its token.
3. Add a **Published application** route: hostname `livocrm.lebiraja.in`, service URL
   `http://nginx:80`. Cloudflare creates the DNS route. Keep the tunnel token private.
4. Enable **Always Use HTTPS** in **SSL/TLS → Edge Certificates** for the hostname.

## 2. Clone and create the secrets

The private repository must be accessible from the server (for example, add a read-only SSH deploy
key to the GitHub repository before cloning).

```bash
sudo install -d -m 0750 /opt
sudo install -d -o "$USER" -g "$USER" -m 0750 /opt/livocrm
git clone git@github.com:lebiraja/LivoCRM.git /opt/livocrm
cd /opt/livocrm
cp .env.production.example .env
openssl rand -hex 32   # use for POSTGRES_PASSWORD and the matching DATABASE_URL password
openssl rand -hex 32   # use for REDIS_PASSWORD and the matching REDIS_URL password
openssl rand -hex 32   # use for SECRET_KEY
${EDITOR:-nano} .env
chmod 600 .env
install -d -m 0700 .secrets
read -rsp 'Cloudflare Tunnel token: ' TUNNEL_TOKEN; echo
printf '%s' "$TUNNEL_TOKEN" > .secrets/cloudflare_tunnel_token
unset TUNNEL_TOKEN
chmod 600 .secrets/cloudflare_tunnel_token
sudo chown 65532:65532 .secrets/cloudflare_tunnel_token
sudo chmod 400 .secrets/cloudflare_tunnel_token
```

Put the first random value in both `POSTGRES_PASSWORD` and `DATABASE_URL`, and the second in both
`REDIS_PASSWORD` and `REDIS_URL`. They are hex strings, so they do not need URL escaping. Set
`GROQ_API_KEYS` if you want AI responses. Registration is disabled in production; create the first
account through the CLI in the next step. The tunnel token file is owned by UID 65532 because the
official cloudflared image runs as a non-root user. Do not commit `.env` or `.secrets/`.

## 3. Pull, build, and start

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml pull db redis nginx cloudflared
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml build --pull backend frontend
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --wait
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml ps
```

Create your initial user. The CLI prompts for the password without echoing it; use 10–72 UTF-8 bytes.
This creates the default pipeline stages too.

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml exec backend \
  python -m app.cli create-user --email you@example.com --full-name 'Your Name'
```

Open <https://livocrm.lebiraja.in/login> and sign in with that account. Public registration remains
closed. To allow self-registration later, change `ALLOW_REGISTRATION=true` in the backend environment
and recreate the backend; the login page will then show the registration link.

## 4. Update the server later

```bash
cd /opt/livocrm
git pull --ff-only origin main
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml pull db redis nginx cloudflared
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml build --pull backend frontend
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --wait --remove-orphans
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml ps
```

## 5. Health checks, logs, and backups

```bash
curl -fsS https://livocrm.lebiraja.in/api/health
sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml logs --tail=100 backend nginx cloudflared
```

In `ps`, the `PORTS` column should be empty for Nginx, backend, database and Redis. Schedule a local
PostgreSQL backup daily (and copy backups off-server for disaster recovery):

```bash
sudo install -m 0750 cloud/deploy/backup-local.sh /usr/local/sbin/livocrm-backup
sudo crontab -e
```

Add this cron line:

```cron
30 2 * * * /usr/local/sbin/livocrm-backup >> /var/log/livocrm-backup.log 2>&1
```

Backups are root-only and kept for 14 days under `/opt/livocrm/backups`. Copy them to encrypted
off-server storage for disaster recovery. To restore, first stop writes to the
application, then pipe a selected backup into Postgres:

```bash
gunzip -c /opt/livocrm/backups/livocrm-postgres-<UTC_TIMESTAMP>.sql.gz \
  | sudo docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml exec -T db \
      sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Production scope

This is a single-server deployment, not a highly available cluster. Keep the host patched, restrict
SSH to your admin IP or use your provider's console, and keep an off-server backup. Browser sessions
use short-lived HttpOnly, Secure, SameSite=Lax cookies; public registrations are off. API bearer
tokens remain supported for integrations. Password reset, email verification, and MFA are not part
of this app yet.
